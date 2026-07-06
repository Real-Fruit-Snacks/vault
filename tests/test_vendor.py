import unittest
from pathlib import Path

import ssg  # noqa: F401  (installs the vendor path)

REPO = Path(__file__).resolve().parent.parent


class VendorImports(unittest.TestCase):
    def test_python_packages_import(self):
        import markdown_it
        import mdit_py_plugins
        import yaml
        import pygments
        self.assertTrue(markdown_it.__file__ and "vendor" in markdown_it.__file__)
        self.assertTrue(pygments.__file__ and "vendor" in pygments.__file__)
        self.assertTrue(yaml.__file__ and "vendor" in yaml.__file__)
        self.assertTrue(mdit_py_plugins.__file__ and "vendor" in mdit_py_plugins.__file__)

    def test_markdown_it_renders(self):
        from markdown_it import MarkdownIt
        html = MarkdownIt("commonmark").render("**hi**")
        self.assertIn("<strong>hi</strong>", html)

    def test_client_assets_present(self):
        for rel in [
            "site-assets/tokens.css",
            "site-assets/mermaid.min.js",
            "site-assets/minisearch.min.js",
            "site-assets/mermaid-LICENSE.txt",
            "site-assets/minisearch-LICENSE.txt",
            "site-assets/fonts/JetBrainsMono-Regular.woff2",
            "site-assets/fonts/JetBrainsMono-Bold.woff2",
            "site-assets/fonts/JetBrainsMono-Italic.woff2",
            "site-assets/fonts/JetBrainsMono-BoldItalic.woff2",
            "site-assets/fonts/InterVariable.woff2",
            "site-assets/fonts/InterVariable-Italic.woff2",
            "site-assets/fonts/OFL-JetBrainsMono.txt",
            "site-assets/fonts/LICENSE-Inter.txt",
        ]:
            self.assertTrue((REPO / rel).is_file(), f"missing {rel}")

    def test_tokens_css_has_twb_variables(self):
        css = (REPO / "site-assets/tokens.css").read_text(encoding="utf-8")
        self.assertIn("--twb-bg-0", css)
        self.assertIn("--twb-accent", css)

    def test_vendor_licenses_present(self):
        for name in ["markdown-it-py", "mdurl", "mdit-py-plugins", "pygments", "pyyaml"]:
            self.assertTrue((REPO / "tools/vendor" / f"{name}-LICENSE.txt").is_file(), name)


if __name__ == "__main__":
    unittest.main()
