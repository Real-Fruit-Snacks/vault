import datetime
import unittest

from ssg import bases
from ssg.config import SiteConfig
from ssg.vault import scan_vault
from ssg.links import LinkResolver
from tests.helpers import VaultCase

NOW = datetime.datetime(2026, 7, 8, 12, 0, 0)


class CtxTests(VaultCase):
    def ctx(self, files, path, filedata=None, formulas=None):
        vault = scan_vault(self.make_vault(files), SiteConfig())
        resolver = LinkResolver(vault)
        return bases.NoteCtx(path, vault.notes[path], resolver,
                             filedata=filedata or {}, formulas=formulas or {},
                             build_now=NOW)

    def test_property_refs(self):
        ctx = self.ctx({"A.md": "---\nprice: 9\nstatus: done\n---\nx"}, "A.md")
        self.assertEqual(ctx.resolve("price"), 9)
        self.assertEqual(ctx.resolve("note.status"), "done")

    def test_file_fields(self):
        fd = {"mtime": {"A.md": datetime.date(2026, 7, 6)}, "size": {"A.md": 12}}
        ctx = self.ctx({"A.md": "hello world!"}, "A.md", filedata=fd)
        self.assertEqual(ctx.resolve("file.name"), "A.md")
        self.assertEqual(ctx.resolve("file.basename"), "A")
        self.assertEqual(ctx.resolve("file.ext"), "md")
        self.assertEqual(ctx.resolve("file.mtime"), datetime.date(2026, 7, 6))
        self.assertEqual(ctx.resolve("file.size"), 12)

    def test_file_hastag_method(self):
        ctx = self.ctx({"A.md": "---\ntags: [book]\n---\nx"}, "A.md")
        handled, val = ctx.file_method("hasTag", ["book"])
        self.assertTrue(handled)
        self.assertTrue(val)

    def test_formula_ref_with_cycle_guard(self):
        from ssg import baseexpr
        formulas = {"double": baseexpr.parse("price * 2"),
                    "loop": baseexpr.parse("formula.loop")}
        ctx = self.ctx({"A.md": "---\nprice: 4\n---\nx"}, "A.md", formulas=formulas)
        self.assertEqual(ctx.resolve("formula.double"), 8)
        self.assertIsNone(ctx.resolve("formula.loop"))  # cycle -> null

    def test_file_method_dispatch_via_expr(self):
        from ssg import baseexpr
        ctx = self.ctx({
            "Folder/A.md": "---\ntags: [book]\n---\nsee [[B]]",
            "Folder/B.md": "x",
        }, "Folder/A.md")
        self.assertTrue(baseexpr.evaluate(baseexpr.parse('file.inFolder("Folder")'), ctx))
        self.assertFalse(baseexpr.evaluate(baseexpr.parse('file.inFolder("Other")'), ctx))
        self.assertTrue(baseexpr.evaluate(baseexpr.parse('file.hasLink("B")'), ctx))
        self.assertFalse(baseexpr.evaluate(baseexpr.parse('file.hasLink("Nope")'), ctx))
        self.assertTrue(baseexpr.evaluate(baseexpr.parse('file.hasProperty("tags")'), ctx))
        self.assertFalse(baseexpr.evaluate(baseexpr.parse('file.hasProperty("nope")'), ctx))

    def test_file_aslink_returns_link(self):
        from ssg.basevalue import Link
        ctx = self.ctx({"A.md": "x"}, "A.md")
        handled, val = ctx.file_method("asLink", ["Display Text"])
        self.assertTrue(handled)
        self.assertIsInstance(val, Link)
        self.assertEqual(val.display, "Display Text")

    def test_hastag_hierarchical_match(self):
        from ssg import baseexpr
        ctx = self.ctx({"A.md": "---\ntags: [book/scifi]\n---\nx"}, "A.md")
        self.assertTrue(baseexpr.evaluate(baseexpr.parse('file.hasTag("book/scifi")'), ctx))
        # parent-tag query also matches the more specific child tag
        self.assertTrue(baseexpr.evaluate(baseexpr.parse('file.hasTag("book")'), ctx))


class EvaluateTests(VaultCase):
    def _eval(self, files, base_yaml):
        vault = scan_vault(self.make_vault(files), SiteConfig())
        resolver = LinkResolver(vault)
        base = bases.parse_base(base_yaml, "T.base", [])
        return base, vault, resolver

    def test_property_to_property_filter(self):
        base, vault, resolver = self._eval(
            {"A.md": "---\nprice: 10\ncost: 3\n---\nx",
             "B.md": "---\nprice: 2\ncost: 5\n---\nx"},
            "views:\n  - type: table\n    name: V\n    filters: price > cost\n")
        matches = bases.evaluate(base, base.views[0], vault, resolver, [], build_now=NOW)
        self.assertEqual(matches, ["A.md"])

    def test_sort_by_formula(self):
        base, vault, resolver = self._eval(
            {"A.md": "---\nprice: 2\n---\nx", "B.md": "---\nprice: 9\n---\nx"},
            "formulas:\n  neg: 0 - price\n"
            "views:\n  - type: table\n    name: V\n"
            "    sort:\n      - {property: formula.neg, direction: ASC}\n")
        matches = bases.evaluate(base, base.views[0], vault, resolver, [], build_now=NOW)
        self.assertEqual(matches, ["B.md", "A.md"])  # neg ascending => price desc


class ParseTests(unittest.TestCase):
    def test_parse_groupby_and_summaries(self):
        base = bases.parse_base(
            "views:\n  - type: table\n    name: V\n"
            "    groupBy: {property: status, direction: DESC}\n"
            "    summaries: {price: Sum, formula.ppu: Average}\n", "T.base", [])
        v = base.views[0]
        self.assertEqual(v.group_by, ("status", "DESC"))
        self.assertIn(("price", "Sum"), v.summaries)
        self.assertIn(("formula.ppu", "Average"), v.summaries)
