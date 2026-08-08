# -*- coding: utf-8 -*-
import tempfile
import unittest
import json
from pathlib import Path

from game import ATTR_NAMES, Game, NODES
from save_manager import load_save, safe_filename, save_game, validate_save_payload
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
        quality = graph_quality(NODES)
        self.assertEqual(quality["unreachable"], [])
        self.assertEqual(len(quality["endings"]), 79)
        self.assertEqual(quality["semantic_duplicates"], [])

    def test_story_validator_handles_bad_choice_shape(self):
        errors = validate_nodes({"start": {"title": "t", "text": "x", "choices": ["bad"]}}, ATTR_NAMES)
        self.assertIn("start.choices[0]: 必须是对象", errors)

    def test_story_validator_rejects_malformed_effects(self):
        errors = validate_nodes({
            "start": {
                "title": "t",
                "text": "x",
                "choices": [{"text": "a", "next": "end", "effect": None}],
            },
            "end": {"title": "e", "text": "done", "choices": []},
        }, ATTR_NAMES)
        self.assertIn("start.choices[0].effect: 必须是对象", errors)

    def test_achievement_ending_references_match_story(self):
        data_path = Path(__file__).resolve().parents[1] / "data" / "achievements.json"
        achievements = json.loads(data_path.read_text(encoding="utf-8"))["achievements"]
        endings = {node_id for node_id, node in NODES.items() if not node.get("choices")}
        for achievement in achievements:
            trigger = achievement.get("trigger", {})
            if trigger.get("type") == "ending_id":
                self.assertIn(trigger.get("ending"), endings, achievement.get("id"))
        all_endings = next(a for a in achievements if a.get("id") == "all_endings")
        self.assertEqual(all_endings["trigger"]["count"], len(endings))
        pill_true = next(a for a in achievements if a.get("id") == "pill_true_ending")
        self.assertEqual(pill_true["trigger"]["ending"], "end_pill_saint")

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
        self.assertEqual(len(quality["semantic_duplicates"]), 1)

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

    def test_save_filename_cannot_escape_runtime_directory(self):
        self.assertEqual(safe_filename("../outside.json"), "outside.json")
        self.assertEqual(safe_filename(".."), "")
        self.assertEqual(safe_filename(None), "")


if __name__ == "__main__":
    unittest.main()
