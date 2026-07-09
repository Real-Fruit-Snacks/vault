from __future__ import annotations

import datetime
import html as html_mod
import re
from dataclasses import dataclass, field

import yaml

from . import baseexpr, mdtext, urls
from .basevalue import BaseError, Link

VIEW_TYPES = {"table", "cards", "list"}


@dataclass
class BaseView:
    name: str
    type: str
    filters: object
    order: list
    sort: list
    limit: int
    image: str
    group_by: object = None            # (property, "ASC"|"DESC") or None
    summaries: list = field(default_factory=list)  # [(column, agg_or_expr)]


@dataclass
class Base:
    path: str
    title: str
    filters: object
    views: list
    display_names: dict
    formulas: dict = field(default_factory=dict)  # name -> AST (or None)


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
    formulas = {}
    raw_formulas = data.get("formulas")
    if isinstance(raw_formulas, dict):
        for name, expr in raw_formulas.items():
            formulas[str(name)] = baseexpr.parse(expr) if isinstance(expr, str) else None
            if formulas[str(name)] is None:
                warnings.append(f"{rel}: formula {name!r} did not parse; renders empty")
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
        for s in item.get("sort") if isinstance(item.get("sort"), list) else []:
            if isinstance(s, dict) and isinstance(s.get("property"), str):
                direction = str(s.get("direction", "ASC")).upper()
                sort.append((s["property"], "DESC" if direction == "DESC" else "ASC"))
        limit = (item["limit"] if isinstance(item.get("limit"), int)
                 and not isinstance(item.get("limit"), bool) and item["limit"] > 0 else 0)
        image = item.get("image") if isinstance(item.get("image"), str) else ""
        group_by = None
        gb = item.get("groupBy")
        if isinstance(gb, dict) and isinstance(gb.get("property"), str):
            gdir = "DESC" if str(gb.get("direction", "ASC")).upper() == "DESC" else "ASC"
            group_by = (gb["property"], gdir)
        elif isinstance(gb, str):
            group_by = (gb, "ASC")
        summaries = []
        sm = item.get("summaries")
        if isinstance(sm, dict):
            for col, agg in sm.items():
                summaries.append((str(col), str(agg)))
        views.append(BaseView(
            name=name, type=vtype,
            filters=_parse_filters(item.get("filters"), rel, warnings),
            order=order, sort=sort, limit=limit, image=image,
            group_by=group_by, summaries=summaries))
    return Base(path=rel, title=rel.rsplit("/", 1)[-1][:-5],
                filters=_parse_filters(data.get("filters"), rel, warnings),
                views=views, display_names=display_names, formulas=formulas)


class NoteCtx:
    """Per-note evaluation context for the expression engine."""

    def __init__(self, path, note, resolver, filedata=None, formulas=None,
                 build_now=None):
        self.path = path
        self.note = note
        self.resolver = resolver
        self.filedata = filedata or {}
        self.formulas = formulas or {}
        self.build_now = build_now or datetime.datetime.now()
        self._links = None
        self._formula_cache = {}
        self._formula_active = set()

    # -- engine protocol ----------------------------------------------------
    def resolve(self, name):
        if name == "file" or name == "note":
            # bare namespace refs are not values on their own
            raise BaseError(f"{name} is not a value")
        if name.startswith("file."):
            return self._file_field(name[5:])
        if name.startswith("note."):
            return self._prop(name[5:])
        if name.startswith("formula."):
            return self._formula(name[8:])
        return self._prop(name)

    def file_method(self, name, args):
        if name == "hasTag":
            return True, (all(self.has_tag(a) for a in args) if args else False)
        if name == "inFolder":
            return True, (self.in_folder(args[0]) if args else False)
        if name == "hasLink":
            return True, (self.has_link(args[0]) if args else False)
        if name == "hasProperty":
            return True, (self.has_property(args[0]) if args else False)
        if name == "asLink":
            return True, Link(self.path[:-3], str(args[0]) if args else "")
        return False, None

    # -- value helpers ------------------------------------------------------
    def value(self, ref):
        """Public: value of a column/sort/group ref; null on failure."""
        try:
            return self.resolve(ref)
        except BaseError:
            return None

    def _prop(self, prop):
        value = self.note.frontmatter.get(prop)
        if isinstance(value, str):
            m = _WIKILINK_VAL_RE.match(value.strip())
            if m:
                return Link(m.group(1).strip(), (m.group(2) or "").strip())
        return value

    def _file_field(self, fieldname):
        base = self.path.rsplit("/", 1)[-1]
        if fieldname == "name":
            return base
        if fieldname == "basename":
            return base[:-3] if base.lower().endswith(".md") else base
        if fieldname == "path":
            return self.path
        if fieldname == "folder":
            return self.path.rsplit("/", 1)[0] if "/" in self.path else ""
        if fieldname == "ext":
            return "md"
        if fieldname == "tags":
            return list(self.note.tags)
        if fieldname == "size":
            return self.filedata.get("size", {}).get(self.path)
        if fieldname == "ctime":
            return self.filedata.get("ctime", {}).get(self.path)
        if fieldname == "mtime":
            return self.filedata.get("mtime", {}).get(self.path)
        if fieldname == "links":
            return sorted(self._link_set())
        if fieldname == "properties":
            return dict(self.note.frontmatter)
        raise BaseError(f"unknown file.{fieldname}")

    def _formula(self, name):
        if name in self._formula_cache:
            return self._formula_cache[name]
        if name in self._formula_active:      # cycle
            return None
        ast = self.formulas.get(name)
        if ast is None:
            self._formula_cache[name] = None
            return None
        self._formula_active.add(name)
        result = baseexpr.evaluate(ast, self)
        self._formula_active.discard(name)
        self._formula_cache[name] = result
        return result

    def _link_set(self):
        if self._links is None:
            self._links = set()
            for t in mdtext.find_wikilink_targets(self.note.body):
                dest = self.resolver.resolve_note(t, self.path)
                if dest:
                    self._links.add(dest)
        return self._links

    def has_tag(self, tag):
        t = str(tag).lstrip("#").lower()
        return any(x.lower() == t or x.lower().startswith(t + "/")
                   for x in self.note.tags)

    def in_folder(self, folder):
        f = str(folder).strip("/").lower()
        mine = (self.path.rsplit("/", 1)[0] if "/" in self.path else "").lower()
        return mine == f or mine.startswith(f + "/")

    def has_link(self, target):
        dest = self.resolver.resolve_note(str(target), self.path)
        return dest is not None and dest in self._link_set()

    def has_property(self, prop):
        return str(prop) in self.note.frontmatter


def _compile_tree(tree, cache, rel, warnings, warned):
    """Compile every leaf expression once; warn on unparseable leaves."""
    if tree is None:
        return
    if tree[0] == "expr":
        text = tree[1]
        if text not in cache:
            cache[text] = baseexpr.as_predicate(text)
        if cache[text] is None and text not in warned:
            warned.add(text)
            warnings.append(f"{rel}: unsupported filter expression {text!r}; treated as false")
        return
    for child in tree[1]:
        _compile_tree(child, cache, rel, warnings, warned)


def _match_tree(tree, ctx, cache):
    kind = tree[0]
    if kind == "expr":
        fn = cache.get(tree[1])
        return bool(fn(ctx)) if fn else False
    children = tree[1]
    if kind == "and":
        return all(_match_tree(c, ctx, cache) for c in children)
    if kind == "or":
        return any(_match_tree(c, ctx, cache) for c in children)
    return not any(_match_tree(c, ctx, cache) for c in children)  # not


def _cmp_key(val):
    if isinstance(val, bool):
        return (0, float(val), "")
    if isinstance(val, (int, float)):
        return (0, float(val), "")
    if isinstance(val, datetime.date):
        base = val if isinstance(val, datetime.datetime) else datetime.datetime(val.year, val.month, val.day)
        return (0, base.timestamp(), "")
    if isinstance(val, str):
        return (1, 0.0, val.lower())
    if isinstance(val, Link):
        return (1, 0.0, (val.display or val.target).lower())
    return (2, 0.0, str(val).lower())


def make_ctx(path, vault, resolver, filedata, formulas, build_now):
    return NoteCtx(path, vault.notes[path], resolver,
                   filedata=filedata, formulas=formulas, build_now=build_now)


def evaluate(base, view, vault, resolver, warnings, filedata=None, build_now=None):
    cache, warned = {}, set()
    for tree in (base.filters, view.filters):
        if tree is not None:
            _compile_tree(tree, cache, base.path, warnings, warned)
    ctxs, matches = {}, []
    for path in sorted(vault.notes):
        ctx = make_ctx(path, vault, resolver, filedata or {}, base.formulas, build_now)
        ctxs[path] = ctx
        ok = True
        for tree in (base.filters, view.filters):
            if tree is not None and not _match_tree(tree, ctx, cache):
                ok = False
                break
        if ok:
            matches.append(path)
    for prop, direction in reversed(view.sort):
        present = [p for p in matches if ctxs[p].value(prop) is not None]
        absent = [p for p in matches if ctxs[p].value(prop) is None]
        present.sort(key=lambda p: _cmp_key(ctxs[p].value(prop)), reverse=(direction == "DESC"))
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
                f"<td>{_cell_html(ctx.value(col), col, resolver, output_path, path)}</td>")
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
            raw = ctx.value(view.image)
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
            f"{_cell_html(ctx.value(c), c, resolver, output_path, path)}</div>"
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
