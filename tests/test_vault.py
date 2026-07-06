import unittest

from ssg.config import SiteConfig
from ssg.vault import scan_vault
from tests.helpers import VaultCase, PNG_1PX


class ScanTests(VaultCase):
    def test_collects_notes_and_assets(self):
        root = self.make_vault({
            "Home.md": "# Welcome",
            "Projects/Plan.md": "---\ntitle: The Plan\ntags: [proj, deep/nest]\naliases: [plan]\n---\nBody #inline",
            "Attachments/pic.png": PNG_1PX,
            ".obsidian/app.json": "{}",
            "site.config.json": "{}",
            "Private/secret.md": "hidden",
        })
        vault = scan_vault(root, SiteConfig(exclude=["Private"]))
        self.assertIn("Home.md", vault.notes)
        self.assertIn("Projects/Plan.md", vault.notes)
        self.assertNotIn("Private/secret.md", vault.notes)
        self.assertIn("Attachments/pic.png", vault.assets)
        self.assertEqual(len(vault.notes), 2)

    def test_dot_folders_and_dotfiles_never_publish(self):
        # Obsidian keeps config, plugins, and deleted notes in dot-folders
        # (.obsidian, .trash, ...) — none of it may reach the site, at any
        # depth, and none of it should even produce warnings.
        vault = scan_vault(self.make_vault({
            "Real.md": "keep",
            ".obsidian/workspace.json": "{}",
            ".obsidian/plugins/dataview/main.js": "x",
            ".trash/Deleted.md": "gone",
            "Sub/.hidden/Secret.md": "nested",
            "Sub/.DS_Store": "junk",
            "Sub/Visible.md": "keep too",
        }), SiteConfig())
        self.assertEqual(sorted(vault.notes), ["Real.md", "Sub/Visible.md"])
        self.assertEqual(vault.assets, {})
        self.assertEqual(vault.warnings, [])

    def test_infrastructure_names_publish_inside_vault(self):
        # The vault is isolated in Notes/, so user folders named like repo
        # machinery are ordinary content; only build-output names stay reserved.
        root = self.make_vault({
            "docs/Guide.md": "a",
            "tools/Tips.md": "b",
            "public/Ghost.md": "c",
        })
        vault = scan_vault(root, SiteConfig())
        self.assertIn("docs/Guide.md", vault.notes)
        self.assertIn("tools/Tips.md", vault.notes)
        self.assertNotIn("public/Ghost.md", vault.notes)

    def test_frontmatter_parsed(self):
        root = self.make_vault({
            "Projects/Plan.md": "---\ntitle: The Plan\ntags: [proj]\naliases: [plan]\n---\nBody #inline and #proj again",
        })
        vault = scan_vault(root, SiteConfig())
        note = vault.notes["Projects/Plan.md"]
        self.assertEqual(note.title, "The Plan")
        self.assertEqual(note.aliases, ["plan"])
        self.assertEqual(note.tags, ["proj", "inline"])  # deduped case-insensitively
        self.assertEqual(note.body.strip(), "Body #inline and #proj again")

    def test_title_defaults_to_basename(self):
        root = self.make_vault({"Notes/My Note.md": "text"})
        vault = scan_vault(root, SiteConfig())
        self.assertEqual(vault.notes["Notes/My Note.md"].title, "My Note")

    def test_malformed_frontmatter_warns(self):
        root = self.make_vault({"Bad.md": "---\n: {unbalanced\n---\ntext"})
        vault = scan_vault(root, SiteConfig())
        self.assertEqual(vault.notes["Bad.md"].frontmatter, {})
        self.assertTrue(any("Bad.md" in w for w in vault.warnings))

    def test_unrecognized_file_warns(self):
        root = self.make_vault({"n.md": "x", "data.xyz": "?"})
        vault = scan_vault(root, SiteConfig())
        self.assertNotIn("data.xyz", vault.assets)
        self.assertTrue(any("data.xyz" in w for w in vault.warnings))

    def test_publish_false_excludes_note(self):
        vault = scan_vault(self.make_vault({
            "A.md": "---\npublish: false\n---\nsecret",
            "B.md": "public",
        }), SiteConfig())
        self.assertNotIn("A.md", vault.notes)
        self.assertIn("B.md", vault.notes)
        self.assertEqual(vault.skipped, 1)

    def test_publish_true_and_other_values_included(self):
        vault = scan_vault(self.make_vault({
            "A.md": "---\npublish: true\n---\nx",
            "B.md": "---\npublish: 'false'\n---\nonly boolean false excludes",
            "C.md": "no frontmatter",
        }), SiteConfig())
        self.assertEqual(set(vault.notes), {"A.md", "B.md", "C.md"})
        self.assertEqual(vault.skipped, 0)


if __name__ == "__main__":
    unittest.main()
