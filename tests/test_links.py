import unittest

from ssg.config import SiteConfig
from ssg.links import LinkResolver, build_backlinks
from ssg.vault import scan_vault
from tests.helpers import VaultCase, PNG_1PX


def make_resolver(case, files):
    vault = scan_vault(case.make_vault(files), SiteConfig())
    return vault, LinkResolver(vault)


class ResolveTests(VaultCase):
    def test_unique_basename(self):
        _, r = make_resolver(self, {"a/Target.md": "x", "b/Other.md": "y"})
        self.assertEqual(r.resolve_note("Target", "b/Other.md"), "a/Target.md")

    def test_case_insensitive(self):
        _, r = make_resolver(self, {"a/Target.md": "x"})
        self.assertEqual(r.resolve_note("target", "a/Target.md"), "a/Target.md")

    def test_exact_path(self):
        _, r = make_resolver(self, {"a/N.md": "x", "b/N.md": "y"})
        self.assertEqual(r.resolve_note("a/N", "b/N.md"), "a/N.md")

    def test_ambiguous_warns_and_picks_first(self):
        _, r = make_resolver(self, {"a/N.md": "x", "b/N.md": "y", "c/S.md": "z"})
        self.assertEqual(r.resolve_note("N", "c/S.md"), "a/N.md")
        self.assertTrue(any("ambiguous" in w for w in r.warnings))

    def test_alias(self):
        _, r = make_resolver(self, {"a/Long Name.md": "---\naliases: [short]\n---\nx"})
        self.assertEqual(r.resolve_note("short", "a/Long Name.md"), "a/Long Name.md")

    def test_missing_returns_none(self):
        _, r = make_resolver(self, {"a/N.md": "x"})
        self.assertIsNone(r.resolve_note("Ghost", "a/N.md"))

    def test_empty_target_is_self(self):
        _, r = make_resolver(self, {"a/N.md": "x"})
        self.assertEqual(r.resolve_note("", "a/N.md"), "a/N.md")

    def test_asset_by_basename(self):
        _, r = make_resolver(self, {"n.md": "x", "Attachments/pic.png": PNG_1PX})
        self.assertEqual(r.resolve_asset("pic.png", "n.md"), "Attachments/pic.png")


class BacklinkTests(VaultCase):
    def test_backlinks(self):
        vault, r = make_resolver(self, {
            "One.md": "links to [[Two]] and ![[Two]] again",
            "Two.md": "links back [[One]]",
            "Three.md": "links [[Two]]",
        })
        back = build_backlinks(vault, r)
        self.assertEqual(back["Two.md"], ["One.md", "Three.md"])
        self.assertEqual(back["One.md"], ["Two.md"])


if __name__ == "__main__":
    unittest.main()
