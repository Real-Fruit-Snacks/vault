import datetime
import unittest

from ssg import baseexpr as be
from ssg import basevalue as bv

NOW = datetime.datetime(2026, 7, 8, 12, 0, 0)


class FakeCtx:
    def __init__(self, props):
        self.props = props
        self.build_now = NOW

    def resolve(self, name):
        if name in self.props:
            return self.props[name]
        raise bv.BaseError(f"unknown ref {name}")


class EvalTests(unittest.TestCase):
    def ev(self, text, props=None):
        return be.evaluate(be.parse(text), FakeCtx(props or {}))

    def test_arithmetic_and_concat(self):
        self.assertEqual(self.ev("1 + 2 * 3"), 7)
        self.assertEqual(self.ev('"a" + "b"'), "ab")
        self.assertEqual(self.ev('price.toFixed(2) + " dollars"', {"price": 3.5}), "3.50 dollars")

    def test_comparison_and_boolean(self):
        self.assertTrue(self.ev('price > 10 && status == "done"',
                                {"price": 20, "status": "done"}))
        self.assertFalse(self.ev('price > 10 || status == "x"',
                                 {"price": 5, "status": "y"}))

    def test_property_to_property(self):
        self.assertTrue(self.ev("price > cost", {"price": 10, "cost": 3}))

    def test_if_and_functions(self):
        self.assertEqual(self.ev('if(done, "yes", "no")', {"done": True}), "yes")
        self.assertEqual(self.ev("min(3, 1, 2)"), 1)

    def test_method_chain(self):
        self.assertTrue(self.ev('title.lower().contains("hi")', {"title": "OHIO"}))

    def test_now_compare(self):
        past = datetime.date(2020, 1, 1)
        self.assertTrue(self.ev("due < now()", {"due": past}))

    def test_unknown_ref_degrades_to_null(self):
        self.assertIsNone(self.ev("nope"))
        self.assertIsNone(self.ev("nope.length"))

    def test_type_error_degrades_to_null(self):
        self.assertIsNone(self.ev('"a" * "b"'))

    def test_compile_and_predicate(self):
        fn = be.compile('price > 5')
        self.assertTrue(fn(FakeCtx({"price": 9})))
        pred = be.as_predicate('price > 5')
        self.assertTrue(pred(FakeCtx({"price": 9})))
        self.assertFalse(pred(FakeCtx({"price": 1})))
        self.assertIsNone(be.compile("1 +"))       # parse error -> None
        self.assertIsNone(be.as_predicate("1 +"))

    def test_deep_valid_chain_degrades_not_crash(self):
        node = be.parse("x" + ".reverse()" * 4000)  # parses via the iterative postfix loop
        self.assertIsNotNone(node)
        # evaluation recurses on .recv; must degrade to None rather than raise
        self.assertIsNone(be.evaluate(node, FakeCtx({"x": [1, 2]})))
