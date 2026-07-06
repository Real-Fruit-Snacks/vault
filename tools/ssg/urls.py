from __future__ import annotations

import posixpath
import re
import unicodedata
from urllib.parse import quote


def note_output_path(note_path: str) -> str:
    if note_path.lower().endswith(".md"):
        return note_path[:-3] + ".html"
    return note_path


def canvas_output_path(canvas_path: str) -> str:
    return canvas_path[:-7] + ".html"


def base_output_path(base_path: str) -> str:
    return base_path[:-5] + ".html"


def page_output_path(path: str) -> str:
    """Output path for anything a wikilink can resolve to."""
    low = path.lower()
    if low.endswith(".canvas"):
        return canvas_output_path(path)
    if low.endswith(".base"):
        return base_output_path(path)
    return note_output_path(path)


def tag_slug(tag: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]", "-", tag.replace("/", "-"))
    return re.sub(r"-{2,}", "-", slug).strip("-").lower() or "tag"


def tag_output_path(tag: str) -> str:
    return f"_tags/{tag_slug(tag)}.html"


def rel_href(from_output: str, to_output: str, fragment: str = "") -> str:
    from_dir = posixpath.dirname(from_output) or "."
    rel = posixpath.relpath(to_output, from_dir)
    href = quote(rel)
    if fragment:
        href += "#" + quote(fragment)
    return href


def root_prefix(output_path: str) -> str:
    return "../" * output_path.count("/")


_HEADING_STRIP_RE = re.compile(r"[^\w\s-]", re.UNICODE)


def slugify_heading(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _HEADING_STRIP_RE.sub("", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text.lower() or "section"
