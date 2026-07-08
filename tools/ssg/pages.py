from __future__ import annotations

import html as html_mod
from string import Template

from . import urls
from .config import BANNER_STYLES, SiteConfig
from .vault import Note, Vault

_PAGE = Template("""<!DOCTYPE html>
<html lang="en" data-root="$root"$note_attr data-rail="collapsed"$banner_attr>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$page_title · $site_title</title>
<link rel="icon" type="image/svg+xml" href="${root}site-assets/favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="${root}site-assets/favicon.png">
<link rel="apple-touch-icon" href="${root}site-assets/favicon.png">
<link rel="manifest" href="${root}site.webmanifest">
<meta name="theme-color" media="(prefers-color-scheme: dark)" content="#090c0d">
<meta name="theme-color" media="(prefers-color-scheme: light)" content="#f5f7f4">
<link rel="alternate" type="application/atom+xml" title="$site_title" href="${root}feed.xml">
$head_meta<link rel="stylesheet" href="${root}site-assets/tokens.css">
<link rel="stylesheet" href="${root}site-assets/fonts.css">
<link rel="stylesheet" href="${root}site-assets/site.css">
<script>(function(){var t=localStorage.getItem("twb-theme");if(t)document.documentElement.setAttribute("data-theme",t);if(localStorage.getItem("twb-sidebar")==="collapsed")document.documentElement.setAttribute("data-sidebar","collapsed");if(localStorage.getItem("twb-rail")==="expanded")document.documentElement.removeAttribute("data-rail");if(localStorage.getItem("twb-nav-colors")==="on")document.documentElement.setAttribute("data-nav-colors","on");if(localStorage.getItem("twb-width")==="full")document.documentElement.setAttribute("data-width","full");var pm=localStorage.getItem("twb-pet");if(pm!=="cursor")document.documentElement.setAttribute("data-pet",pm==="off"?"off":"float");var ps=parseInt(localStorage.getItem("twb-pet-size"),10);if(ps>=16&&ps<=64)document.documentElement.style.setProperty("--pet-size",ps+"px");var po=parseInt(localStorage.getItem("twb-pet-opacity"),10);if(po>=15&&po<=100)document.documentElement.style.setProperty("--pet-base-opacity",(po/100).toFixed(3));if(localStorage.getItem("twb-crt")==="on")document.documentElement.setAttribute("data-crt","on");if(localStorage.getItem("twb-progress")==="on")document.documentElement.setAttribute("data-progress","on");var ts=localStorage.getItem("twb-textsize");if(ts==="s"||ts==="l")document.documentElement.setAttribute("data-textsize",ts);var ac=localStorage.getItem("twb-accent");if(ac&&"12345".indexOf(ac)>-1)document.documentElement.setAttribute("data-accent",ac);try{if(!sessionStorage.getItem("twb-booted")){document.documentElement.setAttribute("data-boot","1");sessionStorage.setItem("twb-booted","1");setTimeout(function(){document.documentElement.removeAttribute("data-boot");},4000);}}catch(e){}})();</script>
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
$banner<header class="topbar">
<button class="nav-toggle" aria-label="Toggle navigation">≡</button>
<a class="site-title manifest-label" href="${root}index.html">$site_title</a>
<nav class="breadcrumbs manifest-label">$breadcrumbs</nav>
<div class="search">
<input id="search-input" type="search" placeholder="search" autocomplete="off">
<div id="search-results" role="listbox" aria-live="polite" aria-label="Search results" hidden></div>
</div>
<button id="cmd-toggle" aria-label="Open command palette" title="Command palette (Ctrl / ⌘ K)"><span></span></button>
<button id="random-note" aria-label="Open a random note" title="Random note"><span></span></button>
<a class="graph-link" href="${root}graph.html" aria-label="Graph view" title="Graph view"><span></span></a>
<div class="settings-wrap">
<button id="settings-toggle" aria-label="Settings" aria-haspopup="true" aria-expanded="false" title="Settings"><span></span></button>
<div id="settings-menu" class="settings-menu" hidden>
<div class="settings-head"><span>Settings</span><button id="settings-close" class="menu-close" type="button" aria-label="Close settings">&times;</button></div>
<button id="theme-toggle" class="settings-row"><span class="settings-label">Theme</span><span class="settings-val"></span></button>
<button id="accent-color" class="settings-row"><span class="settings-label">Accent color</span><span class="settings-val"></span></button>
<button id="nav-colors" class="settings-row"><span class="settings-label">Folder colors</span><span class="settings-val"></span></button>
<button id="width-toggle" class="settings-row"><span class="settings-label">Full-width notes</span><span class="settings-val"></span></button>
<button id="rail-toggle" class="settings-row"><span class="settings-label">Outline panel</span><span class="settings-val"></span></button>
<button id="progress-toggle" class="settings-row"><span class="settings-label">Reading progress</span><span class="settings-val"></span></button>
<button id="text-size" class="settings-row"><span class="settings-label">Text size</span><span class="settings-val"></span></button>
$pet_toggle<button id="crt-toggle" class="settings-row"><span class="settings-label">CRT mode</span><span class="settings-val"></span></button>
</div>
</div>
$pet_panel</header>
<div class="layout">
<nav class="sidebar" id="sidebar">
<div class="nav-controls">
<button type="button" id="nav-expand-all">expand</button>
<button type="button" id="nav-collapse-all">collapse</button>
</div>
$nav</nav>
<main class="content" id="main">
<article class="note$note_class">
$content
</article>
$note_nav$backlinks
</main>
<aside class="toc">$toc</aside>
</div>
<script defer src="${root}search-index.js"></script>
<script defer src="${root}site-assets/minisearch.min.js"></script>
<script defer src="${root}site-assets/app.js"></script>
<script defer src="${root}site-assets/palette.js"></script>
<script defer src="${root}site-assets/boot.js"></script>
<script defer src="${root}graph-index.js"></script>
<script defer src="${root}site-assets/graph.js"></script>
$pet$mermaid
</body>
</html>
""")

_FAVICON_DATA_URI = (
    "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%2032%2032'%3E"
    "%3Crect%20x='0.5'%20y='0.5'%20width='31'%20height='31'%20rx='6'%20fill='%23090c0d'%20stroke='%232a363d'/%3E"
    "%3Cpath%20d='M9%209l14%203M9%209l5%2014M23%2012l-9%2011'%20stroke='%2363f2ab'%20stroke-width='2.2'%20fill='none'/%3E"
    "%3Ccircle%20cx='9'%20cy='9'%20r='4'%20fill='%2363f2ab'/%3E"
    "%3Ccircle%20cx='23'%20cy='12'%20r='4'%20fill='%2363f2ab'/%3E"
    "%3Ccircle%20cx='14'%20cy='23'%20r='4'%20fill='%2363f2ab'/%3E%3C/svg%3E"
)

_PET_SVG = (
    '<svg viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">'
    '<path class="pet-body" d="M2 16 V7 Q2 1 8 1 Q14 1 14 7 V16 '
    'L12 14.4 L10 16 L8 14.4 L6 16 L4 14.4 Z"/>'
    '<g class="pet-eyes-open"><rect x="5" y="6" width="2" height="3"/>'
    '<rect x="9" y="6" width="2" height="3"/></g>'
    '<g class="pet-eyes-closed"><rect x="5" y="8" width="2" height="1"/>'
    '<rect x="9" y="8" width="2" height="1"/></g>'
    '<g class="pet-eyes-happy"><path d="M4.6 8 L6 6.6 L7.4 8"/>'
    '<path d="M8.6 8 L10 6.6 L11.4 8"/></g>'
    "</svg>")

# The pet is decorative chrome: hidden from the accessibility tree, and the
# whole feature is emitted only when site.config.json enables it.
PET_HTML = ('<div id="site-pet" aria-hidden="true"><div class="pet-tilt">'
            '<div class="pet-sprite" title="pet the ghost to recolor it">' + _PET_SVG +
            "</div></div></div>")

# Self-contained by design: hosts serve 404 pages at arbitrary URLs, so
# relative asset links cannot be trusted here. Token values are baked in.
_NOT_FOUND = Template("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>404 · $site_title</title>
<link rel="icon" type="image/svg+xml" href="$favicon">
<style>
:root {
  --bg: #090c0d; --panel: #0e1214; --border: #2a363d;
  --text: #dce4df; --muted: #879994; --accent: #63f2ab;
}
@media (prefers-color-scheme: light) {
  :root {
    --bg: #f5f7f4; --panel: #edf2ee; --border: #bfcbc5;
    --text: #17201d; --muted: #60706a; --accent: #007a4d;
  }
}
:root[data-theme="dark"] {
  --bg: #090c0d; --panel: #0e1214; --border: #2a363d;
  --text: #dce4df; --muted: #879994; --accent: #63f2ab;
}
:root[data-theme="light"] {
  --bg: #f5f7f4; --panel: #edf2ee; --border: #bfcbc5;
  --text: #17201d; --muted: #60706a; --accent: #007a4d;
}
* { box-sizing: border-box; }
body {
  margin: 0; min-height: 100vh; display: flex;
  align-items: center; justify-content: center;
  background: var(--bg); color: var(--text);
  font-family: ui-monospace, Consolas, "Courier New", monospace;
}
main {
  background: var(--panel); border: 1px solid var(--border);
  border-radius: 8px; padding: 36px 44px; text-align: center;
}
.code {
  font-size: 11px; font-weight: 600; letter-spacing: 0.09em;
  text-transform: uppercase; color: var(--muted);
}
h1 { font-size: 20px; margin: 10px 0 18px; }
a { color: var(--accent); }
</style>
<script>(function(){var t=localStorage.getItem("twb-theme");if(t)document.documentElement.setAttribute("data-theme",t);})();</script>
</head>
<body>
<main>
<div class="code">404</div>
<h1>This page doesn't exist.</h1>
<p><a href="$home">back to the vault</a></p>
</main>
</body>
</html>
""")


def not_found_page(config: SiteConfig) -> str:
    return _NOT_FOUND.substitute(
        site_title=html_mod.escape(config.title),
        favicon=_FAVICON_DATA_URI,
        home=html_mod.escape(config.site_url, quote=True) if config.site_url else "/",
    )


def _head_meta(config: SiteConfig, output_path: str, page_title: str,
               description: str) -> str:
    """Per-page discovery metadata: description, Open Graph, Twitter card, and
    (only when site_url is configured) the absolute canonical/og:url/og:image."""
    esc = lambda s: html_mod.escape(s, quote=True)
    desc = (description or config.description or "").strip()
    out = []
    if desc:
        out.append(f'<meta name="description" content="{esc(desc)}">')
    out.append(f'<meta property="og:title" content="{esc(page_title)}">')
    out.append('<meta property="og:type" content="website">')
    out.append(f'<meta property="og:site_name" content="{esc(config.title)}">')
    if desc:
        out.append(f'<meta property="og:description" content="{esc(desc)}">')
    out.append('<meta name="twitter:card" content="summary">')
    out.append(f'<meta name="twitter:title" content="{esc(page_title)}">')
    if desc:
        out.append(f'<meta name="twitter:description" content="{esc(desc)}">')
    if config.site_url:
        base = config.site_url.rstrip("/")
        url = f"{base}/{output_path}"
        out.append(f'<link rel="canonical" href="{esc(url)}">')
        out.append(f'<meta property="og:url" content="{esc(url)}">')
        out.append(f'<meta property="og:image" content="{esc(base)}/site-assets/favicon.png">')
    return "\n".join(out) + ("\n" if out else "")


def build_note_nav(prev, nxt, output_path: str) -> str:
    """Footer previous/next links between notes. prev/nxt are (title, path)
    tuples or None; an absent side still renders a spacer so 'next' stays right."""
    if not prev and not nxt:
        return ""
    def side(item, cls, label):
        if not item:
            return '<span class="note-nav-gap"></span>'
        href = urls.rel_href(output_path, urls.note_output_path(item[1]))
        return (f'<a class="note-nav-link {cls}" href="{href}">'
                f'<span class="note-nav-dir">{label}</span>'
                f'<span class="note-nav-title">{html_mod.escape(item[0])}</span></a>')
    return (f'<nav class="note-nav" aria-label="Adjacent notes">'
            f'{side(prev, "note-nav-prev", "Previous")}'
            f'{side(nxt, "note-nav-next", "Next")}</nav>')


def render_page(*, config: SiteConfig, output_path: str, page_title: str,
                content_html: str, nav_html: str, breadcrumbs: str = "",
                toc: str = "", backlinks: str = "", has_mermaid: bool = False,
                note_id: str = "", full_width: bool = False, wide: bool = False,
                description: str = "", note_nav: str = "") -> str:
    root = urls.root_prefix(output_path)
    mermaid = ""
    if has_mermaid:
        mermaid = (
            f'<script src="{root}site-assets/mermaid.min.js"></script>\n'
            "<script>mermaid.initialize({startOnLoad:true,"
            'theme:document.documentElement.getAttribute("data-theme")==="light"?"neutral":"dark"});'
            "</script>"
        )
    banner = ""
    banner_attr = ""
    if config.banner_enabled and config.banner_text.strip():
        # Defense in depth: the config loader validates banner_style, but a
        # programmatically built SiteConfig could carry anything.
        style = config.banner_style if config.banner_style in BANNER_STYLES else "info"
        text = config.banner_text.strip()
        # The banner is a fixed-height sticky strip; the title attribute keeps
        # long, ellipsized messages readable on hover.
        banner = (f'<div class="site-banner site-banner-{style}" '
                  f'title="{html_mod.escape(text, quote=True)}">'
                  f"{html_mod.escape(text)}</div>\n")
        banner_attr = ' data-banner="on"'  # shifts the sticky chrome offsets
    pet = ""
    pet_toggle = ""
    pet_panel = ""
    if config.pet_enabled:
        pet = PET_HTML + f'\n<script defer src="{root}site-assets/pet.js"></script>\n'
        # Runtime show/hide lives in the top bar; the pet markup and script are
        # still gated by pet_enabled, so the opener only appears alongside them.
        pet_toggle = ('<button id="pet-open" class="settings-row" aria-haspopup="true" '
                      'aria-expanded="false"><span class="settings-label">Pet</span>'
                      '<span class="settings-val"></span></button>')
        pet_panel = (
            '<div id="pet-panel" class="settings-menu pet-panel" hidden>'
            '<div class="settings-head"><span>Pet</span>'
            '<button id="pet-close" class="menu-close" type="button" aria-label="Close pet panel">&times;</button></div>'
            '<div class="pet-group-label manifest-label">Appearance</div>'
            '<div id="pet-mode" class="pet-seg" role="group" aria-label="Pet mode">'
            '<button data-mode="float">Roam</button>'
            '<button data-mode="cursor">Cursor</button>'
            '<button data-mode="off">Off</button></div>'
            '<label class="pet-slider"><span>Size</span>'
            '<input id="pet-size" type="range" min="16" max="64" step="2"></label>'
            '<label class="pet-slider"><span>Opacity</span>'
            '<input id="pet-opacity" type="range" min="15" max="100" step="5"></label>'
            '<div id="pet-color" class="pet-swatches" role="group" aria-label="Pet color">'
            + "".join('<button data-color="%d" style="--sw:var(%s)"></button>' % (i, tok)
                      for i, tok in enumerate(
                          ["--twb-accent", "--twb-accent-alt", "--twb-warm",
                           "--twb-violet", "--twb-orange", "--twb-red"]))
            + '</div>'
            '<div class="pet-group-label manifest-label">Behavior</div>'
            + "".join(
                '<button id="pet-q-%s" class="settings-row pet-quirk">'
                '<span class="settings-label">%s</span><span class="settings-val"></span></button>'
                % (qid, label) for qid, label in [
                    ("nap", "Nap when idle"), ("flee", "Flee from cursor"),
                    ("read", "Read along"), ("tricks", "Do tricks"),
                    ("speech", "Speech bubbles")])
            + '</div>')
    note_attr = f' data-note="{html_mod.escape(note_id)}"' if note_id else ""
    note_class = " note-full" if full_width else (" note-wide" if wide else "")
    return _PAGE.substitute(
        root=root,
        page_title=html_mod.escape(page_title),
        site_title=html_mod.escape(config.title),
        head_meta=_head_meta(config, output_path, page_title, description),
        breadcrumbs=breadcrumbs,
        nav=nav_html,
        content=content_html,
        backlinks=backlinks,
        note_nav=note_nav,
        toc=toc,
        mermaid=mermaid,
        banner=banner,
        banner_attr=banner_attr,
        pet=pet,
        pet_toggle=pet_toggle,
        pet_panel=pet_panel,
        note_attr=note_attr,
        note_class=note_class,
    )


def build_nav(vault: Vault, current_note_path: str, output_path: str, tools=(),
              home_note=None, canvases=(), bases=()) -> str:
    tree: dict = {}
    for path in list(vault.notes) + list(canvases) + list(bases):
        if path == home_note:  # reachable via the site title; omit from the tree
            continue
        parts = path.split("/")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part + "/", {})
        node[parts[-1]] = path
    notes_href = urls.rel_href(output_path, "notes.html")
    nav = (f'<div class="nav-notes">'
           f'<a class="manifest-label" href="{notes_href}">notes</a>'
           f'<ul class="nav-tree">{_nav_level(tree, "", current_note_path, output_path)}</ul>'
           f"</div>")
    if tools:
        index_href = urls.rel_href(output_path, "tools/index.html")
        items = []
        for title, tool_output, icon in tools:
            cls = ' class="active"' if tool_output == output_path else ""
            icon_attr = f' data-icon="{html_mod.escape(icon)}"' if icon else ""
            href = urls.rel_href(output_path, tool_output)
            items.append(f'<li><a{cls}{icon_attr} href="{href}">{html_mod.escape(title)}</a></li>')
        nav += (f'<div class="nav-tools">'
                f'<a class="manifest-label" href="{index_href}">tools</a>'
                f'<ul class="nav-tree">{"".join(items)}</ul></div>')
    return nav


def folder_color(name: str) -> int:
    """Stable palette index (0-5) from the folder name alone, so a folder
    keeps its color as the vault grows. Deliberately not hash(): that is
    randomized per process."""
    h = 0
    for ch in name.lower():
        h = (h * 31 + ord(ch)) % 100003
    return h % 6


def _nav_level(node: dict, prefix: str, current: str, output_path: str) -> str:
    out = []
    folders = sorted((k for k in node if k.endswith("/")), key=str.lower)
    files = sorted((k for k in node if not k.endswith("/")), key=str.lower)
    for folder in folders:
        full = prefix + folder
        open_attr = " open" if current.startswith(full) else ""
        # Only top-level folders carry a color; the branch inherits it.
        color_attr = f' data-color="{folder_color(folder[:-1])}"' if not prefix else ""
        out.append(
            f"<li{color_attr}><details{open_attr}><summary>{html_mod.escape(folder[:-1])}</summary>"
            f"<ul>{_nav_level(node[folder], full, current, output_path)}</ul></details></li>")
    for name in files:
        path = node[name]
        cls = ' class="active"' if path == current else ""
        if name.lower().endswith(".canvas"):
            href = urls.rel_href(output_path, urls.canvas_output_path(path))
            out.append(f'<li><a{cls} data-kind="canvas" href="{href}">'
                       f"{html_mod.escape(name[:-7])}</a></li>")
        elif name.lower().endswith(".base"):
            href = urls.rel_href(output_path, urls.base_output_path(path))
            out.append(f'<li><a{cls} data-kind="base" href="{href}">'
                       f"{html_mod.escape(name[:-5])}</a></li>")
        else:
            href = urls.rel_href(output_path, urls.note_output_path(path))
            out.append(f'<li><a{cls} href="{href}">{html_mod.escape(name[:-3])}</a></li>')
    return "".join(out)


def build_breadcrumbs(note_path: str) -> str:
    parts = note_path.split("/")
    last = parts[-1]
    if last.lower().endswith(".md"):
        last = last[:-3]
    elif last.lower().endswith(".canvas"):
        last = last[:-7]
    elif last.lower().endswith(".base"):
        last = last[:-5]
    names = parts[:-1] + [last]
    return '<span class="crumb-sep">/</span>'.join(
        f"<span>{html_mod.escape(n)}</span>" for n in names)


def build_toc(headings) -> str:
    items = list(headings)
    if len(items) < 2:
        return ""
    # Indent relative to the shallowest heading present, so a note whose top
    # heading is an h2 still starts flush left.
    min_lvl = min(lvl for lvl, _, _ in items)
    lis = "".join(
        f'<li class="toc-l{lvl - min_lvl + 1}"><a href="#{slug}">{html_mod.escape(text)}</a></li>'
        for lvl, text, slug in items)
    return ('<div class="toc-title manifest-label">On this page</div>'
            f'<ul class="toc-list">{lis}</ul>')


def build_backlinks_panel(note_path: str, backlinks: dict, vault: Vault, output_path: str) -> str:
    sources = backlinks.get(note_path, [])
    if not sources:
        return ""
    items = "".join(
        f'<li><a href="{urls.rel_href(output_path, urls.note_output_path(src))}">'
        f"{html_mod.escape(vault.notes[src].title)}</a></li>"
        for src in sources)
    return (f'<section class="backlinks"><div class="manifest-label">'
            f"Linked mentions ({len(sources)})</div><ul>{items}</ul></section>")


def note_header(note: Note, output_path: str, updated: str = "") -> str:
    chips = "".join(
        f'<a class="tag" href="{urls.rel_href(output_path, urls.tag_output_path(t))}">'
        f"#{html_mod.escape(t)}</a>"
        for t in note.tags)
    parts = []
    if updated:
        parts.append(f'<span class="note-updated manifest-label">'
                     f"updated {html_mod.escape(updated)}</span>")
    if chips:
        parts.append(f'<div class="note-tags">{chips}</div>')
    meta = f'<div class="note-meta">{"".join(parts)}</div>' if parts else ""
    return (f'<header class="note-header"><h1>{html_mod.escape(note.title)}</h1>'
            f"{meta}</header>")


def tag_page_content(tag: str, note_paths, vault: Vault, output_path: str) -> str:
    items = "".join(
        f'<li><a href="{urls.rel_href(output_path, urls.note_output_path(p))}">'
        f"{html_mod.escape(vault.notes[p].title)}</a></li>"
        for p in sorted(note_paths, key=str.lower))
    return (f'<h1><span class="manifest-label">tag</span> #{html_mod.escape(tag)}</h1>'
            f'<ul class="note-list">{items}</ul>')


def tags_index_content(tag_map: dict, output_path: str) -> str:
    items = "".join(
        f'<li><a class="tag" href="{urls.rel_href(output_path, urls.tag_output_path(t))}">'
        f'#{html_mod.escape(t)}</a> <span class="manifest-label">{len(paths)}</span></li>'
        for t, paths in sorted(tag_map.items(), key=lambda kv: kv[0].lower()))
    return f'<h1>Tags</h1><ul class="note-list">{items}</ul>'


def home_hero(config) -> str:
    """Title + description banner atop the generated homepage (no home note)."""
    title = html_mod.escape(config.title)
    desc = (f'<p class="home-hero-desc">{html_mod.escape(config.description)}</p>'
            if config.description else "")
    return (f'<header class="home-hero">'
            f'<h1 class="home-hero-title">{title}</h1>{desc}</header>')


def home_sections(vault: Vault, dates: dict, tag_map: dict, tools,
                  output_path: str, home_note=None, canvases=(), bases=()) -> str:
    """Build-time homepage sections: recently updated notes, tag chips, tools.

    Regenerated on every build, so the homepage tracks the vault as notes
    change. Sections with nothing to show are omitted (e.g. no git dates)."""
    sections = []
    dated = [(dates[p], p) for p in vault.notes if p in dates and p != home_note]
    dated += [(dates[p], p) for p in canvases if p in dates and p != home_note]
    dated += [(dates[p], p) for p in bases if p in dates and p != home_note]
    dated.sort(key=lambda dp: dp[1].lower())
    dated.sort(key=lambda dp: dp[0], reverse=True)
    if dated:
        def entry(p):
            if p.lower().endswith(".canvas"):
                return p.rsplit("/", 1)[-1][:-7], urls.canvas_output_path(p)
            if p.lower().endswith(".base"):
                return p.rsplit("/", 1)[-1][:-5], urls.base_output_path(p)
            return vault.notes[p].title, urls.note_output_path(p)
        rows = []
        for d, p in dated[:8]:
            title, out = entry(p)
            href = urls.rel_href(output_path, out)
            folder = p.rsplit("/", 1)[0] if "/" in p else ""
            crumb = (f'<span class="home-recent-path">{html_mod.escape(folder)}</span>'
                     if folder else "")
            rows.append(
                f'<li><a class="home-recent-link" href="{href}">'
                f'<span class="home-recent-title">{html_mod.escape(title)}</span>{crumb}</a>'
                f'<span class="home-date">{html_mod.escape(d)}</span></li>')
        sections.append(_home_section(
            "recently updated", "", f'<ul class="home-recent">{"".join(rows)}</ul>', output_path))
    if tag_map:
        sections.append(_home_section(
            "tags", "_tags/index.html",
            f'<div class="home-tags">{_tag_chips(tag_map, output_path)}</div>', output_path))
    if tools:
        items = []
        for title, tool_output, icon in tools:
            icon_attr = f' data-icon="{html_mod.escape(icon)}"' if icon else ""
            href = urls.rel_href(output_path, tool_output)
            items.append(f'<li><a{icon_attr} href="{href}">{html_mod.escape(title)}</a></li>')
        sections.append(_home_section(
            "tools", "tools/index.html",
            f'<ul class="home-tools">{"".join(items)}</ul>', output_path))
    if not sections:
        return ""
    return f'<div class="home-sections">{"".join(sections)}</div>'


def _home_section(label: str, index_path: str, body: str, output_path: str) -> str:
    if index_path:
        head = (f'<a class="manifest-label section-head" '
                f'href="{urls.rel_href(output_path, index_path)}">{label}</a>')
    else:
        head = f'<span class="manifest-label section-head">{label}</span>'
    return f'<section class="home-section">{head}{body}</section>'


def _tag_chips(tag_map: dict, output_path: str) -> str:
    return "".join(
        f'<a class="tag" href="{urls.rel_href(output_path, urls.tag_output_path(t))}">'
        f'#{html_mod.escape(t)}<span class="home-count">{len(paths)}</span></a>'
        for t, paths in sorted(tag_map.items(), key=lambda kv: kv[0].lower()))


def _notes_index_item(p: str, vault: Vault, output_path: str) -> str:
    if p.lower().endswith(".canvas"):
        href = urls.rel_href(output_path, urls.canvas_output_path(p))
        title = p.rsplit("/", 1)[-1][:-7]
        return (f'<li><a data-kind="canvas" href="{href}">'
                f"{html_mod.escape(title)}</a></li>")
    if p.lower().endswith(".base"):
        href = urls.rel_href(output_path, urls.base_output_path(p))
        title = p.rsplit("/", 1)[-1][:-5]
        return (f'<li><a data-kind="base" href="{href}">'
                f"{html_mod.escape(title)}</a></li>")
    href = urls.rel_href(output_path, urls.note_output_path(p))
    return f'<li><a href="{href}">{html_mod.escape(vault.notes[p].title)}</a></li>'


def notes_index_content(vault: Vault, tag_map: dict, output_path: str, home_note=None,
                        canvases=(), bases=()) -> str:
    """The notes screen: every folder with its notes, then the tag cloud."""
    groups: dict = {}
    for path in list(vault.notes) + list(canvases) + list(bases):
        if path == home_note:  # reachable via the site title; omit like the sidebar
            continue
        folder = path.rsplit("/", 1)[0] if "/" in path else ""
        groups.setdefault(folder, []).append(path)
    sections = []
    for folder in sorted(groups, key=str.lower):
        label = html_mod.escape(folder) if folder else "vault root"
        items = "".join(
            _notes_index_item(p, vault, output_path)
            for p in sorted(groups[folder], key=str.lower))
        sections.append(
            f'<section class="notes-folder">'
            f'<span class="manifest-label section-head folder-head">{label}</span>'
            f'<ul class="note-list">{items}</ul></section>')
    if tag_map:
        sections.append(
            f'<section class="notes-folder">'
            f'<a class="manifest-label section-head" '
            f'href="{urls.rel_href(output_path, "_tags/index.html")}">tags</a>'
            f'<div class="home-tags">{_tag_chips(tag_map, output_path)}</div></section>')
    return f"<h1>Notes</h1>{''.join(sections)}"
