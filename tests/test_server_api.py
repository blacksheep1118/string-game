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

    def test_destiny_map_endpoint(self):
        response = self.client.post("/api/destiny_map", json={"session_id": "none"})
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["map"]["branches"])

    def test_chapter_zero_goal_and_neutral_route(self):
        self.assertIn("缘起", get_goal("第〇章 · 一念之善"))
        self.assertEqual(infer_route("help_old", {"title": "第〇章 · 一念之善", "text": "老人求水"}), "未定")


if __name__ == "__main__":
    unittest.main()
