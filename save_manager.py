# -*- coding: utf-8 -*-
"""Shared save-file utilities for all game frontends."""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from typing import Any

SCHEMA_VERSION = 2
SAVE_PREFIX = "save_"
SAFE_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$")


def ensure_save_dir(save_dir: str) -> None:
    os.makedirs(save_dir, exist_ok=True)


def safe_filename(filename: str) -> str:
    if not isinstance(filename, str):
        return ""
    basename = os.path.basename(filename or "")
    if basename in {"", ".", ".."} or basename.startswith("_"):
        return ""
    return basename if SAFE_FILENAME_RE.fullmatch(basename) else ""


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
    if not isinstance(data, dict):
        raise ValueError("存档必须是 JSON 对象")
    migrated = dict(data)
    migrated.setdefault("schema_version", 1)
    migrated.setdefault("player_name", "叶尘")
    migrated.setdefault("current_node", "start")
    migrated.setdefault("path_history", [])
    migrated.setdefault("attrs", {})
    migrated.setdefault("trait", "")
    migrated.setdefault("artifacts", [])
    migrated.setdefault("inventory", [])
    migrated.setdefault("affinity", {})
    migrated.setdefault("reputation", {"正道": 0, "魔道": 0, "散修": 0})
    migrated.setdefault("resources", {"灵石": 0, "心魔": 0, "历练": 0, "丹药": 0, "轮回": 0})
    migrated.setdefault("flags", {})
    migrated.setdefault("rng_state", None)
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
        "artifacts": list(getattr(game, "artifacts", [])),
        "inventory": list(getattr(game, "inventory", [])),
        "affinity": dict(getattr(game, "affinity", {})),
        "reputation": dict(getattr(game, "reputation", {})),
        "resources": dict(getattr(game, "resources", {})),
        "flags": dict(getattr(game, "flags", {})),
        "rng_state": getattr(game, "rng", None).getstate() if getattr(game, "rng", None) else None,
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
    payload = json.dumps(migrate_save(data), ensure_ascii=False, indent=2)
    fd, temporary = tempfile.mkstemp(prefix=".save-", suffix=".tmp", dir=save_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, filepath)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
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
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
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
    try:
        data = migrate_save(payload)
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc)) from exc
    if not isinstance(data["current_node"], str) or data["current_node"] not in nodes:
        raise ValueError("存档节点不存在")
    if not isinstance(data.get("player_name"), str) or len(data["player_name"]) > 40:
        raise ValueError("存档角色名格式错误")
    if not isinstance(data.get("trait"), str) or len(data["trait"]) > 80:
        raise ValueError("存档词条格式错误")
    attrs = data.get("attrs", {})
    if not isinstance(attrs, dict):
        raise ValueError("存档属性格式错误")
    unknown_attrs = sorted(set(attrs) - set(attr_names))
    if unknown_attrs:
        raise ValueError(f"存档包含未知属性: {', '.join(unknown_attrs)}")
    for name in attr_names:
        try:
            if isinstance(attrs.get(name), bool):
                raise ValueError
            attrs[name] = int(attrs.get(name, 20))
        except (TypeError, ValueError):
            raise ValueError(f"{name}属性必须是整数")
        if attrs[name] < 0 or attrs[name] > 999:
            raise ValueError(f"{name}属性超出存档范围")
    if sum(attrs.values()) > 5000:
        raise ValueError("存档属性总和超出范围")
    data["attrs"] = attrs
    if not isinstance(data.get("path_history"), list) or len(data["path_history"]) > 10000:
        raise ValueError("存档路径格式错误")
    if any(not isinstance(node_id, str) or len(node_id) > 200 for node_id in data["path_history"]):
        raise ValueError("存档路径格式错误")
    unknown_history = [node_id for node_id in data["path_history"] if node_id not in nodes]
    if unknown_history:
        raise ValueError("存档路径包含不存在节点")
    for key in ("resources", "reputation", "affinity", "flags"):
        if not isinstance(data.get(key), dict):
            raise ValueError(f"存档字段 {key} 格式错误")
    for key in ("artifacts", "inventory"):
        values = data.get(key)
        if not isinstance(values, list) or len(values) > 200:
            raise ValueError(f"存档字段 {key} 格式错误")
        if any(not isinstance(value, str) or len(value) > 120 for value in values):
            raise ValueError(f"存档字段 {key} 格式错误")
    for key in ("resources", "reputation", "affinity"):
        values = data[key]
        if len(values) > 100 or any(not isinstance(name, str) or len(name) > 80 for name in values):
            raise ValueError(f"存档字段 {key} 格式错误")
        for name, value in values.items():
            if isinstance(value, bool):
                raise ValueError(f"存档字段 {key} 格式错误")
            try:
                values[name] = int(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"存档字段 {key} 格式错误") from exc
    flags = data["flags"]
    if len(flags) > 100 or any(not isinstance(name, str) or len(name) > 80 for name in flags):
        raise ValueError("存档字段 flags 格式错误")
    for name, value in flags.items():
        if isinstance(value, list):
            if len(value) > 500 or any(not isinstance(item, str) or len(item) > 200 for item in value):
                raise ValueError("存档字段 flags 格式错误")
        elif isinstance(value, dict):
            if name != "initial_attrs" or len(value) > 20:
                raise ValueError("存档字段 flags 格式错误")
            for attr_name, attr_value in value.items():
                if not isinstance(attr_name, str) or len(attr_name) > 80:
                    raise ValueError("存档字段 flags 格式错误")
                try:
                    numeric_value = int(attr_value)
                except (TypeError, ValueError) as exc:
                    raise ValueError("存档字段 flags 格式错误") from exc
                if numeric_value < 0 or numeric_value > 999:
                    raise ValueError("存档字段 flags 格式错误")
                value[attr_name] = numeric_value
        elif isinstance(value, (tuple, set)):
            raise ValueError("存档字段 flags 格式错误")
    rng_state = data.get("rng_state")
    if rng_state is not None and not isinstance(rng_state, (list, tuple)):
        raise ValueError("存档随机状态格式错误")
    return data
