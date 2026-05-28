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


if __name__ == "__main__":
    unittest.main()
