import unittest

from ssg.markdown import render_markdown


class FenceTests(unittest.TestCase):
    def test_python_fence_is_highlighted_and_framed(self):
        res = render_markdown("```python\ndef f():\n    return 1\n```\n")
        self.assertIn('<figure class="code-block">', res.html)
        self.assertIn('code-lang', res.html)
        self.assertIn(">python<", res.html)
        self.assertIn('<span class="k">def</span>', res.html)

    def test_unknown_language_is_escaped_plain(self):
        res = render_markdown("```nosuchlang\na < b\n```\n")
        self.assertIn("a &lt; b", res.html)

    def test_no_language_gets_prompt_label(self):
        res = render_markdown("```\nplain\n```\n")
        self.assertIn("&gt;_", res.html)

    def test_mermaid_fence(self):
        res = render_markdown("```mermaid\ngraph TD; A-->B;\n```\n")
        self.assertIn('<pre class="mermaid">', res.html)
        self.assertIn("A--&gt;B", res.html)
        self.assertTrue(res.has_mermaid)

    def test_no_mermaid_flag_without_diagram(self):
        self.assertFalse(render_markdown("hello").has_mermaid)


class HeadingTests(unittest.TestCase):
    def test_ids_and_toc(self):
        res = render_markdown("# Alpha One\n\n## Beta Two\n\n## Beta Two\n")
        self.assertIn('<h1 id="alpha-one">', res.html)
        self.assertIn('<h2 id="beta-two">', res.html)
        self.assertIn('<h2 id="beta-two-1">', res.html)
        self.assertEqual(res.headings[0], (1, "Alpha One", "alpha-one"))
        self.assertEqual(len(res.headings), 3)


class TaskTests(unittest.TestCase):
    def test_states(self):
        md = "- [ ] open\n- [x] done\n- [-] dropped\n- [>] later\n- [!] urgent\n- [?] custom\n"
        html = render_markdown(md).html
        self.assertIn('task-todo', html)
        self.assertIn('task-done', html)
        self.assertIn('task-cancelled', html)
        self.assertIn('task-deferred', html)
        self.assertIn('task-important', html)
        self.assertIn('task-other', html)
        self.assertIn('data-task="x"', html)
        self.assertNotIn("[x]", html)

    def test_marker_not_applied_outside_lists(self):
        html = render_markdown("[x] not a task\n").html
        self.assertIn("[x] not a task", html)


class HeadingAnchorTests(unittest.TestCase):
    def test_headings_get_anchor_links(self):
        html = render_markdown("## Hello World").html
        self.assertIn('<a class="h-anchor" href="#hello-world" '
                      'aria-label="Link to this section">#</a></h2>', html)

    def test_duplicate_heading_anchor_uses_deduped_slug(self):
        html = render_markdown("## Same\n\n## Same").html
        self.assertIn('href="#same-1"', html)


class TableTests(unittest.TestCase):
    def test_tables_enabled(self):
        html = render_markdown("| a | b |\n|---|---|\n| 1 | 2 |\n").html
        self.assertIn("<table>", html)


if __name__ == "__main__":
    unittest.main()
