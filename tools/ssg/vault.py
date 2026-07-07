from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import mdtext
from .config import BUILTIN_EXCLUDE_DIRS, BUILTIN_EXCLUDE_FILES, SiteConfig


@dataclass
class Note:
    path: str
    title: str
    frontmatter: dict
    body: str
    tags: list = field(default_factory=list)
    aliases: list = field(default_factory=list)


@dataclass
class Vault:
    root: Path
    notes: dict = field(default_factory=dict)
    assets: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    skipped: int = 0
    canvases: dict = field(default_factory=dict)   # rel -> absolute Path
    bases: dict = field(default_factory=dict)      # rel -> Path
    unpublished: set = field(default_factory=set)  # rel paths of publish: false notes


def _string_list(value) -> list:
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _load_note(path: Path, rel: str, warnings: list) -> Note:
    text = path.read_text(encoding="utf-8", errors="replace")
    fm_text, body = mdtext.split_frontmatter(text)
    frontmatter = {}
    if fm_text is not None:
        try:
            loaded = yaml.safe_load(fm_text)
            if isinstance(loaded, dict):
                frontmatter = loaded
            elif loaded is not None:
                warnings.append(f"{rel}: frontmatter is not a mapping; ignored")
        except yaml.YAMLError as exc:
            warnings.append(f"{rel}: malformed frontmatter ignored ({exc})")
    basename = rel.rsplit("/", 1)[-1][:-3]
    title = frontmatter["title"] if isinstance(frontmatter.get("title"), str) else basename
    raw_tags = _string_list(frontmatter.get("tags")) + mdtext.find_inline_tags(body)
    seen, tags = set(), []
    for tag in raw_tags:
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            tags.append(tag)
    return Note(path=rel, title=title, frontmatter=frontmatter, body=body,
                tags=tags, aliases=_string_list(frontmatter.get("aliases")))


def scan_vault(root: Path, config: SiteConfig) -> Vault:
    vault = Vault(root=root)
    exclude = [e.strip("/") for e in config.exclude]
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        parts = rel.split("/")
        if parts[0] in BUILTIN_EXCLUDE_DIRS:
            continue
        if any(part.startswith(".") for part in parts):
            continue
        # Top-level folders whose name starts with "_" (e.g. "_drafts") are
        # private scratch space and never publish. Only the vault root is
        # checked, so nested "_" folders and top-level "_" files are unaffected.
        if len(parts) > 1 and parts[0].startswith("_"):
            continue
        if len(parts) == 1 and parts[0] in BUILTIN_EXCLUDE_FILES:
            continue
        if any(rel == ex or rel.startswith(ex + "/") for ex in exclude):
            continue
        suffix = path.suffix.lower()
        if suffix == ".md":
            note = _load_note(path, rel, vault.warnings)
            if note.frontmatter.get("publish") is False:
                vault.skipped += 1
                vault.unpublished.add(rel)
                continue
            vault.notes[rel] = note
        elif suffix == ".canvas":
            vault.canvases[rel] = path
        elif suffix == ".base":
            vault.bases[rel] = path
        elif suffix in config.asset_extensions:
            vault.assets[rel] = path
        else:
            vault.warnings.append(f"{rel}: unrecognized file type skipped")
    return vault
