# -*- coding: utf-8 -*-
import tempfile
import unittest

from game import ATTR_NAMES, Game, NODES
from save_manager import load_save, save_game, validate_save_payload
from story_tools import validate_nodes


class StoryIntegrityTest(unittest.TestCase):
    def test_story_graph_is_valid(self):
        self.assertEqual(validate_nodes(NODES, ATTR_NAMES), [])

    def test_story_validator_handles_bad_choice_shape(self):
        errors = validate_nodes({"start": {"title": "t", "text": "x", "choices": ["bad"]}}, ATTR_NAMES)
        self.assertIn("start.choices[0]: 必须是对象", errors)

    def test_save_roundtrip_uses_schema_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Game()
            game.player_name = "测试"
            game.attrs = {name: 20 for name in ATTR_NAMES}
            filename, data = save_game(tmp, game, NODES)
            loaded = load_save(tmp, filename)
            self.assertGreaterEqual(loaded["schema_version"], 2)
            self.assertEqual(loaded["player_name"], data["player_name"])

    def test_imported_save_rejects_missing_node(self):
        with self.assertRaises(ValueError):
            validate_save_payload({"current_node": "missing-node"}, NODES, ATTR_NAMES)

    def test_imported_save_rejects_non_integer_attrs(self):
        with self.assertRaises(ValueError):
            validate_save_payload({"current_node": "start", "attrs": {"根骨": "bad"}}, NODES, ATTR_NAMES)


if __name__ == "__main__":
    unittest.main()
