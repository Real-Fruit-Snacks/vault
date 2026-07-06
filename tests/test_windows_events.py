"""Data-integrity checks for the Windows Event ID reference dataset.

The dataset is JS, but it's a plain array of object literals, so we parse the
per-entry fields with a regex and assert the invariants the tool relies on:
IDs are unique per channel, criticalities are from the fixed set, and every
category has a matching label in tool.js.
"""
import re
import unittest
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent.parent / "site-tools" / "windows-events"
EVENTS_JS = TOOL_DIR / "events.js"
TOOL_JS = TOOL_DIR / "tool.js"

ENTRY_RE = re.compile(
    r'\{\s*id:\s*(\d+),\s*log:\s*"([^"]+)",\s*cat:\s*"([^"]+)",\s*crit:\s*"([^"]+)",'
    r'\s*title:\s*"((?:[^"\\]|\\.)*)"')
VALID_CRIT = {"high", "medium", "low", "info"}


def parse_entries():
    text = EVENTS_JS.read_text(encoding="utf-8")
    return [
        {"id": int(m.group(1)), "log": m.group(2), "cat": m.group(3),
         "crit": m.group(4), "title": m.group(5)}
        for m in ENTRY_RE.finditer(text)
    ]


class WindowsEventsDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = parse_entries()

    def test_dataset_is_substantial(self):
        # Guard against a parse regression silently emptying the checks below.
        self.assertGreaterEqual(len(self.entries), 90)

    def test_ids_unique_per_channel(self):
        seen = set()
        for e in self.entries:
            key = (e["id"], e["log"])
            self.assertNotIn(key, seen, f"duplicate {e['id']} in {e['log']}")
            seen.add(key)

    def test_same_id_may_repeat_across_channels(self):
        # Sanity check that the per-channel model is real: id 25 exists in both
        # Sysmon and Terminal Services. If this stops being true the dataset
        # changed; the uniqueness test above still protects correctness.
        channels_for_25 = {e["log"] for e in self.entries if e["id"] == 25}
        self.assertGreaterEqual(len(channels_for_25), 2)

    def test_criticalities_valid(self):
        for e in self.entries:
            self.assertIn(e["crit"], VALID_CRIT, f"{e['id']} has crit {e['crit']}")

    def test_every_category_has_a_label(self):
        labels = TOOL_JS.read_text(encoding="utf-8")
        cat_block = re.search(r"var CAT_LABEL = \{(.*?)\};", labels, re.DOTALL)
        self.assertIsNotNone(cat_block, "CAT_LABEL map not found in tool.js")
        labelled = set(re.findall(r"(\w+):", cat_block.group(1)))
        for e in self.entries:
            self.assertIn(e["cat"], labelled, f"category {e['cat']} has no label")

    def test_titles_present(self):
        for e in self.entries:
            self.assertTrue(e["title"].strip(), f"{e['id']} has an empty title")


if __name__ == "__main__":
    unittest.main()
