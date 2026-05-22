# -*- coding: utf-8 -*-
"""仙途 · 文字修仙 — Flask 后端服务器"""
import json
import os
import sys
from datetime import datetime

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game import Game, NODES, ATTR_NAMES, TRAITS, ATTR_TOTAL, ATTR_MIN, create_character

app = Flask(__name__, static_folder="static", static_url_path="")

# 全局游戏实例（简化：单用户）
games: dict[str, Game] = {}
SAVE_DIR = "saves"


def get_or_create_game(session_id: str) -> Game:
    if session_id not in games:
        games[session_id] = Game()
    return games[session_id]


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/new_game", methods=["POST"])
def api_new_game():
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = Game()
    g.player_name = data.get("name", "叶尘")
    games[sid] = g
    return jsonify({
        "node": g.current_node,
        "attrs": g.attrs,
        "trait": g.trait,
        "player_name": g.player_name,
        "state": "need_attrs",
    })


@app.route("/api/set_attrs", methods=["POST"])
def api_set_attrs():
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return jsonify({"error": "no game"}), 400

    attrs = data.get("attrs", {})
    trait_key = data.get("trait", "1")

    # 验证属性总和
    total = sum(attrs.get(k, 0) for k in ATTR_NAMES)
    if total > ATTR_TOTAL:
        return jsonify({"error": f"属性总和超过{ATTR_TOTAL}"}), 400

    for k in ATTR_NAMES:
        if attrs.get(k, ATTR_MIN) < ATTR_MIN:
            return jsonify({"error": f"{k}不能低于{ATTR_MIN}"}), 400

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
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return jsonify({"error": "no game"}), 400

    choice_idx = data.get("choice", 0)
    node = NODES.get(g.current_node)
    if not node or choice_idx >= len(node.get("choices", [])):
        return jsonify({"error": "invalid choice"}), 400

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
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return jsonify({"error": "no game"}), 400
    return jsonify(get_node_data(g))


@app.route("/api/save", methods=["POST"])
def api_save():
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    g = games.get(sid)
    if not g:
        return jsonify({"error": "no game"}), 400

    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    save_data = {
        "player_name": g.player_name,
        "current_node": g.current_node,
        "path_history": g.path_history,
        "attrs": g.attrs,
        "trait": g.trait,
        "title": NODES[g.current_node]["title"],
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 如果指定了 overwrite 文件名，覆盖该文件（不更新时间戳后缀）
    overwrite = data.get("overwrite", "")
    if overwrite:
        filepath = os.path.join(SAVE_DIR, overwrite)
    else:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        filename = f"save_{ts}.json"
        filepath = os.path.join(SAVE_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    basename = os.path.basename(filepath)
    return jsonify({"ok": True, "filename": basename, "saved_at": save_data["saved_at"]})


@app.route("/api/saves", methods=["GET"])
def api_saves():
    if not os.path.exists(SAVE_DIR):
        return jsonify([])

    saves = []
    for f in sorted(os.listdir(SAVE_DIR), reverse=True):
        if f.endswith(".json"):
            filepath = os.path.join(SAVE_DIR, f)
            try:
                with open(filepath, "r", encoding="utf-8") as fp:
                    d = json.load(fp)
                saves.append({
                    "filename": f,
                    "name": d.get("player_name", "未知"),
                    "title": d.get("title", "未知"),
                    "saved_at": d.get("saved_at", "未知"),
                })
            except (json.JSONDecodeError, KeyError):
                pass
    return jsonify(saves)


@app.route("/api/load", methods=["POST"])
def api_load():
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    filename = data.get("filename", "")

    filepath = os.path.join(SAVE_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "存档不存在"}), 400

    with open(filepath, "r", encoding="utf-8") as f:
        d = json.load(f)

    g = Game()
    g.player_name = d.get("player_name", "叶尘")
    g.current_node = d.get("current_node", "start")
    g.path_history = d.get("path_history", [])
    g.attrs = d.get("attrs", {k: 20 for k in ATTR_NAMES})
    g.trait = d.get("trait", "")
    games[sid] = g

    return jsonify(get_node_data(g))


@app.route("/api/restart", methods=["POST"])
def api_restart():
    data = request.get_json() or {}
    sid = data.get("session_id", "default")
    # 完全重置游戏状态，回到命名阶段
    if sid in games:
        del games[sid]
    return jsonify({"state": "restart"})


@app.route("/api/delete_save", methods=["POST"])
def api_delete_save():
    data = request.get_json() or {}
    filename = data.get("filename", "")
    filepath = os.path.join(SAVE_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"ok": True})
    return jsonify({"error": "存档不存在"}), 400


def get_node_data(g: Game) -> dict:
    node = NODES.get(g.current_node)
    if not node:
        return {"error": "node not found"}

    is_ending = len(node.get("choices", [])) == 0

    return {
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
    print("╔══════════════════════════════════════╗")
    print("║     ✦ 仙 途 · 文 字 修 仙 ✦        ║")
    print("║   浏览器版本 — http://127.0.0.1:5000  ║")
    print("╚══════════════════════════════════════╝")
    app.run(host="127.0.0.1", port=5000, debug=False)
