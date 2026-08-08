# -*- coding: utf-8 -*-
from pathlib import Path
import json
import unittest


BASE_DIR = Path(__file__).resolve().parents[1]


class StaticAssetsTest(unittest.TestCase):
    def test_frontend_assets_are_split_and_linked(self):
        html = (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('/style.css', html)
        self.assertIn('/app.js', html)
        self.assertNotIn('<style>', html)
        self.assertNotIn('<script>', html)

    def test_pwa_manifest_is_valid_json(self):
        manifest = json.loads((BASE_DIR / "static" / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["short_name"], "仙途")
        self.assertTrue(manifest["icons"])

    def test_service_worker_caches_all_local_javascript_entrypoints(self):
        worker = (BASE_DIR / "static" / "service-worker.js").read_text(encoding="utf-8")
        self.assertIn("'/app.js'", worker)
        self.assertIn("'/js/animations.js'", worker)

    def test_frontend_does_not_reference_removed_start_screen_handler(self):
        app_js = (BASE_DIR / "static" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("showStartScreen", app_js)


if __name__ == "__main__":
    unittest.main()
