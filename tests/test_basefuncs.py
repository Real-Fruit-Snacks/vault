import datetime
import unittest

from ssg import basefuncs as bf
from ssg import basevalue as bv

NOW = datetime.datetime(2026, 7, 8, 12, 0, 0)


class GlobalTests(unittest.TestCase):
    def test_if(self):
        self.assertEqual(bf.call_global("if", [True, "y", "n"], NOW), "y")
        self.assertEqual(bf.call_global("if", [0, "y", "n"], NOW), "n")
        self.assertIsNone(bf.call_global("if", [False, "y"], NOW))

    def test_now_today(self):
        self.assertEqual(bf.call_global("now", [], NOW), NOW)
        self.assertEqual(bf.call_global("today", [], NOW), datetime.date(2026, 7, 8))

    def test_number_min_max(self):
        self.assertEqual(bf.call_global("number", ["42"], NOW), 42)
        self.assertEqual(bf.call_global("min", [3, 1, 2], NOW), 1)
        self.assertEqual(bf.call_global("max", [3, 1, 2], NOW), 3)

    def test_date_and_link_and_list(self):
        self.assertEqual(bf.call_global("date", ["2026-07-08"], NOW), datetime.date(2026, 7, 8))
        self.assertEqual(bf.call_global("link", ["A", "Alpha"], NOW), bv.Link("A", "Alpha"))
        self.assertEqual(bf.call_global("list", ["x"], NOW), ["x"])
        self.assertEqual(bf.call_global("list", [["x", "y"]], NOW), ["x", "y"])

    def test_unknown_global_raises(self):
        with self.assertRaises(bv.BaseError):
            bf.call_global("random", [], NOW)


class StringMethodTests(unittest.TestCase):
    def test_predicates(self):
        self.assertTrue(bf.call_method("Hello", "contains", ["ell"]))
        self.assertTrue(bf.call_method("Hello", "startsWith", ["He"]))
        self.assertTrue(bf.call_method("Hello", "endsWith", ["lo"]))
        self.assertTrue(bf.call_method("", "isEmpty", []))
        self.assertTrue(bf.call_method("abc", "containsAny", ["z", "b"]))
        self.assertTrue(bf.call_method("abc", "containsAll", ["a", "c"]))

    def test_transforms(self):
        self.assertEqual(bf.call_method("Hi", "lower", []), "hi")
        self.assertEqual(bf.call_method("hi there", "title", []), "Hi There")
        self.assertEqual(bf.call_method("  x ", "trim", []), "x")
        self.assertEqual(bf.call_method("a,b,c", "split", [","]), ["a", "b", "c"])
        self.assertEqual(bf.call_method("aXa", "replace", ["X", "-"]), "a-a")
        self.assertEqual(bf.call_method("ab", "repeat", [2]), "abab")
        self.assertEqual(bf.call_method("abc", "slice", [1]), "bc")

    def test_length_field(self):
        self.assertEqual(bf.get_field("hello", "length"), 5)


class NumberMethodTests(unittest.TestCase):
    def test_methods(self):
        self.assertEqual(bf.call_method(3.14159, "round", [2]), 3.14)
        self.assertEqual(bf.call_method(-3, "abs", []), 3)
        self.assertEqual(bf.call_method(3.2, "floor", []), 3)
        self.assertEqual(bf.call_method(3.2, "ceil", []), 4)
        self.assertEqual(bf.call_method(3.14159, "toFixed", [2]), "3.14")


class DateMethodTests(unittest.TestCase):
    def test_fields_and_format(self):
        d = datetime.date(2026, 7, 8)
        self.assertEqual(bf.get_field(d, "year"), 2026)
        self.assertEqual(bf.get_field(d, "month"), 7)
        self.assertEqual(bf.call_method(d, "format", ["%Y/%m"]), "2026/07")


class ListMethodTests(unittest.TestCase):
    def test_methods(self):
        self.assertEqual(bf.get_field([1, 2, 3], "length"), 3)
        self.assertTrue(bf.call_method([1, 2], "contains", [2]))
        self.assertEqual(bf.call_method(["b", "a"], "sort", []), ["a", "b"])
        self.assertEqual(bf.call_method([1, 1, 2], "unique", []), [1, 2])
        self.assertEqual(bf.call_method(["a", "b"], "join", [", "]), "a, b")
        self.assertEqual(bf.call_method([1, 2], "reverse", []), [2, 1])

    def test_unknown_method_raises(self):
        with self.assertRaises(bv.BaseError):
            bf.call_method("x", "nope", [])


class DegradeTests(unittest.TestCase):
    def test_missing_args_raise_baseerror(self):
        cases = [
            lambda: bf.call_global("min", [], NOW),
            lambda: bf.call_global("max", [], NOW),
            lambda: bf.call_global("link", [], NOW),
            lambda: bf.call_method("hi", "contains", []),
            lambda: bf.call_method("hi", "startsWith", []),
            lambda: bf.call_method("hi", "repeat", []),
            lambda: bf.call_method("hi", "replace", ["a"]),
            lambda: bf.call_method([1, 2], "contains", []),
            lambda: bf.call_method(bv.Link("a"), "linksTo", []),
        ]
        for fn in cases:
            with self.assertRaises(bv.BaseError):
                fn()

    def test_bad_values_raise_baseerror(self):
        with self.assertRaises(bv.BaseError):
            bf.call_method("a,b", "split", [""])
        with self.assertRaises(bv.BaseError):
            bf.call_method(3.14, "toFixed", [-1])
