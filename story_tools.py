# -*- coding: utf-8 -*-
"""Utilities for validating and exporting story nodes."""
from __future__ import annotations

import argparse
import json
import os
from typing import Any


def validate_nodes(nodes: dict[str, dict[str, Any]], attr_names: list[str] | tuple[str, ...] = ()) -> list[str]:
    errors: list[str] = []
    if "start" not in nodes:
        errors.append("缺少 start 节点")

    for node_id, node in nodes.items():
        if not isinstance(node, dict):
            errors.append(f"{node_id}: 节点不是对象")
            continue
        if not node.get("title"):
            errors.append(f"{node_id}: 缺少 title")
        if not node.get("text"):
            errors.append(f"{node_id}: 缺少 text")

        choices = node.get("choices", [])
        if not isinstance(choices, list):
            errors.append(f"{node_id}: choices 必须是列表")
            continue

        for idx, choice in enumerate(choices):
            prefix = f"{node_id}.choices[{idx}]"
            if not isinstance(choice, dict):
                errors.append(f"{prefix}: 必须是对象")
                continue
            if not choice.get("text"):
                errors.append(f"{prefix}: 缺少 text")
            for key in ("next", "fail"):
                target = choice.get(key)
                if target and target not in nodes:
                    errors.append(f"{prefix}.{key}: 指向不存在节点 {target}")
            for attr_group in ("effect", "require"):
                values = choice.get(attr_group, {})
                if values and not isinstance(values, dict):
                    errors.append(f"{prefix}.{attr_group}: 必须是对象")
                    continue
                for attr, value in values.items():
                    if attr_names and attr not in attr_names:
                        errors.append(f"{prefix}.{attr_group}: 未知属性 {attr}")
                    if not isinstance(value, int):
                        errors.append(f"{prefix}.{attr_group}.{attr}: 必须是整数")
    return errors


def export_nodes(nodes: dict[str, dict[str, Any]], output_path: str) -> None:
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False, indent=2)


def load_external_nodes(path: str) -> dict[str, dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("剧情数据必须是对象")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="剧情节点校验/导出工具")
    parser.add_argument("command", choices=["validate", "export"])
    parser.add_argument("--output", default=os.path.join("data", "story_nodes.json"))
    args = parser.parse_args()

    from game import ATTR_NAMES, NODES

    errors = validate_nodes(NODES, ATTR_NAMES)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    if args.command == "export":
        export_nodes(NODES, args.output)
        print(f"已导出剧情节点: {args.output}")
    else:
        print(f"剧情节点校验通过，共 {len(NODES)} 个节点。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
