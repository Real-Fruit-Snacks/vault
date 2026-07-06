import unittest

from ssg.config import SiteConfig
from ssg.graphdata import build_graph
from ssg.links import LinkResolver, build_backlinks
from ssg.vault import scan_vault
from tests.helpers import VaultCase


def make_graph(case, files):
    vault = scan_vault(case.make_vault(files), SiteConfig())
    resolver = LinkResolver(vault)
    return build_graph(vault, build_backlinks(vault, resolver))


class GraphDataTests(VaultCase):
    def test_every_note_is_a_node_with_stable_sorted_ids(self):
        graph = make_graph(self, {
            "B.md": "no links here",
            "A.md": "see [[B]]",
            "Sub/C.md": "see [[A]]",
        })
        self.assertEqual(
            [(n["id"], n["url"]) for n in graph["nodes"]],
            [(0, "A.html"), (1, "B.html"), (2, "Sub/C.html")])

    def test_titles_come_from_notes(self):
        graph = make_graph(self, {"A.md": "---\ntitle: Alpha\n---\nbody"})
        self.assertEqual(graph["nodes"][0]["title"], "Alpha")

    def test_edges_are_undirected_deduplicated_pairs(self):
        graph = make_graph(self, {
            "A.md": "[[B]] and [[B]] again",
            "B.md": "back to [[A]]",
        })
        self.assertEqual(graph["edges"], [[0, 1]])

    def test_embeds_create_edges(self):
        graph = make_graph(self, {"A.md": "![[B]]", "B.md": "content"})
        self.assertEqual(graph["edges"], [[0, 1]])

    def test_orphans_and_unresolved_links_have_no_edges(self):
        graph = make_graph(self, {"A.md": "[[Nowhere]]", "B.md": "alone"})
        self.assertEqual(len(graph["nodes"]), 2)
        self.assertEqual(graph["edges"], [])

    def test_self_links_produce_no_edges(self):
        graph = make_graph(self, {"A.md": "see [[A]]"})
        self.assertEqual(graph["edges"], [])

    def test_edges_sorted(self):
        graph = make_graph(self, {"A.md": "[[C]]", "B.md": "[[C]]", "C.md": "x"})
        self.assertEqual(graph["edges"], [[0, 2], [1, 2]])


if __name__ == "__main__":
    unittest.main()
