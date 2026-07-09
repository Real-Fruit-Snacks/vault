import unittest

from ssg import urls


class UrlTests(unittest.TestCase):
    def test_note_output_path(self):
        self.assertEqual(urls.note_output_path("Folder/My Note.md"), "Folder/My Note.html")

    def test_tag_output_path(self):
        self.assertEqual(urls.tag_output_path("proj/site"), "_tags/proj/site.html")
        self.assertEqual(urls.tag_output_path("Reading"), "_tags/reading.html")
        # each segment is slugged independently
        self.assertEqual(urls.tag_output_path("Net Ops/DNS"), "_tags/net-ops/dns.html")

    def test_rel_href_same_dir(self):
        self.assertEqual(urls.rel_href("a/one.html", "a/two space.html"), "two%20space.html")

    def test_rel_href_updir_and_fragment(self):
        self.assertEqual(urls.rel_href("a/b/x.html", "c/y.html", "some-head"),
                         "../../c/y.html#some-head")

    def test_rel_href_from_root(self):
        self.assertEqual(urls.rel_href("index.html", "Folder/Note.html"), "Folder/Note.html")

    def test_root_prefix(self):
        self.assertEqual(urls.root_prefix("index.html"), "")
        self.assertEqual(urls.root_prefix("a/b/c.html"), "../../")

    def test_slugify_heading(self):
        self.assertEqual(urls.slugify_heading("Hello, World!"), "hello-world")
        self.assertEqual(urls.slugify_heading("  Spaced   Out  "), "spaced-out")
        self.assertEqual(urls.slugify_heading("!!!"), "section")


if __name__ == "__main__":
    unittest.main()
