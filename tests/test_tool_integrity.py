"""Structural integrity checks for every tool under site-tools/.

Catches the mistakes that a data-free logic tool is prone to: a malformed
tool.json, a missing manifest field, a stray learn section, or a `src`/`href`
in body.html that points at an asset which doesn't exist (a typo there fails
silently in the browser, not the build).
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "site-tools"
REF_RE = re.compile(r'(?:src|href)\s*=\s*"([^"]+)"')


def tool_dirs():
    return sorted(p for p in TOOLS_DIR.iterdir()
                  if p.is_dir() and (p / "tool.json").is_file() and (p / "body.html").is_file())


class ToolIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dirs = tool_dirs()

    def test_there_are_tools(self):
        self.assertGreater(len(self.dirs), 10)

    def test_manifests_are_complete(self):
        for d in self.dirs:
            meta = json.loads((d / "tool.json").read_text(encoding="utf-8"))
            self.assertIsInstance(meta, dict, f"{d.name}: tool.json is not an object")
            for field in ("title", "description", "icon", "learn_title"):
                val = meta.get(field)
                self.assertIsInstance(val, str, f"{d.name}: {field} missing or not a string")
                self.assertTrue(val.strip(), f"{d.name}: {field} is empty")

    def test_learn_section_present(self):
        for d in self.dirs:
            learn = d / "learn.html"
            self.assertTrue(learn.is_file(), f"{d.name}: learn.html missing")
            self.assertTrue(learn.read_text(encoding="utf-8").strip(), f"{d.name}: learn.html empty")

    def test_body_asset_references_resolve(self):
        for d in self.dirs:
            body = (d / "body.html").read_text(encoding="utf-8")
            for ref in REF_RE.findall(body):
                # Only local, same-tool asset references are our responsibility;
                # they are written slug-relative (e.g. "nmap-builder/tool.js").
                if ref.startswith(d.name + "/"):
                    target = TOOLS_DIR / ref
                    self.assertTrue(target.is_file(),
                                    f"{d.name}: body.html references missing asset {ref}")


if __name__ == "__main__":
    unittest.main()
