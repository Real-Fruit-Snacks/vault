import unittest

from ssg import tags


class AncestorsTests(unittest.TestCase):
    def test_single_segment(self):
        self.assertEqual(tags.ancestors("python"), ["python"])

    def test_multi_segment(self):
        self.assertEqual(tags.ancestors("a/b/c"), ["a", "a/b", "a/b/c"])


class BuildTagTreeTests(unittest.TestCase):
    def test_flat_tags_become_sorted_roots(self):
        roots = tags.build_tag_tree({"python": {"A.md"}, "git": {"B.md"}})
        self.assertEqual([r.path for r in roots], ["git", "python"])
        self.assertEqual([r.children for r in roots], [[], []])

    def test_root_sort_is_case_insensitive(self):
        roots = tags.build_tag_tree({"Zebra": {"A.md"}, "apple": {"B.md"}})
        self.assertEqual([r.path for r in roots], ["apple", "Zebra"])

    def test_parent_is_synthesized_when_absent(self):
        roots = tags.build_tag_tree({"proj/site": {"A.md"}})
        self.assertEqual(len(roots), 1)
        proj = roots[0]
        self.assertEqual(proj.path, "proj")
        self.assertEqual(proj.name, "proj")
        self.assertEqual(proj.direct, set())            # nothing tagged bare #proj
        self.assertEqual([c.path for c in proj.children], ["proj/site"])
        self.assertEqual(proj.children[0].name, "site")

    def test_notes_aggregate_and_dedup(self):
        # A.md carries both parent and child; B.md only the child.
        roots = tags.build_tag_tree({"proj": {"A.md"}, "proj/site": {"A.md", "B.md"}})
        proj = roots[0]
        self.assertEqual(proj.direct, {"A.md"})
        self.assertEqual(proj.notes, {"A.md", "B.md"})   # union, de-duplicated
        self.assertEqual(proj.children[0].notes, {"A.md", "B.md"})

    def test_aggregate_count_is_at_least_child_count(self):
        roots = tags.build_tag_tree(
            {"net": {"A.md"}, "net/vpn": {"B.md"}, "net/dns": {"C.md"}})
        net = roots[0]
        self.assertEqual(len(net.notes), 3)
        self.assertTrue(all(len(net.notes) >= len(c.notes) for c in net.children))

    def test_children_sorted_case_insensitively(self):
        roots = tags.build_tag_tree(
            {"net/Zulu": {"A.md"}, "net/alpha": {"B.md"}})
        self.assertEqual([c.name for c in roots[0].children], ["alpha", "Zulu"])

    def test_deep_nesting(self):
        roots = tags.build_tag_tree({"a/b/c": {"A.md"}})
        self.assertEqual([n.path for n in tags.iter_nodes(roots)],
                         ["a", "a/b", "a/b/c"])
        self.assertEqual(roots[0].notes, {"A.md"})


class IterNodesTests(unittest.TestCase):
    def test_preorder_over_forest(self):
        roots = tags.build_tag_tree(
            {"git": {"A.md"}, "net/vpn": {"B.md"}})
        self.assertEqual([n.path for n in tags.iter_nodes(roots)],
                         ["git", "net", "net/vpn"])
