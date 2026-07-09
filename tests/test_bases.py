"""Unit tests for Obsidian bases support."""
import tempfile
import unittest
from pathlib import Path

from ssg import bases, urls
from ssg.bases import parse_base, BaseView, NoteCtx, evaluate, render_base
from ssg.config import load_config, SiteConfig
from ssg.links import LinkResolver
from ssg.obsidian import NoteRenderer
from ssg.vault import scan_vault
from tests.helpers import VaultCase


def make_vault(files):
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp, scan_vault(root, load_config(root))


class BasePathTests(unittest.TestCase):
    def test_base_output_path(self):
        self.assertEqual(urls.base_output_path("Bases/Reading.base"), "Bases/Reading.html")

    def test_page_output_path_dispatch(self):
        self.assertEqual(urls.page_output_path("Bases/Reading.base"), "Bases/Reading.html")
        self.assertEqual(urls.page_output_path("Boards/Plan.canvas"), "Boards/Plan.html")
        self.assertEqual(urls.page_output_path("Note.md"), "Note.html")


class BaseScanAndResolveTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.vault = make_vault({
            "Note.md": "see [[Reading]] and ![[Reading.base]]",
            "Bases/Reading.base": "views:\n  - type: table\n",
        })
        self.addCleanup(self.tmp.cleanup)

    def test_scanner_collects_bases(self):
        self.assertIn("Bases/Reading.base", self.vault.bases)
        self.assertFalse(any("unrecognized" in w for w in self.vault.warnings))

    def test_wikilink_resolves_to_base(self):
        resolver = LinkResolver(self.vault)
        self.assertEqual(resolver.resolve_note("Reading", "Note.md"), "Bases/Reading.base")

    def test_note_and_canvas_beat_base(self):
        tmp, vault = make_vault({
            "Reading.md": "the note",
            "Bases/Reading.base": "views: []\n",
        })
        self.addCleanup(tmp.cleanup)
        self.assertEqual(LinkResolver(vault).resolve_note("Reading", "x"), "Reading.md")

    def test_resolve_base_exact_and_basename(self):
        resolver = LinkResolver(self.vault)
        self.assertEqual(resolver.resolve_base("Bases/Reading.base", "Note.md"),
                         "Bases/Reading.base")
        self.assertEqual(resolver.resolve_base("Reading.base", "Note.md"),
                         "Bases/Reading.base")
        self.assertIsNone(resolver.resolve_base("Nope.base", "Note.md"))


BASE_YAML = """\
filters:
  and:
    - file.hasTag("book")
    - 'status != "done"'
formulas:
  pp: "price / pages"
properties:
  status:
    displayName: Status
views:
  - type: table
    name: Reading queue
    order: [file.name, status, rating]
    sort:
      - property: rating
        direction: desc
    limit: 20
  - type: cards
    name: Covers
    image: cover
    order: [file.name, rating]
  - type: kanban
    name: Nope
"""


class BaseParseTests(unittest.TestCase):
    def setUp(self):
        self.warnings = []
        self.base = parse_base(BASE_YAML, "Bases/Reading.base", self.warnings)

    def test_basics(self):
        self.assertEqual(self.base.title, "Reading")
        self.assertEqual(self.base.display_names, {"status": "Status"})
        self.assertEqual(self.base.filters,
                         ("and", [("expr", 'file.hasTag("book")'),
                                  ("expr", 'status != "done"')]))

    def test_views(self):
        self.assertEqual(len(self.base.views), 2)  # kanban skipped
        table, cards = self.base.views
        self.assertEqual((table.type, table.name), ("table", "Reading queue"))
        self.assertEqual(table.order, ["file.name", "status", "rating"])
        self.assertEqual(table.sort, [("rating", "DESC")])
        self.assertEqual(table.limit, 20)
        self.assertEqual((cards.type, cards.image), ("cards", "cover"))
        self.assertTrue(any("kanban" in w for w in self.warnings))

    def test_malformed(self):
        w = []
        self.assertIsNone(parse_base(":\nbroken: [", "B.base", w))
        self.assertIsNone(parse_base("- just\n- a list\n", "B.base", w))
        self.assertEqual(len(w), 2)

    def test_view_defaults(self):
        base = parse_base("views:\n  - type: table\n", "B.base", [])
        self.assertEqual(base.views[0].name, "Table 1")
        self.assertEqual(base.views[0].order, [])
        self.assertEqual(base.views[0].limit, 0)

    def test_unhashable_view_type_does_not_raise(self):
        w = []
        base = parse_base('views:\n  - type: ["x"]\n  - type: table\n', "B.base", w)
        self.assertEqual(len(base.views), 1)  # the bad view skipped, table kept
        self.assertTrue(any("unsupported view type" in x for x in w))

    def test_deeply_nested_yaml_does_not_crash(self):
        w = []
        deep = "filters: " + "{and: [" * 400 + "'x'" + "]}" * 400
        self.assertIsNone(parse_base(deep, "B.base", w))
        self.assertTrue(any("invalid base YAML" in x for x in w))


class ExtensionQualifiedWikilinkTests(unittest.TestCase):
    def test_canvas_extension_does_not_fall_back_to_base(self):
        tmp, vault = make_vault({
            "Note.md": "see [[Reading.canvas]]",
            "Bases/Reading.base": "views: []\n",
        })
        self.addCleanup(tmp.cleanup)
        resolver = LinkResolver(vault)
        self.assertIsNone(resolver.resolve_note("Reading.canvas", "Note.md"))

    def test_base_extension_does_not_fall_back_to_note(self):
        tmp, vault = make_vault({
            "Reading.md": "the note",
        })
        self.addCleanup(tmp.cleanup)
        resolver = LinkResolver(vault)
        self.assertIsNone(resolver.resolve_note("Reading.base", "Note.md"))

    def test_extensionless_link_still_resolves_to_base(self):
        tmp, vault = make_vault({
            "Bases/Reading.base": "views: []\n",
        })
        self.addCleanup(tmp.cleanup)
        resolver = LinkResolver(vault)
        self.assertEqual(resolver.resolve_note("Reading", "Note.md"), "Bases/Reading.base")


LIB = {
    "Library/A.md": "---\ntags: [book]\nstatus: reading\nrating: 8\n---\nx",
    "Library/B.md": "---\ntags: [book]\nstatus: done\nrating: 9\n---\nx",
    "Library/C.md": "---\ntags: [book]\nstatus: reading\n---\nno rating",
    "Library/D.md": "---\ntags: [movie]\nstatus: reading\nrating: 10\n---\nx",
}


def view(**kw):
    args = dict(name="V", type="table", filters=None, order=[], sort=[], limit=0, image="")
    args.update(kw)
    return BaseView(**args)


class EvaluateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp, cls.vault = make_vault(LIB)
        cls.resolver = LinkResolver(cls.vault)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_eval(self, base_filters=None, **view_kw):
        base = parse_base("views:\n  - type: table\n", "Bases/T.base", [])
        base.filters = base_filters
        w = []
        got = evaluate(base, view(**view_kw), self.vault, self.resolver, w)
        return got, w

    def test_global_and_view_filters_combine(self):
        got, _ = self.run_eval(base_filters=("expr", 'file.hasTag("book")'),
                               filters=("expr", 'status == "reading"'))
        self.assertEqual(got, ["Library/A.md", "Library/C.md"])

    def test_or_and_not(self):
        got, _ = self.run_eval(base_filters=("or", [("expr", "rating >= 9"),
                                                    ("expr", 'status == "reading"')]))
        self.assertEqual(set(got), {"Library/A.md", "Library/B.md",
                                    "Library/C.md", "Library/D.md"})
        got, _ = self.run_eval(base_filters=("not", [("expr", 'file.hasTag("movie")')]))
        self.assertEqual(set(got), {"Library/A.md", "Library/B.md", "Library/C.md"})

    def test_unsupported_expression_warns_once_and_excludes(self):
        got, w = self.run_eval(base_filters=("expr", "rating++ > 3"))
        self.assertEqual(got, [])
        self.assertEqual(len([x for x in w if "unsupported filter" in x]), 1)

    def test_short_circuit_still_warns_about_unsupported_expression(self):
        # the first AND child is false for every note, so the second (broken)
        # child is never evaluated — the warning must still appear
        got, w = self.run_eval(base_filters=("and", [
            ("expr", 'status == "nonexistent"'),
            ("expr", "rating ++ 1"),
        ]))
        self.assertEqual(got, [])
        self.assertEqual(
            len([x for x in w if "unsupported filter expression" in x]), 1)

    def test_sort_desc_missing_last_and_limit(self):
        got, _ = self.run_eval(base_filters=("expr", 'file.hasTag("book")'),
                               sort=[("rating", "DESC")])
        self.assertEqual(got, ["Library/B.md", "Library/A.md", "Library/C.md"])
        got, _ = self.run_eval(base_filters=("expr", 'file.hasTag("book")'),
                               sort=[("rating", "ASC")])
        self.assertEqual(got, ["Library/A.md", "Library/B.md", "Library/C.md"])
        got, _ = self.run_eval(base_filters=("expr", 'file.hasTag("book")'),
                               sort=[("rating", "DESC")], limit=1)
        self.assertEqual(got, ["Library/B.md"])


RENDER_LIB = dict(LIB)
RENDER_LIB["Library/A.md"] = ("---\ntags: [book]\nstatus: reading\nrating: 8\n"
                              "cover: '[[diagram.png]]'\nnext: '[[B]]'\n---\nx")
RENDER_LIB["Attachments/diagram.png"] = "png"

RENDER_YAML = """\
filters: file.hasTag("book")
formulas:
  pp: "1 +"
properties:
  status:
    displayName: Status
views:
  - type: table
    name: Queue
    order: [file.name, status, next, formula.pp]
    sort:
      - property: rating
        direction: DESC
  - type: cards
    name: Covers
    image: cover
    order: [file.name, rating]
"""


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp, cls.vault = make_vault(RENDER_LIB)
        cls.resolver = LinkResolver(cls.vault)
        cls.warnings = []
        cls.base = parse_base(RENDER_YAML, "Bases/Reading.base", cls.warnings)
        cls.html = render_base(cls.base, cls.vault, cls.resolver,
                               "Bases/Reading.html", cls.warnings)

    def test_table_structure(self):
        self.assertIn('class="base-table"', self.html)
        self.assertIn("<th>Status</th>", self.html)          # displayName
        self.assertIn("<th>name</th>", self.html)            # file.name label
        self.assertIn('href="../Library/A.html"', self.html)
        self.assertIn("3 notes", self.html)

    def test_sorted_rows(self):
        self.assertLess(self.html.find("Library/B.html"), self.html.find("Library/A.html"))

    def test_wikilink_cell_resolves(self):
        # NoteCtx resolves wikilink-shaped property values to Link objects;
        # _cell_html renders those as an internal-link anchor.
        self.assertIn('class="internal-link"', self.html)
        self.assertNotIn("Link(target=", self.html)

    def test_tabs_and_hidden_views(self):
        self.assertIn('class="base-tabs"', self.html)
        self.assertIn('data-view="Queue"', self.html)
        self.assertIn("<section class=\"base-view\" data-view=\"Queue\"", self.html)
        self.assertIn("hidden", self.html)
        self.assertIn("site-assets/bases.js", self.html)

    def test_cards_view_and_image(self):
        self.assertIn('class="base-cards"', self.html)
        # cover is a wikilink-shaped property (NoteCtx hands back a Link);
        # _resolve_image must resolve it to the cover <img> src.
        self.assertIn('<img src=', self.html)
        self.assertIn('src="../Attachments/diagram.png"', self.html)

    def test_embed_mode(self):
        html = render_base(self.base, self.vault, self.resolver,
                           "Library/Shelf.html", [], view="Covers", embed=True)
        self.assertIn('class="base-embed"', html)
        self.assertIn('href="../Bases/Reading.html"', html)
        self.assertNotIn("base-tabs", html)
        self.assertNotIn("bases.js", html)
        self.assertIn("base-cards", html)

    def test_empty_base_notice(self):
        empty = parse_base("filters: x\n", "Bases/E.base", [])
        html = render_base(empty, self.vault, self.resolver, "Bases/E.html", [])
        self.assertIn("base-empty", html)

    def test_html_escaping(self):
        w = []
        vault_tmp, vault = make_vault({
            "X.md": "---\ntags: [book]\nstatus: '<script>alert(1)</script>'\n---\nx"})
        self.addCleanup(vault_tmp.cleanup)
        base = parse_base(
            "views:\n  - type: table\n    order: [file.name, status]\n", "B.base", w)
        html = render_base(base, vault, LinkResolver(vault), "B.html", w)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)


class RenderNewFeaturesTests(VaultCase):
    def test_formula_cell_renders_value(self):
        from ssg.links import LinkResolver
        vault = scan_vault(self.make_vault({"A.md": "---\nprice: 3\n---\nx"}), SiteConfig())
        base = bases.parse_base(
            "formulas:\n  dbl: price * 2\n"
            "views:\n  - type: table\n    name: V\n    order: [file.name, formula.dbl]\n",
            "B.base", [])
        html = bases.render_base(base, vault, LinkResolver(vault), "B.html", [])
        self.assertIn("<td>6</td>", html)

    def test_group_headers_and_summary(self):
        from ssg.links import LinkResolver
        vault = scan_vault(self.make_vault({
            "A.md": "---\nstatus: done\nprice: 2\n---\nx",
            "B.md": "---\nstatus: done\nprice: 3\n---\nx",
            "C.md": "---\nstatus: todo\nprice: 5\n---\nx"}), SiteConfig())
        base = bases.parse_base(
            "views:\n  - type: table\n    name: V\n    order: [file.name, price]\n"
            "    groupBy: {property: status, direction: ASC}\n"
            "    summaries: {price: Sum}\n", "B.base", [])
        html = bases.render_base(base, vault, LinkResolver(vault), "B.html", [])
        self.assertIn("base-group-head", html)
        self.assertIn("done", html)
        self.assertIn("base-summary", html)
        self.assertIn("10", html)  # overall Sum of prices 2+3+5

    def test_list_view(self):
        from ssg.links import LinkResolver
        vault = scan_vault(self.make_vault({"A.md": "---\nprice: 3\n---\nx"}), SiteConfig())
        base = bases.parse_base(
            "views:\n  - type: list\n    name: V\n    order: [file.name, price]\n", "B.base", [])
        html = bases.render_base(base, vault, LinkResolver(vault), "B.html", [])
        self.assertIn("base-list", html)
        self.assertIn("A", html)

    def test_formula_column_empty_with_parse_warning(self):
        from ssg.links import LinkResolver
        vault = scan_vault(self.make_vault({"A.md": "---\nprice: 5\n---\nx"}), SiteConfig())
        warnings = []
        base = bases.parse_base(
            'formulas:\n  bad: "1 +"\n'
            "views:\n  - type: table\n    name: V\n    order: [formula.bad]\n",
            "B.base", warnings)
        # an unparseable formula warns at parse time
        self.assertTrue(any("bad" in w for w in warnings), warnings)
        html = bases.render_base(base, vault, LinkResolver(vault), "B.html", [])
        # the single formula column renders an empty cell (no value leaked)
        self.assertIn("<tbody><tr><td></td></tr></tbody>", html)

    def test_list_chip_escaped_once(self):
        from ssg.links import LinkResolver
        vault = scan_vault(self.make_vault(
            {"A.md": "---\ngenre: [\"A & B\"]\n---\nx"}), SiteConfig())
        base = bases.parse_base(
            "views:\n  - type: table\n    name: V\n    order: [file.name, genre]\n",
            "B.base", [])
        html = bases.render_base(base, vault, LinkResolver(vault), "B.html", [])
        self.assertIn("A &amp; B", html)          # escaped once
        self.assertNotIn("A &amp;amp; B", html)    # not double-escaped


class BaseEmbedTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.vault = make_vault({
            "Shelf.md": "before\n\n![[Reading.base#Covers]]\n\nafter",
            "Missing.md": "![[Nope.base]]",
            "Bases/Reading.base": "views:\n  - type: table\n",
        })
        self.addCleanup(self.tmp.cleanup)
        self.renderer = NoteRenderer(self.vault, LinkResolver(self.vault))

    def test_embed_dispatches_to_provider(self):
        calls = []

        def provider(rel, view, out):
            calls.append((rel, view, out))
            return '<div class="base-embed">RENDERED</div>'

        self.renderer.base_provider = provider
        html = self.renderer.render_note(self.vault.notes["Shelf.md"]).html
        self.assertIn("RENDERED", html)
        self.assertEqual(calls, [("Bases/Reading.base", "Covers", "Shelf.html")])

    def test_embed_without_provider_is_broken_link(self):
        html = self.renderer.render_note(self.vault.notes["Shelf.md"]).html
        self.assertIn("broken-link", html)

    def test_missing_base_warns(self):
        self.renderer.base_provider = lambda rel, view, out: "X"
        html = self.renderer.render_note(self.vault.notes["Missing.md"]).html
        self.assertIn("broken-link", html)
        self.assertTrue(any("Nope.base" in w for w in self.renderer.warnings))

    def test_hostile_view_name_cannot_forge_tokens(self):
        tmp, vault = make_vault({
            "Evil.md": "![[Reading.base#x--><!--twb-base-embed:evil#p-->more]]",
            "Bases/Reading.base": "views:\n  - type: table\n",
        })
        self.addCleanup(tmp.cleanup)
        renderer = NoteRenderer(vault, LinkResolver(vault))
        calls = []
        renderer.base_provider = lambda rel, view, out: calls.append(rel) or "<div>OK</div>"
        html = renderer.render_note(vault.notes["Evil.md"]).html
        self.assertEqual(calls, ["Bases/Reading.base"])  # exactly one, validated rel
        self.assertNotIn("evil", "".join(calls))
        self.assertNotIn("twb-base-embed", html)  # no unconsumed tokens leak


if __name__ == "__main__":
    unittest.main()
