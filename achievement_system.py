# -*- coding: utf-8 -*-
"""成就系统"""
from __future__ import annotations

import json
import os
from typing import Any


class AchievementSystem:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.achievements = self._load_achievements()
        self.unlocked = set()  # 已解锁的成就ID

    def _load_achievements(self) -> list[dict[str, Any]]:
        """加载成就定义"""
        path = os.path.join(self.data_dir, "achievements.json")
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("achievements", [])
        except (OSError, json.JSONDecodeError):
            return []

    def load_unlocked(self, save_dir: str) -> None:
        """从存档加载已解锁成就"""
        path = os.path.join(save_dir, "_achievements.json")
        if not os.path.exists(path):
            self.unlocked = set()
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.unlocked = set(data.get("unlocked", []))
        except (OSError, json.JSONDecodeError):
            self.unlocked = set()

    def save_unlocked(self, save_dir: str) -> None:
        """保存已解锁成就"""
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, "_achievements.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"unlocked": list(self.unlocked)}, f, ensure_ascii=False, indent=2)

    def check_achievements(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """检查并返回新解锁的成就"""
        newly_unlocked = []
        for ach in self.achievements:
            ach_id = ach.get("id")
            if not ach_id or ach_id in self.unlocked:
                continue

            trigger = ach.get("trigger", {})
            if self._check_trigger(trigger, context):
                self.unlocked.add(ach_id)
                newly_unlocked.append({
                    "id": ach_id,
                    "name": ach.get("name", ""),
                    "desc": ach.get("desc", ""),
                    "icon": ach.get("icon", "🏆"),
                    "category": ach.get("category", ""),
                    "hidden": ach.get("hidden", False),
                })

        return newly_unlocked

    def _check_trigger(self, trigger: dict[str, Any], context: dict[str, Any]) -> bool:
        """检查触发条件是否满足"""
        trigger_type = trigger.get("type")

        if trigger_type == "ending_count":
            return context.get("ending_count", 0) >= trigger.get("count", 0)

        if trigger_type == "ending_rank":
            if "route" in trigger:
                return (context.get("route") == trigger["route"] and
                        context.get("rank") == trigger["rank"])
            return context.get("rank") == trigger.get("rank")

        if trigger_type == "ending_id":
            return context.get("node_id") == trigger.get("ending")

        if trigger_type == "attrs_all_above":
            attrs = context.get("attrs", {})
            value = trigger.get("value", 0)
            node = trigger.get("node")
            if node and context.get("node_id") != node:
                return False
            return all(int(v) >= value for v in attrs.values())

        if trigger_type == "attr_reach":
            attrs = context.get("attrs", {})
            attr_name = trigger.get("attr")
            value = trigger.get("value", 0)
            return int(attrs.get(attr_name, 0)) >= value

        if trigger_type == "attrs_balanced":
            attrs = context.get("attrs", {})
            if not attrs:
                return False
            values = [int(v) for v in attrs.values()]
            max_diff = trigger.get("max_diff", 10)
            return max(values) - min(values) <= max_diff

        if trigger_type == "attrs_specialist":
            attrs = context.get("attrs", {})
            if not attrs:
                return False
            values = sorted([int(v) for v in attrs.values()], reverse=True)
            if len(values) < 2:
                return False
            diff = trigger.get("diff", 20)
            return values[0] - values[1] >= diff

        if trigger_type == "path_length":
            path_length = context.get("path_length", 0)
            if "max" in trigger:
                return path_length <= trigger["max"]
            if "min" in trigger:
                return path_length >= trigger["min"]
            return False

        if trigger_type == "resource_reach":
            resources = context.get("resources", {})
            resource_name = trigger.get("resource")
            value = trigger.get("value", 0)
            return int(resources.get(resource_name, 0)) >= value

        if trigger_type == "ending_with_resource":
            if not context.get("is_ending"):
                return False
            resources = context.get("resources", {})
            resource_name = trigger.get("resource")
            resource_value = int(resources.get(resource_name, 0))

            if "min_value" in trigger and resource_value < trigger["min_value"]:
                return False
            if "max_value" in trigger and resource_value > trigger["max_value"]:
                return False

            rank = context.get("rank", "C")
            min_rank = trigger.get("min_rank", "C")
            rank_order = {"SS": 5, "S": 4, "A": 3, "B": 2, "C": 1, "D": 0}
            return rank_order.get(rank, 0) >= rank_order.get(min_rank, 0)

        if trigger_type == "artifacts_count":
            artifacts = context.get("artifacts", [])
            return len(artifacts) >= trigger.get("min", 0)

        if trigger_type == "artifacts_all":
            artifacts = context.get("artifacts", [])
            required = trigger.get("artifacts", [])
            return all(art in artifacts for art in required)

        if trigger_type == "reputation_reach":
            reputation = context.get("reputation", {})
            faction = trigger.get("faction")
            value = trigger.get("value", 0)
            return int(reputation.get(faction, 0)) >= value

        if trigger_type == "random_events":
            insights = context.get("insights", [])
            return len(insights) >= trigger.get("min", 0)

        if trigger_type == "save_count":
            return context.get("save_count", 0) >= trigger.get("count", 0)

        if trigger_type == "legacy_points":
            return context.get("legacy_points", 0) >= trigger.get("value", 0)

        if trigger_type == "quick_restart_count":
            return context.get("quick_restart_count", 0) >= trigger.get("count", 0)

        if trigger_type == "view_destiny_map":
            return context.get("viewed_destiny_map", False)

        if trigger_type == "view_gallery":
            return context.get("viewed_gallery", False)

        if trigger_type == "change_settings":
            return context.get("changed_settings", False)

        if trigger_type == "score_reach":
            return context.get("score", 0) >= trigger.get("value", 0)

        if trigger_type == "challenge_zero_start":
            if not context.get("is_zero_start", False):
                return False
            rank = context.get("rank", "C")
            min_rank = trigger.get("min_rank", "C")
            rank_order = {"SS": 5, "S": 4, "A": 3, "B": 2, "C": 1, "D": 0}
            return rank_order.get(rank, 0) >= rank_order.get(min_rank, 0)

        return False

    def get_all_visible(self) -> list[dict[str, Any]]:
        """获取所有可见成就（已解锁或未隐藏）"""
        result = []
        for ach in self.achievements:
            ach_id = ach.get("id")
            is_unlocked = ach_id in self.unlocked
            is_hidden = ach.get("hidden", False)

            if is_unlocked or not is_hidden:
                result.append({
                    "id": ach_id,
                    "name": ach.get("name", ""),
                    "desc": ach.get("desc", ""),
                    "icon": ach.get("icon", "🏆"),
                    "category": ach.get("category", ""),
                    "unlocked": is_unlocked,
                    "hidden": is_hidden and not is_unlocked,
                })

        return result

    def get_stats(self) -> dict[str, Any]:
        """获取成就统计"""
        total = len(self.achievements)
        unlocked_count = len(self.unlocked)
        hidden_total = sum(1 for ach in self.achievements if ach.get("hidden", False))
        hidden_unlocked = sum(1 for ach in self.achievements
                             if ach.get("hidden", False) and ach.get("id") in self.unlocked)

        return {
            "total": total,
            "unlocked": unlocked_count,
            "hidden_total": hidden_total,
            "hidden_unlocked": hidden_unlocked,
            "progress": round(unlocked_count / total * 100, 1) if total > 0 else 0,
        }
