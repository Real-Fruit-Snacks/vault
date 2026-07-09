import unittest

from ssg import baseexpr as be


class ParseTests(unittest.TestCase):
    def test_literals(self):
        self.assertEqual(be.parse("42"), be.Lit(42))
        self.assertEqual(be.parse("3.5"), be.Lit(3.5))
        self.assertEqual(be.parse('"hi"'), be.Lit("hi"))
        self.assertEqual(be.parse("'hi'"), be.Lit("hi"))
        self.assertEqual(be.parse("true"), be.Lit(True))
        self.assertEqual(be.parse("false"), be.Lit(False))
        self.assertEqual(be.parse("null"), be.Lit(None))

    def test_ref_dotted(self):
        self.assertEqual(be.parse("price"), be.Ref("price"))
        self.assertEqual(be.parse("file.name"), be.Ref("file.name"))
        self.assertEqual(be.parse("note.age"), be.Ref("note.age"))
        self.assertEqual(be.parse("formula.ppu"), be.Ref("formula.ppu"))

    def test_arithmetic_precedence(self):
        # 1 + 2 * 3  ->  1 + (2 * 3)
        t = be.parse("1 + 2 * 3")
        self.assertEqual(t, be.Binary("+", be.Lit(1), be.Binary("*", be.Lit(2), be.Lit(3))))

    def test_comparison_and_boolean(self):
        t = be.parse("price > 10 && status == \"done\"")
        self.assertEqual(t, be.Binary(
            "&&",
            be.Binary(">", be.Ref("price"), be.Lit(10)),
            be.Binary("==", be.Ref("status"), be.Lit("done"))))

    def test_unary_not_and_neg(self):
        self.assertEqual(be.parse("!done"), be.Unary("!", be.Ref("done")))
        self.assertEqual(be.parse("-5"), be.Lit(-5))
        self.assertEqual(be.parse("-price"), be.Unary("-", be.Ref("price")))

    def test_parens(self):
        t = be.parse("(1 + 2) * 3")
        self.assertEqual(t, be.Binary("*", be.Binary("+", be.Lit(1), be.Lit(2)), be.Lit(3)))

    def test_global_call(self):
        self.assertEqual(be.parse("now()"), be.Call("now", []))
        self.assertEqual(be.parse('if(price, "y", "n")'),
                         be.Call("if", [be.Ref("price"), be.Lit("y"), be.Lit("n")]))

    def test_method_and_field_chain(self):
        # price.toFixed(2)
        self.assertEqual(be.parse("price.toFixed(2)"),
                         be.Method(be.Ref("price"), "toFixed", [be.Lit(2)]))
        # title.lower().contains("x")
        self.assertEqual(
            be.parse('title.lower().contains("x")'),
            be.Method(be.Method(be.Ref("title"), "lower", []), "contains", [be.Lit("x")]))
        # tags.length  (field, no parens)
        self.assertEqual(be.parse("tags.length"), be.Field(be.Ref("tags"), "length"))

    def test_file_hastag_is_method_on_file_ref(self):
        # file.hasTag("book") -> Method(Ref("file"), "hasTag", ["book"])
        self.assertEqual(be.parse('file.hasTag("book")'),
                         be.Method(be.Ref("file"), "hasTag", [be.Lit("book")]))

    def test_namespaced_field_chain(self):
        self.assertEqual(be.parse("file.tags.length"),
                         be.Field(be.Ref("file.tags"), "length"))
        self.assertEqual(be.parse("note.age.year"),
                         be.Field(be.Ref("note.age"), "year"))
        # a genuine call still wins over field-extension
        self.assertEqual(be.parse('file.tags.contains("x")'),
                         be.Method(be.Ref("file.tags"), "contains", [be.Lit("x")]))

    def test_string_escapes_preserve_non_ascii(self):
        self.assertEqual(be.parse('"a\\tb"'), be.Lit("a\tb"))
        self.assertEqual(be.parse('"café\\tx"'), be.Lit("café\tx"))

    def test_syntax_error_returns_none(self):
        self.assertIsNone(be.parse("1 +"))
        self.assertIsNone(be.parse("(1 + 2"))
        self.assertIsNone(be.parse("price >"))
        self.assertIsNone(be.parse("@#$"))
        self.assertIsNone(be.parse(""))

    def test_deeply_nested_input_degrades_not_crash(self):
        self.assertIsNone(be.parse("!" * 5000 + "x"))
        self.assertIsNone(be.parse("(" * 5000 + "1" + ")" * 5000))
