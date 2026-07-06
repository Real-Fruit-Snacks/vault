"""Every tool's declared sidebar icon must be wired up in site.css.

A tool.json can name an `icon` (e.g. "radar"); the sidebar renders it from a
`--ticon-<name>` mask referenced by `a[data-icon="<name>"]::before`. It is easy
to add a tool with a new icon and forget the CSS, which silently falls back to
the generic glyph. This test fails loudly in that case.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "site-tools"
SITE_CSS = ROOT / "site-assets" / "site.css"


def tool_icons():
    icons = {}
    for meta_path in sorted(TOOLS_DIR.glob("*/tool.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        icon = meta.get("icon")
        if isinstance(icon, str) and icon:
            icons[meta_path.parent.name] = icon
    return icons


class ToolIconWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = SITE_CSS.read_text(encoding="utf-8")
        cls.icons = tool_icons()

    def test_there_are_tools_with_icons(self):
        # Guard against the glob silently finding nothing.
        self.assertGreater(len(self.icons), 5)

    def test_every_icon_has_a_mask_variable(self):
        for slug, icon in self.icons.items():
            self.assertIn(f"--ticon-{icon}:", self.css,
                          f"{slug}: no --ticon-{icon} mask defined in site.css")

    def test_every_icon_has_a_data_icon_rule(self):
        for slug, icon in self.icons.items():
            self.assertRegex(
                self.css, re.compile(r'a\[data-icon="' + re.escape(icon) + r'"\]::before'),
                f"{slug}: no a[data-icon=\"{icon}\"] rule in site.css")


if __name__ == "__main__":
    unittest.main()
