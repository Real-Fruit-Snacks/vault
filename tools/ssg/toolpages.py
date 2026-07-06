from __future__ import annotations

import html as html_mod
import json
from dataclasses import dataclass, field
from pathlib import Path

from . import urls

ASSET_SUFFIXES = {".js", ".css"}


@dataclass
class Tool:
    slug: str
    title: str
    description: str
    body_html: str
    assets: dict = field(default_factory=dict)  # filename -> absolute source Path
    learn_html: str = ""
    learn_title: str = "learn more"
    icon: str = ""  # sidebar icon name; falls back to the generic tool glyph


def discover_tools(source_dir: Path, warnings: list) -> list:
    """Collect tools from site-tools/<slug>/ (tool.json + body.html [+ js/css])."""
    tools = []
    if not source_dir.is_dir():
        return tools
    for tool_dir in sorted(p for p in source_dir.iterdir() if p.is_dir()):
        meta_path = tool_dir / "tool.json"
        body_path = tool_dir / "body.html"
        if not meta_path.is_file() or not body_path.is_file():
            warnings.append(
                f"site-tools/{tool_dir.name}: missing tool.json or body.html; skipped")
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"site-tools/{tool_dir.name}: invalid tool.json ({exc}); skipped")
            continue
        if not isinstance(meta, dict):
            warnings.append(f"site-tools/{tool_dir.name}: tool.json is not an object; skipped")
            continue
        title = meta["title"] if isinstance(meta.get("title"), str) else tool_dir.name
        description = meta["description"] if isinstance(meta.get("description"), str) else ""
        learn_title = meta["learn_title"] if isinstance(meta.get("learn_title"), str) else "learn more"
        icon = meta["icon"] if isinstance(meta.get("icon"), str) else ""
        learn_path = tool_dir / "learn.html"
        learn_html = learn_path.read_text(encoding="utf-8") if learn_path.is_file() else ""
        assets = {p.name: p for p in sorted(tool_dir.iterdir())
                  if p.is_file() and p.suffix.lower() in ASSET_SUFFIXES}
        tools.append(Tool(slug=tool_dir.name, title=title, description=description,
                          body_html=body_path.read_text(encoding="utf-8"), assets=assets,
                          learn_html=learn_html, learn_title=learn_title, icon=icon))
    return tools


def tool_output_path(tool: Tool) -> str:
    return f"tools/{tool.slug}.html"


def tool_page_content(tool: Tool) -> str:
    desc = ""
    if tool.description:
        desc = f'<p class="tool-desc">{html_mod.escape(tool.description)}</p>'
    learn = ""
    if tool.learn_html:
        learn = (f'<details class="tool-learn">'
                 f'<summary class="manifest-label">{html_mod.escape(tool.learn_title)}</summary>'
                 f'<div class="tool-learn-body">{tool.learn_html}</div></details>')
    return (f'<header class="note-header"><h1>{html_mod.escape(tool.title)}</h1>'
            f"{desc}</header>{tool.body_html}{learn}")


def tools_index_content(tools: list, output_path: str) -> str:
    items = "".join(
        f'<li><a href="{urls.rel_href(output_path, tool_output_path(t))}">'
        f"{html_mod.escape(t.title)}</a>"
        f'<div class="tool-desc">{html_mod.escape(t.description)}</div></li>'
        for t in tools)
    return f'<h1>Tools</h1><ul class="note-list">{items}</ul>'
