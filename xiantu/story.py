"""外置剧情数据加载器。

剧情只保留一份规范来源：``data/story_nodes.json``。过去 ``game.py``
还内嵌了一份旧副本，容易出现桌面端、Web 端和编辑器读取不同剧情的情况。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import story_file


def load_nodes(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """加载并做最小格式校验，错误在启动时尽早暴露。"""

    target = Path(path) if path else story_file()
    try:
        with target.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except FileNotFoundError as exc:
        raise RuntimeError(f"找不到剧情文件: {target}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"剧情 JSON 无法解析: {target}: {exc}") from exc

    if not isinstance(data, dict) or not data:
        raise RuntimeError(f"剧情文件必须是非空对象: {target}")
    if "start" not in data:
        raise RuntimeError(f"剧情文件缺少 start 节点: {target}")
    return data


NODES = load_nodes()
