"""平台无关的游戏状态与选择结算引擎。"""

from __future__ import annotations

import copy
import random
from typing import Any

from .story import NODES


ATTR_NAMES = ["根骨", "幸运", "魅力", "精神", "悟性"]
ATTR_MIN = 5
ATTR_TOTAL = 100


def _to_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_to_tuple(item) for item in value)
    return value

TRAITS = {
    "1": {"name": "天生剑骨", "desc": "根骨+10，自幼筋骨异于常人", "bonus": {"根骨": 10}},
    "2": {"name": "天命所归", "desc": "幸运+15，冥冥中有气运加身", "bonus": {"幸运": 15}},
    "3": {"name": "龙凤之姿", "desc": "魅力+15，天生一副好皮囊", "bonus": {"魅力": 15}},
    "4": {"name": "心如磐石", "desc": "精神+15，意志坚不可摧", "bonus": {"精神": 15}},
    "5": {"name": "七窍玲珑", "desc": "悟性+15，一点即通举一反三", "bonus": {"悟性": 15}},
    "6": {
        "name": "天道酬勤",
        "desc": "五项各+4，全面均衡发展",
        "bonus": {"根骨": 4, "幸运": 4, "魅力": 4, "精神": 4, "悟性": 4},
    },
}


DEFAULT_RESOURCES = {"灵石": 0, "心魔": 0, "历练": 0, "丹药": 0, "轮回": 0}
DEFAULT_REPUTATION = {"正道": 0, "魔道": 0, "散修": 0}


def validate_attrs(attrs: Any) -> dict[str, int]:
    """验证并规范化角色创建属性。允许少分配，但不允许越界。"""

    if not isinstance(attrs, dict):
        raise ValueError("属性格式错误")
    unknown = sorted(set(attrs) - set(ATTR_NAMES))
    if unknown:
        raise ValueError(f"存在未知属性: {', '.join(unknown)}")

    try:
        normalized = {}
        for name in ATTR_NAMES:
            raw = attrs.get(name, ATTR_MIN)
            if isinstance(raw, bool) or (isinstance(raw, float) and not raw.is_integer()):
                raise ValueError
            normalized[name] = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("属性必须是整数") from exc
    if any(value < ATTR_MIN for value in normalized.values()):
        raise ValueError(f"每项属性不能低于{ATTR_MIN}")
    if sum(normalized.values()) > ATTR_TOTAL:
        raise ValueError(f"属性总和超过{ATTR_TOTAL}")
    return normalized


def apply_character_setup(
    game: "Game",
    attrs: Any,
    trait_key: str = "1",
    fortune_bonus: int = 0,
    legacy_bonus: int = 0,
) -> dict[str, int]:
    """把角色创建结果写入状态，供 Web、桌面端和测试共用。"""

    normalized = validate_attrs(attrs)
    initial_attrs = dict(normalized)
    trait = TRAITS.get(str(trait_key), TRAITS["1"])
    for name, bonus in trait["bonus"].items():
        normalized[name] += int(bonus)
    normalized["幸运"] += int(fortune_bonus) + int(legacy_bonus)

    game.trait = trait["name"]
    game.attrs = normalized
    game.current_node = "start"
    game.path_history = []
    game.reset_run_state()
    game.flags["initial_attrs"] = initial_attrs
    if legacy_bonus:
        game.resources["轮回"] = int(legacy_bonus)
    return normalized


def _value(game: "Game", name: str) -> int:
    if name in game.attrs:
        value = int(game.attrs[name])
    else:
        value = int(game.resources.get(name, 0))
    if name == "根骨" and "青霜剑" in getattr(game, "artifacts", []):
        value += 5
    if name == "悟性" and "药王鼎" in getattr(game, "artifacts", []):
        value += 3
    return value


def _apply_effect(game: "Game", effects: dict[str, Any]) -> None:
    for name, delta in effects.items():
        if name in game.attrs:
            game.attrs[name] += int(delta)
        elif name in game.resources:
            game.resources[name] += int(delta)
        elif name in game.reputation:
            game.reputation[name] += int(delta)
        elif name in game.affinity:
            game.affinity[name] += int(delta)


def resolve_choice(
    game: "Game",
    choice_index: int,
    nodes: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """执行一次选择，并让所有前端得到一致的判定、奖励和反馈。"""

    from playability import (
        apply_node_rewards,
        diff_feedback,
        ensure_gameplay_state,
        maybe_random_event,
        snapshot,
    )

    story = nodes or NODES
    try:
        if isinstance(choice_index, bool) or (
            isinstance(choice_index, float) and not choice_index.is_integer()
        ):
            raise ValueError
        index = int(choice_index)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid_choice") from exc

    node = story.get(game.current_node)
    if not node or index < 0 or index >= len(node.get("choices", [])):
        raise ValueError("invalid_choice")

    ensure_gameplay_state(game)
    before = snapshot(game)
    previous_node_id = game.current_node
    game.path_history.append(previous_node_id)
    choice = node["choices"][index]
    feedback = [f"你选择了：{choice.get('text', '')}"]

    requirements = choice.get("require", {})
    passed = all(_value(game, name) >= int(value) for name, value in requirements.items())
    if requirements and passed:
        desc = "、".join(f"{name}≥{value}" for name, value in requirements.items())
        feedback.append(f"判定通过：{desc}")

    # 新手前四步允许最多 5 点的低差距判定通过，避免首次体验被随机卡死。
    if requirements and not passed and len(game.path_history) <= 4 and "fail" in choice:
        shortest = min(_value(game, name) - int(value) for name, value in requirements.items())
        if shortest >= -5:
            passed = True
            feedback.append("初入仙途的机缘护住了你，本次低差距判定勉强通过。")

    # 先按选择前的状态判定，再结算选择本身的收益或代价。
    _apply_effect(game, choice.get("effect", {}))

    # 太虚令只对明确的秘境/洞府风险提供一次重判。
    if (
        not passed
        and "fail" in choice
        and "太虚令" in getattr(game, "artifacts", [])
        and not game.flags.get("taixu_reroll_used")
        and any(word in choice.get("text", "") for word in ("秘境", "洞府"))
    ):
        game.flags["taixu_reroll_used"] = True
        passed = True
        feedback.append("太虚令替你重判一次，秘境凶险暂时退去。")

    if not passed and "fail" in choice:
        feedback.append("判定失败：能力不足，命运转向更艰难的路线。")
        target = choice["fail"]
    else:
        target = choice.get("next", game.current_node)

    if target not in story:
        raise ValueError("story_target_missing")
    game.current_node = target
    feedback.extend(apply_node_rewards(game, target, story[target]))
    feedback.extend(maybe_random_event(game))
    feedback.extend(diff_feedback(before, game))
    return {
        "from": previous_node_id,
        "passed": passed,
        "feedback": feedback,
        "choice": choice.get("text", ""),
    }


class Game:
    """不依赖 UI 的单局状态。"""

    def __init__(self) -> None:
        self.current_node = "start"
        self.player_name = ""
        self.path_history: list[str] = []
        self.attrs = {name: 20 for name in ATTR_NAMES}
        self.trait = ""
        self.artifacts: list[str] = []
        self.inventory: list[str] = []
        self.affinity: dict[str, int] = {}
        self.reputation = dict(DEFAULT_REPUTATION)
        self.resources = dict(DEFAULT_RESOURCES)
        self.flags: dict[str, Any] = {"rewarded_nodes": [], "insights": [], "minigames": []}
        self.start_time = None
        self.challenge_mode = False
        self.combat_stats = {"hp": 100, "max_hp": 100}
        self.rng = random.Random()

    def reset_run_state(self) -> None:
        self.artifacts = []
        self.inventory = []
        self.affinity = {}
        self.reputation = dict(DEFAULT_REPUTATION)
        self.resources = dict(DEFAULT_RESOURCES)
        self.flags = {"rewarded_nodes": [], "insights": [], "minigames": []}
        self.rng.seed()

    def checkpoint(self) -> dict[str, Any]:
        return copy.deepcopy(
            {
                "current_node": self.current_node,
                "path_history": self.path_history,
                "attrs": self.attrs,
                "trait": self.trait,
                "artifacts": self.artifacts,
                "inventory": self.inventory,
                "affinity": self.affinity,
                "reputation": self.reputation,
                "resources": self.resources,
                "flags": self.flags,
                "rng_state": self.rng.getstate(),
            }
        )

    def restore_checkpoint(self, checkpoint: dict[str, Any]) -> None:
        for key, value in checkpoint.items():
            if key == "rng_state":
                self.rng.setstate(_to_tuple(value))
            else:
                setattr(self, key, copy.deepcopy(value))

    def make_choice(self, choice_idx: int) -> dict[str, Any]:
        return resolve_choice(self, choice_idx)

    def load_data(self, data: dict[str, Any]) -> None:
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("current_node", "start"), str)
            or data.get("current_node", "start") not in NODES
        ):
            raise ValueError("存档节点不存在")
        self.player_name = data.get("player_name", "叶尘")
        self.current_node = data.get("current_node", "start")
        self.path_history = list(data.get("path_history", []))
        self.attrs = dict(data.get("attrs", {name: 20 for name in ATTR_NAMES}))
        self.trait = data.get("trait", "")
        self.artifacts = list(data.get("artifacts", []))
        self.inventory = list(data.get("inventory", []))
        self.affinity = dict(data.get("affinity", {}))
        self.reputation = dict(data.get("reputation", DEFAULT_REPUTATION))
        self.resources = dict(data.get("resources", DEFAULT_RESOURCES))
        self.flags = dict(data.get("flags", {"rewarded_nodes": [], "insights": []}))
        rng_state = data.get("rng_state")
        if rng_state is not None:
            try:
                self.rng.setstate(_to_tuple(rng_state))
            except (TypeError, ValueError, IndexError, OverflowError):
                self.rng.seed()

        from playability import ensure_gameplay_state

        ensure_gameplay_state(self)
