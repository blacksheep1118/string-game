# -*- coding: utf-8 -*-
"""仙途 · 文字修仙 — Flask 后端服务器"""
import json
import os
import sys
import argparse
import re
import socket
import threading
import time

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
    BONUS_ENDING_TEXT,
    BONUS_ENDING_TITLE,
    bonus_ending_available,
    choice_hints,
    destiny_map,
    ensure_gameplay_state,
    get_goal,
    infer_route,
    load_progression,
    mini_game_for,
    PIVOTAL_NODES,
    check_achievements,
    daily_fortune,
    quick_restart_game,
    record_ending,
    record_bonus_ending,
    read_progress_records,
    resolve_mini_game,
    score_summary,
    update_progression,
)
from achievement_system import AchievementSystem

STATIC_DIR = os.path.join(RESOURCE_DIR, "static")
DATA_DIR = os.path.join(RESOURCE_DIR, "data")
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

# 全局游戏实例（简化：单用户）
games: dict[str, Game] = {}
game_last_seen: dict[str, float] = {}
SESSION_TTL_SECONDS = 60 * 60 * 6
MAX_SESSIONS = 512
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
GAME_LOCK = threading.RLock()
SAVE_DIR = os.environ.get("XIANTU_SAVE_DIR", os.path.join(APP_DIR, "saves"))
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

# 成就系统实例
achievement_system = AchievementSystem(DATA_DIR)
achievement_system.load_unlocked(SAVE_DIR)


def safe_save_path(filename: str) -> str:
    return save_path(SAVE_DIR, filename)


def error_response(message: str, code: str = "bad_request", status: int = 400):
    return jsonify({"ok": False, "error": message, "code": code}), status


SESSION_ROUTES = {
    "/api/new_game",
    "/api/set_attrs",
    "/api/choice",
    "/api/state",
    "/api/save",
    "/api/load",
    "/api/record_ending",
    "/api/bonus_ending",
    "/api/restart",
    "/api/destiny_map",
    "/api/quick_restart",
    "/api/progression_event",
    "/api/mini_game",
}


def is_valid_session_id(value: object) -> bool:
    return isinstance(value, str) and bool(SESSION_ID_RE.fullmatch(value))


@app.before_request
def validate_api_request():
    """在进入路由前拒绝非对象 JSON 和危险 session key。"""

    if request.path not in SESSION_ROUTES:
        if request.path == "/api/gallery":
            sid = request.args.get("session_id", "")
            if sid and not is_valid_session_id(sid):
                return error_response("session_id 格式无效", "invalid_session", 400)
        return None
    if request.method != "POST":
        return None
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("请求 JSON 必须是对象", "invalid_json", 400)
    if not is_valid_session_id(payload.get("session_id", "default")):
        return error_response("session_id 格式无效", "invalid_session", 400)
    return None


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
    if sid not in games and len(games) >= MAX_SESSIONS:
        return error_response("当前在线游戏数量已达上限", "session_limit", 429)
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
    _, fortune_bonus = daily_fortune()
    try:
        attrs = validate_attrs(attrs)
        apply_character_setup(g, attrs, trait_key, fortune_bonus=fortune_bonus, legacy_bonus=legacy_bonus)
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

    node_data = get_node_data(g)
    node_data["achievements"] = check_and_return_achievements(g, node_data)
    return jsonify(node_data)


@app.route("/api/choice", methods=["POST"])
def api_choice():
    cleanup_sessions()
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return error_response("no game", "no_game")
    touch_session(sid)

    if not g.trait:
        return error_response("请先完成角色属性与词条设置", "setup_required", 409)
    with GAME_LOCK:
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
        # 首次打开 Web 页面时，前端会探测是否存在可恢复的当前局。
        # “还没有当前局”是正常状态，不应让浏览器控制台出现 400 错误。
        return jsonify({"ok": True, "state": "need_new_game", "node_id": "start", "trait": ""})
    touch_session(sid)
    return jsonify(get_node_data(g))


@app.route("/api/mini_game", methods=["POST"])
def api_mini_game():
    """执行当前节点的一次路线试炼，规则与终端入口共享。"""

    cleanup_sessions()
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return error_response("no game", "no_game")
    if not g.trait:
        return error_response("请先完成角色属性与词条设置", "setup_required", 409)
    touch_session(sid)
    with GAME_LOCK:
        try:
            feedback = resolve_mini_game(g, g.current_node, str(data.get("action", "")))
        except ValueError as exc:
            code = str(exc)
            if code not in {"mini_game_node_mismatch", "invalid_mini_game_action", "mini_game_completed"}:
                code = "invalid_mini_game"
            return error_response(code, code)
        node_data = get_node_data(g)
        node_data["feedback"] = feedback
        node_data["achievements"] = check_and_return_achievements(g, node_data)
        return jsonify(node_data)


@app.route("/api/save", methods=["POST"])
def api_save():
    cleanup_sessions()
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return error_response("no game", "no_game")
    if not g.trait:
        return error_response("请先完成角色属性与词条设置", "setup_required", 409)
    touch_session(sid)

    # 如果指定了 overwrite 文件名，覆盖该文件（不更新时间戳后缀）
    overwrite = data.get("overwrite", "")
    with GAME_LOCK:
        try:
            filename, save_data = save_game(SAVE_DIR, g, NODES, overwrite=overwrite)
        except ValueError as exc:
            return error_response(str(exc), "invalid_filename")
        update_progression(SAVE_DIR, increments={"save_count": 1})
        achievements = check_and_return_achievements(g, get_node_data(g))
        return jsonify({
            "ok": True,
            "filename": filename,
            "saved_at": save_data["saved_at"],
            "achievements": achievements,
        })


@app.route("/api/saves", methods=["GET"])
def api_saves():
    return jsonify(list_saves(SAVE_DIR))


@app.route("/api/load", methods=["POST"])
def api_load():
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    filename = data.get("filename", "")

    with GAME_LOCK:
        cleanup_sessions()
        if sid not in games and len(games) >= MAX_SESSIONS:
            return error_response("当前在线游戏数量已达上限", "session_limit", 429)
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
    with GAME_LOCK:
        ensure_gameplay_state(g)
        try:
            settlement = record_ending(SAVE_DIR, g, NODES)
        except ValueError as exc:
            return error_response(str(exc), "not_ending")

        newly_unlocked = check_and_return_achievements(g, get_node_data(g))
        return jsonify({
            "ok": True,
            "total": len(settlement["gallery"]),
            "is_new": settlement["is_new"],
            "progression": settlement["progression"],
            "score_summary": settlement["summary"],
            "bonus_available": bonus_ending_available(SAVE_DIR, NODES),
            "achievements": newly_unlocked,
        })


@app.route("/api/bonus_ending", methods=["POST"])
def api_bonus_ending():
    """在收集全部普通结局后记录一次隐藏结局。"""

    cleanup_sessions()
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return error_response("no game", "no_game")
    if not g.trait:
        return error_response("请先完成角色属性与词条设置", "setup_required", 409)
    touch_session(sid)
    with GAME_LOCK:
        try:
            settlement = record_bonus_ending(SAVE_DIR, g, NODES)
        except ValueError as exc:
            code = str(exc)
            if code not in {"bonus_locked", "bonus_completed"}:
                code = "bonus_unavailable"
            return error_response(code, code)
        payload = get_bonus_node_data(g)
        payload["feedback"] = ["你已收集全部普通结局，隐藏命运向你敞开。"]
        payload["achievements"] = check_and_return_achievements(g, payload)
        payload["settlement"] = settlement["summary"]
        return jsonify(payload)


@app.route("/api/gallery", methods=["GET"])
def api_gallery():
    """获取结局画廊"""
    sid = request.args.get("session_id", "")
    if sid and sid in games:
        update_progression(SAVE_DIR, flags={"viewed_gallery": True})
        check_and_return_achievements(games[sid], get_node_data(games[sid]))
    return jsonify(read_gallery())


@app.route("/api/story_stats", methods=["GET"])
def api_story_stats():
    """返回由当前剧情数据计算出的规模，避免前端写死旧统计。"""

    endings = sum(1 for node in NODES.values() if not node.get("choices"))
    return jsonify({
        "ok": True,
        "nodes": len(NODES),
        "endings": endings,
        "bonus_endings": 1,
        "total_endings": endings + 1,
    })


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
    fortune, bonus = daily_fortune()
    return jsonify({"fortune": fortune, "bonus": bonus})


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
    return read_progress_records(SAVE_DIR, "_gallery.json")


@app.route("/api/progression", methods=["GET"])
def api_progression():
    return jsonify({"ok": True, "progression": load_progression(SAVE_DIR), "achievement_hints": ACHIEVEMENT_HINTS})


@app.route("/api/progression_event", methods=["POST"])
def api_progression_event():
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    event = data.get("event", "")
    if event not in {"changed_settings"}:
        return error_response("不支持的进度事件", "invalid_event")
    progression = update_progression(SAVE_DIR, flags={event: True})
    achievements = []
    game = games.get(sid)
    if game:
        achievements = check_and_return_achievements(game, get_node_data(game))
    return jsonify({"ok": True, "progression": progression, "achievements": achievements})


def check_and_return_achievements(g: Game, data: dict) -> list[dict]:
    """检查并返回新解锁的成就"""
    del data  # 结算上下文由共享层从节点和状态重新计算，避免入口间漂移。
    if not g.trait and NODES.get(g.current_node, {}).get("choices"):
        return []
    return check_achievements(SAVE_DIR, DATA_DIR, g, NODES)


@app.route("/api/achievements_full", methods=["GET"])
def api_achievements_full():
    """获取完整成就列表"""
    sid = request.args.get("session_id", "")
    if sid and sid in games:
        check_and_return_achievements(games[sid], get_node_data(games[sid]))
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
        update_progression(SAVE_DIR, flags={"viewed_destiny_map": True})
        achievements = check_and_return_achievements(g, get_node_data(g))
    else:
        achievements = []
    return jsonify({
        "ok": True,
        "map": destiny_map(NODES, current_path, read_gallery()),
        "achievements": achievements,
    })


@app.route("/api/quick_restart", methods=["POST"])
def api_quick_restart():
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    old = games.get(sid)
    if not old:
        return error_response("no game", "no_game")
    if not old.trait:
        return error_response("请先完成角色属性与词条设置", "setup_required", 409)
    with GAME_LOCK:
        g, legacy = quick_restart_game(old, SAVE_DIR)
        games[sid] = g
        touch_session(sid)
        data = get_node_data(g)
        data["feedback"] = [f"轮回重启：保留角色倾向，幸运获得轮回加成 +{legacy}。"]
        data["achievements"] = check_and_return_achievements(g, data)
        return jsonify(data)


def get_node_data(g: Game) -> dict:
    node = NODES.get(g.current_node)
    if not node:
        return {"error": "node not found"}

    ensure_gameplay_state(g)
    is_ending = len(node.get("choices", [])) == 0
    route = infer_route(g.current_node, node)
    summary = score_summary(g, node.get("title", "")) if is_ending else None
    fortune, fortune_bonus = daily_fortune()

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
        "mini_game": mini_game_for(g.current_node, node, g),
        "achievement_hints": ACHIEVEMENT_HINTS,
        "score_summary": summary,
        "fortune": fortune,
        "fortune_bonus": fortune_bonus,
        "bonus_available": bonus_ending_available(SAVE_DIR, NODES),
        "bonus_unlocked": BONUS_ENDING_TITLE in {
            entry.get("title", "") for entry in read_gallery()
        },
        "pivot": pivot,  # 新增：关键转折点信息
    }


def get_bonus_node_data(g: Game) -> dict:
    fortune, fortune_bonus = daily_fortune()
    return {
        "ok": True,
        "node_id": "bonus_ending",
        "title": BONUS_ENDING_TITLE,
        "text": BONUS_ENDING_TEXT,
        "choices": [],
        "is_ending": True,
        "attrs": g.attrs,
        "resources": g.resources,
        "artifacts": g.artifacts,
        "inventory": g.inventory,
        "affinity": g.affinity,
        "reputation": g.reputation,
        "trait": g.trait,
        "player_name": g.player_name,
        "goal": "见证全部命运分支，完成隐藏结算。",
        "route": "天命",
        "mini_game": None,
        "achievement_hints": ACHIEVEMENT_HINTS,
        "score_summary": score_summary(g, BONUS_ENDING_TITLE),
        "fortune": fortune,
        "fortune_bonus": fortune_bonus,
        "bonus_available": False,
        "bonus_unlocked": True,
        "bonus_ending": True,
        "pivot": None,
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
