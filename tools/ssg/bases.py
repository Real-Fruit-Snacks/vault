from __future__ import annotations

import datetime
import html as html_mod
import re
from dataclasses import dataclass

import yaml

from . import mdtext, urls

VIEW_TYPES = {"table", "cards"}


@dataclass
class BaseView:
    name: str
    type: str
    filters: object
    order: list
    sort: list
    limit: int
    image: str


@dataclass
class Base:
    path: str
    title: str
    filters: object
    views: list
    display_names: dict


def _parse_filters(node, rel, warnings):
    """Filter tree: ("expr", text) | (op, [children]) | None."""
    if node is None:
        return None
    if isinstance(node, str):
        return ("expr", node)
    if isinstance(node, dict) and len(node) == 1:
        op = next(iter(node))
        if op in ("and", "or", "not"):
            raw = node[op]
            children = raw if isinstance(raw, list) else [raw]
            parsed = [_parse_filters(c, rel, warnings) for c in children]
            return (op, [p for p in parsed if p is not None])
    warnings.append(f"{rel}: unsupported filters node {node!r}; ignored")
    return None


def parse_base(text, rel, warnings):
    try:
        data = yaml.safe_load(text)
    except (yaml.YAMLError, RecursionError) as exc:
        warnings.append(f"{rel}: invalid base YAML ({exc}); skipped")
        return None
    if not isinstance(data, dict):
        warnings.append(f"{rel}: base is not a YAML mapping; skipped")
        return None
    if data.get("formulas"):
        warnings.append(f"{rel}: formulas are not supported; formula columns render empty")
    display_names = {}
    props = data.get("properties")
    if isinstance(props, dict):
        for key, meta in props.items():
            if isinstance(meta, dict) and isinstance(meta.get("displayName"), str):
                display_names[str(key)] = meta["displayName"]
    views = []
    raw_views = data.get("views")
    for i, item in enumerate(raw_views if isinstance(raw_views, list) else []):
        if not isinstance(item, dict):
            continue
        vtype = item.get("type")
        if not isinstance(vtype, str) or vtype not in VIEW_TYPES:
            warnings.append(f"{rel}: unsupported view type {vtype!r}; view skipped")
            continue
        name = (item["name"] if isinstance(item.get("name"), str)
                else f"{vtype.capitalize()} {i + 1}")
        order = ([str(c) for c in item["order"] if isinstance(c, (str, int))]
                 if isinstance(item.get("order"), list) else [])
        sort = []
        raw_sort = item.get("sort")
        for s in raw_sort if isinstance(raw_sort, list) else []:
            if isinstance(s, dict) and isinstance(s.get("property"), str):
                direction = str(s.get("direction", "ASC")).upper()
                sort.append((s["property"], "DESC" if direction == "DESC" else "ASC"))
        limit = (item["limit"] if isinstance(item.get("limit"), int)
                 and not isinstance(item.get("limit"), bool) and item["limit"] > 0 else 0)
        image = item.get("image") if isinstance(item.get("image"), str) else ""
        views.append(BaseView(name=name, type=vtype,
                              filters=_parse_filters(item.get("filters"), rel, warnings),
                              order=order, sort=sort, limit=limit, image=image))
    return Base(path=rel, title=rel.rsplit("/", 1)[-1][:-5],
                filters=_parse_filters(data.get("filters"), rel, warnings),
                views=views, display_names=display_names)


class NoteCtx:
    """Per-note evaluation context for filter expressions and cell values."""

    def __init__(self, path, note, resolver):
        self.path = path
        self.note = note
        self.resolver = resolver
        self._links = None

    def get(self, operand):
        if operand == "file.name":
            return self.path.rsplit("/", 1)[-1][:-3]
        if operand == "file.path":
            return self.path
        if operand == "file.folder":
            return self.path.rsplit("/", 1)[0] if "/" in self.path else ""
        if operand == "file.ext":
            return "md"
        if operand == "file.tags":
            return list(self.note.tags)
        value = self.note.frontmatter.get(operand)
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()
        return value

    def has_tag(self, tag):
        t = str(tag).lstrip("#").lower()
        return any(x.lower() == t or x.lower().startswith(t + "/")
                   for x in self.note.tags)

    def in_folder(self, folder):
        f = str(folder).strip("/").lower()
        mine = (self.path.rsplit("/", 1)[0] if "/" in self.path else "").lower()
        return mine == f or mine.startswith(f + "/")

    def has_link(self, target):
        if self._links is None:
            self._links = set()
            for t in mdtext.find_wikilink_targets(self.note.body):
                dest = self.resolver.resolve_note(t, self.path)
                if dest:
                    self._links.add(dest)
        dest = self.resolver.resolve_note(str(target), self.path)
        return dest is not None and dest in self._links

    def has_property(self, prop):
        return str(prop) in self.note.frontmatter


_LIT = r'"[^"]*"|\'[^\']*\'|-?\d+(?:\.\d+)?|true|false|null'
_OPERAND = r'file\.(?:name|path|folder|ext|tags)|[A-Za-z_][A-Za-z0-9_-]*'
_CMP_RE = re.compile(rf'^({_OPERAND})\s*(==|!=|>=|<=|>|<)\s*({_LIT})$')
_FUNC_RE = re.compile(rf'^file\.(hasTag|inFolder|hasLink|hasProperty)\(\s*({_LIT})\s*\)$')
_CONTAINS_RE = re.compile(rf'^contains\(\s*({_OPERAND})\s*,\s*({_LIT})\s*\)$')
_BARE_RE = re.compile(rf'^({_OPERAND})$')
_FUNC_METHOD = {"hasTag": "has_tag", "inFolder": "in_folder",
                "hasLink": "has_link", "hasProperty": "has_property"}


def _literal(text):
    if text.startswith(('"', "'")):
        return text[1:-1]
    if text == "true":
        return True
    if text == "false":
        return False
    if text == "null":
        return None
    return float(text) if "." in text else int(text)


def _compare(val, op, lit):
    if op == "==":
        return val == lit
    if op == "!=":
        return val != lit
    # Ordering needs matching, orderable types; anything else is false.
    if isinstance(val, bool) or isinstance(lit, bool):
        return False
    both_num = isinstance(val, (int, float)) and isinstance(lit, (int, float))
    both_str = isinstance(val, str) and isinstance(lit, str)
    if not (both_num or both_str):
        return False
    if op == ">":
        return val > lit
    if op == "<":
        return val < lit
    if op == ">=":
        return val >= lit
    return val <= lit


def compile_expr(text):
    """Compile one filter expression to a predicate, or None if unsupported."""
    t = text.strip()
    if not t:
        return None
    # Consume every leading negation (whitespace-interleaved too) in one
    # loop, so hostile chains like "! ! ! …" can't recurse per run.
    negations = 0
    while t.startswith("!"):
        t = t[1:].lstrip()
        negations += 1
    if negations:
        if not t:
            return None
        inner = compile_expr(t)  # t has no leading "!", so depth is 2 max
        if inner is None:
            return None
        if negations % 2 == 0:
            return inner
        return lambda ctx: not inner(ctx)
    m = _FUNC_RE.match(t)
    if m:
        method, lit = _FUNC_METHOD[m.group(1)], _literal(m.group(2))
        return lambda ctx: getattr(ctx, method)(lit)
    m = _CONTAINS_RE.match(t)
    if m:
        operand, lit = m.group(1), _literal(m.group(2))

        def contains(ctx):
            val = ctx.get(operand)
            if isinstance(val, list):
                return lit in val
            if isinstance(val, str) and isinstance(lit, str):
                return lit.lower() in val.lower()
            return False
        return contains
    m = _CMP_RE.match(t)
    if m:
        operand, op, lit = m.group(1), m.group(2), _literal(m.group(3))
        return lambda ctx: _compare(ctx.get(operand), op, lit)
    m = _BARE_RE.match(t)
    if m:
        operand = m.group(1)

        def truthy(ctx):
            val = ctx.get(operand)
            if isinstance(val, str):
                return bool(val.strip())
            return bool(val)
        return truthy
    return None


def _precompile(tree, cache, rel, warnings, warned):
    """Precompile every leaf expression in the filter tree and warn if unsupported."""
    if tree is None:
        return
    if tree[0] == "expr":
        text = tree[1]
        if text not in cache:
            cache[text] = compile_expr(text)
        if cache[text] is None and text not in warned:
            warned.add(text)
            warnings.append(
                f"{rel}: unsupported filter expression {text!r}; treated as false")
        return
    for child in tree[1]:
        _precompile(child, cache, rel, warnings, warned)


def _eval_tree(tree, ctx, cache, rel, warnings, warned):
    kind = tree[0]
    if kind == "expr":
        text = tree[1]
        if text not in cache:
            cache[text] = compile_expr(text)
        fn = cache[text]
        if fn is None:
            return False
        return fn(ctx)
    children = tree[1]
    if kind == "and":
        return all(_eval_tree(c, ctx, cache, rel, warnings, warned) for c in children)
    if kind == "or":
        return any(_eval_tree(c, ctx, cache, rel, warnings, warned) for c in children)
    # not: true when no child matches
    return not any(_eval_tree(c, ctx, cache, rel, warnings, warned) for c in children)


def _cmp_key(val):
    if isinstance(val, bool):
        return (0, float(val), "")
    if isinstance(val, (int, float)):
        return (0, float(val), "")
    if isinstance(val, str):
        return (1, 0.0, val.lower())
    return (2, 0.0, str(val).lower())


def evaluate(base, view, vault, resolver, warnings):
    cache, warned = {}, set()
    # Precompile every expression once and warn if unsupported, so warnings
    # appear even if short-circuit evaluation skips the expression.
    for tree in (base.filters, view.filters):
        if tree is not None:
            _precompile(tree, cache, base.path, warnings, warned)
    ctxs = {}
    matches = []
    for path in sorted(vault.notes):
        ctx = NoteCtx(path, vault.notes[path], resolver)
        ctxs[path] = ctx
        ok = True
        for tree in (base.filters, view.filters):
            if tree is not None and not _eval_tree(
                    tree, ctx, cache, base.path, warnings, warned):
                ok = False
                break
        if ok:
            matches.append(path)
    # Apply sort keys lowest-priority first (stable), missing values last.
    for prop, direction in reversed(view.sort):
        present = [p for p in matches if ctxs[p].get(prop) is not None]
        absent = [p for p in matches if ctxs[p].get(prop) is None]
        present.sort(key=lambda p: _cmp_key(ctxs[p].get(prop)),
                     reverse=(direction == "DESC"))
        matches = present + absent
    if view.limit:
        matches = matches[:view.limit]
    return matches


_WIKILINK_VAL_RE = re.compile(r"^\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]$")
_IMG_VAL_RE = re.compile(r"^!?\[\[([^\]|#]+)[^\]]*\]\]$")
_URL_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)


def _chip(text, href=None):
    body = html_mod.escape(str(text))
    if href:
        return f'<a class="tag" href="{href}">{body}</a>'
    return f'<span class="base-chip">{body}</span>'


def _cell_html(value, prop, resolver, output_path, from_path):
    if value is None:
        return ""
    if isinstance(value, bool):
        cls = "base-bool" if value else "base-bool base-no"
        return f'<span class="{cls}">{"✓" if value else "✗"}</span>'
    if isinstance(value, list):
        chips = []
        for item in value:
            if prop in ("tags", "file.tags"):
                href = urls.rel_href(output_path, urls.tag_output_path(str(item)))
                chips.append(_chip(f"#{item}", href))
            else:
                chips.append(_chip(item))
        return f'<span class="base-chips">{"".join(chips)}</span>'
    if isinstance(value, str):
        m = _WIKILINK_VAL_RE.match(value.strip())
        if m:
            target, alias = m.group(1).strip(), (m.group(2) or "").strip()
            resolved = resolver.resolve_note(target, from_path)
            label = html_mod.escape(alias or target)
            if resolved is None:
                return f'<span class="broken-link">{label}</span>'
            href = urls.rel_href(output_path, urls.page_output_path(resolved))
            return f'<a class="internal-link" href="{href}">{label}</a>'
        return html_mod.escape(value)
    return html_mod.escape(str(value))


def _col_label(base, col):
    if col in base.display_names:
        return base.display_names[col]
    if col == "file.name":
        return "name"
    if col.startswith("formula."):
        return col[len("formula."):]
    return col


def _row_cells(base, cols, path, ctx, vault, resolver, output_path):
    cells = []
    for col in cols:
        if col == "file.name":
            href = urls.rel_href(output_path, urls.note_output_path(path))
            cells.append(f'<td><a href="{href}">'
                         f"{html_mod.escape(vault.notes[path].title)}</a></td>")
        elif col.startswith("formula."):
            cells.append("<td></td>")
        else:
            cells.append(
                f"<td>{_cell_html(ctx.get(col), col, resolver, output_path, path)}</td>")
    return "".join(cells)


def _table_html(base, view, matches, vault, resolver, output_path):
    cols = view.order or ["file.name"]
    heads = "".join(f"<th>{html_mod.escape(_col_label(base, c))}</th>" for c in cols)
    rows = []
    for path in matches:
        ctx = NoteCtx(path, vault.notes[path], resolver)
        rows.append(f"<tr>{_row_cells(base, cols, path, ctx, vault, resolver, output_path)}</tr>")
    return (f'<p class="base-count manifest-label">{len(matches)} notes</p>'
            f'<div class="base-table-wrap"><table class="base-table">'
            f"<thead><tr>{heads}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")


def _resolve_image(raw, resolver, from_path):
    if not isinstance(raw, str) or not raw.strip():
        return None
    m = _IMG_VAL_RE.match(raw.strip())
    target = m.group(1).strip() if m else raw.strip()
    if _URL_RE.match(target):
        return None
    return resolver.resolve_asset(target, from_path)


def _cards_html(base, view, matches, vault, resolver, output_path, warnings):
    cards = []
    warned_img = False
    # The image property renders as the cover; repeating it as a text row
    # would show the raw asset link (usually broken) under its own picture.
    props = [c for c in view.order
             if c != "file.name" and not c.startswith("formula.") and c != view.image]
    for path in matches:
        ctx = NoteCtx(path, vault.notes[path], resolver)
        img = ""
        if view.image:
            raw = ctx.get(view.image)
            src = _resolve_image(raw, resolver, path)
            if src:
                img = (f'<img src="{urls.rel_href(output_path, src)}" alt="" '
                       f'loading="lazy">')
            elif raw and not warned_img:
                warned_img = True
                warnings.append(f"{base.path}: cards image {raw!r} could not be resolved")
        href = urls.rel_href(output_path, urls.note_output_path(path))
        title = f'<a class="base-card-title" href="{href}">' \
                f"{html_mod.escape(vault.notes[path].title)}</a>"
        rows = "".join(
            f'<div class="base-card-prop"><span class="manifest-label">'
            f"{html_mod.escape(_col_label(base, c))}</span>"
            f"{_cell_html(ctx.get(c), c, resolver, output_path, path)}</div>"
            for c in props)
        cards.append(f'<div class="base-card">{img}<div class="base-card-body">'
                     f"{title}{rows}</div></div>")
    return (f'<p class="base-count manifest-label">{len(matches)} notes</p>'
            f'<div class="base-cards">{"".join(cards)}</div>')


def render_base(base, vault, resolver, output_path, warnings, view=None, embed=False):
    views = base.views
    if view:
        chosen = [v for v in views if v.name == view]
        if not chosen:
            warnings.append(f"{base.path}: no view named {view!r}; using default")
        views = chosen or views[:1]
    elif embed:
        views = views[:1]
    head = ""
    if embed:
        href = urls.rel_href(output_path, urls.base_output_path(base.path))
        head = (f'<div class="base-embed-head manifest-label">'
                f'<a href="{href}">{html_mod.escape(base.title)}</a></div>')
    if not views:
        inner = '<p class="base-empty">This base defines no supported views.</p>'
        return f'<div class="{"base-embed" if embed else "base-block"}">{head}{inner}</div>'
    sections = []
    for i, v in enumerate(views):
        matches = evaluate(base, v, vault, resolver, warnings)
        if v.type == "table":
            body = _table_html(base, v, matches, vault, resolver, output_path)
        else:
            body = _cards_html(base, v, matches, vault, resolver, output_path, warnings)
        hidden = " hidden" if (not embed and i > 0) else ""
        name_attr = html_mod.escape(v.name, quote=True)
        sections.append(f'<section class="base-view"{hidden} '
                        f'data-view="{name_attr}">{body}</section>')
    tabs = script = ""
    if not embed and len(views) > 1:
        btns = "".join(
            f'<button type="button" class="base-tab{" active" if i == 0 else ""}" '
            f'data-view="{html_mod.escape(v.name, quote=True)}">'
            f"{html_mod.escape(v.name)}</button>"
            for i, v in enumerate(views))
        tabs = f'<div class="base-tabs">{btns}</div>'
        script = (f'<script defer src="{urls.root_prefix(output_path)}'
                  f'site-assets/bases.js"></script>')
    cls = "base-embed" if embed else "base-block"
    return f'<div class="{cls}">{head}{tabs}{"".join(sections)}</div>{script}'
