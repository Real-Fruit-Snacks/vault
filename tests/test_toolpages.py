import json
import tempfile
import unittest
from pathlib import Path

from ssg import pages, toolpages
from ssg.config import SiteConfig
from ssg.vault import scan_vault
from tests.helpers import VaultCase


class DiscoveryTests(unittest.TestCase):
    def make_tools_dir(self, tools: dict) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        for slug, files in tools.items():
            d = root / slug
            d.mkdir(parents=True)
            for name, content in files.items():
                (d / name).write_text(content, encoding="utf-8")
        return root

    def test_discovers_valid_tool(self):
        root = self.make_tools_dir({
            "char-analyzer": {
                "tool.json": json.dumps({"title": "Character Analyzer",
                                         "description": "Classify characters.",
                                         "learn_title": "Unicode 101",
                                         "icon": "type"}),
                "body.html": "<p>tool body</p>",
                "tool.js": "// js",
                "tool.css": "/* css */",
                "learn.html": "<p>LEARN CONTENT</p>",
                "notes.txt": "not an asset",
            },
        })
        warnings = []
        tools = toolpages.discover_tools(root, warnings)
        self.assertEqual(len(tools), 1)
        tool = tools[0]
        self.assertEqual(tool.slug, "char-analyzer")
        self.assertEqual(tool.title, "Character Analyzer")
        self.assertEqual(tool.description, "Classify characters.")
        self.assertEqual(tool.body_html, "<p>tool body</p>")
        self.assertEqual(tool.learn_html, "<p>LEARN CONTENT</p>")
        self.assertEqual(tool.learn_title, "Unicode 101")
        self.assertEqual(tool.icon, "type")
        self.assertEqual(sorted(tool.assets), ["tool.css", "tool.js"])
        self.assertEqual(warnings, [])

    def test_learn_section_optional_with_default_title(self):
        root = self.make_tools_dir({
            "plain": {"tool.json": "{}", "body.html": "<p>x</p>"},
        })
        tool = toolpages.discover_tools(root, [])[0]
        self.assertEqual(tool.learn_html, "")
        self.assertEqual(tool.learn_title, "learn more")
        self.assertEqual(tool.icon, "")

    def test_missing_body_warns_and_skips(self):
        root = self.make_tools_dir({"broken": {"tool.json": "{}"}})
        warnings = []
        self.assertEqual(toolpages.discover_tools(root, warnings), [])
        self.assertTrue(any("broken" in w for w in warnings))

    def test_invalid_json_warns_and_skips(self):
        root = self.make_tools_dir({"bad": {"tool.json": "{nope", "body.html": "<p>x</p>"}})
        warnings = []
        self.assertEqual(toolpages.discover_tools(root, warnings), [])
        self.assertTrue(any("bad" in w for w in warnings))

    def test_missing_source_dir_is_fine(self):
        warnings = []
        self.assertEqual(toolpages.discover_tools(Path("no/such/dir"), warnings), [])
        self.assertEqual(warnings, [])

    def test_title_defaults_to_slug(self):
        root = self.make_tools_dir({"mystery": {"tool.json": "{}", "body.html": "<p>x</p>"}})
        tools = toolpages.discover_tools(root, [])
        self.assertEqual(tools[0].title, "mystery")

    def test_output_path(self):
        root = self.make_tools_dir({"char-analyzer": {"tool.json": "{}", "body.html": "<p>x</p>"}})
        tool = toolpages.discover_tools(root, [])[0]
        self.assertEqual(toolpages.tool_output_path(tool), "tools/char-analyzer.html")


class ContentTests(unittest.TestCase):
    def _tool(self):
        return toolpages.Tool(slug="char-analyzer", title="Character Analyzer",
                              description="Classify <chars>.", body_html="<p>BODY</p>",
                              assets={})

    def test_tool_page_content(self):
        html = toolpages.tool_page_content(self._tool())
        self.assertIn("<h1>Character Analyzer</h1>", html)
        self.assertIn("Classify &lt;chars&gt;.", html)
        self.assertIn("<p>BODY</p>", html)
        self.assertNotIn("tool-learn", html)

    def test_tool_page_content_with_learn_section(self):
        tool = self._tool()
        tool.learn_html = "<p>LEARN</p>"
        tool.learn_title = "Unicode <101>"
        html = toolpages.tool_page_content(tool)
        self.assertIn('<details class="tool-learn">', html)
        self.assertIn("Unicode &lt;101&gt;", html)
        self.assertIn("<p>LEARN</p>", html)
        self.assertNotIn("<details open", html)  # collapsed by default

    def test_tools_index_content(self):
        html = toolpages.tools_index_content([self._tool()], "tools/index.html")
        self.assertIn('href="char-analyzer.html"', html)
        self.assertIn("Character Analyzer", html)
        self.assertIn("Classify &lt;chars&gt;.", html)


class NavToolsTests(VaultCase):
    def test_nav_tools_group(self):
        vault = scan_vault(self.make_vault({"Home.md": "x"}), SiteConfig())
        nav = pages.build_nav(vault, "", "tools/char-analyzer.html",
                              tools=[("Character Analyzer", "tools/char-analyzer.html", "type")])
        self.assertIn('class="nav-tools"', nav)
        self.assertIn('href="index.html"', nav)  # tools group header links tools index
        self.assertIn('class="active"', nav)
        self.assertIn('data-icon="type"', nav)
        self.assertIn(">Character Analyzer</a>", nav)

    def test_nav_tool_without_icon_gets_no_attribute(self):
        vault = scan_vault(self.make_vault({"Home.md": "x"}), SiteConfig())
        nav = pages.build_nav(vault, "", "Home.html",
                              tools=[("Plain Tool", "tools/plain.html", "")])
        self.assertNotIn("data-icon", nav)

    def test_nav_without_tools_unchanged(self):
        vault = scan_vault(self.make_vault({"Home.md": "x"}), SiteConfig())
        nav = pages.build_nav(vault, "Home.md", "Home.html")
        self.assertNotIn("nav-tools", nav)


if __name__ == "__main__":
    unittest.main()
