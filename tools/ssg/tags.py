from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class TagNode:
    path: str                                   # full tag path, e.g. "net/vpn"
    name: str                                   # leaf segment, e.g. "vpn"
    direct: set = field(default_factory=set)    # notes tagged exactly this path
    notes: set = field(default_factory=set)     # aggregate: direct + all descendants
    children: list = field(default_factory=list)


def ancestors(path: str) -> list:
    """Every prefix of a tag path, shallowest first.

    ancestors("a/b/c") -> ["a", "a/b", "a/b/c"]
    """
    segs = path.split("/")
    return ["/".join(segs[: i + 1]) for i in range(len(segs))]


def build_tag_tree(direct: dict) -> list:
    """Turn a flat {full-tag-path: set(note paths)} map into a sorted tree.

    A node is materialized for every path and every ancestor prefix, so a
    parent (#net) is synthesized even when only a child (#net/vpn) is tagged.
    Each node's `notes` aggregates its own `direct` notes plus every
    descendant's, de-duplicated. Roots and children are sorted
    case-insensitively by their leaf segment.
    """
    nodes: dict = {}
    for tag in direct:
        for anc in ancestors(tag):
            if anc not in nodes:
                nodes[anc] = TagNode(path=anc, name=anc.split("/")[-1])
    for tag, paths in direct.items():
        nodes[tag].direct |= set(paths)

    roots: list = []
    for path, node in nodes.items():
        if "/" in path:
            nodes[path.rsplit("/", 1)[0]].children.append(node)
        else:
            roots.append(node)
    for node in nodes.values():
        node.children.sort(key=lambda n: n.name.lower())
    roots.sort(key=lambda n: n.name.lower())

    def aggregate(node: TagNode) -> set:
        acc = set(node.direct)
        for child in node.children:
            acc |= aggregate(child)
        node.notes = acc
        return acc

    for root in roots:
        aggregate(root)
    return roots


def iter_nodes(roots) -> Iterator:
    """Pre-order walk over the whole forest."""
    for node in roots:
        yield node
        yield from iter_nodes(node.children)
