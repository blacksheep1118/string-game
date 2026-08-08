# -*- coding: utf-8 -*-
import tempfile
import unittest
import json
from pathlib import Path

from playability import (
    BONUS_ENDING_TITLE,
    bonus_ending_available,
    check_achievements,
    mini_game_for,
    load_progression,
    record_bonus_ending,
    record_ending,
    resolve_mini_game,
    update_progression,
)
from xiantu.engine import ATTR_NAMES, Game
from xiantu.story import NODES


class PlayabilityPersistenceTest(unittest.TestCase):
    def setUp(self):
        self.data_dir = str(Path(__file__).resolve().parents[1] / "data")
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_shared_ending_settlement_and_achievement_state(self):
        game = Game()
        game.player_name = "测试"
        game.trait = "天生剑骨"
        game.attrs = {name: 20 for name in ATTR_NAMES}
        game.current_node = "end_sword_god"

        settlement = record_ending(self.tmp.name, game, NODES)
        self.assertTrue(settlement["is_new"])
        self.assertEqual(len(settlement["gallery"]), 1)
        self.assertIn("score", settlement["record"])
        self.assertIn("rank", settlement["record"])

        unlocked = check_achievements(self.tmp.name, self.data_dir, game, NODES)
        unlocked_ids = {item["id"] for item in unlocked}
        self.assertIn("first_ending", unlocked_ids)

        repeated = record_ending(self.tmp.name, game, NODES)
        self.assertFalse(repeated["is_new"])
        self.assertEqual(len(repeated["gallery"]), 1)

    def test_progression_counters_and_flags_are_normalized(self):
        update_progression(
            self.tmp.name,
            increments={"save_count": 1, "quick_restart_count": 2},
            flags={"viewed_gallery": True},
        )
        progression = load_progression(self.tmp.name)
        self.assertEqual(progression["save_count"], 1)
        self.assertEqual(progression["quick_restart_count"], 2)
        self.assertTrue(progression["viewed_gallery"])
        self.assertFalse(progression["changed_settings"])

    def test_route_trial_is_rewarded_once_and_persisted_in_game_state(self):
        game = Game()
        game.player_name = "测试"
        game.trait = "天生剑骨"
        game.current_node = "sword_tactic"
        game.attrs = {name: 20 for name in ATTR_NAMES}

        panel = mini_game_for(game.current_node, NODES[game.current_node], game)
        self.assertEqual(panel["type"], "combat")
        self.assertFalse(panel["completed"])
        self.assertIsNone(mini_game_for("end_sword_god", NODES["end_sword_god"], game))

        feedback = resolve_mini_game(game, game.current_node, "defend")
        self.assertTrue(feedback)
        self.assertEqual(game.resources["历练"], 1)
        self.assertTrue(mini_game_for(game.current_node, NODES[game.current_node], game)["completed"])
        with self.assertRaisesRegex(ValueError, "mini_game_completed"):
            resolve_mini_game(game, game.current_node, "defend")

    def test_bonus_ending_uses_shared_settlement_after_all_story_endings(self):
        normal_titles = [
            node["title"] for node in NODES.values() if not node.get("choices")
        ]
        with open(Path(self.tmp.name) / "_gallery.json", "w", encoding="utf-8") as stream:
            json.dump([{"title": title} for title in normal_titles], stream, ensure_ascii=False)

        self.assertTrue(bonus_ending_available(self.tmp.name, NODES))
        game = Game()
        game.player_name = "全结局玩家"
        game.trait = "万法归一"
        game.attrs = {name: 99 for name in ATTR_NAMES}
        settlement = record_bonus_ending(self.tmp.name, game, NODES)
        self.assertIn(BONUS_ENDING_TITLE, {item["title"] for item in settlement["gallery"]})
        self.assertEqual(settlement["summary"]["rank"], "SS")
        self.assertFalse(bonus_ending_available(self.tmp.name, NODES))


if __name__ == "__main__":
    unittest.main()
