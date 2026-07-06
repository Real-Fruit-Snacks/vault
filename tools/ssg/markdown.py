from __future__ import annotations

import html as html_mod
import re
from dataclasses import dataclass, field

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.footnote import footnote_plugin
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from . import urls

# Task states styled by the terminal-workbench Obsidian theme.
TASK_STATE_NAMES = {
    " ": "todo",
    "x": "done",
    "X": "done",
    "-": "cancelled",
    ">": "deferred",
    "!": "important",
}
_TASK_RE = re.compile(r"^\[(.)\][ \t]+")
_FORMATTER = HtmlFormatter(nowrap=True)


@dataclass
class RenderResult:
    html: str
    headings: list = field(default_factory=list)
    has_mermaid: bool = False


def _render_fence(self, tokens, idx, options, env):
    token = tokens[idx]
    info = (token.info or "").strip()
    lang = info.split()[0] if info else ""
    code = token.content
    if lang.lower() == "mermaid":
        env["has_mermaid"] = True
        return '<pre class="mermaid">' + html_mod.escape(code) + "</pre>\n"
    body = None
    if lang:
        try:
            body = highlight(code, get_lexer_by_name(lang), _FORMATTER)
        except ClassNotFound:
            body = None
    if body is None:
        body = html_mod.escape(code)
    label = html_mod.escape(lang) if lang else "&gt;_"
    return (
        f'<figure class="code-block">'
        f'<figcaption class="code-lang manifest-label">{label}</figcaption>'
        f'<pre class="code-body"><code>{body}</code></pre></figure>\n'
    )


def create_markdown() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": True, "linkify": False, "typographer": False})
    md.enable(["table", "strikethrough"])
    md.use(footnote_plugin)
    md.add_render_rule("fence", _render_fence)
    return md


_MD = create_markdown()


def _transform_tasks(tokens) -> None:
    for i, tok in enumerate(tokens):
        if tok.type != "inline" or not tok.children or i < 2:
            continue
        if tokens[i - 1].type != "paragraph_open" or tokens[i - 2].type != "list_item_open":
            continue
        first = tok.children[0]
        if first.type != "text":
            continue
        m = _TASK_RE.match(first.content)
        if not m:
            continue
        state = m.group(1)
        name = TASK_STATE_NAMES.get(state, "other")
        tokens[i - 2].attrJoin("class", f"task-list-item task-{name}")
        first.content = first.content[m.end():]
        marker = Token("html_inline", "", 0)
        marker.content = f'<span class="task-marker" data-task="{html_mod.escape(state, quote=True)}"></span>'
        tok.children.insert(0, marker)


def _inline_text(token) -> str:
    parts = []
    for child in token.children or []:
        if child.type in ("text", "code_inline"):
            parts.append(child.content)
    return "".join(parts).strip()


def _assign_heading_ids(tokens) -> list:
    headings = []
    used: dict = {}
    for i, tok in enumerate(tokens):
        if tok.type != "heading_open":
            continue
        text = _inline_text(tokens[i + 1])
        slug = urls.slugify_heading(text)
        n = used.get(slug, 0)
        used[slug] = n + 1
        if n:
            slug = f"{slug}-{n}"
        tok.attrSet("id", slug)
        inline = tokens[i + 1]
        if inline.children is not None:
            anchor = Token("html_inline", "", 0)
            anchor.content = (f'<a class="h-anchor" href="#{slug}" '
                              f'aria-label="Link to this section">#</a>')
            inline.children.append(anchor)
        headings.append((int(tok.tag[1]), text, slug))
    return headings


def render_markdown(text: str) -> RenderResult:
    env: dict = {}
    tokens = _MD.parse(text, env)
    _transform_tasks(tokens)
    headings = _assign_heading_ids(tokens)
    html_out = _MD.renderer.render(tokens, _MD.options, env)
    return RenderResult(html=html_out, headings=headings,
                        has_mermaid=bool(env.get("has_mermaid")))
