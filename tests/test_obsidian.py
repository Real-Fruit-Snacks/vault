import unittest

from ssg.config import SiteConfig
from ssg.links import LinkResolver
from ssg.obsidian import NoteRenderer
from ssg.vault import scan_vault
from tests.helpers import VaultCase, PNG_1PX


def render(case, files, note_path, output_path=None):
    vault = scan_vault(case.make_vault(files), SiteConfig())
    renderer = NoteRenderer(vault, LinkResolver(vault))
    return renderer, renderer.render_note(vault.notes[note_path], output_path)


class WikilinkTests(VaultCase):
    def test_resolved_link(self):
        _, res = render(self, {"A.md": "go [[B Note]]", "sub/B Note.md": "x"}, "A.md")
        self.assertIn('<a class="internal-link" href="sub/B%20Note.html">B Note</a>', res.html)

    def test_alias_label(self):
        _, res = render(self, {"A.md": "go [[B|the b]]", "B.md": "x"}, "A.md")
        self.assertIn(">the b</a>", res.html)

    def test_heading_fragment(self):
        _, res = render(self, {"A.md": "go [[B#My Part]]", "B.md": "## My Part\nx"}, "A.md")
        self.assertIn('href="B.html#my-part"', res.html)

    def test_broken_link(self):
        r, res = render(self, {"A.md": "go [[Ghost]]"}, "A.md")
        self.assertIn('<span class="broken-link"', res.html)
        self.assertIn("Ghost", res.html)
        self.assertTrue(any("Ghost" in w for w in r.warnings))

    def test_links_in_code_untouched(self):
        _, res = render(self, {"A.md": "```\n[[B]]\n```", "B.md": "x"}, "A.md")
        self.assertNotIn("internal-link", res.html)


class EmbedTests(VaultCase):
    def test_image_embed(self):
        _, res = render(self, {"A.md": "![[pic.png]]", "img/pic.png": PNG_1PX}, "A.md")
        self.assertIn('<img src="img/pic.png" alt="pic.png">', res.html)

    def test_image_embed_with_width(self):
        _, res = render(self, {"A.md": "![[pic.png|300]]", "img/pic.png": PNG_1PX}, "A.md")
        self.assertIn('width="300"', res.html)

    def test_note_embed_transcludes(self):
        _, res = render(self, {"A.md": "before\n\n![[B]]\n\nafter", "B.md": "embedded text"}, "A.md")
        self.assertIn('class="note-embed"', res.html)
        self.assertIn("embedded text", res.html)

    def test_nested_embed_becomes_link(self):
        _, res = render(self, {"A.md": "![[B]]", "B.md": "![[C]]", "C.md": "deep"}, "A.md")
        self.assertNotIn("deep", res.html)
        self.assertIn('href="C.html"', res.html)

    def test_cycle_guard(self):
        _, res = render(self, {"A.md": "![[B]]", "B.md": "![[A]]"}, "A.md")
        self.assertIn("Embed cycle", res.html)

    def test_heading_embed_extracts_section(self):
        files = {"A.md": "![[B#Two]]", "B.md": "# One\nfirst\n# Two\nsecond\n# Three\nthird"}
        _, res = render(self, files, "A.md")
        self.assertIn("second", res.html)
        self.assertNotIn("first", res.html)
        self.assertNotIn("third", res.html)


class CalloutTests(VaultCase):
    def test_basic_callout(self):
        _, res = render(self, {"A.md": "> [!note] Heads up\n> body **bold**"}, "A.md")
        self.assertIn('data-callout="note"', res.html)
        self.assertIn("Heads up", res.html)
        self.assertIn("<strong>bold</strong>", res.html)

    def test_default_title_is_type(self):
        _, res = render(self, {"A.md": "> [!warning]\n> careful"}, "A.md")
        self.assertIn("Warning", res.html)

    def test_foldable(self):
        _, res = render(self, {"A.md": "> [!tip]- Hidden\n> secret"}, "A.md")
        self.assertIn("<details", res.html)
        self.assertNotIn(" open>", res.html)

    def test_plain_blockquote_untouched(self):
        _, res = render(self, {"A.md": "> just a quote"}, "A.md")
        self.assertIn("<blockquote>", res.html)
        self.assertNotIn("callout", res.html)

    def test_nested_callout(self):
        md = "> [!note] Outer\n> outer body\n> > [!tip] Inner\n> > inner body"
        _, res = render(self, {"A.md": md}, "A.md")
        self.assertIn('data-callout="note"', res.html)
        self.assertIn('data-callout="tip"', res.html)


class TagTests(VaultCase):
    def test_inline_tag_links(self):
        _, res = render(self, {"sub/A.md": "about #proj/site stuff"}, "sub/A.md")
        self.assertIn('<a class="tag" href="../_tags/proj/site.html">#proj/site</a>', res.html)


class OutputPathTests(VaultCase):
    def test_homepage_override(self):
        _, res = render(self, {"Home.md": "go [[sub/B]]", "sub/B.md": "x"},
                        "Home.md", output_path="index.html")
        self.assertIn('href="sub/B.html"', res.html)


if __name__ == "__main__":
    unittest.main()
