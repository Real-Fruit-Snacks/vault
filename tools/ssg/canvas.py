from __future__ import annotations

import html as html_mod
import json
import math
import re
from dataclasses import dataclass

from . import urls
from .obsidian import IMAGE_EXTS, extract_section
from .vault import Note

PRESET_COLORS = {
    "1": "var(--twb-red)", "2": "var(--twb-orange)", "3": "var(--twb-warm)",
    "4": "var(--twb-accent)", "5": "var(--twb-accent-alt)", "6": "var(--twb-violet)",
}
_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{3,8}$")
NODE_TYPES = {"text", "file", "link", "group"}
SIDES = ("top", "right", "bottom", "left")
PAD = 24


def canvas_color(value):
    if not isinstance(value, str):
        return None
    if value in PRESET_COLORS:
        return PRESET_COLORS[value]
    if _HEX_RE.match(value):
        return value
    return None


@dataclass
class Canvas:
    path: str
    title: str
    nodes: list
    edges: list
    width: float
    height: float
    text_content: str


def _opt_str(item: dict, key: str) -> str:
    return item[key] if isinstance(item.get(key), str) else ""


def parse_canvas(text: str, rel: str, warnings: list):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        warnings.append(f"{rel}: invalid canvas JSON ({exc}); skipped")
        return None
    if not isinstance(data, dict):
        warnings.append(f"{rel}: canvas is not a JSON object; skipped")
        return None

    nodes = []
    raw_nodes = data.get("nodes")
    for item in raw_nodes if isinstance(raw_nodes, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            x, y, w, h = (float(item["x"]), float(item["y"]),
                          float(item["width"]), float(item["height"]))
            if not all(math.isfinite(v) for v in (x, y, w, h)):
                raise ValueError("non-finite coordinate")
            node = {
                "id": str(item["id"]),
                "type": item.get("type"),
                "x": x, "y": y, "w": w, "h": h,
                "color": canvas_color(item.get("color")),
            }
        except (KeyError, TypeError, ValueError):
            warnings.append(f"{rel}: node missing/invalid id/x/y/width/height; skipped")
            continue
        node_type = node["type"]
        if not isinstance(node_type, str) or node_type not in NODE_TYPES:
            warnings.append(f"{rel}: unknown node type {node_type!r}")
            node["type"] = "unknown"
        for key in ("text", "file", "subpath", "url", "label"):
            node[key] = _opt_str(item, key)
        nodes.append(node)

    ids = {n["id"] for n in nodes}
    edges = []
    raw_edges = data.get("edges")
    for item in raw_edges if isinstance(raw_edges, list) else []:
        if not isinstance(item, dict):
            continue
        from_node, to_node = item.get("fromNode"), item.get("toNode")
        if not isinstance(from_node, str) or not isinstance(to_node, str) or \
                from_node not in ids or to_node not in ids:
            warnings.append(f"{rel}: edge references a missing node; skipped")
            continue
        edges.append({
            "from": item["fromNode"], "to": item["toNode"],
            "from_side": item.get("fromSide") if item.get("fromSide") in SIDES else None,
            "to_side": item.get("toSide") if item.get("toSide") in SIDES else None,
            "from_end": item.get("fromEnd", "none"),
            "to_end": item.get("toEnd", "arrow"),
            "color": canvas_color(item.get("color")),
            "label": _opt_str(item, "label"),
        })

    if nodes:
        min_x = min(n["x"] for n in nodes)
        min_y = min(n["y"] for n in nodes)
        for n in nodes:
            n["x"] += PAD - min_x
            n["y"] += PAD - min_y
        width = max(n["x"] + n["w"] for n in nodes) + PAD
        height = max(n["y"] + n["h"] for n in nodes) + PAD
    else:
        width = height = 2.0 * PAD

    return Canvas(
        path=rel, title=rel.rsplit("/", 1)[-1][:-7], nodes=nodes, edges=edges,
        width=width, height=height,
        text_content=" ".join(n["text"] for n in nodes if n["type"] == "text" and n["text"]))


@dataclass
class CanvasRender:
    html: str
    has_mermaid: bool = False


def _style(n) -> str:
    color = f" --canvas-color: {n['color']};" if n["color"] else ""
    return (f'style="left:{n["x"]:g}px;top:{n["y"]:g}px;'
            f'width:{n["w"]:g}px;height:{n["h"]:g}px;{color}"')


def _placeholder(n, label: str) -> str:
    return (f'<div class="canvas-node canvas-card canvas-missing" {_style(n)}>'
            f"{html_mod.escape(label)}</div>")


def _file_card(n, canvas, vault, renderer, output_path, warnings, render) -> str:
    target = n["file"]
    ext = ("." + target.rsplit(".", 1)[-1].lower()) if "." in target else ""
    if ext in IMAGE_EXTS and target in vault.assets:
        src = urls.rel_href(output_path, target)
        return (f'<div class="canvas-node canvas-card canvas-image" {_style(n)}>'
                f'<img src="{src}" alt="{html_mod.escape(target, quote=True)}"></div>')
    if ext == ".canvas" and target in vault.canvases:
        href = urls.rel_href(output_path, urls.canvas_output_path(target))
        title = target.rsplit("/", 1)[-1][:-7]
        return (f'<div class="canvas-node canvas-card" {_style(n)}>'
                f'<div class="canvas-embed-head manifest-label">'
                f'<a href="{href}">{html_mod.escape(title)}</a></div></div>')
    if ext == ".base" and target in vault.bases:
        href = urls.rel_href(output_path, urls.base_output_path(target))
        title = target.rsplit("/", 1)[-1][:-5]
        return (f'<div class="canvas-node canvas-card" {_style(n)}>'
                f'<div class="canvas-embed-head manifest-label">'
                f'<a href="{href}">{html_mod.escape(title)}</a></div></div>')
    note = vault.notes.get(target)
    if note is not None:
        res = renderer.render_note(note, output_path=output_path)
        if res.has_mermaid:
            render.has_mermaid = True
        inner = res.html
        frag = ""
        if n["subpath"].startswith("#") and not n["subpath"].startswith("#^"):
            slug = urls.slugify_heading(n["subpath"][1:])
            inner = extract_section(res.html, slug)
            frag = slug
        href = urls.rel_href(output_path, urls.note_output_path(target), frag)
        return (f'<div class="canvas-node canvas-card" {_style(n)}>'
                f'<div class="canvas-embed-head manifest-label">'
                f'<a href="{href}">{html_mod.escape(note.title)}</a></div>'
                f'<div class="canvas-embed-body">{inner}</div></div>')
    if target in vault.unpublished:
        warnings.append(f"{canvas.path}: card embeds unpublished note {target}")
        return _placeholder(n, "not published")
    if target in vault.assets:  # non-image asset: link to it
        href = urls.rel_href(output_path, target)
        return (f'<a class="canvas-node canvas-card canvas-link-card" {_style(n)} '
                f'href="{href}">{html_mod.escape(target)}</a>')
    warnings.append(f"{canvas.path}: card references missing file {target}")
    return _placeholder(n, "missing: " + target.rsplit("/", 1)[-1])


def _node_html(n, canvas, vault, renderer, output_path, warnings, render) -> str:
    if n["type"] == "group":
        label = ""
        if n["label"]:
            label = (f'<div class="canvas-group-label manifest-label">'
                     f"{html_mod.escape(n['label'])}</div>")
        return f'<div class="canvas-node canvas-group" {_style(n)}>{label}</div>'
    if n["type"] == "text":
        synthetic = Note(path=canvas.path, title=canvas.title, frontmatter={}, body=n["text"])
        res = renderer.render_note(synthetic, output_path=output_path)
        if res.has_mermaid:
            render.has_mermaid = True
        return (f'<div class="canvas-node canvas-card" {_style(n)}>'
                f'<div class="canvas-card-content">{res.html}</div></div>')
    if n["type"] == "link":
        url = n["url"]
        # Same trust rule as markdown links: only navigable web schemes get
        # a clickable card; javascript:/data:/etc degrade to a dead card.
        if not re.match(r"(?i)^(https?:|mailto:)", url):
            warnings.append(f"{canvas.path}: link card has unsupported URL {url!r}")
            return _placeholder(n, url or "empty link")
        safe = html_mod.escape(url, quote=True)
        return (f'<a class="canvas-node canvas-card canvas-link-card" {_style(n)} '
                f'href="{safe}" target="_blank" rel="noopener">{html_mod.escape(url)}</a>')
    if n["type"] == "file":
        return _file_card(n, canvas, vault, renderer, output_path, warnings, render)
    return _placeholder(n, "unsupported card")


_DIR = {"top": (0, -1), "bottom": (0, 1), "left": (-1, 0), "right": (1, 0)}


def _anchor(n, side):
    if side == "top":
        return (n["x"] + n["w"] / 2, n["y"])
    if side == "bottom":
        return (n["x"] + n["w"] / 2, n["y"] + n["h"])
    if side == "left":
        return (n["x"], n["y"] + n["h"] / 2)
    return (n["x"] + n["w"], n["y"] + n["h"] / 2)


def _pick_sides(a, b, from_side, to_side):
    best = None
    for fs in ((from_side,) if from_side else SIDES):
        for ts in ((to_side,) if to_side else SIDES):
            pa, pb = _anchor(a, fs), _anchor(b, ts)
            d = (pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2
            if best is None or d < best[0]:
                best = (d, fs, ts)
    return best[1], best[2]


def edges_svg(canvas) -> str:
    by_id = {n["id"]: n for n in canvas.nodes}
    parts = []
    for e in canvas.edges:
        a, b = by_id[e["from"]], by_id[e["to"]]
        fs, ts = _pick_sides(a, b, e["from_side"], e["to_side"])
        (x1, y1), (x2, y2) = _anchor(a, fs), _anchor(b, ts)
        dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        ext = min(max(dist / 2, 40.0), 200.0)
        c1 = (x1 + _DIR[fs][0] * ext, y1 + _DIR[fs][1] * ext)
        c2 = (x2 + _DIR[ts][0] * ext, y2 + _DIR[ts][1] * ext)
        color = e["color"] or "var(--twb-text-muted)"
        markers = ""
        if e["to_end"] != "none":
            markers += ' marker-end="url(#canvas-arrow)"'
        if e["from_end"] == "arrow":
            markers += ' marker-start="url(#canvas-arrow)"'
        parts.append(
            f'<path d="M {x1:g} {y1:g} C {c1[0]:g} {c1[1]:g}, {c2[0]:g} {c2[1]:g}, '
            f'{x2:g} {y2:g}" stroke="{color}" fill="none" stroke-width="2"{markers}/>')
        if e["label"]:
            mx = (x1 + 3 * (c1[0] + c2[0]) + x2) / 8
            my = (y1 + 3 * (c1[1] + c2[1]) + y2) / 8
            parts.append(f'<text x="{mx:g}" y="{my:g}" class="canvas-edge-label">'
                         f"{html_mod.escape(e['label'])}</text>")
    return (
        f'<svg class="canvas-edges" width="{canvas.width:g}" height="{canvas.height:g}" '
        f'viewBox="0 0 {canvas.width:g} {canvas.height:g}">'
        '<defs><marker id="canvas-arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker></defs>'
        + "".join(parts) + "</svg>")


def canvas_page_content(canvas, vault, renderer, output_path, warnings) -> CanvasRender:
    render = CanvasRender(html="")
    ordered = ([n for n in canvas.nodes if n["type"] == "group"]
               + [n for n in canvas.nodes if n["type"] != "group"])
    parts = [_node_html(n, canvas, vault, renderer, output_path, warnings, render)
             for n in ordered]
    root = urls.root_prefix(output_path)
    render.html = (
        f'<div id="canvas-view">'
        f'<div class="canvas-controls"><button id="canvas-fit" type="button" '
        f'class="manifest-label">fit</button></div>'
        f'<div class="canvas-world" style="width:{canvas.width:g}px;'
        f'height:{canvas.height:g}px">'
        f"{edges_svg(canvas)}{''.join(parts)}</div></div>"
        f'<script defer src="{root}site-assets/canvas.js"></script>')
    return render
