# -*- coding: utf-8 -*-
"""仙途 · 文字修仙 — Flask 后端服务器"""
import json
import os
import sys
import argparse
import socket
import time
from datetime import datetime

from flask import Flask, jsonify, request, send_file, send_from_directory

# PyInstaller 打包后资源路径处理
if getattr(sys, 'frozen', False):
    RESOURCE_DIR = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
else:
    RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = RESOURCE_DIR

sys.path.insert(0, RESOURCE_DIR)
from xiantu.engine import (
    ATTR_MIN,
    ATTR_NAMES,
    Game,
    apply_character_setup,
    resolve_choice,
    validate_attrs,
)
from xiantu.story import NODES
from save_manager import (
    delete_save,
    list_saves,
    load_save,
    safe_filename,
    save_game,
    save_path,
    validate_save_payload,
    write_save,
)
from playability import (
    ACHIEVEMENT_HINTS,
    choice_hints,
    destiny_map,
    ensure_gameplay_state,
    get_goal,
    infer_route,
    load_progression,
    mini_game_for,
    PIVOTAL_NODES,
    record_progression,
    score_summary,
)
from achievement_system import AchievementSystem

STATIC_DIR = os.path.join(RESOURCE_DIR, "static")
DATA_DIR = os.path.join(RESOURCE_DIR, "data")
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

# 全局游戏实例（简化：单用户）
games: dict[str, Game] = {}
game_last_seen: dict[str, float] = {}
SESSION_TTL_SECONDS = 60 * 60 * 6
SAVE_DIR = os.environ.get("XIANTU_SAVE_DIR", os.path.join(APP_DIR, "saves"))

# 成就系统实例
achievement_system = AchievementSystem(DATA_DIR)
achievement_system.load_unlocked(SAVE_DIR)


def safe_save_path(filename: str) -> str:
    return save_path(SAVE_DIR, filename)


def error_response(message: str, code: str = "bad_request", status: int = 400):
    return jsonify({"ok": False, "error": message, "code": code}), status


def touch_session(session_id: str) -> None:
    game_last_seen[session_id] = time.time()


def cleanup_sessions() -> None:
    now = time.time()
    expired = [sid for sid, seen_at in game_last_seen.items() if now - seen_at > SESSION_TTL_SECONDS]
    for sid in expired:
        games.pop(sid, None)
        game_last_seen.pop(sid, None)


def get_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"


def get_or_create_game(session_id: str) -> Game:
    cleanup_sessions()
    touch_session(session_id)
    if session_id not in games:
        games[session_id] = Game()
    return games[session_id]


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/new_game", methods=["POST"])
def api_new_game():
    cleanup_sessions()
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = Game()
    ensure_gameplay_state(g)
    g.player_name = str(data.get("name") or "叶尘").strip()[:20] or "叶尘"
    games[sid] = g
    touch_session(sid)
    progression = load_progression(SAVE_DIR)
    return jsonify({
        "ok": True,
        "node": g.current_node,
        "attrs": g.attrs,
        "trait": g.trait,
        "player_name": g.player_name,
        "progression": progression,
        "state": "need_attrs",
    })


@app.route("/api/set_attrs", methods=["POST"])
def api_set_attrs():
    cleanup_sessions()
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return error_response("no game", "no_game")
    touch_session(sid)
    ensure_gameplay_state(g)

    attrs = data.get("attrs", {})
    trait_key = data.get("trait", "1")
    progression = load_progression(SAVE_DIR)
    legacy_bonus = min(10, int(progression.get("legacy_points", 0)))
    try:
        attrs = validate_attrs(attrs)
        apply_character_setup(g, attrs, trait_key, legacy_bonus=legacy_bonus)
    except ValueError as exc:
        message = str(exc)
        if "整数" in message:
            code = "invalid_attr_value"
        elif "超过" in message:
            code = "attrs_overflow"
        elif "低于" in message:
            code = "attr_too_low"
        else:
            code = "invalid_attrs"
        return error_response(message, code)

    return jsonify(get_node_data(g))


@app.route("/api/choice", methods=["POST"])
def api_choice():
    cleanup_sessions()
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return error_response("no game", "no_game")
    touch_session(sid)

    try:
        result = resolve_choice(g, data.get("choice", 0), NODES)
    except ValueError as exc:
        code = str(exc) if str(exc) in {"invalid_choice", "story_target_missing"} else "invalid_choice"
        return error_response("invalid choice" if code == "invalid_choice" else "剧情目标不存在", code)

    data = get_node_data(g)
    data["feedback"] = result["feedback"]
    data["choice_result"] = {"passed": result["passed"], "from": result["from"]}

    # 检查成就
    newly_unlocked = check_and_return_achievements(g, data)
    data["achievements"] = newly_unlocked

    return jsonify(data)


@app.route("/api/state", methods=["POST"])
def api_state():
    cleanup_sessions()
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return error_response("no game", "no_game")
    touch_session(sid)
    return jsonify(get_node_data(g))


@app.route("/api/save", methods=["POST"])
def api_save():
    cleanup_sessions()
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return error_response("no game", "no_game")
    touch_session(sid)

    # 如果指定了 overwrite 文件名，覆盖该文件（不更新时间戳后缀）
    overwrite = data.get("overwrite", "")
    try:
        filename, save_data = save_game(SAVE_DIR, g, NODES, overwrite=overwrite)
    except ValueError as exc:
        return error_response(str(exc), "invalid_filename")
    return jsonify({"ok": True, "filename": filename, "saved_at": save_data["saved_at"]})


@app.route("/api/saves", methods=["GET"])
def api_saves():
    return jsonify(list_saves(SAVE_DIR))


@app.route("/api/load", methods=["POST"])
def api_load():
    cleanup_sessions()
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    filename = data.get("filename", "")

    try:
        d = load_save(SAVE_DIR, filename)
        d = validate_save_payload(d, NODES, ATTR_NAMES)
    except FileNotFoundError:
        return error_response("存档不存在", "save_not_found")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return error_response(str(exc) or "存档格式错误", "invalid_save")

    g = Game()
    g.load_data(d)
    games[sid] = g
    touch_session(sid)

    return jsonify(get_node_data(g))


@app.route("/api/record_ending", methods=["POST"])
def api_record_ending():
    """记录达成的结局到画廊"""
    cleanup_sessions()
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return error_response("no game", "no_game")
    touch_session(sid)
    ensure_gameplay_state(g)

    node = NODES.get(g.current_node, {})
    if node.get("choices"):
        return error_response("当前节点不是结局", "not_ending")
    ending_title = node.get("title", "")

    os.makedirs(SAVE_DIR, exist_ok=True)
    gallery_file = os.path.join(SAVE_DIR, "_gallery.json")
    gallery = read_gallery()
    summary = score_summary(g, ending_title)

    record = {
        "title": ending_title,
        "player_name": g.player_name,
        "trait": g.trait,
        "attrs": g.attrs,
        "path_count": len(g.path_history),
        "score": summary["score"],
        "rank": summary["rank"],
        "achieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 去重：相同结局不重复记录
    existing = [e for e in gallery if isinstance(e, dict) and e.get("title") == ending_title]
    if not existing:
        gallery.append(record)
        with open(gallery_file, "w", encoding="utf-8") as f:
            json.dump(gallery, f, ensure_ascii=False, indent=2)

    leaderboard_file = os.path.join(SAVE_DIR, "_leaderboard.json")
    leaderboard = []
    if os.path.exists(leaderboard_file):
        try:
            with open(leaderboard_file, "r", encoding="utf-8") as f:
                leaderboard = json.load(f)
        except (OSError, json.JSONDecodeError):
            leaderboard = []
    if not isinstance(leaderboard, list):
        leaderboard = []
    cleaned_leaderboard = []
    for item in leaderboard:
        if not isinstance(item, dict):
            continue
        try:
            item = dict(item)
            item["score"] = int(item.get("score", 0))
            item["path_count"] = int(item.get("path_count", 0))
        except (TypeError, ValueError):
            continue
        cleaned_leaderboard.append(item)
    leaderboard = cleaned_leaderboard
    leaderboard.append({
        "player_name": g.player_name,
        "title": ending_title,
        "rank": summary["rank"],
        "score": summary["score"],
        "path_count": len(g.path_history),
        "achieved_at": record["achieved_at"],
    })
    leaderboard.sort(key=lambda item: (-item["score"], item["path_count"]))
    with open(leaderboard_file, "w", encoding="utf-8") as f:
        json.dump(leaderboard[:20], f, ensure_ascii=False, indent=2)

    progression = record_progression(SAVE_DIR, g, ending_title)
    ending_data = get_node_data(g)
    newly_unlocked = check_and_return_achievements(g, ending_data)
    return jsonify({
        "ok": True,
        "total": len(gallery),
        "is_new": not existing,
        "progression": progression,
        "achievements": newly_unlocked,
    })


@app.route("/api/gallery", methods=["GET"])
def api_gallery():
    """获取结局画廊"""
    return jsonify(read_gallery())


@app.route("/api/story_stats", methods=["GET"])
def api_story_stats():
    """返回由当前剧情数据计算出的规模，避免前端写死旧统计。"""

    endings = sum(1 for node in NODES.values() if not node.get("choices"))
    return jsonify({"ok": True, "nodes": len(NODES), "endings": endings})


@app.route("/api/achievements", methods=["GET"])
def api_achievements():
    achievement_system.load_unlocked(SAVE_DIR)
    stats = achievement_system.get_stats()
    return jsonify({
        "achievements": achievement_system.get_all_visible(),
        "endings_count": len(read_gallery()),
        "stats": stats,
    })


@app.route("/api/leaderboard", methods=["GET"])
def api_leaderboard():
    lb_file = os.path.join(SAVE_DIR, "_leaderboard.json")
    if not os.path.exists(lb_file):
        return jsonify([])
    try:
        with open(lb_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data if isinstance(data, list) else [])
    except (OSError, json.JSONDecodeError):
        return jsonify([])


@app.route("/api/fortune", methods=["GET"])
def api_fortune():
    import random
    fortunes = ["大吉", "吉", "中吉", "小吉", "末吉"]
    bonus = {"大吉": 5, "吉": 3, "中吉": 1, "小吉": 0, "末吉": -3}
    f = random.choice(fortunes)
    return jsonify({"fortune": f, "bonus": bonus[f]})


@app.route("/api/restart", methods=["POST"])
def api_restart():
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    # 完全重置游戏状态，回到命名阶段
    if sid in games:
        del games[sid]
    game_last_seen.pop(sid, None)
    return jsonify({"ok": True, "state": "restart"})


@app.route("/api/delete_save", methods=["POST"])
def api_delete_save():
    data = request.get_json() or {}
    filename = data.get("filename", "")
    if delete_save(SAVE_DIR, filename):
        return jsonify({"ok": True})
    return error_response("存档不存在", "save_not_found")


@app.route("/api/export_save/<path:filename>", methods=["GET"])
def api_export_save(filename):
    filepath = safe_save_path(filename)
    if not filepath or not os.path.exists(filepath):
        return error_response("存档不存在", "save_not_found", 404)
    return send_file(filepath, as_attachment=True, download_name=safe_filename(filename))


@app.route("/api/import_save", methods=["POST"])
def api_import_save():
    data = request.get_json(silent=True) or {}
    payload = data.get("save")
    if payload is None and "file" in request.files:
        try:
            payload = json.load(request.files["file"].stream)
        except (OSError, json.JSONDecodeError, TypeError):
            return error_response("存档 JSON 无法解析", "invalid_json")
    if not isinstance(payload, dict):
        return error_response("缺少存档内容", "missing_save")

    try:
        save_data = validate_save_payload(payload, NODES, ATTR_NAMES)
    except ValueError as exc:
        return error_response(str(exc), "invalid_save")

    filename, _ = write_save(SAVE_DIR, save_data)
    return jsonify({"ok": True, "filename": filename, "saved_at": save_data.get("saved_at", "")})


def read_gallery() -> list[dict]:
    gallery_file = os.path.join(SAVE_DIR, "_gallery.json")
    if not os.path.exists(gallery_file):
        return []
    try:
        with open(gallery_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [entry for entry in data if isinstance(entry, dict)] if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


@app.route("/api/progression", methods=["GET"])
def api_progression():
    return jsonify({"ok": True, "progression": load_progression(SAVE_DIR), "achievement_hints": ACHIEVEMENT_HINTS})


def check_and_return_achievements(g: Game, data: dict) -> list[dict]:
    """检查并返回新解锁的成就"""
    ensure_gameplay_state(g)
    achievement_system.load_unlocked(SAVE_DIR)

    # 构建成就检查上下文
    progression = load_progression(SAVE_DIR)
    gallery = read_gallery()

    context = {
        "node_id": g.current_node,
        "attrs": g.attrs,
        "resources": g.resources,
        "artifacts": g.artifacts,
        "reputation": g.reputation,
        "affinity": g.affinity,
        "is_ending": data.get("is_ending", False),
        "route": data.get("route", ""),
        "rank": (data.get("score_summary") or {}).get("rank", "C"),
        "score": (data.get("score_summary") or {}).get("score", 0),
        "path_length": len(g.path_history),
        "ending_count": len(gallery),
        "insights": g.flags.get("insights", []),
        "legacy_points": progression.get("legacy_points", 0),
    }

    # 检查新成就
    newly_unlocked = achievement_system.check_achievements(context)

    # 保存更新后的成就状态
    if newly_unlocked:
        achievement_system.save_unlocked(SAVE_DIR)

    return newly_unlocked


@app.route("/api/achievements_full", methods=["GET"])
def api_achievements_full():
    """获取完整成就列表"""
    achievement_system.load_unlocked(SAVE_DIR)
    achievements = achievement_system.get_all_visible()
    stats = achievement_system.get_stats()
    return jsonify({"ok": True, "achievements": achievements, "stats": stats})


@app.route("/api/destiny_map", methods=["POST"])
def api_destiny_map():
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    current_path = []
    if g:
        current_path = list(g.path_history) + [g.current_node]
    return jsonify({"ok": True, "map": destiny_map(NODES, current_path, read_gallery())})


@app.route("/api/quick_restart", methods=["POST"])
def api_quick_restart():
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    old = games.get(sid)
    if not old:
        return error_response("no game", "no_game")
    ensure_gameplay_state(old)
    g = Game()
    ensure_gameplay_state(g)
    g.player_name = old.player_name or "轮回者"
    g.trait = old.trait
    g.attrs = {k: max(ATTR_MIN, int(v)) for k, v in old.attrs.items()}
    legacy = min(10, int(load_progression(SAVE_DIR).get("legacy_points", 0)))
    g.attrs["幸运"] = g.attrs.get("幸运", 20) + legacy
    g.resources["轮回"] = legacy
    games[sid] = g
    touch_session(sid)
    data = get_node_data(g)
    data["feedback"] = [f"轮回重启：保留角色倾向，幸运获得轮回加成 +{legacy}。"]
    return jsonify(data)


def get_node_data(g: Game) -> dict:
    node = NODES.get(g.current_node)
    if not node:
        return {"error": "node not found"}

    ensure_gameplay_state(g)
    is_ending = len(node.get("choices", [])) == 0
    route = infer_route(g.current_node, node)
    summary = score_summary(g, node.get("title", "")) if is_ending else None

    # 检查是否是关键转折点
    pivot = PIVOTAL_NODES.get(g.current_node)

    return {
        "ok": True,
        "node_id": g.current_node,
        "title": node["title"],
        "text": node["text"],
        "choices": [
            {"index": i, "text": c["text"], "hints": choice_hints(c)}
            for i, c in enumerate(node.get("choices", []))
        ],
        "is_ending": is_ending,
        "attrs": g.attrs,
        "resources": g.resources,
        "artifacts": g.artifacts,
        "inventory": g.inventory,
        "affinity": g.affinity,
        "reputation": g.reputation,
        "trait": g.trait,
        "player_name": g.player_name,
        "goal": get_goal(node["title"]),
        "route": route,
        "mini_game": mini_game_for(g.current_node, node),
        "achievement_hints": ACHIEVEMENT_HINTS,
        "score_summary": summary,
        "pivot": pivot,  # 新增：关键转折点信息
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="仙途 · 文字修仙浏览器版")
    parser.add_argument("--host", default=os.environ.get("XIANTU_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("XIANTU_PORT", "5000")))
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    local_url = f"http://127.0.0.1:{args.port}"
    lan_ip = get_lan_ip()
    lan_url = f"http://{lan_ip}:{args.port}"

    print("╔══════════════════════════════════════╗")
    print("║     ✦ 仙 途 · 文 字 修 仙 ✦        ║")
    print(f"║   本机访问 — {local_url:<23}║")
    if args.host in ("0.0.0.0", "::"):
        print(f"║   手机访问 — {lan_url:<23}║")
    print("║   按 Ctrl+C 退出                    ║")
    print("╚══════════════════════════════════════╝")

    if not args.no_browser:
        import webbrowser
        webbrowser.open(local_url)

    app.run(host=args.host, port=args.port, debug=False)
