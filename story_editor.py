# -*- coding: utf-8 -*-
"""Small command-line story editor for external node JSON."""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

from story_tools import validate_nodes


def read_nodes(path: str) -> dict[str, dict[str, Any]]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    from game import NODES
    return NODES


def write_nodes(path: str, nodes: dict[str, dict[str, Any]]) -> None:
    output_dir = os.path.dirname(path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="仙途剧情 JSON 编辑器")
    parser.add_argument("--file", default=os.path.join("data", "story_nodes.json"))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="列出节点")

    show = sub.add_parser("show", help="查看节点")
    show.add_argument("node_id")

    set_text = sub.add_parser("set-text", help="更新节点正文")
    set_text.add_argument("node_id")
    set_text.add_argument("text")

    set_title = sub.add_parser("set-title", help="更新节点标题")
    set_title.add_argument("node_id")
    set_title.add_argument("title")

    validate = sub.add_parser("validate", help="校验剧情")
    validate.set_defaults(validate_only=True)

    args = parser.parse_args()
    nodes = read_nodes(args.file)

    if args.command == "list":
        for node_id, node in nodes.items():
            print(f"{node_id}\t{node.get('title', '')}")
        return 0

    if args.command == "show":
        node = nodes.get(args.node_id)
        if not node:
            print("节点不存在")
            return 1
        print(json.dumps(node, ensure_ascii=False, indent=2))
        return 0

    if args.command in {"set-text", "set-title"}:
        node = nodes.get(args.node_id)
        if not node:
            print("节点不存在")
            return 1
        if args.command == "set-text":
            node["text"] = args.text
        else:
            node["title"] = args.title
        write_nodes(args.file, nodes)
        print(f"已更新 {args.node_id}")
        return 0

    errors = validate_nodes(nodes)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1
    print(f"剧情校验通过，共 {len(nodes)} 个节点。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
