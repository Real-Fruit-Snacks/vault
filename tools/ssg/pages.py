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
<script>(function(){var t=localStorage.getItem("twb-theme");if(t)document.documentElement.setAttribute("data-theme",t);if(localStorage.getItem("twb-sidebar")==="collapsed")document.documentElement.setAttribute("data-sidebar","collapsed");if(localStorage.getItem("twb-rail")==="expanded")document.documentElement.removeAttribute("data-rail");if(localStorage.getItem("twb-nav-colors")==="on")document.documentElement.setAttribute("data-nav-colors","on");if(localStorage.getItem("twb-width")==="full")document.documentElement.setAttribute("data-width","full");var pm=localStorage.getItem("twb-pet");if(pm!=="cursor")document.documentElement.setAttribute("data-pet",pm==="float"?"float":"off");if(localStorage.getItem("twb-crt")==="on")document.documentElement.setAttribute("data-crt","on");if(localStorage.getItem("twb-progress")==="on")document.documentElement.setAttribute("data-progress","on");var ts=localStorage.getItem("twb-textsize");if(ts==="s"||ts==="l")document.documentElement.setAttribute("data-textsize",ts);var ac=localStorage.getItem("twb-accent");if(ac&&"12345".indexOf(ac)>-1)document.documentElement.setAttribute("data-accent",ac);try{if(!sessionStorage.getItem("twb-booted")&&!(window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches)){document.documentElement.setAttribute("data-boot","1");sessionStorage.setItem("twb-booted","1");setTimeout(function(){document.documentElement.removeAttribute("data-boot");},4000);}}catch(e){}})();</script>
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
<div class="settings-head">Settings</div>
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
</header>
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
    '<svg viewBox="0 0 24 26" xmlns="http://www.w3.org/2000/svg">'
    '<rect class="pet-out" x="11" y="1" width="2" height="1"/><rect class="pet-out" x="8" y="2" width="3" height="1"/><rect class="pet-body" x="11" y="2" width="2" height="1"/><rect class="pet-out" x="13" y="2" width="3" height="1"/><rect class="pet-out" x="6" y="3" width="2" height="1"/><rect class="pet-lt" x="8" y="3" width="4" height="1"/><rect class="pet-body" x="12" y="3" width="4" height="1"/><rect class="pet-out" x="16" y="3" width="2" height="1"/><rect class="pet-out" x="5" y="4" width="1" height="1"/><rect class="pet-lt" x="6" y="4" width="7" height="1"/><rect class="pet-body" x="13" y="4" width="4" height="1"/><rect class="pet-dk" x="17" y="4" width="1" height="1"/><rect class="pet-out" x="18" y="4" width="1" height="1"/><rect class="pet-out" x="4" y="5" width="1" height="1"/><rect class="pet-lt" x="5" y="5" width="2" height="1"/><rect class="pet-hi" x="7" y="5" width="3" height="1"/><rect class="pet-lt" x="10" y="5" width="4" height="1"/><rect class="pet-body" x="14" y="5" width="4" height="1"/><rect class="pet-dk" x="18" y="5" width="1" height="1"/><rect class="pet-out" x="19" y="5" width="1" height="1"/><rect class="pet-out" x="4" y="6" width="1" height="1"/><rect class="pet-lt" x="5" y="6" width="1" height="1"/><rect class="pet-hi" x="6" y="6" width="5" height="1"/><rect class="pet-lt" x="11" y="6" width="3" height="1"/><rect class="pet-body" x="14" y="6" width="4" height="1"/><rect class="pet-dk" x="18" y="6" width="1" height="1"/><rect class="pet-out" x="19" y="6" width="1" height="1"/><rect class="pet-out" x="3" y="7" width="1" height="1"/><rect class="pet-lt" x="4" y="7" width="1" height="1"/><rect class="pet-hi" x="5" y="7" width="7" height="1"/><rect class="pet-lt" x="12" y="7" width="2" height="1"/><rect class="pet-body" x="14" y="7" width="4" height="1"/><rect class="pet-dk" x="18" y="7" width="2" height="1"/><rect class="pet-out" x="20" y="7" width="1" height="1"/><rect class="pet-out" x="3" y="8" width="1" height="1"/><rect class="pet-lt" x="4" y="8" width="1" height="1"/><rect class="pet-hi" x="5" y="8" width="7" height="1"/><rect class="pet-lt" x="12" y="8" width="2" height="1"/><rect class="pet-body" x="14" y="8" width="4" height="1"/><rect class="pet-dk" x="18" y="8" width="2" height="1"/><rect class="pet-out" x="20" y="8" width="1" height="1"/><rect class="pet-out" x="3" y="9" width="1" height="1"/><rect class="pet-lt" x="4" y="9" width="1" height="1"/><rect class="pet-hi" x="5" y="9" width="7" height="1"/><rect class="pet-lt" x="12" y="9" width="2" height="1"/><rect class="pet-body" x="14" y="9" width="4" height="1"/><rect class="pet-dk" x="18" y="9" width="2" height="1"/><rect class="pet-out" x="20" y="9" width="1" height="1"/><rect class="pet-out" x="2" y="10" width="1" height="1"/><rect class="pet-lt" x="3" y="10" width="3" height="1"/><rect class="pet-hi" x="6" y="10" width="5" height="1"/><rect class="pet-lt" x="11" y="10" width="3" height="1"/><rect class="pet-body" x="14" y="10" width="4" height="1"/><rect class="pet-dk" x="18" y="10" width="3" height="1"/><rect class="pet-out" x="21" y="10" width="1" height="1"/><rect class="pet-out" x="2" y="11" width="1" height="1"/><rect class="pet-lt" x="3" y="11" width="4" height="1"/><rect class="pet-hi" x="7" y="11" width="3" height="1"/><rect class="pet-lt" x="10" y="11" width="4" height="1"/><rect class="pet-body" x="14" y="11" width="4" height="1"/><rect class="pet-dk" x="18" y="11" width="3" height="1"/><rect class="pet-out" x="21" y="11" width="1" height="1"/><rect class="pet-out" x="2" y="12" width="1" height="1"/><rect class="pet-body" x="3" y="12" width="1" height="1"/><rect class="pet-lt" x="4" y="12" width="9" height="1"/><rect class="pet-body" x="13" y="12" width="4" height="1"/><rect class="pet-dk" x="17" y="12" width="4" height="1"/><rect class="pet-out" x="21" y="12" width="1" height="1"/><rect class="pet-out" x="2" y="13" width="1" height="1"/><rect class="pet-body" x="3" y="13" width="2" height="1"/><rect class="pet-lt" x="5" y="13" width="7" height="1"/><rect class="pet-body" x="12" y="13" width="5" height="1"/><rect class="pet-dk" x="17" y="13" width="4" height="1"/><rect class="pet-out" x="21" y="13" width="1" height="1"/><rect class="pet-out" x="2" y="14" width="1" height="1"/><rect class="pet-body" x="3" y="14" width="2" height="1"/><rect class="pet-cheek" x="5" y="14" width="2" height="1"/><rect class="pet-body" x="7" y="14" width="9" height="1"/><rect class="pet-dk" x="16" y="14" width="1" height="1"/><rect class="pet-cheek" x="17" y="14" width="2" height="1"/><rect class="pet-dk" x="19" y="14" width="2" height="1"/><rect class="pet-out" x="21" y="14" width="1" height="1"/><rect class="pet-out" x="2" y="15" width="1" height="1"/><rect class="pet-body" x="3" y="15" width="12" height="1"/><rect class="pet-dk" x="15" y="15" width="6" height="1"/><rect class="pet-out" x="21" y="15" width="1" height="1"/><rect class="pet-out" x="2" y="16" width="1" height="1"/><rect class="pet-body" x="3" y="16" width="11" height="1"/><rect class="pet-dk" x="14" y="16" width="7" height="1"/><rect class="pet-out" x="21" y="16" width="1" height="1"/><rect class="pet-out" x="2" y="17" width="1" height="1"/><rect class="pet-dk" x="3" y="17" width="2" height="1"/><rect class="pet-body" x="5" y="17" width="7" height="1"/><rect class="pet-dk" x="12" y="17" width="9" height="1"/><rect class="pet-out" x="21" y="17" width="1" height="1"/><rect class="pet-out" x="2" y="18" width="1" height="1"/><rect class="pet-dk" x="3" y="18" width="18" height="1"/><rect class="pet-out" x="21" y="18" width="1" height="1"/><rect class="pet-out" x="2" y="19" width="1" height="1"/><rect class="pet-dk" x="3" y="19" width="18" height="1"/><rect class="pet-out" x="21" y="19" width="1" height="1"/><rect class="pet-out" x="2" y="20" width="1" height="1"/><rect class="pet-dk" x="3" y="20" width="18" height="1"/><rect class="pet-out" x="21" y="20" width="1" height="1"/><rect class="pet-out" x="2" y="21" width="1" height="1"/><rect class="pet-dk" x="3" y="21" width="4" height="1"/><rect class="pet-out" x="7" y="21" width="1" height="1"/><rect class="pet-dk" x="8" y="21" width="3" height="1"/><rect class="pet-out" x="11" y="21" width="2" height="1"/><rect class="pet-dk" x="13" y="21" width="3" height="1"/><rect class="pet-out" x="16" y="21" width="1" height="1"/><rect class="pet-dk" x="17" y="21" width="4" height="1"/><rect class="pet-out" x="21" y="21" width="1" height="1"/><rect class="pet-out" x="3" y="22" width="1" height="1"/><rect class="pet-dk" x="4" y="22" width="2" height="1"/><rect class="pet-out" x="6" y="22" width="1" height="1"/><rect class="pet-out" x="8" y="22" width="1" height="1"/><rect class="pet-dk" x="9" y="22" width="1" height="1"/><rect class="pet-out" x="10" y="22" width="1" height="1"/><rect class="pet-out" x="13" y="22" width="1" height="1"/><rect class="pet-dk" x="14" y="22" width="1" height="1"/><rect class="pet-out" x="15" y="22" width="1" height="1"/><rect class="pet-out" x="17" y="22" width="1" height="1"/><rect class="pet-dk" x="18" y="22" width="2" height="1"/><rect class="pet-out" x="20" y="22" width="1" height="1"/><rect class="pet-out" x="4" y="23" width="2" height="1"/><rect class="pet-out" x="8" y="23" width="3" height="1"/><rect class="pet-out" x="13" y="23" width="3" height="1"/><rect class="pet-out" x="18" y="23" width="2" height="1"/>'
    '<g class="pet-eyes-open"><rect class="pet-eye-w" x="5" y="10" width="4" height="4"/><rect class="pet-eye-w" x="13" y="10" width="4" height="4"/><g class="pet-pupils"><rect class="pet-eye-p" x="6" y="11" width="2" height="2"/><rect class="pet-eye-p" x="14" y="11" width="2" height="2"/></g></g>'
    '<g class="pet-eyes-closed"><rect class="pet-eye-p" x="5" y="12" width="4" height="1"/><rect class="pet-eye-p" x="13" y="12" width="4" height="1"/></g>'
    '<g class="pet-eyes-happy"><rect class="pet-eye-p" x="5" y="13" width="1" height="1"/><rect class="pet-eye-p" x="6" y="12" width="1" height="1"/><rect class="pet-eye-p" x="7" y="12" width="1" height="1"/><rect class="pet-eye-p" x="8" y="13" width="1" height="1"/><rect class="pet-eye-p" x="13" y="13" width="1" height="1"/><rect class="pet-eye-p" x="14" y="12" width="1" height="1"/><rect class="pet-eye-p" x="15" y="12" width="1" height="1"/><rect class="pet-eye-p" x="16" y="13" width="1" height="1"/></g>'
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
    if config.pet_enabled:
        pet = PET_HTML + f'\n<script defer src="{root}site-assets/pet.js"></script>\n'
        # Runtime show/hide lives in the top bar; the pet markup and script are
        # still gated by pet_enabled, so the toggle only appears alongside them.
        pet_toggle = ('<button id="pet-toggle" class="settings-row">'
                      '<span class="settings-label">Pet</span>'
                      '<span class="settings-val"></span></button>\n')
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
        items = "".join(
            f'<li><a href="{urls.rel_href(output_path, entry(p)[1])}">'
            f"{html_mod.escape(entry(p)[0])}</a>"
            f'<span class="home-date">{html_mod.escape(d)}</span></li>'
            for d, p in dated[:8])
        sections.append(_home_section(
            "recently updated", "", f'<ul class="home-recent">{items}</ul>', output_path))
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


def auto_index_content(vault: Vault, output_path: str) -> str:
    items = "".join(
        f'<li><a href="{urls.rel_href(output_path, urls.note_output_path(p))}">'
        f"{html_mod.escape(p[:-3])}</a></li>"
        for p in sorted(vault.notes, key=str.lower))
    return f'<h1>Notes</h1><ul class="note-list">{items}</ul>'
