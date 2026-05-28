# -*- coding: utf-8 -*-
"""Shared save-file utilities for all game frontends."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

SCHEMA_VERSION = 2
SAVE_PREFIX = "save_"


def ensure_save_dir(save_dir: str) -> None:
    os.makedirs(save_dir, exist_ok=True)


def safe_filename(filename: str) -> str:
    basename = os.path.basename(filename or "")
    if basename.startswith("_"):
        return ""
    return basename


def save_path(save_dir: str, filename: str) -> str:
    basename = safe_filename(filename)
    if not basename:
        return ""
    return os.path.join(save_dir, basename)


def now_label() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_save_filename() -> str:
    return f"{SAVE_PREFIX}{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"


def migrate_save(data: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(data)
    migrated.setdefault("schema_version", 1)
    migrated.setdefault("player_name", "叶尘")
    migrated.setdefault("current_node", "start")
    migrated.setdefault("path_history", [])
    migrated.setdefault("attrs", {})
    migrated.setdefault("trait", "")
    migrated.setdefault("title", "")
    migrated.setdefault("saved_at", "未知")
    migrated["schema_version"] = SCHEMA_VERSION
    return migrated


def build_save_data(game: Any, nodes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    node = nodes.get(game.current_node, {})
    return {
        "schema_version": SCHEMA_VERSION,
        "player_name": game.player_name,
        "current_node": game.current_node,
        "path_history": list(game.path_history),
        "attrs": dict(game.attrs),
        "trait": game.trait,
        "title": node.get("title", ""),
        "saved_at": now_label(),
    }


def write_save(save_dir: str, data: dict[str, Any], overwrite: str = "") -> tuple[str, str]:
    ensure_save_dir(save_dir)
    filename = safe_filename(overwrite) if overwrite else new_save_filename()
    if not filename:
        raise ValueError("存档文件名无效")
    if not filename.endswith(".json"):
        filename = f"{filename}.json"
    filepath = save_path(save_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(migrate_save(data), f, ensure_ascii=False, indent=2)
    return filename, filepath


def save_game(save_dir: str, game: Any, nodes: dict[str, dict[str, Any]], overwrite: str = "") -> tuple[str, dict[str, Any]]:
    data = build_save_data(game, nodes)
    filename, _ = write_save(save_dir, data, overwrite=overwrite)
    return filename, data


def load_save(save_dir: str, filename: str) -> dict[str, Any]:
    filepath = save_path(save_dir, filename)
    if not filepath or not os.path.exists(filepath):
        raise FileNotFoundError("存档不存在")
    with open(filepath, "r", encoding="utf-8") as f:
        return migrate_save(json.load(f))


def list_saves(save_dir: str) -> list[dict[str, Any]]:
    if not os.path.exists(save_dir):
        return []
    saves: list[dict[str, Any]] = []
    for filename in sorted(os.listdir(save_dir), reverse=True):
        if not filename.endswith(".json") or filename.startswith("_"):
            continue
        try:
            data = load_save(save_dir, filename)
        except (json.JSONDecodeError, OSError):
            continue
        saves.append({
            "filename": filename,
            "name": data.get("player_name", "未知"),
            "title": data.get("title", "未知"),
            "saved_at": data.get("saved_at", "未知"),
            "schema_version": data.get("schema_version", 1),
        })
    return saves


def delete_save(save_dir: str, filename: str) -> bool:
    filepath = save_path(save_dir, filename)
    if filepath and os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def validate_save_payload(payload: dict[str, Any], nodes: dict[str, Any], attr_names: list[str]) -> dict[str, Any]:
    data = migrate_save(payload)
    if data["current_node"] not in nodes:
        raise ValueError("存档节点不存在")
    attrs = data.get("attrs", {})
    if not isinstance(attrs, dict):
        raise ValueError("存档属性格式错误")
    for name in attr_names:
        try:
            attrs[name] = int(attrs.get(name, 20))
        except (TypeError, ValueError):
            raise ValueError(f"{name}属性必须是整数")
    data["attrs"] = attrs
    if not isinstance(data.get("path_history"), list):
        data["path_history"] = []
    return data
