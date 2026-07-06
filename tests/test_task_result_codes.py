"""Data-integrity checks for the Task Scheduler result-code reference.

The dataset is JS, but each entry is a flat object literal, so we parse the
structural fields (code, name, fam, sev) with a regex and assert the invariants
the view relies on: codes are hex and unique, families and severities are from
fixed sets, Task Scheduler constants are named while raw exit codes are not, and
every severity used has a matching badge class in the tool's CSS.
"""
import re
import unittest
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent.parent / "site-tools" / "schtasks-builder"
CODES_JS = TOOL_DIR / "result-codes.js"
TOOL_CSS = TOOL_DIR / "tool.css"

ENTRY_RE = re.compile(
    r'\{\s*code:\s*"([^"]+)",\s*name:\s*"([^"]*)",\s*fam:\s*"([^"]+)",\s*sev:\s*"([^"]+)"')
HEX_RE = re.compile(r"^0x[0-9A-Fa-f]+$")
VALID_FAM = {"exit", "sched"}
VALID_SEV = {"high", "medium", "low", "info"}


def parse_entries():
    text = CODES_JS.read_text(encoding="utf-8")
    return [
        {"code": m.group(1), "name": m.group(2), "fam": m.group(3), "sev": m.group(4)}
        for m in ENTRY_RE.finditer(text)
    ]


class TaskResultCodeDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = parse_entries()

    def test_dataset_is_substantial(self):
        # Guard against a parse regression silently emptying the checks below.
        self.assertGreaterEqual(len(self.entries), 50)

    def test_codes_are_hex(self):
        for e in self.entries:
            self.assertRegex(e["code"], HEX_RE, f"{e['code']} is not a 0x hex code")

    def test_codes_unique(self):
        seen = set()
        for e in self.entries:
            self.assertNotIn(e["code"], seen, f"duplicate code {e['code']}")
            seen.add(e["code"])

    def test_families_valid(self):
        for e in self.entries:
            self.assertIn(e["fam"], VALID_FAM, f"{e['code']} has family {e['fam']}")

    def test_severities_valid(self):
        for e in self.entries:
            self.assertIn(e["sev"], VALID_SEV, f"{e['code']} has severity {e['sev']}")

    def test_scheduler_constants_named_exit_codes_not(self):
        # SCHED_* constants carry their WinError.h name; raw program exit codes
        # (fam "exit") are anonymous and render a generic label instead.
        for e in self.entries:
            if e["fam"] == "sched":
                self.assertTrue(e["name"].startswith("SCHED_"),
                                f"{e['code']} should carry a SCHED_ constant name")
            else:
                self.assertEqual(e["name"], "", f"{e['code']} should have no constant name")

    def test_both_families_present(self):
        fams = {e["fam"] for e in self.entries}
        self.assertEqual(fams, VALID_FAM, "expected both exit and sched entries")

    def test_every_severity_has_a_badge_class(self):
        css = TOOL_CSS.read_text(encoding="utf-8")
        for sev in {e["sev"] for e in self.entries}:
            self.assertIn(f".rc-sev-{sev}", css, f"no badge class for severity {sev}")


if __name__ == "__main__":
    unittest.main()
