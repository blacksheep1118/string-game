# -*- coding: utf-8 -*-
import tempfile
import unittest

import server
from playability import get_goal, infer_route


class ServerApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_save_dir = server.SAVE_DIR
        server.SAVE_DIR = self.tmp.name
        server.games.clear()
        server.game_last_seen.clear()
        self.client = server.app.test_client()

    def tearDown(self):
        server.SAVE_DIR = self.old_save_dir
        self.tmp.cleanup()

    def test_rejects_negative_choice_index(self):
        self.client.post("/api/new_game", json={"session_id": "t"})
        self.client.post("/api/set_attrs", json={
            "session_id": "t",
            "attrs": {"根骨": 20, "幸运": 20, "魅力": 20, "精神": 20, "悟性": 20},
            "trait": "1",
        })
        response = self.client.post("/api/choice", json={"session_id": "t", "choice": -1})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "invalid_choice")

    def test_rejects_malformed_session_and_incomplete_setup(self):
        malformed = self.client.post("/api/new_game", json={"session_id": []})
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(malformed.get_json()["code"], "invalid_session")

        self.client.post("/api/new_game", json={"session_id": "t"})
        incomplete = self.client.post("/api/choice", json={"session_id": "t", "choice": 0})
        self.assertEqual(incomplete.status_code, 409)
        self.assertEqual(incomplete.get_json()["code"], "setup_required")

    def test_rejects_fractional_choice_index(self):
        self.client.post("/api/new_game", json={"session_id": "t"})
        self.client.post("/api/set_attrs", json={
            "session_id": "t",
            "attrs": {"根骨": 20, "幸运": 20, "魅力": 20, "精神": 20, "悟性": 20},
            "trait": "1",
        })
        response = self.client.post("/api/choice", json={"session_id": "t", "choice": 0.5})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "invalid_choice")

    def test_rejects_non_integer_attrs(self):
        self.client.post("/api/new_game", json={"session_id": "t"})
        response = self.client.post("/api/set_attrs", json={
            "session_id": "t",
            "attrs": {"根骨": "bad"},
            "trait": "1",
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "invalid_attr_value")

    def test_static_frontend_assets_are_served(self):
        for path in ["/", "/style.css", "/app.js", "/manifest.json", "/service-worker.js"]:
            response = self.client.get(path)
            try:
                self.assertEqual(response.status_code, 200, path)
            finally:
                response.close()

    def test_choice_returns_feedback_and_resources(self):
        self.client.post("/api/new_game", json={"session_id": "t"})
        self.client.post("/api/set_attrs", json={
            "session_id": "t",
            "attrs": {"根骨": 20, "幸运": 20, "魅力": 20, "精神": 20, "悟性": 20},
            "trait": "1",
        })
        response = self.client.post("/api/choice", json={"session_id": "t", "choice": 0})
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertIn("feedback", payload)
        self.assertIn("resources", payload)
        self.assertIn("goal", payload)
        self.assertTrue(any("旅途阅历" in item for item in payload["feedback"]))

    def test_route_trial_endpoint_is_single_use(self):
        self.client.post("/api/new_game", json={"session_id": "t"})
        self.client.post("/api/set_attrs", json={
            "session_id": "t",
            "attrs": {"根骨": 20, "幸运": 20, "魅力": 20, "精神": 20, "悟性": 20},
            "trait": "1",
        })
        server.games["t"].current_node = "sword_tactic"
        state = self.client.post("/api/state", json={"session_id": "t"}).get_json()
        self.assertEqual(state["mini_game"]["type"], "combat")
        result = self.client.post("/api/mini_game", json={"session_id": "t", "action": "defend"})
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.get_json()["mini_game"]["completed"])
        self.assertTrue(result.get_json()["feedback"])

        repeated = self.client.post("/api/mini_game", json={"session_id": "t", "action": "defend"})
        self.assertEqual(repeated.status_code, 400)
        self.assertEqual(repeated.get_json()["code"], "mini_game_completed")

    def test_destiny_map_endpoint(self):
        response = self.client.post("/api/destiny_map", json={"session_id": "none"})
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["map"]["branches"])

    def test_story_stats_are_data_driven(self):
        response = self.client.get("/api/story_stats")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["nodes"], len(server.NODES))
        self.assertEqual(response.get_json()["endings"], 79)
        self.assertEqual(response.get_json()["total_endings"], 80)

    def test_bonus_ending_is_locked_until_gallery_is_complete(self):
        self.client.post("/api/new_game", json={"session_id": "t"})
        self.client.post("/api/set_attrs", json={
            "session_id": "t",
            "attrs": {"根骨": 20, "幸运": 20, "魅力": 20, "精神": 20, "悟性": 20},
            "trait": "1",
        })
        response = self.client.post("/api/bonus_ending", json={"session_id": "t"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "bonus_locked")

    def test_record_ending_updates_gallery_and_leaderboard(self):
        self.client.post("/api/new_game", json={"session_id": "t"})
        game = server.games["t"]
        game.current_node = "end_sword_god"
        response = self.client.post("/api/record_ending", json={"session_id": "t"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["is_new"])
        self.assertEqual(len(self.client.get("/api/gallery").get_json()), 1)
        self.assertEqual(len(self.client.get("/api/leaderboard").get_json()), 1)
        unlocked = {item["id"] for item in response.get_json()["achievements"]}
        self.assertIn("first_ending", unlocked)

        repeated = self.client.post("/api/record_ending", json={"session_id": "t"})
        self.assertEqual(repeated.status_code, 200)
        self.assertFalse(repeated.get_json()["is_new"])
        self.assertEqual(len(self.client.get("/api/leaderboard").get_json()), 1)

    def test_rejects_unsafe_overwrite_and_imported_runtime_values(self):
        self.client.post("/api/new_game", json={"session_id": "t"})
        self.client.post("/api/set_attrs", json={
            "session_id": "t",
            "attrs": {"根骨": 20, "幸运": 20, "魅力": 20, "精神": 20, "悟性": 20},
            "trait": "1",
        })
        unsafe = self.client.post("/api/save", json={
            "session_id": "t",
            "overwrite": "x' onmouseover='alert(1)",
        })
        self.assertEqual(unsafe.status_code, 400)
        self.assertEqual(unsafe.get_json()["code"], "invalid_filename")

        invalid = self.client.post("/api/import_save", json={
            "save": {
                "current_node": "start",
                "attrs": {"根骨": -999999},
            }
        })
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.get_json()["code"], "invalid_save")

    def test_record_ending_rejects_story_node_with_choices(self):
        self.client.post("/api/new_game", json={"session_id": "t"})
        response = self.client.post("/api/record_ending", json={"session_id": "t"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["code"], "not_ending")

    def test_chapter_zero_goal_and_neutral_route(self):
        self.assertIn("缘起", get_goal("第〇章 · 一念之善"))
        self.assertEqual(infer_route("help_old", {"title": "第〇章 · 一念之善", "text": "老人求水"}), "未定")


if __name__ == "__main__":
    unittest.main()
