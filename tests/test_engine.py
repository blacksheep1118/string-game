# -*- coding: utf-8 -*-
import unittest

from xiantu.engine import ATTR_NAMES, Game, apply_character_setup
from xiantu.story import NODES


class EngineTest(unittest.TestCase):
    def test_character_setup_and_checkpoint_restore_all_state(self):
        game = Game()
        game.player_name = "测试"
        game.resources["灵石"] = 9
        apply_character_setup(game, {name: 20 for name in ATTR_NAMES}, "2", legacy_bonus=3)
        self.assertEqual(game.trait, "天命所归")
        self.assertEqual(game.resources["轮回"], 3)

        checkpoint = game.checkpoint()
        result = game.make_choice(0)
        self.assertEqual(result["from"], "start")
        self.assertEqual(game.path_history, ["start"])
        self.assertNotEqual(game.current_node, "start")

        game.restore_checkpoint(checkpoint)
        self.assertEqual(game.current_node, "start")
        self.assertEqual(game.path_history, [])
        self.assertEqual(game.resources["轮回"], 3)

    def test_engine_accepts_more_than_two_choices(self):
        game = Game()
        game.current_node = "pill_choice_branch"
        game.attrs = {name: 30 for name in ATTR_NAMES}
        result = game.make_choice(2)
        self.assertEqual(result["from"], "pill_choice_branch")
        self.assertEqual(game.current_node, "pill_battle_style_1")

    def test_story_loader_is_the_runtime_source(self):
        self.assertEqual(NODES["start"]["title"], "序章 · 天降机缘")
        self.assertEqual(sum(1 for node in NODES.values() if not node.get("choices")), 79)


if __name__ == "__main__":
    unittest.main()
