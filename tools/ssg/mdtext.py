from __future__ import annotations

import re

FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?", re.DOTALL)

# Whole fenced code block: opening fence, body lines, closing fence (or EOF for
# an unclosed fence). The closing fence must repeat the exact opening fence
# string (a longer closing fence is not recognized -- acceptable simplification).
CODE_FENCE_RE = re.compile(
    r"^ {0,3}(?P<fence>`{3,}|~{3,})[^\n]*\n"
    r"(?:(?!^ {0,3}(?P=fence)[ \t]*$).*\n?)*"
    r"(?:^ {0,3}(?P=fence)[ \t]*$\n?|\Z)",
    re.MULTILINE,
)

INLINE_CODE_RE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)

# group(1)=target, group(2)=#heading (with #), group(3)=|alias (with |)
EMBED_RE = re.compile(r"!\[\[([^\[\]|#]*)(#[^\[\]|]+)?(\|[^\[\]]+)?\]\]")
WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\[\]|#]*)(#[^\[\]|]+)?(\|[^\[\]]+)?\]\]")

# Inline tag: start of line or after whitespace/'(' , '#', then word char first.
TAG_RE = re.compile(r"(?:^|(?<=[\s(]))#([A-Za-z0-9_][A-Za-z0-9_/-]*)", re.MULTILINE)


def split_frontmatter(text: str):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def _apply_outside_inline(text: str, fn) -> str:
    parts = []
    pos = 0
    for m in INLINE_CODE_RE.finditer(text):
        parts.append(fn(text[pos:m.start()]))
        parts.append(m.group(0))
        pos = m.end()
    parts.append(fn(text[pos:]))
    return "".join(parts)


def apply_outside_code(text: str, fn) -> str:
    parts = []
    pos = 0
    for m in CODE_FENCE_RE.finditer(text):
        parts.append(_apply_outside_inline(text[pos:m.start()], fn))
        parts.append(m.group(0))
        pos = m.end()
    parts.append(_apply_outside_inline(text[pos:], fn))
    return "".join(parts)


def is_valid_tag(tag: str) -> bool:
    body = tag.replace("/", "").replace("_", "").replace("-", "")
    return bool(body) and not body.isdigit()


def find_wikilink_targets(text: str):
    targets = []

    def collect(segment: str) -> str:
        for regex in (EMBED_RE, WIKILINK_RE):
            for m in regex.finditer(segment):
                target = m.group(1).strip()
                if target:
                    targets.append(target)
        return segment

    apply_outside_code(text, collect)
    return targets


def find_inline_tags(text: str):
    tags = []

    def collect(segment: str) -> str:
        for m in TAG_RE.finditer(segment):
            tag = m.group(1).strip("/")
            if is_valid_tag(tag):
                tags.append(tag)
        return segment

    apply_outside_code(text, collect)
    return tags
