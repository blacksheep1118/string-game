# -*- coding: utf-8 -*-
"""Gameplay enhancement rules shared by the browser API and terminal mode."""
from __future__ import annotations

import json
import os
import random
import re
from datetime import datetime
from typing import Any

ATTR_HINTS = {
    "根骨": "考验根骨，偏向战斗和肉身",
    "幸运": "考验幸运，偏向奇遇和寻宝",
    "魅力": "考验魅力，偏向社交和交易",
    "精神": "考验精神，偏向心魔和意志",
    "悟性": "考验悟性，偏向功法和炼丹",
}

CHAPTER_GOALS = {
    "序章": "做出第一道命运选择，确定你的仙途起点。",
    "第〇章": "完成缘起事件，明确你会如何回应第一次机缘。",
    "第一章": "找到可靠引路人，取得修行资格。",
    "第二章": "完成入门抉择，形成最初流派倾向。",
    "第三章": "建立核心能力，获得第一份成长资源。",
    "第四章": "处理第一次重大危机，积累声望或代价。",
    "第五章": "突破路线瓶颈，决定正邪或逍遥方向。",
    "第六章": "扩大影响力，完成流派专属考验。",
    "第七章": "收束关键羁绊，准备最终结局判定。",
    "第八章": "迎接终局选择，结算你的修行成果。",
    "终章": "完成最终命运，解锁轮回积累。",
}

ROUTE_KEYWORDS = {
    "剑修": ("sword", "剑", "妖兽", "青霜"),
    "丹修": ("pill", "丹", "药王", "炼丹"),
    "宗门": ("sect", "宗门", "玄天", "掌门", "白眉"),
    "散修": ("woods", "太虚", "洞府", "散修", "wander"),
    "古玉": ("jade", "古玉", "天魔", "心魔", "possessed"),
    "商道": ("rich", "商", "灵石", "富", "交易"),
}

ROUTE_REWARDS = {
    "剑修": {"attr": {"根骨": 1}, "resource": {"历练": 2}, "text": "剑意更凝练，历练 +2，根骨 +1。"},
    "丹修": {"attr": {"悟性": 1}, "resource": {"丹药": 1}, "text": "丹道经验增长，丹药 +1，悟性 +1。"},
    "宗门": {"reputation": {"正道": 1}, "affinity": {"同门": 1}, "text": "宗门关系推进，正道声望 +1，同门羁绊 +1。"},
    "散修": {"resource": {"灵石": 2, "历练": 1}, "text": "散修行走四方，灵石 +2，历练 +1。"},
    "古玉": {"resource": {"心魔": 1}, "text": "古玉低鸣，心魔 +1。力量越近，风险越深。"},
    "商道": {"resource": {"灵石": 4}, "attr": {"魅力": 1}, "text": "商道见识增长，灵石 +4，魅力 +1。"},
}

GENERIC_REWARD = {"resource": {"历练": 1}, "text": "旅途阅历增加，历练 +1。"}

ARTIFACT_EFFECTS = {
    "青霜剑": "战斗判定 +5",
    "妖丹": "突破时额外获得历练",
    "太虚令": "秘境失败时可重判一次",
    "药王鼎": "炼丹收益提高",
    "侠义勋章": "正道声望结算提高",
}

ARTIFACT_NODES = {
    "sword_tactic": "妖丹",
    "give_core": "青霜剑",
    "end_inheritance": "太虚令",
    "end_saint": "药王鼎",
    "end_hero": "侠义勋章",
}

ACHIEVEMENT_HINTS = [
    "剑心通明：沿剑修路线保持低心魔达成高评价结局。",
    "丹心未染：丹修路线积累丹药，同时避免心魔过高。",
    "八面玲珑：用高魅力解决宗门或商道关键分支。",
    "逆天改命：坏结局也会提供线索，下一轮更容易找到隐藏路线。",
]

RANDOM_EVENTS = [
    ("路边遗宝", {"灵石": 3}, {"幸运": 1}, "你在古树下拾得旧囊，灵石 +3，幸运 +1。"),
    ("灵泉沐浴", {"历练": 2}, {"精神": 1}, "你发现隐秘灵泉，历练 +2，精神 +1。"),
    ("黑市传闻", {"灵石": 2}, {"魅力": 1}, "黑市传闻带来新门路，灵石 +2，魅力 +1。"),
    ("心魔低语", {"心魔": 1}, {}, "耳边响起低语，心魔 +1，但你窥见了隐藏道路。"),
]


def ensure_gameplay_state(game: Any) -> None:
    if not hasattr(game, "resources") or not isinstance(game.resources, dict):
        game.resources = {}
    for name, default in {"灵石": 0, "心魔": 0, "历练": 0, "丹药": 0, "轮回": 0}.items():
        game.resources.setdefault(name, default)
    if not hasattr(game, "artifacts") or not isinstance(game.artifacts, list):
        game.artifacts = []
    if not hasattr(game, "inventory") or not isinstance(game.inventory, list):
        game.inventory = []
    if not hasattr(game, "affinity") or not isinstance(game.affinity, dict):
        game.affinity = {}
    if not hasattr(game, "reputation") or not isinstance(game.reputation, dict):
        game.reputation = {"正道": 0, "魔道": 0, "散修": 0}
    for name in ("正道", "魔道", "散修"):
        game.reputation.setdefault(name, 0)
    if not hasattr(game, "flags") or not isinstance(game.flags, dict):
        game.flags = {}
    game.flags.setdefault("rewarded_nodes", [])
    game.flags.setdefault("insights", [])


def get_chapter(title: str) -> str:
    match = re.match(r"^(序章|终章|第[〇一二三四五六七八九十]+章)", title or "")
    return match.group(1) if match else ""


def get_goal(title: str) -> str:
    chapter = get_chapter(title)
    return CHAPTER_GOALS.get(chapter, "探索当前分支，积累属性、资源和线索。")


def infer_route(node_id: str, node: dict[str, Any] | None = None) -> str:
    title = (node or {}).get("title", "")
    text = (node or {}).get("text", "")
    haystack = f"{node_id} {title} {text}"
    for route, keys in ROUTE_KEYWORDS.items():
        if any(key in haystack for key in keys):
            return route
    return "未定"


def choice_hints(choice: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    req = choice.get("require", {})
    if req:
        hints.extend(ATTR_HINTS.get(attr, f"考验{attr}") for attr in req)
    effect = choice.get("effect", {})
    for attr, delta in effect.items():
        if delta > 0:
            hints.append(f"可能提升{attr}")
        elif delta < 0:
            hints.append(f"可能消耗{attr}")
    text = choice.get("text", "")
    if any(word in text for word in ("强行", "拼死", "心魔", "魔")):
        hints.append("高风险高收益")
    if any(word in text for word in ("求援", "结盟", "加入", "交易")):
        hints.append("影响人脉或声望")
    return hints


def snapshot(game: Any) -> dict[str, Any]:
    ensure_gameplay_state(game)
    return {
        "attrs": dict(game.attrs),
        "resources": dict(game.resources),
        "artifacts": list(game.artifacts),
        "inventory": list(game.inventory),
        "affinity": dict(game.affinity),
        "reputation": dict(game.reputation),
    }


def _add_mapping(target: dict[str, int], values: dict[str, int]) -> None:
    for key, delta in values.items():
        target[key] = int(target.get(key, 0)) + int(delta)


def apply_node_rewards(game: Any, node_id: str, node: dict[str, Any]) -> list[str]:
    ensure_gameplay_state(game)
    rewarded = game.flags.setdefault("rewarded_nodes", [])
    if node_id in rewarded:
        return []
    rewarded.append(node_id)

    feedback: list[str] = []
    route = infer_route(node_id, node)
    reward = ROUTE_REWARDS.get(route)
    if not reward:
        reward = GENERIC_REWARD
    _add_mapping(game.attrs, reward.get("attr", {}))
    _add_mapping(game.resources, reward.get("resource", {}))
    _add_mapping(game.reputation, reward.get("reputation", {}))
    _add_mapping(game.affinity, reward.get("affinity", {}))
    feedback.append(reward["text"])

    artifact = ARTIFACT_NODES.get(node_id)
    if artifact and artifact not in game.artifacts:
        game.artifacts.append(artifact)
        feedback.append(f"获得法宝「{artifact}」：{ARTIFACT_EFFECTS.get(artifact, '提供特殊结算加成')}。")

    return feedback


def maybe_random_event(game: Any) -> list[str]:
    ensure_gameplay_state(game)
    luck = int(game.attrs.get("幸运", 20))
    chance = min(0.16, 0.04 + max(0, luck - 20) * 0.002)
    if random.random() >= chance:
        return []
    name, resources, attrs, text = random.choice(RANDOM_EVENTS)
    _add_mapping(game.resources, resources)
    _add_mapping(game.attrs, attrs)
    game.flags.setdefault("insights", []).append(name)
    return [f"【奇遇】{text}"]


def diff_feedback(before: dict[str, Any], game: Any) -> list[str]:
    after = snapshot(game)
    feedback: list[str] = []
    for group, label in (("attrs", "属性"), ("resources", "资源"), ("reputation", "声望"), ("affinity", "羁绊")):
        for key, value in after[group].items():
            old = int(before[group].get(key, 0))
            new = int(value)
            delta = new - old
            if delta:
                sign = "+" if delta > 0 else ""
                feedback.append(f"{label}变化：{key} {sign}{delta}")
    new_artifacts = [a for a in after["artifacts"] if a not in before["artifacts"]]
    for artifact in new_artifacts:
        feedback.append(f"法宝入手：{artifact}（{ARTIFACT_EFFECTS.get(artifact, '特殊效果')}）")
    return feedback


def score_summary(game: Any, ending_title: str) -> dict[str, Any]:
    ensure_gameplay_state(game)
    attrs_total = sum(int(v) for v in game.attrs.values())
    resources_total = int(game.resources.get("灵石", 0)) + int(game.resources.get("历练", 0)) * 2 + int(game.resources.get("丹药", 0)) * 3
    reputation_total = sum(int(v) for v in game.reputation.values())
    artifact_bonus = len(game.artifacts) * 8
    mind_penalty = int(game.resources.get("心魔", 0)) * 4
    score = attrs_total + resources_total + reputation_total * 3 + artifact_bonus - mind_penalty
    if "SS" in ending_title or score >= 220:
        rank = "SS"
    elif "S" in ending_title or score >= 185:
        rank = "S"
    elif "A" in ending_title or score >= 150:
        rank = "A"
    elif score >= 120:
        rank = "B"
    else:
        rank = "C"
    reasons = [
        f"最终属性合计 {attrs_total}",
        f"资源结算 +{resources_total}",
        f"声望结算 +{reputation_total * 3}",
        f"法宝结算 +{artifact_bonus}",
    ]
    if mind_penalty:
        reasons.append(f"心魔代价 -{mind_penalty}")
    return {"score": score, "rank": rank, "reasons": reasons}


def mini_game_for(node_id: str, node: dict[str, Any]) -> dict[str, Any] | None:
    route = infer_route(node_id, node)
    if route == "剑修":
        return {"type": "combat", "title": "战斗态势", "bars": [{"label": "剑势", "value": min(100, 35 + node_id.count('_') * 12)}]}
    if route == "丹修":
        return {"type": "alchemy", "title": "炉火火候", "bars": [{"label": "火候", "value": 62}]}
    if route == "古玉":
        return {"type": "mind", "title": "心魔波动", "bars": [{"label": "心魔", "value": 48}]}
    return None


def progression_path(save_dir: str) -> str:
    return os.path.join(save_dir, "_progression.json")


def load_progression(save_dir: str) -> dict[str, Any]:
    path = progression_path(save_dir)
    if not os.path.exists(path):
        return {"legacy_points": 0, "endings": [], "insights": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"legacy_points": 0, "endings": [], "insights": []}
    data.setdefault("legacy_points", 0)
    data.setdefault("endings", [])
    data.setdefault("insights", [])
    return data


def record_progression(save_dir: str, game: Any, ending_title: str) -> dict[str, Any]:
    ensure_gameplay_state(game)
    os.makedirs(save_dir, exist_ok=True)
    data = load_progression(save_dir)
    if ending_title and ending_title not in data["endings"]:
        data["endings"].append(ending_title)
        data["legacy_points"] = int(data.get("legacy_points", 0)) + 1
    for insight in game.flags.get("insights", []):
        if insight not in data["insights"]:
            data["insights"].append(insight)
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(progression_path(save_dir), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def destiny_map(nodes: dict[str, dict[str, Any]], current_path: list[str], gallery: list[dict[str, Any]]) -> dict[str, Any]:
    unlocked_titles = {entry.get("title", "") for entry in gallery}
    current = set(current_path)
    branches: list[dict[str, Any]] = []
    for route in ROUTE_KEYWORDS:
        route_nodes = []
        for node_id, node in nodes.items():
            if infer_route(node_id, node) != route:
                continue
            route_nodes.append({
                "id": node_id,
                "title": node.get("title", node_id),
                "visited": node_id in current,
                "ending_unlocked": node.get("title", "") in unlocked_titles,
                "is_ending": len(node.get("choices", [])) == 0,
            })
            if len(route_nodes) >= 8:
                break
        branches.append({"route": route, "nodes": route_nodes})
    return {"branches": branches, "achievement_hints": ACHIEVEMENT_HINTS}
