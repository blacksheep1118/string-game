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
from game import Game, NODES, ATTR_NAMES, TRAITS, ATTR_TOTAL, ATTR_MIN, create_character
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

STATIC_DIR = os.path.join(RESOURCE_DIR, "static")
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

# 全局游戏实例（简化：单用户）
games: dict[str, Game] = {}
game_last_seen: dict[str, float] = {}
SESSION_TTL_SECONDS = 60 * 60 * 6
SAVE_DIR = os.path.join(APP_DIR, "saves")


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
    g.player_name = data.get("name", "叶尘")
    games[sid] = g
    touch_session(sid)
    return jsonify({
        "ok": True,
        "node": g.current_node,
        "attrs": g.attrs,
        "trait": g.trait,
        "player_name": g.player_name,
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

    attrs = data.get("attrs", {})
    trait_key = data.get("trait", "1")
    if not isinstance(attrs, dict):
        return error_response("属性格式错误", "invalid_attrs")
    try:
        attrs = {k: int(attrs.get(k, ATTR_MIN)) for k in ATTR_NAMES}
    except (TypeError, ValueError):
        return error_response("属性必须是整数", "invalid_attr_value")

    # 验证属性总和
    total = sum(attrs.get(k, 0) for k in ATTR_NAMES)
    if total > ATTR_TOTAL:
        return error_response(f"属性总和超过{ATTR_TOTAL}", "attrs_overflow")

    for k in ATTR_NAMES:
        if attrs.get(k, ATTR_MIN) < ATTR_MIN:
            return error_response(f"{k}不能低于{ATTR_MIN}", "attr_too_low")

    # 补齐默认值
    for k in ATTR_NAMES:
        attrs[k] = attrs.get(k, ATTR_MIN)

    # 应用词条
    if trait_key in TRAITS:
        g.trait = TRAITS[trait_key]["name"]
        for name, bonus in TRAITS[trait_key]["bonus"].items():
            attrs[name] = attrs.get(name, 0) + bonus

    g.attrs = attrs
    g.current_node = "start"

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
        choice_idx = int(data.get("choice", 0))
    except (TypeError, ValueError):
        return error_response("invalid choice", "invalid_choice")
    node = NODES.get(g.current_node)
    if not node or choice_idx < 0 or choice_idx >= len(node.get("choices", [])):
        return error_response("invalid choice", "invalid_choice")

    g.path_history.append(g.current_node)

    choice = node["choices"][choice_idx]

    # 应用属性加成
    effect = choice.get("effect", {})
    for attr, delta in effect.items():
        if attr in g.attrs:
            g.attrs[attr] += delta

    # 检查要求
    req = choice.get("require", {})
    if req:
        met = all(g.attrs.get(k, 0) >= v for k, v in req.items())
        if not met and "fail" in choice:
            g.current_node = choice["fail"]
            return jsonify(get_node_data(g))

    g.current_node = choice.get("next", g.current_node)
    return jsonify(get_node_data(g))


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
    except FileNotFoundError:
        return error_response("存档不存在", "save_not_found")

    g = Game()
    g.player_name = d.get("player_name", "叶尘")
    g.current_node = d.get("current_node", "start")
    g.path_history = d.get("path_history", [])
    g.attrs = d.get("attrs", {k: 20 for k in ATTR_NAMES})
    g.trait = d.get("trait", "")
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

    node = NODES.get(g.current_node, {})
    ending_title = node.get("title", "")

    os.makedirs(SAVE_DIR, exist_ok=True)
    gallery_file = os.path.join(SAVE_DIR, "_gallery.json")
    gallery = []
    if os.path.exists(gallery_file):
        with open(gallery_file, "r", encoding="utf-8") as f:
            gallery = json.load(f)

    record = {
        "title": ending_title,
        "player_name": g.player_name,
        "trait": g.trait,
        "attrs": g.attrs,
        "path_count": len(g.path_history),
        "achieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 去重：相同结局不重复记录
    existing = [e for e in gallery if e["title"] == ending_title]
    if not existing:
        gallery.append(record)
        with open(gallery_file, "w", encoding="utf-8") as f:
            json.dump(gallery, f, ensure_ascii=False, indent=2)

    return jsonify({"ok": True, "total": len(gallery), "is_new": not existing})


@app.route("/api/gallery", methods=["GET"])
def api_gallery():
    """获取结局画廊"""
    gallery_file = os.path.join(SAVE_DIR, "_gallery.json")
    if not os.path.exists(gallery_file):
        return jsonify([])
    with open(gallery_file, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/api/achievements", methods=["GET"])
def api_achievements():
    pf = os.path.join(SAVE_DIR, "_persist.json")
    if not os.path.exists(pf):
        return jsonify({"achievements": [], "endings_count": 0})
    with open(pf, "r", encoding="utf-8") as f:
        d = json.load(f)
    return jsonify({"achievements": d.get("achievements", []), "endings_count": d.get("endings_count", 0)})


@app.route("/api/leaderboard", methods=["GET"])
def api_leaderboard():
    lb_file = os.path.join(SAVE_DIR, "_leaderboard.json")
    if not os.path.exists(lb_file):
        return jsonify([])
    with open(lb_file, "r", encoding="utf-8") as f:
        return jsonify(json.load(f))


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
        except json.JSONDecodeError:
            return error_response("存档 JSON 无法解析", "invalid_json")
    if not isinstance(payload, dict):
        return error_response("缺少存档内容", "missing_save")

    try:
        save_data = validate_save_payload(payload, NODES, ATTR_NAMES)
    except ValueError as exc:
        return error_response(str(exc), "invalid_save")

    filename, _ = write_save(SAVE_DIR, save_data)
    return jsonify({"ok": True, "filename": filename, "saved_at": save_data.get("saved_at", "")})


def get_node_data(g: Game) -> dict:
    node = NODES.get(g.current_node)
    if not node:
        return {"error": "node not found"}

    is_ending = len(node.get("choices", [])) == 0

    return {
        "ok": True,
        "node_id": g.current_node,
        "title": node["title"],
        "text": node["text"],
        "choices": [
            {"index": i, "text": c["text"]}
            for i, c in enumerate(node.get("choices", []))
        ],
        "is_ending": is_ending,
        "attrs": g.attrs,
        "trait": g.trait,
        "player_name": g.player_name,
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
