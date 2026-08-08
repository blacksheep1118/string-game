# -*- coding: utf-8 -*-
"""Gameplay enhancement rules shared by the browser API and terminal mode."""
from __future__ import annotations

import json
import os
import random
import re
import tempfile
import hashlib
from datetime import date, datetime
from typing import Any

from xiantu.story import NODES

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

ROUTE_ID_PREFIXES = (
    ("剑修", ("sword_", "end_sword", "give_core")),
    ("丹修", ("pill_", "end_pill", "ch4_pill", "end_saint", "end_solid", "end_deviation")),
    ("宗门", ("sect_", "end_sect", "end_alliance", "end_leader", "end_hero")),
    ("散修", ("woods_", "end_wander", "end_isolate", "end_late_", "end_mortal")),
    ("古玉", ("jade_", "end_possessed", "end_coexist", "end_haunted")),
    ("商道", ("rich_", "end_rich", "end_merchant", "end_philanthropist", "ch4_rich")),
)

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
    "end_breakthrough": "妖灵珠",
    "end_inheritance": "太虚令",
    "end_saint": "药王鼎",
    "end_hero": "侠义勋章",
}

INVENTORY_NODES = {
    "pill_power": "筑基丹",
    "pill_caution": "清心丹",
    "pill_rush": "狂暴丹",
    "pill_heal": "回春丹",
    "pill_poison_path_3": "毒丹",
    "end_pill_saint": "九转金丹",
}

REPUTATION_NODES = {
    "end_alliance": {"正道": 5},
    "end_leader": {"正道": 4},
    "end_hero": {"正道": 3},
    "end_fallen": {"魔道": 5},
    "end_possessed": {"魔道": 4},
    "end_isolate": {"散修": 4},
    "end_wander": {"散修": 3},
}

# 关键命运转折点 - 会触发视觉特效
PIVOTAL_NODES = {
    "accept": {"type": "major", "text": "命运分岔点", "shake": "medium", "flash": "#c9a96e"},
    "sword_tactic": {"type": "major", "text": "剑道天赋觉醒", "shake": "heavy", "flash": "#6b8e6b"},
    "give_core": {"type": "major", "text": "获得剑心", "shake": "medium", "flash": "#49627a"},
    "pill_choice_branch": {"type": "major", "text": "丹道分岔", "shake": "light", "flash": "#c9a96e"},
    "jade_trust": {"type": "critical", "text": "心魔入侵！", "shake": "heavy", "flash": "#8b3a3a"},
    "sect_neutral": {"type": "major", "text": "宗门抉择", "shake": "medium", "flash": "#6b8e6b"},
    "ch4_rich_expand": {"type": "minor", "text": "商道机缘", "shake": "light", "flash": "#c9a96e"},
    "woods_explore": {"type": "major", "text": "散修奇遇", "shake": "medium", "flash": "#49627a"},
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

FORTUNE_BONUS = {"大吉": 5, "吉": 3, "中吉": 1, "小吉": 0, "末吉": -3}
BONUS_ENDING_TITLE = "【隐藏结局】天命所归  评价：SS+——你已洞悉一切"
BONUS_ENDING_TEXT = (
    "你已踏遍仙途的每一个角落，见证了所有的命运分支。\n\n"
    "诸般结局在你心中汇聚成河——你终于明白，仙途不是一条路，\n"
    "而是万千可能性的总和。天道有常，众生皆苦。\n\n"
    "而你，已超脱其中。\n\n"
    "═══════════════════\n"
    "  🏆 达成隐藏结局：天命所归\n"
    "  评价：SS+ —— 你已洞悉一切\n"
    "═══════════════════"
)


def daily_fortune(day: date | None = None) -> tuple[str, int]:
    """返回跨入口一致的每日运势，不因刷新或切换前端改变。"""

    current = day or date.today()
    digest = hashlib.sha256(current.isoformat().encode("ascii")).digest()
    fortunes = tuple(FORTUNE_BONUS)
    fortune = fortunes[digest[0] % len(fortunes)]
    return fortune, FORTUNE_BONUS[fortune]


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
    game.flags.setdefault("minigames", [])


def get_chapter(title: str) -> str:
    match = re.match(r"^(序章|终章|第[〇一二三四五六七八九十]+章)", title or "")
    return match.group(1) if match else ""


def get_goal(title: str) -> str:
    chapter = get_chapter(title)
    return CHAPTER_GOALS.get(chapter, "探索当前分支，积累属性、资源和线索。")


def infer_route(node_id: str, node: dict[str, Any] | None = None) -> str:
    explicit_route = (node or {}).get("route")
    if explicit_route in ROUTE_REWARDS:
        return explicit_route
    for route, prefixes in ROUTE_ID_PREFIXES:
        if any(str(node_id).startswith(prefix) for prefix in prefixes):
            return route
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
            hints.append(f"可能提升{attr}" if attr != "心魔" else "会增加心魔")
        elif delta < 0:
            hints.append(f"可能消耗{attr}" if attr != "心魔" else "可能压制心魔")
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
        if artifact == "妖丹":
            game.resources["历练"] += 1
            feedback.append("妖丹淬体生效：历练 +1。")
        elif artifact == "药王鼎":
            game.resources["丹药"] += 2
            feedback.append("药王鼎炼丹收益提高：丹药 +2。")
        elif artifact == "侠义勋章":
            game.reputation["正道"] += 2
            feedback.append("侠义勋章振奋人心：正道声望 +2。")

    item = INVENTORY_NODES.get(node_id)
    if item and item not in game.inventory:
        game.inventory.append(item)
        feedback.append(f"收入丹药「{item}」，可在后续丹道结算中留下记录。")

    _add_mapping(game.reputation, REPUTATION_NODES.get(node_id, {}))
    text = str(node.get("text", ""))
    for marker, npc in (("师父", "师父"), ("白眉", "白眉道人"), ("道侣", "道侣")):
        if marker in text:
            game.affinity[npc] = int(game.affinity.get(npc, 0)) + 1

    return feedback


def maybe_random_event(game: Any) -> list[str]:
    ensure_gameplay_state(game)
    rng = getattr(game, "rng", random)
    luck = int(game.attrs.get("幸运", 20))
    chance = min(0.16, 0.04 + max(0, luck - 20) * 0.002)
    if rng.random() >= chance:
        return []
    name, resources, attrs, text = rng.choice(RANDOM_EVENTS)
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
    artifact_effect_bonus = 0
    if "妖丹" in game.artifacts:
        artifact_effect_bonus += 5
    if "侠义勋章" in game.artifacts:
        artifact_effect_bonus += 6
    mind_penalty = int(game.resources.get("心魔", 0)) * 4
    score = attrs_total + resources_total + reputation_total * 3 + artifact_bonus + artifact_effect_bonus - mind_penalty
    if "SS" in ending_title or score >= 220:
        rank = "SS"
    elif "S" in ending_title or score >= 185:
        rank = "S"
    elif "A" in ending_title or score >= 150:
        rank = "A"
    elif score >= 120:
        rank = "B"
    elif score >= 80:
        rank = "C"
    else:
        rank = "D"
    reasons = [
        f"最终属性合计 {attrs_total}",
        f"资源结算 +{resources_total}",
        f"声望结算 +{reputation_total * 3}",
        f"法宝结算 +{artifact_bonus}",
    ]
    if artifact_effect_bonus:
        reasons.append(f"法宝效果结算 +{artifact_effect_bonus}")
    if mind_penalty:
        reasons.append(f"心魔代价 -{mind_penalty}")
    return {"score": score, "rank": rank, "reasons": reasons}


def mini_game_for(node_id: str, node: dict[str, Any], game: Any | None = None) -> dict[str, Any] | None:
    if not node.get("choices"):
        return None
    route = infer_route(node_id, node)
    marker = f"mini:{node_id}"
    completed = False
    if game is not None:
        ensure_gameplay_state(game)
        completed = marker in game.flags.get("minigames", [])
    if route == "剑修":
        return {
            "type": "combat",
            "title": "战斗态势",
            "bars": [{"label": "剑势", "value": min(100, 35 + node_id.count("_") * 12)}],
            "prompt": "高根骨可降低战斗代价。",
            "actions": [
                {"id": "attack", "label": "强攻", "hint": "根骨≥30更稳定"},
                {"id": "defend", "label": "守势", "hint": "精神≥25可减轻心魔"},
            ],
            "completed": completed,
        }
    if route == "丹修":
        return {
            "type": "alchemy",
            "title": "炉火火候",
            "bars": [{"label": "火候", "value": 62}],
            "prompt": "稳健路线更容易留下丹药，冒险路线更容易获得高评价。",
            "actions": [
                {"id": "stabilize", "label": "稳火", "hint": "悟性≥24可获得丹药"},
                {"id": "risk", "label": "赌炉", "hint": "高收益，也会增加心魔"},
            ],
            "completed": completed,
        }
    if route == "古玉":
        return {
            "type": "mind",
            "title": "心魔波动",
            "bars": [{"label": "心魔", "value": 48}],
            "prompt": "精神越高，越容易从古玉分支全身而退。",
            "actions": [
                {"id": "resist", "label": "守住道心", "hint": "精神≥30可压制心魔"},
                {"id": "embrace", "label": "借魔破境", "hint": "获得历练，但心魔上升"},
            ],
            "completed": completed,
        }
    return None


def resolve_mini_game(game: Any, node_id: str, action: str) -> list[str]:
    """执行一次可复现的路线试炼；状态标记防止重复刷奖励。"""

    ensure_gameplay_state(game)
    if game.current_node != node_id:
        raise ValueError("mini_game_node_mismatch")
    node = NODES.get(node_id, {})
    panel = mini_game_for(node_id, node)
    if not panel or action not in {item["id"] for item in panel.get("actions", [])}:
        raise ValueError("invalid_mini_game_action")
    marker = f"mini:{node_id}"
    if marker in game.flags.get("minigames", []):
        raise ValueError("mini_game_completed")

    route = infer_route(node_id, node)
    feedback: list[str] = []
    if route == "剑修":
        if action == "attack":
            success = int(game.attrs.get("根骨", 0)) + (5 if "青霜剑" in game.artifacts else 0) >= 30
            if success:
                game.attrs["根骨"] += 2
                game.resources["历练"] += 3
                feedback.append("强攻得手：根骨 +2，历练 +3。")
            else:
                game.attrs["精神"] += 1
                game.resources["心魔"] += 1
                feedback.append("强攻受挫：精神 +1，心魔 +1。")
        else:
            game.attrs["精神"] += 2
            game.resources["历练"] += 1
            feedback.append("守势化解锋芒：精神 +2，历练 +1。")
    elif route == "丹修":
        if action == "stabilize":
            if int(game.attrs.get("悟性", 0)) >= 24:
                game.resources["丹药"] += 2
                game.attrs["悟性"] += 1
                feedback.append("稳火成功：丹药 +2，悟性 +1。")
            else:
                game.resources["丹药"] += 1
                feedback.append("火候勉强稳定：丹药 +1。")
        else:
            game.resources["丹药"] += 3
            game.resources["心魔"] += 1
            feedback.append("赌炉成功：丹药 +3，但心魔 +1。")
    elif route == "古玉":
        if action == "resist":
            if int(game.attrs.get("精神", 0)) >= 30:
                game.resources["心魔"] = max(0, game.resources["心魔"] - 2)
                game.attrs["精神"] += 2
                feedback.append("道心稳固：心魔 -2，精神 +2。")
            else:
                game.resources["心魔"] += 1
                feedback.append("道心出现裂痕：心魔 +1。")
        else:
            game.resources["历练"] += 4
            game.resources["心魔"] += 2
            feedback.append("借魔窥见秘术：历练 +4，心魔 +2。")

    game.flags.setdefault("minigames", []).append(marker)
    return feedback


def progression_path(save_dir: str) -> str:
    return os.path.join(save_dir, "_progression.json")


def load_progression(save_dir: str) -> dict[str, Any]:
    path = progression_path(save_dir)
    defaults = {
        "legacy_points": 0,
        "endings": [],
        "insights": [],
        "artifacts": [],
        "save_count": 0,
        "quick_restart_count": 0,
        "viewed_gallery": False,
        "viewed_destiny_map": False,
        "changed_settings": False,
    }
    if not os.path.exists(path):
        return defaults
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, TypeError):
        return defaults
    if not isinstance(data, dict):
        return defaults
    try:
        data["legacy_points"] = max(0, int(data.get("legacy_points", 0)))
    except (TypeError, ValueError):
        data["legacy_points"] = 0
    for key in ("endings", "insights", "artifacts"):
        if not isinstance(data.get(key), list):
            data[key] = []
        data[key] = [item for item in data[key] if isinstance(item, str)][:500]
    for key in ("save_count", "quick_restart_count"):
        try:
            data[key] = max(0, int(data.get(key, 0)))
        except (TypeError, ValueError):
            data[key] = 0
    for key in ("viewed_gallery", "viewed_destiny_map", "changed_settings"):
        data[key] = bool(data.get(key, False))
    return data


def update_progression(
    save_dir: str,
    *,
    increments: dict[str, int] | None = None,
    flags: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """更新跨轮回统计，供三个入口共享。"""

    os.makedirs(save_dir, exist_ok=True)
    data = load_progression(save_dir)
    for key, amount in (increments or {}).items():
        if key not in ("save_count", "quick_restart_count"):
            continue
        try:
            data[key] = max(0, int(data.get(key, 0)) + int(amount))
        except (TypeError, ValueError):
            data[key] = 0
    for key, value in (flags or {}).items():
        if key in ("viewed_gallery", "viewed_destiny_map", "changed_settings"):
            data[key] = bool(data.get(key, False) or value)
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _atomic_write_json(progression_path(save_dir), data)
    return data


def _atomic_write_json(path: str, payload: Any) -> None:
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".xiantu-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


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
    for artifact in game.artifacts:
        if artifact not in data["artifacts"]:
            data["artifacts"].append(artifact)
    data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _atomic_write_json(progression_path(save_dir), data)
    return data


def quick_restart_game(game: Any, save_dir: str) -> tuple[Any, int]:
    """以当前角色倾向开启新轮回，并统一累加轮回次数。"""

    from xiantu.engine import ATTR_MIN, Game

    ensure_gameplay_state(game)
    restarted = Game()
    ensure_gameplay_state(restarted)
    restarted.player_name = getattr(game, "player_name", "") or "轮回者"
    restarted.trait = getattr(game, "trait", "")
    restarted.attrs = {
        name: max(ATTR_MIN, int(value))
        for name, value in getattr(game, "attrs", {}).items()
    }
    legacy = min(10, int(load_progression(save_dir).get("legacy_points", 0)))
    restarted.attrs["幸运"] = restarted.attrs.get("幸运", 20) + legacy
    restarted.resources["轮回"] = legacy
    update_progression(save_dir, increments={"quick_restart_count": 1})
    return restarted, legacy


def read_progress_records(save_dir: str, filename: str) -> list[dict[str, Any]]:
    """读取跨入口共享的 JSON 记录；损坏或脏数据不会拖垮游戏。"""

    path = os.path.join(save_dir, filename)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, TypeError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def bonus_ending_available(save_dir: str, nodes: dict[str, dict[str, Any]]) -> bool:
    """全部普通结局收集完成后开放一次性的隐藏结局。"""

    normal_titles = {
        str(node.get("title", ""))
        for node in nodes.values()
        if not node.get("choices")
    }
    unlocked = {
        str(entry.get("title", ""))
        for entry in read_progress_records(save_dir, "_gallery.json")
    }
    return bool(normal_titles) and normal_titles.issubset(unlocked) and BONUS_ENDING_TITLE not in unlocked


def _write_progress_records(save_dir: str, filename: str, records: list[dict[str, Any]]) -> None:
    os.makedirs(save_dir, exist_ok=True)
    _atomic_write_json(os.path.join(save_dir, filename), records)


def record_ending(
    save_dir: str,
    game: Any,
    nodes: dict[str, dict[str, Any]],
    *,
    ending_title: str | None = None,
) -> dict[str, Any]:
    """统一写入画廊、排行榜和轮回进度，保证入口间结算一致。"""

    ensure_gameplay_state(game)
    node = nodes.get(game.current_node, {})
    if ending_title is None:
        if node.get("choices"):
            raise ValueError("当前节点不是结局")
        ending_title = str(node.get("title", ""))
    else:
        ending_title = str(ending_title).strip()
        if not ending_title:
            raise ValueError("结局标题不能为空")
    summary = score_summary(game, ending_title)
    achieved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    run_material = {
        "title": ending_title,
        "player_name": game.player_name,
        "trait": game.trait,
        "attrs": game.attrs,
        "path_history": game.path_history,
    }
    run_id = hashlib.sha256(
        json.dumps(run_material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:24]

    gallery = read_progress_records(save_dir, "_gallery.json")
    existing = [entry for entry in gallery if entry.get("title") == ending_title]
    record = {
        "title": ending_title,
        "player_name": game.player_name,
        "trait": game.trait,
        "attrs": dict(game.attrs),
        "path_count": len(game.path_history),
        "score": summary["score"],
        "rank": summary["rank"],
        "achieved_at": achieved_at,
        "run_id": run_id,
    }
    if not existing:
        gallery.append(record)
        _write_progress_records(save_dir, "_gallery.json", gallery)

    leaderboard = read_progress_records(save_dir, "_leaderboard.json")
    cleaned: list[dict[str, Any]] = []
    for entry in leaderboard:
        try:
            item = dict(entry)
            item["score"] = int(item.get("score", 0))
            item["path_count"] = int(item.get("path_count", item.get("decisions", 0)))
        except (TypeError, ValueError):
            continue
        cleaned.append(item)
    same_run = any(
        item.get("run_id") == run_id
        or (
            not item.get("run_id")
            and item.get("player_name", item.get("player", "")) == game.player_name
            and item.get("title", item.get("ending", "")) == ending_title
            and int(item.get("path_count", item.get("decisions", -1))) == len(game.path_history)
            and int(item.get("score", -1)) == int(summary["score"])
        )
        for item in cleaned
    )
    if not same_run:
        cleaned.append({
            "player_name": game.player_name,
            "player": game.player_name,
            "title": ending_title,
            "ending": ending_title,
            "rank": summary["rank"],
            "score": summary["score"],
            "path_count": len(game.path_history),
            "decisions": len(game.path_history),
            "achieved_at": achieved_at,
            "date": datetime.now().strftime("%m-%d %H:%M"),
            "run_id": run_id,
        })
    cleaned.sort(key=lambda item: (-int(item.get("score", 0)), int(item.get("path_count", 0))))
    _write_progress_records(save_dir, "_leaderboard.json", cleaned[:50])

    progression = record_progression(save_dir, game, ending_title)
    return {
        "record": record,
        "summary": summary,
        "gallery": gallery,
        "is_new": not existing,
        "is_new_attempt": not same_run,
        "progression": progression,
    }


def record_bonus_ending(save_dir: str, game: Any, nodes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """按统一结算规则记录全结局后的隐藏结局。"""

    if not bonus_ending_available(save_dir, nodes):
        unlocked = {
            str(entry.get("title", ""))
            for entry in read_progress_records(save_dir, "_gallery.json")
        }
        if BONUS_ENDING_TITLE in unlocked:
            raise ValueError("bonus_completed")
        raise ValueError("bonus_locked")
    return record_ending(save_dir, game, nodes, ending_title=BONUS_ENDING_TITLE)


def check_achievements(
    save_dir: str,
    data_dir: str,
    game: Any,
    nodes: dict[str, dict[str, Any]],
    *,
    viewed_gallery: bool = False,
    viewed_destiny_map: bool = False,
    changed_settings: bool = False,
) -> list[dict[str, Any]]:
    """使用同一份 data/achievements.json 检查所有入口的成就。"""

    from achievement_system import AchievementSystem

    ensure_gameplay_state(game)
    system = AchievementSystem(data_dir)
    system.load_unlocked(save_dir)
    progression = load_progression(save_dir)
    if viewed_gallery or viewed_destiny_map or changed_settings:
        progression = update_progression(
            save_dir,
            flags={
                "viewed_gallery": viewed_gallery,
                "viewed_destiny_map": viewed_destiny_map,
                "changed_settings": changed_settings,
            },
        )
    gallery = read_progress_records(save_dir, "_gallery.json")
    node = nodes.get(game.current_node, {})
    is_ending = not node.get("choices")
    ending_title = str(node.get("title", ""))
    summary = score_summary(game, ending_title) if is_ending else {}
    cumulative_artifacts = list(dict.fromkeys(
        list(progression.get("artifacts", [])) + list(game.artifacts)
    ))
    initial_attrs = game.flags.get("initial_attrs")
    if not isinstance(initial_attrs, dict):
        initial_attrs = game.attrs
    trigger_context = {
        "node_id": game.current_node,
        "attrs": game.attrs,
        "resources": game.resources,
        "artifacts": cumulative_artifacts,
        "reputation": game.reputation,
        "affinity": game.affinity,
        "is_ending": is_ending,
        "route": infer_route(game.current_node, node),
        "rank": summary.get("rank", "C"),
        "score": summary.get("score", 0),
        "path_length": len(game.path_history),
        "ending_count": len(gallery),
        "insights": game.flags.get("insights", []),
        "legacy_points": progression.get("legacy_points", 0),
        "save_count": progression.get("save_count", 0),
        "quick_restart_count": progression.get("quick_restart_count", 0),
        "viewed_gallery": progression.get("viewed_gallery", False),
        "viewed_destiny_map": progression.get("viewed_destiny_map", False),
        "changed_settings": progression.get("changed_settings", False),
        "is_zero_start": all(int(value) == 5 for value in initial_attrs.values()),
    }
    newly_unlocked = system.check_achievements(trigger_context)
    if newly_unlocked:
        system.save_unlocked(save_dir)
    return newly_unlocked


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
