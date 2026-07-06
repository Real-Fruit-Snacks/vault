from __future__ import annotations

import html as html_mod
import re

from . import mdtext, urls
from .links import LinkResolver
from .markdown import RenderResult, render_markdown
from .vault import Note, Vault

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
CALLOUT_HEAD_RE = re.compile(r"^\[!([A-Za-z0-9_-]+)\]([+-]?)[ \t]*(.*)$")
EMBED_COMMENT_RE = re.compile(r"<!--twb-embed:([^#>]*)#([^>]*)-->")
BASE_EMBED_COMMENT_RE = re.compile(r"<!--twb-base-embed:([^#>]*)#([^>]*)-->")
_QUOTE_PREFIX_RE = re.compile(r"^ {0,3}> ?")


def _extract_section(html_out: str, slug: str) -> str:
    m = re.search(rf'<h([1-6])[^>]*\bid="{re.escape(slug)}"', html_out)
    if not m:
        return html_out
    level = int(m.group(1))
    rest = html_out[m.start():]
    nxt = re.search(rf"<h[1-{level}][ >]", rest[1:])
    return rest[: nxt.start() + 1] if nxt else rest


extract_section = _extract_section  # public: canvas file-cards embed heading sections


class NoteRenderer:
    def __init__(self, vault: Vault, resolver: LinkResolver):
        self.vault = vault
        self.resolver = resolver
        self.warnings: list = []
        self.base_provider = None  # set by build.py once bases are parsed

    def render_note(self, note: Note, output_path=None) -> RenderResult:
        base = output_path or urls.note_output_path(note.path)
        return self._render(note, base, active=set(), depth=0)

    # --- pipeline ---

    def _render(self, note: Note, base_output: str, active: set, depth: int) -> RenderResult:
        active = active | {note.path}
        text = self._transform_callouts(note.body)
        text = mdtext.apply_outside_code(text, lambda seg: self._inline(seg, note.path, base_output))
        result = render_markdown(text)
        result.html = self._inject_note_embeds(result.html, base_output, active, depth, result)
        result.html = self._inject_base_embeds(result.html, base_output)
        return result

    def _inline(self, segment: str, from_path: str, base_output: str) -> str:
        segment = mdtext.EMBED_RE.sub(lambda m: self._embed_html(m, from_path, base_output), segment)
        segment = mdtext.WIKILINK_RE.sub(lambda m: self._wikilink_html(m, from_path, base_output), segment)
        segment = mdtext.TAG_RE.sub(lambda m: self._tag_html(m, base_output), segment)
        return segment

    # --- callouts ---

    def _transform_callouts(self, text: str) -> str:
        parts = []
        pos = 0
        for m in mdtext.CODE_FENCE_RE.finditer(text):
            parts.append(self._callouts_in(text[pos:m.start()]))
            parts.append(m.group(0))
            pos = m.end()
        parts.append(self._callouts_in(text[pos:]))
        return "".join(parts)

    def _callouts_in(self, text: str) -> str:
        lines = text.split("\n")
        out = []
        i = 0
        while i < len(lines):
            if lines[i].lstrip().startswith(">"):
                run = []
                while i < len(lines) and lines[i].lstrip().startswith(">"):
                    run.append(lines[i])
                    i += 1
                out.append(self._convert_run(run))
            else:
                out.append(lines[i])
                i += 1
        return "\n".join(out)

    def _convert_run(self, run: list) -> str:
        inner = [_QUOTE_PREFIX_RE.sub("", ln) for ln in run]
        m = CALLOUT_HEAD_RE.match(inner[0])
        if not m:
            return "\n".join(run)
        ctype = m.group(1).lower()
        fold = m.group(2)
        title = html_mod.escape(m.group(3).strip() or ctype.capitalize())
        body_md = self._callouts_in("\n".join(inner[1:]))
        if fold:
            open_attr = " open" if fold == "+" else ""
            head = (f'<details class="callout" data-callout="{ctype}"{open_attr}>\n'
                    f'<summary class="callout-title manifest-label">{title}</summary>\n'
                    f'<div class="callout-body">')
            tail = "</div>\n</details>"
        else:
            head = (f'<div class="callout" data-callout="{ctype}">\n'
                    f'<div class="callout-title manifest-label">{title}</div>\n'
                    f'<div class="callout-body">')
            tail = "</div>\n</div>"
        return f"{head}\n\n{body_md}\n\n{tail}"

    # --- inline elements ---

    def _wikilink_html(self, m, from_path: str, base_output: str) -> str:
        target = m.group(1).strip()
        heading = (m.group(2) or "")[1:].strip()
        alias = (m.group(3) or "")[1:].strip()
        if not target and not heading:
            return m.group(0)
        label = alias or (f"{target} § {heading}" if target and heading else target or heading)
        resolved = self.resolver.resolve_note(target, from_path)
        if resolved is None:
            self.warnings.append(f"{from_path}: broken link {m.group(0)}")
            return (f'<span class="broken-link" title="no note named '
                    f'{html_mod.escape(target, quote=True)}">{html_mod.escape(label)}</span>')
        frag = ""
        if heading and not heading.startswith("^"):
            frag = urls.slugify_heading(heading)
        href = urls.rel_href(base_output, urls.page_output_path(resolved), frag)
        return f'<a class="internal-link" href="{href}">{html_mod.escape(label)}</a>'

    def _embed_html(self, m, from_path: str, base_output: str) -> str:
        target = m.group(1).strip()
        heading = (m.group(2) or "")[1:].strip()
        alias = (m.group(3) or "")[1:].strip()
        basename = target.rsplit("/", 1)[-1]
        ext = ("." + basename.rsplit(".", 1)[-1].lower()) if "." in basename else ""
        if ext in IMAGE_EXTS:
            asset = self.resolver.resolve_asset(target, from_path)
            if asset is None:
                self.warnings.append(f"{from_path}: missing embed {m.group(0)}")
                return f'<span class="broken-link">{html_mod.escape(target)}</span>'
            src = urls.rel_href(base_output, asset)
            if alias and alias.isdigit():
                return f'<img src="{src}" alt="{html_mod.escape(target, quote=True)}" width="{alias}">'
            return f'<img src="{src}" alt="{html_mod.escape(alias or target, quote=True)}">'
        if ext == ".base":
            resolved = self.resolver.resolve_base(target, from_path)
            if resolved is None:
                self.warnings.append(f"{from_path}: missing embed {m.group(0)}")
                return f'<span class="broken-link">{html_mod.escape(target)}</span>'
            # ">" and "#" would terminate or re-delimit the comment token,
            # letting note content forge a second token with an unvalidated rel.
            view = heading.replace(">", "").replace("#", "")
            return f"\n\n<!--twb-base-embed:{resolved}#{view}-->\n\n"
        if ext and ext != ".md":
            asset = self.resolver.resolve_asset(target, from_path)
            if asset is None:
                self.warnings.append(f"{from_path}: missing embed {m.group(0)}")
                return f'<span class="broken-link">{html_mod.escape(target)}</span>'
            href = urls.rel_href(base_output, asset)
            return f'<a class="internal-link file-embed" href="{href}">{html_mod.escape(alias or target)}</a>'
        resolved = self.resolver.resolve_note(target, from_path)
        if resolved is None:
            self.warnings.append(f"{from_path}: missing embed {m.group(0)}")
            return f'<span class="broken-link">{html_mod.escape(target or m.group(0))}</span>'
        frag = urls.slugify_heading(heading) if heading and not heading.startswith("^") else ""
        return f"\n\n<!--twb-embed:{resolved}#{frag}-->\n\n"

    def _tag_html(self, m, base_output: str) -> str:
        tag = m.group(1).strip("/")
        if not mdtext.is_valid_tag(tag):
            return m.group(0)
        href = urls.rel_href(base_output, urls.tag_output_path(tag))
        return f'<a class="tag" href="{href}">#{html_mod.escape(tag)}</a>'

    # --- note transclusion ---

    def _inject_note_embeds(self, html_out: str, base_output: str, active: set,
                            depth: int, result: RenderResult) -> str:
        def repl(m):
            target_path, frag = m.group(1), m.group(2)
            target = self.vault.notes.get(target_path)
            if target is None:
                return '<span class="broken-link">missing embed</span>'
            href = urls.rel_href(base_output, urls.note_output_path(target_path))
            title = html_mod.escape(target.title)
            if target_path in active:
                return ('<div class="callout" data-callout="warning">'
                        '<div class="callout-title manifest-label">Embed cycle</div>'
                        f'<div class="callout-body"><p><a href="{href}">{title}</a> '
                        "embeds itself.</p></div></div>")
            if depth >= 1:
                return f'<a class="internal-link" href="{href}">{title}</a>'
            sub = self._render(target, base_output, active, depth + 1)
            if sub.has_mermaid:
                result.has_mermaid = True
            inner = _extract_section(sub.html, frag) if frag else sub.html
            return (f'<section class="note-embed">'
                    f'<div class="note-embed-title manifest-label"><a href="{href}">{title}</a></div>'
                    f"{inner}</section>")

        return EMBED_COMMENT_RE.sub(repl, html_out)

    def _inject_base_embeds(self, html_out: str, base_output: str) -> str:
        def repl(m):
            rel, view = m.group(1), m.group(2)
            rendered = self.base_provider(rel, view, base_output) \
                if self.base_provider else None
            if rendered is None:
                return '<span class="broken-link">missing embed</span>'
            return rendered

        return BASE_EMBED_COMMENT_RE.sub(repl, html_out)
