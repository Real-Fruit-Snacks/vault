from __future__ import annotations

from . import urls
from .vault import Vault


def build_graph(vault: Vault, backlinks: dict) -> dict:
    """Undirected note graph derived from the backlinks structure, so graph
    edges always agree with the backlinks panels. Node ids are positions in
    sorted(vault.notes), stable across builds."""
    order = sorted(vault.notes)
    index = {path: i for i, path in enumerate(order)}
    nodes = [{"id": index[path], "title": vault.notes[path].title,
              "url": urls.note_output_path(path)} for path in order]
    edge_set = set()
    for target, sources in backlinks.items():
        for src in sources:
            a, b = index[src], index[target]
            edge_set.add((a, b) if a < b else (b, a))
    return {"nodes": nodes, "edges": [list(pair) for pair in sorted(edge_set)]}
