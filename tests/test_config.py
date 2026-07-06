import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from ssg.config import SiteConfig, load_config, BUILTIN_EXCLUDE_DIRS


class ConfigTests(unittest.TestCase):
    def test_defaults_when_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(Path(tmp))
        self.assertEqual(cfg.title, "Real-Fruit-Snacks")
        self.assertEqual(cfg.homepage, "Home.md")
        self.assertEqual(cfg.exclude, [])
        self.assertIn(".png", cfg.asset_extensions)

    def test_loads_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "site.config.json").write_text(
                json.dumps({"title": "My Vault", "homepage": "Start.md",
                            "exclude": ["Private"], "asset_extensions": [".PNG"]}),
                encoding="utf-8")
            cfg = load_config(Path(tmp))
        self.assertEqual(cfg.title, "My Vault")
        self.assertEqual(cfg.homepage, "Start.md")
        self.assertEqual(cfg.exclude, ["Private"])
        self.assertEqual(cfg.asset_extensions, [".png"])

    def test_description_default_and_parse(self):
        self.assertEqual(SiteConfig().description, "")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "site.config.json").write_text(
                json.dumps({"description": "A vault of notes.", "site_url": "https://x.test"}),
                encoding="utf-8")
            cfg = load_config(Path(tmp))
        self.assertEqual(cfg.description, "A vault of notes.")
        self.assertEqual(cfg.site_url, "https://x.test")

    def test_builtin_excludes_cover_build_output_names(self):
        # Only names the build's own output can collide with are reserved;
        # everything else inside the Notes/ vault publishes.
        for d in ("public", "_tags"):
            self.assertIn(d, BUILTIN_EXCLUDE_DIRS)
        for d in ("docs", "tools", "tests", "site-assets"):
            self.assertNotIn(d, BUILTIN_EXCLUDE_DIRS)

    def test_invalid_json_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "site.config.json").write_text("{not json", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                cfg = load_config(Path(tmp))
        self.assertEqual(cfg.title, "Real-Fruit-Snacks")

    def test_non_object_json_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "site.config.json").write_text("[1, 2]", encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                cfg = load_config(Path(tmp))
        self.assertEqual(cfg.homepage, "Home.md")

    def test_asset_extensions_normalized_to_dot_prefixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "site.config.json").write_text(
                json.dumps({"asset_extensions": ["PNG", ".Jpg"]}), encoding="utf-8")
            cfg = load_config(Path(tmp))
        self.assertEqual(cfg.asset_extensions, [".png", ".jpg"])

    def test_site_url_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "site.config.json").write_text(
                json.dumps({"site_url": "https://example.test/vault/"}),
                encoding="utf-8")
            cfg = load_config(Path(tmp))
        self.assertEqual(cfg.site_url, "https://example.test/vault/")

    def test_site_url_defaults_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(Path(tmp))
        self.assertEqual(cfg.site_url, "")

    def test_banner_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(Path(tmp))
        self.assertFalse(cfg.banner_enabled)
        self.assertEqual(cfg.banner_text, "")
        self.assertEqual(cfg.banner_style, "info")

    def test_banner_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "site.config.json").write_text(
                json.dumps({"banner_enabled": True, "banner_text": "Heads up",
                            "banner_style": "warn"}), encoding="utf-8")
            cfg = load_config(Path(tmp))
        self.assertTrue(cfg.banner_enabled)
        self.assertEqual(cfg.banner_text, "Heads up")
        self.assertEqual(cfg.banner_style, "warn")

    def test_banner_bad_style_warns_and_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "site.config.json").write_text(
                json.dumps({"banner_style": "neon"}), encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cfg = load_config(Path(tmp))
        self.assertEqual(cfg.banner_style, "info")
        self.assertIn("banner_style", buf.getvalue())

    def test_banner_type_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "site.config.json").write_text(
                json.dumps({"banner_enabled": "yes", "banner_text": 42}),
                encoding="utf-8")
            cfg = load_config(Path(tmp))
        self.assertFalse(cfg.banner_enabled)
        self.assertEqual(cfg.banner_text, "")

    def test_underscore_keys_are_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "site.config.json").write_text(
                json.dumps({"_banner_style_options": "info | warn",
                            "_title": "should not apply", "title": "Kept"}),
                encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                cfg = load_config(Path(tmp))
        self.assertEqual(cfg.title, "Kept")

    def test_pet_defaults_off_and_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = load_config(Path(tmp))
        self.assertFalse(cfg.pet_enabled)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "site.config.json").write_text(
                json.dumps({"pet_enabled": True}), encoding="utf-8")
            cfg = load_config(Path(tmp))
        self.assertTrue(cfg.pet_enabled)
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "site.config.json").write_text(
                json.dumps({"pet_enabled": "yes"}), encoding="utf-8")
            cfg = load_config(Path(tmp))
        self.assertFalse(cfg.pet_enabled)


if __name__ == "__main__":
    unittest.main()
