import unittest

from ssg import mdtext


class FrontmatterTests(unittest.TestCase):
    def test_split(self):
        fm, body = mdtext.split_frontmatter("---\ntitle: X\n---\nBody here")
        self.assertEqual(fm, "title: X")
        self.assertEqual(body, "Body here")

    def test_no_frontmatter(self):
        fm, body = mdtext.split_frontmatter("Just text")
        self.assertIsNone(fm)
        self.assertEqual(body, "Just text")

    def test_dashes_mid_document_are_not_frontmatter(self):
        fm, body = mdtext.split_frontmatter("intro\n---\nkey: v\n---\n")
        self.assertIsNone(fm)


class OutsideCodeTests(unittest.TestCase):
    def test_skips_fenced_blocks_and_inline_code(self):
        text = "a [[X]]\n```py\n[[not me]]\n```\nb `[[nor me]]` c [[Y]]"
        out = mdtext.apply_outside_code(text, lambda s: s.replace("[[", "(("))
        self.assertIn("((X]]", out)
        self.assertIn("((Y]]", out)
        self.assertIn("[[not me]]", out)
        self.assertIn("`[[nor me]]`", out)

    def test_unclosed_fence_treated_as_code(self):
        text = "before [[A]]\n```\n[[inside]]\n"
        out = mdtext.apply_outside_code(text, lambda s: s.replace("[[", "(("))
        self.assertIn("((A]]", out)
        self.assertIn("[[inside]]", out)


class FindTests(unittest.TestCase):
    def test_targets_from_links_and_embeds(self):
        text = "See [[Note One]] and ![[img.png]] and [[Folder/Two|alias]] and [[Three#Head]]"
        self.assertEqual(
            mdtext.find_wikilink_targets(text),
            ["img.png", "Note One", "Folder/Two", "Three"],
        )

    def test_heading_only_link_yields_no_target(self):
        self.assertEqual(mdtext.find_wikilink_targets("[[#Local Heading]]"), [])

    def test_tags(self):
        text = "line #alpha and #proj/site mid.\n#lead but not h#ash or #123\n```\n#code\n```"
        self.assertEqual(mdtext.find_inline_tags(text), ["alpha", "proj/site", "lead"])


if __name__ == "__main__":
    unittest.main()
