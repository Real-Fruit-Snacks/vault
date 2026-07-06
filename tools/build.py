#!/usr/bin/env python3
"""Build the vault into a static site. Requires only Python 3.9+; no network."""
import argparse
import html as html_mod
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ssg import bases as basesmod  # noqa: E402
from ssg import canvas as canvasmod  # noqa: E402
from ssg import gitdates, graphdata, mdtext, pages, toolpages, urls  # noqa: E402
from ssg.config import load_config  # noqa: E402
from ssg.links import LinkResolver, build_backlinks  # noqa: E402
from ssg.obsidian import NoteRenderer  # noqa: E402
from ssg.vault import scan_vault  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def plain_text(body: str) -> str:
    parts = []
    pos = 0
    for m in mdtext.CODE_FENCE_RE.finditer(body):
        parts.append(body[pos:m.start()])
        pos = m.end()
    parts.append(body[pos:])
    text = " ".join(parts)
    text = re.sub(r"!?\[\[([^\]|#]*)[^\]]*\]\]", r" \1 ", text)
    text = re.sub(r"[#>*_`~\[\]()|!-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def html_text(html_src: str) -> str:
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html_src)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_mod.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def write(dest: Path, content: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")


def note_description(note) -> str:
    """A short summary for meta/OG tags: an explicit frontmatter field if the
    author wrote one, else the opening prose trimmed to a sentence-ish length."""
    for key in ("description", "summary"):
        value = note.frontmatter.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    text = plain_text(note.body)
    return text[:155].rstrip() + "…" if len(text) > 156 else text


def _abs_url(site_url: str, path: str) -> str:
    """Absolute URL when site_url is set, else a root-relative path."""
    return f"{site_url.rstrip('/')}/{path}" if site_url else f"/{path}"


def build_robots(site_url: str) -> str:
    lines = ["User-agent: *", "Allow: /"]
    if site_url:
        lines.append(f"Sitemap: {site_url.rstrip('/')}/sitemap.xml")
    return "\n".join(lines) + "\n"


def build_manifest(config) -> str:
    return json.dumps({
        "name": config.title,
        "short_name": config.title,
        "start_url": ".",
        "display": "standalone",
        "background_color": "#090c0d",
        "theme_color": "#090c0d",
        "icons": [
            {"src": "site-assets/favicon.svg", "sizes": "any", "type": "image/svg+xml"},
            {"src": "site-assets/favicon.png", "sizes": "32x32", "type": "image/png"},
        ],
    }, ensure_ascii=False, indent=2) + "\n"


def build_sitemap(site_url: str, page_paths, page_dates) -> str:
    rows = []
    for path in page_paths:
        loc = html_mod.escape(_abs_url(site_url, path))
        lastmod = page_dates.get(path)
        inner = f"<loc>{loc}</loc>"
        if lastmod:
            inner += f"<lastmod>{lastmod}</lastmod>"
        rows.append(f"  <url>{inner}</url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def build_feed(config, feed_items) -> str:
    """Atom feed of recently updated entries. feed_items: (title, path, date)."""
    site_url = config.site_url
    home = f"{site_url.rstrip('/')}/" if site_url else "/"
    self_href = _abs_url(site_url, "feed.xml")
    stamp = (feed_items[0][2] if feed_items else "1970-01-01") + "T00:00:00Z"
    esc = lambda s: html_mod.escape(s, quote=True)
    entries = []
    for title, path, date in feed_items:
        url = _abs_url(site_url, path)
        entries.append(
            "  <entry>\n"
            f"    <title>{html_mod.escape(title)}</title>\n"
            f'    <link href="{esc(url)}"/>\n'
            f"    <id>{html_mod.escape(url)}</id>\n"
            f"    <updated>{date}T00:00:00Z</updated>\n"
            "  </entry>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom">\n'
            f"  <title>{html_mod.escape(config.title)}</title>\n"
            f'  <link href="{esc(home)}"/>\n'
            f'  <link rel="self" href="{esc(self_href)}"/>\n'
            f"  <id>{html_mod.escape(home)}</id>\n"
            f"  <updated>{stamp}</updated>\n"
            + ("\n".join(entries) + "\n" if entries else "")
            + "</feed>\n")


def _col_label_words(base, cols):
    return [base.display_names.get(c, c.rsplit(".", 1)[-1]) for c in cols]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build the vault site.")
    parser.add_argument("--vault", type=Path, default=REPO_ROOT / "Notes")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    vault_root = args.vault.resolve()
    if not vault_root.is_dir():
        print(f"ERROR: vault directory not found: {vault_root}")
        return 1
    out = (args.out or (REPO_ROOT / "public")).resolve()

    config = load_config(vault_root)
    vault = scan_vault(vault_root, config)
    dates = gitdates.note_dates(vault_root)
    resolver = LinkResolver(vault)
    backlinks = build_backlinks(vault, resolver)
    renderer = NoteRenderer(vault, resolver)
    tools = toolpages.discover_tools(REPO_ROOT / "site-tools", vault.warnings)
    nav_tools = sorted(((t.title, toolpages.tool_output_path(t), t.icon) for t in tools),
                       key=lambda item: item[0].lower())
    home = next((c for c in (config.homepage, "Home.md", "index.md") if c in vault.notes), None)

    canvases = {}
    for rel in sorted(vault.canvases):
        parsed = canvasmod.parse_canvas(
            vault.canvases[rel].read_text(encoding="utf-8", errors="replace"),
            rel, vault.warnings)
        if parsed is not None:
            canvases[rel] = parsed
    note_outputs = {urls.note_output_path(p) for p in vault.notes}
    for rel in sorted(canvases):
        out_path = urls.canvas_output_path(rel)
        if out_path in note_outputs:
            vault.warnings.append(
                f"canvas '{rel}' collides with a note page at {out_path}; canvas skipped")
            del canvases[rel]
    canvas_paths = sorted(canvases)

    bases = {}
    for rel in sorted(vault.bases):
        parsed_base = basesmod.parse_base(
            vault.bases[rel].read_text(encoding="utf-8", errors="replace"),
            rel, vault.warnings)
        if parsed_base is not None:
            bases[rel] = parsed_base
    taken_outputs = note_outputs | {urls.canvas_output_path(p) for p in canvases}
    for rel in sorted(bases):
        out_path = urls.base_output_path(rel)
        if out_path in taken_outputs:
            vault.warnings.append(
                f"base '{rel}' collides with an existing page at {out_path}; base skipped")
            del bases[rel]
    base_paths = sorted(bases)
    renderer.base_provider = lambda rel, view_name, out_path: (
        basesmod.render_base(bases[rel], vault, resolver, out_path, vault.warnings,
                             view=view_name or None, embed=True)
        if rel in bases else None)

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(REPO_ROOT / "site-assets", out / "site-assets")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    for rel, src in vault.assets.items():
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)

    results = {}
    # Linear reading order for previous/next links (the home note is reachable
    # from the title, so it stays out of the chain).
    nav_order = [p for p in sorted(vault.notes) if p != home]
    order_index = {p: i for i, p in enumerate(nav_order)}
    for path in sorted(vault.notes):
        note = vault.notes[path]
        out_path = urls.note_output_path(path)
        res = renderer.render_note(note)
        results[path] = res
        prev = nxt = None
        if path in order_index:
            i = order_index[path]
            if i > 0:
                prev = (vault.notes[nav_order[i - 1]].title, nav_order[i - 1])
            if i < len(nav_order) - 1:
                nxt = (vault.notes[nav_order[i + 1]].title, nav_order[i + 1])
        write(out / out_path, pages.render_page(
            config=config, output_path=out_path, page_title=note.title,
            content_html=pages.note_header(note, out_path, dates.get(path, "")) + res.html,
            nav_html=pages.build_nav(vault, path, out_path, tools=nav_tools, home_note=home,
                                     canvases=canvas_paths, bases=base_paths),
            breadcrumbs=pages.build_breadcrumbs(path),
            toc=pages.build_toc(res.headings),
            backlinks=pages.build_backlinks_panel(path, backlinks, vault, out_path),
            has_mermaid=res.has_mermaid,
            note_id=out_path,
            description=note_description(note),
            note_nav=pages.build_note_nav(prev, nxt, out_path)))

    tag_map: dict = {}       # display tag -> set of note paths (one display spelling per slug)
    slug_display: dict = {}  # slug -> first-seen display spelling
    tag_warnings: list = []
    for path, note in sorted(vault.notes.items()):
        for tag in note.tags:
            slug = urls.tag_slug(tag)
            display = slug_display.setdefault(slug, tag)
            if display != tag:
                tag_warnings.append(
                    f"tag '{tag}' merges with '{display}' (both map to _tags/{slug}.html)")
            tag_map.setdefault(display, set()).add(path)
    for tag in sorted(tag_map):
        out_path = urls.tag_output_path(tag)
        write(out / out_path, pages.render_page(
            config=config, output_path=out_path, page_title=f"#{tag}",
            content_html=pages.tag_page_content(tag, tag_map[tag], vault, out_path),
            nav_html=pages.build_nav(vault, "", out_path, tools=nav_tools, home_note=home,
                                     canvases=canvas_paths, bases=base_paths),
            breadcrumbs=f"<span>tags</span><span class=\"crumb-sep\">/</span>"
                        f"<span>{html_mod.escape(tag)}</span>",
            description=f"Notes tagged #{tag}."))
    if tag_map:
        write(out / "_tags/index.html", pages.render_page(
            config=config, output_path="_tags/index.html", page_title="Tags",
            content_html=pages.tags_index_content(tag_map, "_tags/index.html"),
            nav_html=pages.build_nav(vault, "", "_tags/index.html", tools=nav_tools, home_note=home,
                                     canvases=canvas_paths, bases=base_paths),
            breadcrumbs="<span>tags</span>",
            description="Every tag in the vault."))

    notes_collision = next((p for p in vault.notes if urls.note_output_path(p) == "notes.html"), None)
    if notes_collision is not None:
        vault.warnings.append(
            f"note '{notes_collision}' is overwritten by the notes index page at notes.html")
    write(out / "notes.html", pages.render_page(
        config=config, output_path="notes.html", page_title="Notes",
        content_html=pages.notes_index_content(vault, tag_map, "notes.html", home,
                                               canvases=canvas_paths, bases=base_paths),
        nav_html=pages.build_nav(vault, "", "notes.html", tools=nav_tools, home_note=home,
                                 canvases=canvas_paths, bases=base_paths),
        breadcrumbs="<span>notes</span>",
        description="Browse every note, folder, and tag in the vault."))

    home_extra = pages.home_sections(vault, dates, tag_map, nav_tools, "index.html", home,
                                     canvases=canvas_paths, bases=base_paths)
    if home is not None:
        # Rewrites index.html even when the home note's own output path is
        # index.html, so the homepage sections are always appended there.
        note = vault.notes[home]
        res = renderer.render_note(note, output_path="index.html")
        write(out / "index.html", pages.render_page(
            config=config, output_path="index.html", page_title=note.title,
            content_html=pages.note_header(note, "index.html", dates.get(home, ""))
                         + res.html + home_extra,
            nav_html=pages.build_nav(vault, home, "index.html", tools=nav_tools, home_note=home,
                                     canvases=canvas_paths, bases=base_paths),
            breadcrumbs=pages.build_breadcrumbs(home),
            toc=pages.build_toc(res.headings),
            backlinks=pages.build_backlinks_panel(home, backlinks, vault, "index.html"),
            has_mermaid=res.has_mermaid,
            note_id=urls.note_output_path(home),
            description=note_description(note)))
    else:
        write(out / "index.html", pages.render_page(
            config=config, output_path="index.html", page_title=config.title,
            content_html=pages.auto_index_content(vault, "index.html") + home_extra,
            nav_html=pages.build_nav(vault, "", "index.html", tools=nav_tools, home_note=home,
                                     canvases=canvas_paths, bases=base_paths),
            description=config.description))

    for rel in canvas_paths:
        out_path = urls.canvas_output_path(rel)
        render = canvasmod.canvas_page_content(
            canvases[rel], vault, renderer, out_path, vault.warnings)
        write(out / out_path, pages.render_page(
            config=config, output_path=out_path, page_title=canvases[rel].title,
            content_html=render.html,
            nav_html=pages.build_nav(vault, rel, out_path, tools=nav_tools,
                                     home_note=home, canvases=canvas_paths, bases=base_paths),
            breadcrumbs=pages.build_breadcrumbs(rel),
            has_mermaid=render.has_mermaid, full_width=True,
            description=f"{canvases[rel].title} — an Obsidian canvas."))

    for rel in base_paths:
        out_path = urls.base_output_path(rel)
        body = basesmod.render_base(bases[rel], vault, resolver, out_path, vault.warnings)
        write(out / out_path, pages.render_page(
            config=config, output_path=out_path, page_title=bases[rel].title,
            content_html=(f'<header class="note-header"><h1>'
                          f"{html_mod.escape(bases[rel].title)}</h1></header>" + body),
            nav_html=pages.build_nav(vault, rel, out_path, tools=nav_tools, home_note=home,
                                     canvases=canvas_paths, bases=base_paths),
            breadcrumbs=pages.build_breadcrumbs(rel), wide=True,
            description=f"{bases[rel].title} — an Obsidian base view."))

    for tool in tools:
        out_path = toolpages.tool_output_path(tool)
        write(out / out_path, pages.render_page(
            config=config, output_path=out_path, page_title=tool.title,
            content_html=toolpages.tool_page_content(tool),
            nav_html=pages.build_nav(vault, "", out_path, tools=nav_tools, home_note=home,
                                     canvases=canvas_paths, bases=base_paths),
            breadcrumbs=f"<span>tools</span><span class=\"crumb-sep\">/</span>"
                        f"<span>{html_mod.escape(tool.title)}</span>", wide=True,
            description=tool.description))
        for name, src in tool.assets.items():
            dest = out / "tools" / tool.slug / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
    if tools:
        write(out / "tools/index.html", pages.render_page(
            config=config, output_path="tools/index.html", page_title="Tools",
            content_html=toolpages.tools_index_content(tools, "tools/index.html"),
            nav_html=pages.build_nav(vault, "", "tools/index.html", tools=nav_tools, home_note=home,
                                     canvases=canvas_paths, bases=base_paths),
            breadcrumbs="<span>tools</span>",
            description="Interactive, offline browser tools."))

    tool_paths = {toolpages.tool_output_path(t) for t in tools}
    if tools:
        tool_paths.add("tools/index.html")
    for path in sorted(vault.notes):
        note_out = urls.note_output_path(path)
        if note_out in tool_paths:
            vault.warnings.append(
                f"note '{path}' is overwritten by a tool page at {note_out}")

    graph_collision = next((p for p in vault.notes if urls.note_output_path(p) == "graph.html"), None)
    if graph_collision is not None:
        vault.warnings.append(
            f"note '{graph_collision}' is overwritten by the graph view page at graph.html")

    write(out / "graph.html", pages.render_page(
        config=config, output_path="graph.html", page_title="Graph",
        content_html='<div id="graph-view"><canvas></canvas></div>',
        nav_html=pages.build_nav(vault, "", "graph.html", tools=nav_tools, home_note=home,
                                 canvases=canvas_paths, bases=base_paths),
        breadcrumbs="<span>graph</span>", full_width=True,
        description="Interactive graph of the notes and how they link together."))

    not_found_collision = next((p for p in vault.notes if urls.note_output_path(p) == "404.html"), None)
    if not_found_collision is not None:
        vault.warnings.append(
            f"note '{not_found_collision}' is overwritten by the 404 page at 404.html")

    write(out / "404.html", pages.not_found_page(config))

    entries = []
    for i, path in enumerate(sorted(vault.notes)):
        note = vault.notes[path]
        entries.append({
            "id": i,
            "title": note.title,
            "url": urls.note_output_path(path),
            "headings": " ".join(t for _, t, _ in results[path].headings),
            "hs": [[t, s] for _, t, s in results[path].headings],
            "text": plain_text(note.body)[:5000],
            "type": "note",
        })
    for rel in canvas_paths:
        c = canvases[rel]
        entries.append({
            "id": len(entries), "title": c.title,
            "url": urls.canvas_output_path(rel),
            "headings": "", "hs": [],
            "text": plain_text(c.text_content)[:5000], "type": "note",
        })
    for rel in base_paths:
        b = bases[rel]
        words = [b.title] + [v.name for v in b.views]
        for v in b.views:
            words.extend(_col_label_words(b, v.order))
        entries.append({
            "id": len(entries), "title": b.title,
            "url": urls.base_output_path(rel),
            "headings": "", "hs": [],
            "text": " ".join(words)[:5000], "type": "note",
        })
    for tool in tools:
        entries.append({
            "id": len(entries),
            "title": tool.title,
            "url": toolpages.tool_output_path(tool),
            "headings": "",
            "hs": [],
            "text": html_text(f"{tool.description} {tool.body_html} {tool.learn_html}")[:5000],
            "type": "tool",
        })
    write(out / "search-index.js",
          "window.TWB_SEARCH_INDEX=" + json.dumps(entries, ensure_ascii=False) + ";\n"
          + "window.TWB_NOTE_COUNT=" + str(len(vault.notes)) + ";")

    graph = graphdata.build_graph(vault, backlinks)
    write(out / "graph-index.js",
          "window.TWB_GRAPH=" + json.dumps(graph, ensure_ascii=False) + ";")

    # Discovery + syndication files. robots.txt and the web manifest are always
    # written; sitemap.xml and feed.xml use absolute URLs when site_url is set
    # and root-relative paths otherwise.
    page_paths = list(dict.fromkeys(
        [urls.note_output_path(p) for p in sorted(vault.notes)]
        + [urls.tag_output_path(t) for t in sorted(tag_map)]
        + (["_tags/index.html"] if tag_map else [])
        + ["notes.html", "index.html"]
        + [urls.canvas_output_path(p) for p in canvas_paths]
        + [urls.base_output_path(p) for p in base_paths]
        + [toolpages.tool_output_path(t) for t in tools]
        + (["tools/index.html"] if tools else [])
        + ["graph.html"]))
    page_dates = {}
    for p in vault.notes:
        if p in dates:
            page_dates[urls.note_output_path(p)] = dates[p]
    for p in canvas_paths:
        if p in dates:
            page_dates[urls.canvas_output_path(p)] = dates[p]
    for p in base_paths:
        if p in dates:
            page_dates[urls.base_output_path(p)] = dates[p]
    write(out / "robots.txt", build_robots(config.site_url))
    write(out / "site.webmanifest", build_manifest(config))
    write(out / "sitemap.xml", build_sitemap(config.site_url, page_paths, page_dates))

    feed_src = []
    for p in vault.notes:
        if p in dates and p != home:
            feed_src.append((dates[p], vault.notes[p].title, urls.note_output_path(p)))
    for p in canvas_paths:
        if p in dates:
            feed_src.append((dates[p], canvases[p].title, urls.canvas_output_path(p)))
    for p in base_paths:
        if p in dates:
            feed_src.append((dates[p], bases[p].title, urls.base_output_path(p)))
    feed_src.sort(key=lambda item: item[1].lower())
    feed_src.sort(key=lambda item: item[0], reverse=True)
    feed_items = [(title, path, d) for d, title, path in feed_src[:20]]
    write(out / "feed.xml", build_feed(config, feed_items))

    warnings = list(dict.fromkeys(vault.warnings + resolver.warnings + renderer.warnings + tag_warnings))
    for warning in warnings:
        print(f"WARNING: {warning}")
    skipped = f" ({vault.skipped} unpublished)" if vault.skipped else ""
    print(f"Built {len(vault.notes)} notes{skipped}, {len(vault.assets)} assets, "
          f"{len(tag_map)} tags, {len(tools)} tools, {len(canvases)} canvases, "
          f"{len(bases)} bases, {len(warnings)} warnings -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
