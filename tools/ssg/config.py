from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_ASSET_EXTENSIONS = [
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".pdf", ".mp4", ".webm", ".mp3", ".wav", ".zip",
]

# The vault lives in Notes/, isolated from repo machinery, so folder names
# inside it are fair game for publishing. Dot-folders (.obsidian, .git, ...)
# are skipped by the scanner's dotfile rule; only names the build's own
# output can collide with stay reserved.
BUILTIN_EXCLUDE_DIRS = {"public", "_tags"}
BUILTIN_EXCLUDE_FILES = {"site.config.json"}

# Single source of truth for banner tones: the loader validates against it
# and the renderer clamps to it. Adding a tone means extending this plus the
# .site-banner-<name> CSS rule.
BANNER_STYLES = ("info", "warn")


@dataclass
class SiteConfig:
    title: str = "Real-Fruit-Snacks"
    homepage: str = "Home.md"
    exclude: list = field(default_factory=list)
    asset_extensions: list = field(default_factory=lambda: list(DEFAULT_ASSET_EXTENSIONS))
    site_url: str = ""
    description: str = ""
    banner_enabled: bool = False
    banner_text: str = ""
    banner_style: str = "info"
    pet_enabled: bool = False


def load_config(vault_root: Path) -> SiteConfig:
    cfg = SiteConfig()
    cfg_path = vault_root / "site.config.json"
    if not cfg_path.is_file():
        return cfg
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"WARNING: site.config.json ignored ({exc})")
        return cfg
    if not isinstance(data, dict):
        print("WARNING: site.config.json is not a JSON object; ignored")
        return cfg
    if isinstance(data.get("title"), str):
        cfg.title = data["title"]
    if isinstance(data.get("homepage"), str):
        cfg.homepage = data["homepage"]
    if isinstance(data.get("site_url"), str):
        cfg.site_url = data["site_url"]
    if isinstance(data.get("description"), str):
        cfg.description = data["description"]
    if isinstance(data.get("exclude"), list):
        cfg.exclude = [str(x).strip("/") for x in data["exclude"]]
    if isinstance(data.get("asset_extensions"), list):
        exts = [str(x).lower().strip() for x in data["asset_extensions"]]
        cfg.asset_extensions = [e if e.startswith(".") else "." + e for e in exts if e]
    if isinstance(data.get("banner_enabled"), bool):
        cfg.banner_enabled = data["banner_enabled"]
    if isinstance(data.get("banner_text"), str):
        cfg.banner_text = data["banner_text"]
    if isinstance(data.get("banner_style"), str):
        if data["banner_style"] in BANNER_STYLES:
            cfg.banner_style = data["banner_style"]
        else:
            print(f"WARNING: banner_style {data['banner_style']!r} not recognized; using 'info'")
    if isinstance(data.get("pet_enabled"), bool):
        cfg.pet_enabled = data["pet_enabled"]
    return cfg
