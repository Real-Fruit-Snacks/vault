import datetime
import unittest

from ssg import updated
from ssg.config import SiteConfig
from ssg.vault import scan_vault
from tests.helpers import VaultCase


class FromFrontmatterTests(unittest.TestCase):
    def test_string_datetime_no_seconds(self):
        self.assertEqual(updated._from_frontmatter({"updated": "2026-07-06T21:50"}),
                         "2026-07-06T21:50:00")

    def test_string_date_only(self):
        self.assertEqual(updated._from_frontmatter({"updated": "2026-07-06"}),
                         "2026-07-06T00:00:00")

    def test_string_space_separated_with_seconds(self):
        self.assertEqual(updated._from_frontmatter({"updated": "2026-07-06 21:50:33"}),
                         "2026-07-06T21:50:33")

    def test_python_date_object(self):
        self.assertEqual(updated._from_frontmatter({"updated": datetime.date(2026, 7, 6)}),
                         "2026-07-06T00:00:00")

    def test_python_datetime_object(self):
        self.assertEqual(
            updated._from_frontmatter({"updated": datetime.datetime(2026, 7, 6, 21, 50, 33)}),
            "2026-07-06T21:50:33")

    def test_field_priority_updated_beats_date(self):
        self.assertEqual(
            updated._from_frontmatter({"date": "2020-01-01", "updated": "2026-07-06"}),
            "2026-07-06T00:00:00")

    def test_unrecognized_value_ignored(self):
        self.assertIsNone(updated._from_frontmatter({"updated": "sometime last week"}))
        self.assertIsNone(updated._from_frontmatter({"tags": ["x"]}))


class ResolveTests(VaultCase):
    def test_frontmatter_overrides_git(self):
        vault = scan_vault(self.make_vault({
            "A.md": "---\nupdated: 2026-07-06T21:50\n---\nbody",
        }), SiteConfig())
        # git says the file is old; frontmatter should win for both display + order.
        display, order = updated.resolve(vault, {"A.md": "2020-01-01"})
        self.assertEqual(display["A.md"], "2026-07-06")
        self.assertEqual(order["A.md"], "2026-07-06T21:50:00")

    def test_git_fallback_when_no_frontmatter_date(self):
        vault = scan_vault(self.make_vault({"A.md": "no frontmatter body"}), SiteConfig())
        display, order = updated.resolve(vault, {"A.md": "2026-07-06"})
        self.assertEqual(display["A.md"], "2026-07-06")
        self.assertEqual(order["A.md"], "2026-07-06T00:00:00")

    def test_non_note_path_uses_git(self):
        vault = scan_vault(self.make_vault({"A.md": "body"}), SiteConfig())
        # A canvas/base path appears only in git_dates, never in vault.notes.
        display, order = updated.resolve(vault, {"A.md": "2026-07-06", "Board.canvas": "2026-07-05"})
        self.assertEqual(display["Board.canvas"], "2026-07-05")
        self.assertEqual(order["Board.canvas"], "2026-07-05T00:00:00")

    def test_frontmatter_note_absent_from_git_still_resolved(self):
        vault = scan_vault(self.make_vault({
            "New.md": "---\nupdated: 2026-07-08\n---\nbody",
        }), SiteConfig())
        display, order = updated.resolve(vault, {})  # uncommitted: not in git
        self.assertEqual(display["New.md"], "2026-07-08")
        self.assertEqual(order["New.md"], "2026-07-08T00:00:00")

    def test_undated_path_absent_from_both(self):
        vault = scan_vault(self.make_vault({"A.md": "body"}), SiteConfig())
        display, order = updated.resolve(vault, {})
        self.assertNotIn("A.md", display)
        self.assertNotIn("A.md", order)
