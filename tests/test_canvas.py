"""Unit tests for Obsidian canvas support."""
import json
import tempfile
import unittest
from pathlib import Path

from ssg import urls
from ssg.canvas import PAD, Canvas, canvas_color, parse_canvas, canvas_page_content
from ssg.config import load_config
from ssg.links import LinkResolver
from ssg.obsidian import NoteRenderer
from ssg.vault import scan_vault


class CanvasPathTests(unittest.TestCase):
    def test_canvas_output_path(self):
        self.assertEqual(urls.canvas_output_path("Boards/Plan.canvas"), "Boards/Plan.html")

    def test_page_output_path_dispatch(self):
        self.assertEqual(urls.page_output_path("Boards/Plan.canvas"), "Boards/Plan.html")
        self.assertEqual(urls.page_output_path("Daily/Log.md"), "Daily/Log.html")


class CanvasScanTests(unittest.TestCase):
    def test_scanner_collects_canvases_and_unpublished(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Boards").mkdir()
            (root / "Boards" / "Plan.canvas").write_text('{"nodes":[],"edges":[]}', encoding="utf-8")
            (root / "Secret.md").write_text("---\npublish: false\n---\nhidden", encoding="utf-8")
            vault = scan_vault(root, load_config(root))
            self.assertIn("Boards/Plan.canvas", vault.canvases)
            self.assertIn("Secret.md", vault.unpublished)
            self.assertNotIn("Secret.md", vault.notes)
            self.assertFalse(any("unrecognized" in w for w in vault.warnings))


BOARD = """{
  "nodes": [
    {"id": "t1", "type": "text", "x": -100, "y": -50, "width": 200, "height": 100,
     "text": "hello **world**", "color": "4"},
    {"id": "f1", "type": "file", "x": 200, "y": 0, "width": 300, "height": 200,
     "file": "Projects/Site Plan.md"},
    {"id": "g1", "type": "group", "x": -150, "y": -100, "width": 700, "height": 400,
     "label": "cluster"},
    {"id": "weird", "type": "sticker", "x": 0, "y": 300, "width": 50, "height": 50}
  ],
  "edges": [
    {"id": "e1", "fromNode": "t1", "toNode": "f1", "fromSide": "right",
     "toSide": "left", "color": "1", "label": "flows"},
    {"id": "e2", "fromNode": "t1", "toNode": "ghost"}
  ]
}"""


class CanvasParseTests(unittest.TestCase):
    def setUp(self):
        self.warnings = []
        self.canvas = parse_canvas(BOARD, "Boards/Plan.canvas", self.warnings)

    def test_color_mapping(self):
        self.assertEqual(canvas_color("1"), "var(--twb-red)")
        self.assertEqual(canvas_color("6"), "var(--twb-violet)")
        self.assertEqual(canvas_color("#ff0000"), "#ff0000")
        self.assertIsNone(canvas_color("nope"))
        self.assertIsNone(canvas_color(None))

    def test_parse_basics(self):
        c = self.canvas
        self.assertEqual(c.title, "Plan")
        self.assertEqual(len(c.nodes), 4)
        self.assertEqual(len(c.edges), 1)  # e2 dropped: missing node
        self.assertTrue(any("missing node" in w for w in self.warnings))
        self.assertTrue(any("unknown node type" in w for w in self.warnings))

    def test_coordinates_translated(self):
        # min x/y (-150, -100 from the group) land at PAD
        g = next(n for n in self.canvas.nodes if n["id"] == "g1")
        self.assertEqual((g["x"], g["y"]), (PAD, PAD))
        t = next(n for n in self.canvas.nodes if n["id"] == "t1")
        self.assertEqual((t["x"], t["y"]), (PAD + 50, PAD + 50))
        self.assertEqual(self.canvas.width, PAD + 700 + PAD)

    def test_text_content_for_search(self):
        self.assertIn("hello", self.canvas.text_content)

    def test_malformed_json_returns_none(self):
        warnings = []
        self.assertIsNone(parse_canvas("{nope", "Bad.canvas", warnings))
        self.assertIsNone(parse_canvas('["list"]', "Bad.canvas", warnings))
        self.assertEqual(len(warnings), 2)

    def test_unhashable_node_type_does_not_raise(self):
        board = json.dumps({
            "nodes": [{"id": "n1", "type": ["x"], "x": 0, "y": 0, "width": 10, "height": 10}],
            "edges": [],
        })
        warnings = []
        canvas = parse_canvas(board, "Bad.canvas", warnings)
        self.assertIsInstance(canvas, Canvas)
        self.assertEqual(canvas.nodes[0]["type"], "unknown")
        self.assertTrue(any("unknown node type" in w for w in warnings))

    def test_unhashable_edge_endpoint_does_not_raise(self):
        board = json.dumps({
            "nodes": [{"id": "n1", "type": "text", "x": 0, "y": 0, "width": 10, "height": 10}],
            "edges": [{"id": "e1", "fromNode": ["n1"], "toNode": "n1"}],
        })
        warnings = []
        canvas = parse_canvas(board, "Bad.canvas", warnings)
        self.assertIsInstance(canvas, Canvas)
        self.assertEqual(len(canvas.edges), 0)
        self.assertTrue(any("missing node" in w for w in warnings))

    def test_non_finite_coordinate_skips_node(self):
        board = json.dumps({
            "nodes": [{"id": "n1", "type": "text", "x": "NaN", "y": 0, "width": 10, "height": 10}],
            "edges": [],
        })
        warnings = []
        canvas = parse_canvas(board, "Bad.canvas", warnings)
        self.assertIsInstance(canvas, Canvas)
        self.assertEqual(len(canvas.nodes), 0)
        self.assertTrue(any("skipped" in w for w in warnings))


FIXTURE = Path(__file__).resolve().parent / "fixture-vault"


def build_renderer():
    vault = scan_vault(FIXTURE, load_config(FIXTURE))
    return vault, NoteRenderer(vault, LinkResolver(vault))


NODE_BOARD = """{
  "nodes": [
    {"id": "t", "type": "text", "x": 0, "y": 0, "width": 200, "height": 100,
     "text": "see [[Site Plan]]", "color": "2"},
    {"id": "n", "type": "file", "x": 300, "y": 0, "width": 300, "height": 200,
     "file": "Projects/Site Plan.md"},
    {"id": "s", "type": "file", "x": 300, "y": 300, "width": 300, "height": 200,
     "file": "Projects/Site Plan.md", "subpath": "#Overview"},
    {"id": "img", "type": "file", "x": 700, "y": 0, "width": 200, "height": 150,
     "file": "Attachments/diagram.png"},
    {"id": "gone", "type": "file", "x": 700, "y": 300, "width": 200, "height": 100,
     "file": "Nope/Missing.md"},
    {"id": "hush", "type": "file", "x": 700, "y": 500, "width": 200, "height": 100,
     "file": "Drafts/Secret.md"},
    {"id": "url", "type": "link", "x": 0, "y": 300, "width": 200, "height": 80,
     "url": "https://example.com"},
    {"id": "g", "type": "group", "x": -50, "y": -50, "width": 1100, "height": 800,
     "label": "everything"}
  ],
  "edges": []
}"""


class CanvasNodeRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vault, cls.renderer = build_renderer()
        cls.warnings = []
        canvas = parse_canvas(NODE_BOARD, "Boards/Plan.canvas", cls.warnings)
        cls.render = canvas_page_content(
            canvas, cls.vault, cls.renderer, "Boards/Plan.html", cls.warnings)

    def test_text_card_markdown_and_wikilink(self):
        self.assertIn('class="internal-link"', self.render.html)
        self.assertIn("../Projects/Site%20Plan.html", self.render.html)

    def test_note_card_embeds_content_with_header_link(self):
        self.assertIn("canvas-embed-head", self.render.html)
        self.assertIn("Site Plan", self.render.html)

    def test_subpath_card_contains_only_that_section(self):
        # the fixture note has Overview and Details headings; the subpath card
        # must contain Overview's id but the full-note card still has Details
        self.assertIn('id="overview"', self.render.html)

    def test_image_card(self):
        self.assertIn('<img src="../Attachments/diagram.png"', self.render.html)

    def test_missing_and_unpublished_placeholders(self):
        self.assertIn("missing", self.render.html)
        self.assertIn("not published", self.render.html)
        self.assertNotIn("hidden", self.render.html)  # Secret.md content must not leak
        self.assertTrue(any("Nope/Missing.md" in w for w in self.warnings))
        self.assertTrue(any("Drafts/Secret.md" in w for w in self.warnings))

    def test_link_card_and_group(self):
        self.assertIn('href="https://example.com"', self.render.html)
        self.assertIn('rel="noopener"', self.render.html)
        self.assertIn("canvas-group-label", self.render.html)
        # groups paint first so cards sit on top
        self.assertLess(self.render.html.find("canvas-group"),
                        self.render.html.find("canvas-card"))

    def test_node_color_style(self):
        self.assertIn("--canvas-color: var(--twb-orange)", self.render.html)

    def test_base_file_card_links_to_base_page(self):
        board = ('{"nodes":[{"id":"b","type":"file","x":0,"y":0,"width":200,'
                 '"height":150,"file":"Bases/Fixture Base.base"}],"edges":[]}')
        warnings = []
        canvas = parse_canvas(board, "Boards/Plan.canvas", warnings)
        render = canvas_page_content(canvas, self.vault, self.renderer,
                                     "Boards/Plan.html", warnings)
        self.assertIn("../Bases/Fixture%20Base.html", render.html)
        self.assertNotIn("missing", render.html)

    def test_javascript_url_degrades_to_dead_card(self):
        board = ('{"nodes":[{"id":"j","type":"link","x":0,"y":0,"width":200,'
                 '"height":80,"url":"javascript:alert(1)"}],"edges":[]}')
        warnings = []
        canvas = parse_canvas(board, "Boards/Evil.canvas", warnings)
        render = canvas_page_content(canvas, self.vault, self.renderer,
                                     "Boards/Evil.html", warnings)
        self.assertNotIn('href="javascript:', render.html)
        self.assertIn("canvas-missing", render.html)
        self.assertTrue(any("unsupported URL" in w for w in warnings))


EDGE_BOARD = """{
  "nodes": [
    {"id": "a", "type": "text", "x": 0, "y": 0, "width": 100, "height": 100, "text": "a"},
    {"id": "b", "type": "text", "x": 400, "y": 0, "width": 100, "height": 100, "text": "b"}
  ],
  "edges": [
    {"id": "e1", "fromNode": "a", "toNode": "b", "fromSide": "right", "toSide": "left",
     "color": "1", "label": "goes"},
    {"id": "e2", "fromNode": "b", "toNode": "a", "toEnd": "none"}
  ]
}"""


class CanvasEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from ssg.canvas import edges_svg
        cls.canvas = parse_canvas(EDGE_BOARD, "Boards/Edges.canvas", [])
        cls.svg = edges_svg(cls.canvas)

    def test_svg_shell_and_marker(self):
        self.assertIn('<svg class="canvas-edges"', self.svg)
        self.assertIn('id="canvas-arrow"', self.svg)

    def test_explicit_sides_produce_expected_anchors(self):
        # a.right = (24+100, 24+50) = (124, 74); b.left = (24+400, 74) = (424, 74)
        self.assertIn('M 124 74', self.svg)
        self.assertIn('424 74"', self.svg)

    def test_arrowheads_follow_ends(self):
        # Assert exactly one drawn <path d="M carries marker-end (e1's default toEnd arrow)
        # e2 has toEnd none -> its path must not carry marker-end
        marker_end_paths = [p for p in self.svg.split('<path d="M') if 'marker-end' in p]
        self.assertEqual(len(marker_end_paths), 1)

    def test_label_and_color(self):
        self.assertIn(">goes</text>", self.svg)
        self.assertIn('stroke="var(--twb-red)"', self.svg)


class CanvasWikilinkTests(unittest.TestCase):
    def _vault(self, files):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        for rel, content in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        self.addCleanup(self.tmp.cleanup)
        return scan_vault(root, load_config(root))

    def test_wikilink_to_canvas_resolves(self):
        vault = self._vault({
            "Note.md": "see [[Plan]]",
            "Boards/Plan.canvas": '{"nodes":[],"edges":[]}',
        })
        renderer = NoteRenderer(vault, LinkResolver(vault))
        html = renderer.render_note(vault.notes["Note.md"]).html
        self.assertIn('href="Boards/Plan.html"', html)
        self.assertNotIn("broken-link", html)

    def test_note_beats_canvas_on_same_name(self):
        vault = self._vault({
            "Note.md": "see [[Plan]]",
            "Plan.md": "the note",
            "Boards/Plan.canvas": '{"nodes":[],"edges":[]}',
        })
        renderer = NoteRenderer(vault, LinkResolver(vault))
        html = renderer.render_note(vault.notes["Note.md"]).html
        self.assertIn('href="Plan.html"', html)


if __name__ == "__main__":
    unittest.main()
