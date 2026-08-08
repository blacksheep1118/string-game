# -*- coding: utf-8 -*-
"""Utilities for validating and exporting story nodes."""
from __future__ import annotations

import argparse
import json
import os
from typing import Any


DEFAULT_RESOURCE_NAMES = ("灵石", "心魔", "历练", "丹药", "轮回", "正道", "魔道", "散修")


def validate_nodes(
    nodes: dict[str, dict[str, Any]],
    attr_names: list[str] | tuple[str, ...] = (),
    resource_names: list[str] | tuple[str, ...] = DEFAULT_RESOURCE_NAMES,
) -> list[str]:
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
                if target and (not isinstance(target, str) or target not in nodes):
                    errors.append(f"{prefix}.{key}: 指向不存在节点 {target}")
            if not choice.get("next") and not choice.get("fail"):
                errors.append(f"{prefix}: 缺少 next 或 fail 目标")
            for attr_group in ("effect", "require"):
                values = choice.get(attr_group, {})
                if not isinstance(values, dict):
                    errors.append(f"{prefix}.{attr_group}: 必须是对象")
                    continue
                for attr, value in values.items():
                    if attr_names and attr not in attr_names and attr not in resource_names:
                        errors.append(f"{prefix}.{attr_group}: 未知属性 {attr}")
                    if isinstance(value, bool) or not isinstance(value, int):
                        errors.append(f"{prefix}.{attr_group}.{attr}: 必须是整数")
    return errors


def reachable_nodes(nodes: dict[str, dict[str, Any]], start: str = "start") -> set[str]:
    """Return nodes reachable through both successful and failed choices."""
    if start not in nodes:
        return set()
    reached = {start}
    pending = [start]
    while pending:
        node_id = pending.pop()
        for choice in nodes.get(node_id, {}).get("choices", []):
            if not isinstance(choice, dict):
                continue
            for key in ("next", "fail"):
                target = choice.get(key)
                if target in nodes and target not in reached:
                    reached.add(target)
                    pending.append(target)
    return reached


def ending_nodes(nodes: dict[str, dict[str, Any]]) -> set[str]:
    """Return terminal story nodes with no choices."""
    return {node_id for node_id, node in nodes.items() if not node.get("choices", [])}


def placeholder_nodes(nodes: dict[str, dict[str, Any]]) -> list[str]:
    """Find obvious placeholder or intentionally missing story content."""
    markers = ("缺失节点", "此节点不可达", "TODO", "待补")
    return sorted(
        node_id
        for node_id, node in nodes.items()
        if any(marker in f"{node.get('title', '')} {node.get('text', '')}" for marker in markers)
    )


def duplicate_destinations(nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Report choices in one node that share the same successful destination."""
    duplicates = []
    for node_id, node in nodes.items():
        destinations: dict[str, list[int]] = {}
        for index, choice in enumerate(node.get("choices", [])):
            if not isinstance(choice, dict) or not choice.get("next"):
                continue
            destinations.setdefault(choice["next"], []).append(index)
        for target, indexes in destinations.items():
            if len(indexes) > 1:
                duplicates.append({"node": node_id, "target": target, "choices": indexes})
    return duplicates


def semantic_duplicate_choices(nodes: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """报告连目标、条件和效果都相同的伪选择。"""

    duplicates = []
    for node_id, node in nodes.items():
        signatures: dict[str, list[int]] = {}
        for index, choice in enumerate(node.get("choices", [])):
            if not isinstance(choice, dict):
                continue
            signature = json.dumps({
                "next": choice.get("next"),
                "fail": choice.get("fail"),
                "effect": choice.get("effect", {}),
                "require": choice.get("require", {}),
            }, ensure_ascii=False, sort_keys=True)
            signatures.setdefault(signature, []).append(index)
        for signature, indexes in signatures.items():
            if len(indexes) > 1:
                duplicates.append({"node": node_id, "choices": indexes, "signature": signature})
    return duplicates


def graph_quality(nodes: dict[str, dict[str, Any]], start: str = "start") -> dict[str, Any]:
    """Summarize reachability and common content-quality hazards."""
    reached = reachable_nodes(nodes, start)
    return {
        "nodes": len(nodes),
        "reachable": len(reached),
        "unreachable": sorted(set(nodes) - reached),
        "endings": sorted(ending_nodes(nodes)),
        "placeholders": placeholder_nodes(nodes),
        "duplicate_destinations": duplicate_destinations(nodes),
        "semantic_duplicates": semantic_duplicate_choices(nodes),
    }


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
    parser.add_argument("command", choices=["validate", "export", "quality"])
    parser.add_argument("--output", default=os.path.join("data", "story_nodes.json"))
    args = parser.parse_args()

    from xiantu.engine import ATTR_NAMES
    from xiantu.story import NODES

    errors = validate_nodes(NODES, ATTR_NAMES)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1

    if args.command == "export":
        export_nodes(NODES, args.output)
        print(f"已导出剧情节点: {args.output}")
    elif args.command == "quality":
        quality = graph_quality(NODES)
        print(json.dumps({
            "nodes": quality["nodes"],
            "reachable": quality["reachable"],
            "unreachable_count": len(quality["unreachable"]),
            "unreachable": quality["unreachable"],
            "ending_count": len(quality["endings"]),
            "placeholders": quality["placeholders"],
            "duplicate_destinations": quality["duplicate_destinations"],
            "semantic_duplicates": quality["semantic_duplicates"],
        }, ensure_ascii=False, indent=2))
    else:
        print(f"剧情节点校验通过，共 {len(NODES)} 个节点。")
    if args.command == "quality" and (
        quality["unreachable"]
        or quality["placeholders"]
        or quality["semantic_duplicates"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
