import datetime
import unittest

from ssg import basevalue as bv


class TruthyTests(unittest.TestCase):
    def test_falsy(self):
        for v in (None, False, 0, 0.0, "", "   ", []):
            self.assertFalse(bv.truthy(v), v)

    def test_truthy(self):
        for v in (True, 1, -2, "x", [0], datetime.date(2026, 1, 1)):
            self.assertTrue(bv.truthy(v), v)


class TypeNameTests(unittest.TestCase):
    def test_names(self):
        self.assertEqual(bv.type_name(None), "null")
        self.assertEqual(bv.type_name(True), "boolean")
        self.assertEqual(bv.type_name(3), "number")
        self.assertEqual(bv.type_name(3.5), "number")
        self.assertEqual(bv.type_name("x"), "string")
        self.assertEqual(bv.type_name([1]), "list")
        self.assertEqual(bv.type_name(bv.Link("A")), "link")
        self.assertEqual(bv.type_name(datetime.date(2026, 1, 1)), "date")
        self.assertEqual(bv.type_name(datetime.datetime(2026, 1, 1, 5)), "datetime")


class BinaryTests(unittest.TestCase):
    def test_numeric_arithmetic(self):
        self.assertEqual(bv.binary("+", 2, 3), 5)
        self.assertEqual(bv.binary("*", 2, 3), 6)
        self.assertEqual(bv.binary("/", 7, 2), 3.5)
        self.assertEqual(bv.binary("%", 7, 3), 1)

    def test_string_concat_with_plus(self):
        self.assertEqual(bv.binary("+", "a", "b"), "ab")
        self.assertEqual(bv.binary("+", "n=", 3), "n=3")
        self.assertEqual(bv.binary("+", 3, " items"), "3 items")

    def test_date_plus_duration(self):
        d = datetime.date(2026, 1, 1)
        self.assertEqual(bv.binary("+", d, bv.Duration(86400)), datetime.date(2026, 1, 2))

    def test_divide_by_zero_raises(self):
        with self.assertRaises(bv.BaseError):
            bv.binary("/", 1, 0)

    def test_bad_type_raises(self):
        with self.assertRaises(bv.BaseError):
            bv.binary("*", "a", "b")


class CompareTests(unittest.TestCase):
    def test_equality_any_types(self):
        self.assertTrue(bv.compare("==", "a", "a"))
        self.assertTrue(bv.compare("!=", "a", "b"))
        self.assertTrue(bv.compare("==", 3, 3))
        self.assertFalse(bv.compare("==", 3, "3"))

    def test_ordering_numbers_and_strings(self):
        self.assertTrue(bv.compare(">", 5, 3))
        self.assertTrue(bv.compare("<=", "a", "b"))

    def test_ordering_dates(self):
        self.assertTrue(bv.compare("<", datetime.date(2026, 1, 1), datetime.date(2026, 2, 1)))

    def test_ordering_mismatched_types_false(self):
        self.assertFalse(bv.compare(">", "a", 3))
        self.assertFalse(bv.compare("<", None, 3))
