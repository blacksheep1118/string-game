# -*- coding: utf-8 -*-
import tempfile
import unittest

from game import ATTR_NAMES, Game, NODES
from save_manager import load_save, save_game, validate_save_payload
from story_tools import (
    duplicate_destinations,
    ending_nodes,
    graph_quality,
    placeholder_nodes,
    reachable_nodes,
    validate_nodes,
)


class StoryIntegrityTest(unittest.TestCase):
    def test_story_graph_is_valid(self):
        self.assertEqual(validate_nodes(NODES, ATTR_NAMES), [])

    def test_story_validator_handles_bad_choice_shape(self):
        errors = validate_nodes({"start": {"title": "t", "text": "x", "choices": ["bad"]}}, ATTR_NAMES)
        self.assertIn("start.choices[0]: 必须是对象", errors)

    def test_graph_quality_helpers(self):
        nodes = {
            "start": {
                "title": "t",
                "text": "x",
                "choices": [
                    {"text": "a", "next": "end"},
                    {"text": "b", "next": "end"},
                ],
            },
            "end": {"title": "e", "text": "done", "choices": []},
            "orphan": {"title": "o", "text": "unused", "choices": []},
        }
        self.assertEqual(reachable_nodes(nodes), {"start", "end"})
        self.assertEqual(ending_nodes(nodes), {"end", "orphan"})
        self.assertEqual(placeholder_nodes(nodes), [])
        self.assertEqual(
            duplicate_destinations(nodes),
            [{"node": "start", "target": "end", "choices": [0, 1]}],
        )
        quality = graph_quality(nodes)
        self.assertEqual(quality["unreachable"], ["orphan"])
        self.assertEqual(quality["endings"], ["end", "orphan"])

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
