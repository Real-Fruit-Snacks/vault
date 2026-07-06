from __future__ import annotations

from . import mdtext
from .vault import Vault


class LinkResolver:
    def __init__(self, vault: Vault):
        self.vault = vault
        self.warnings: list = []
        self._by_basename: dict = {}
        self._by_alias: dict = {}
        self._assets_by_basename: dict = {}
        self._canvas_by_basename: dict = {}
        self._base_by_basename: dict = {}
        for path in vault.notes:
            base = path.rsplit("/", 1)[-1][:-3].lower()
            self._by_basename.setdefault(base, []).append(path)
        for path, note in vault.notes.items():
            for alias in note.aliases:
                self._by_alias.setdefault(alias.lower(), []).append(path)
        for path in vault.assets:
            base = path.rsplit("/", 1)[-1].lower()
            self._assets_by_basename.setdefault(base, []).append(path)
        for path in vault.canvases:
            base = path.rsplit("/", 1)[-1][:-7].lower()
            self._canvas_by_basename.setdefault(base, []).append(path)
        for path in vault.bases:
            base = path.rsplit("/", 1)[-1][:-5].lower()
            self._base_by_basename.setdefault(base, []).append(path)

    def resolve_note(self, target: str, from_path: str):
        t = target.strip().strip("/")
        if not t:
            return from_path
        cand = t if t.lower().endswith(".md") else t + ".md"
        cand_l = cand.lower()
        exact = [p for p in self.vault.notes if p.lower() == cand_l]
        if exact:
            return exact[0]
        if "/" in cand_l:
            suffix = sorted(p for p in self.vault.notes if p.lower().endswith("/" + cand_l))
            if suffix:
                if len(suffix) > 1:
                    self.warnings.append(
                        f"{from_path}: ambiguous link '[[{target}]]' matches {suffix}; using {suffix[0]}")
                return suffix[0]
            return None
        matches = sorted(self._by_basename.get(cand_l[:-3], []))
        if matches:
            if len(matches) > 1:
                self.warnings.append(
                    f"{from_path}: ambiguous link '[[{target}]]' matches {matches}; using {matches[0]}")
            return matches[0]
        aliases = sorted(self._by_alias.get(t.lower(), []))
        if aliases:
            if len(aliases) > 1:
                self.warnings.append(
                    f"{from_path}: ambiguous alias '[[{target}]]' matches {aliases}; using {aliases[0]}")
            return aliases[0]
        raw = t.lower()
        if raw.endswith(".canvas"):
            exact_canvas = [p for p in self.vault.canvases if p.lower() == raw]
            if exact_canvas:
                return exact_canvas[0]
            stem = raw.rsplit("/", 1)[-1][:-7]
            canvases = sorted(self._canvas_by_basename.get(stem, []))
            if canvases:
                if len(canvases) > 1:
                    self.warnings.append(
                        f"{from_path}: ambiguous link '[[{target}]]' matches {canvases}; "
                        f"using {canvases[0]}")
                return canvases[0]
            return None
        canvases = sorted(self._canvas_by_basename.get(raw, []))
        if canvases:
            if len(canvases) > 1:
                self.warnings.append(
                    f"{from_path}: ambiguous link '[[{target}]]' matches {canvases}; "
                    f"using {canvases[0]}")
            return canvases[0]
        if raw.endswith(".base"):
            exact_base = [p for p in self.vault.bases if p.lower() == t.lower()]
            if exact_base:
                return exact_base[0]
            stem = raw.rsplit("/", 1)[-1][:-5]
            base_matches = sorted(self._base_by_basename.get(stem, []))
            if base_matches:
                if len(base_matches) > 1:
                    self.warnings.append(
                        f"{from_path}: ambiguous link '[[{target}]]' matches {base_matches}; "
                        f"using {base_matches[0]}")
                return base_matches[0]
            return None
        base_matches = sorted(self._base_by_basename.get(raw, []))
        if base_matches:
            if len(base_matches) > 1:
                self.warnings.append(
                    f"{from_path}: ambiguous link '[[{target}]]' matches {base_matches}; "
                    f"using {base_matches[0]}")
            return base_matches[0]
        return None

    def resolve_asset(self, target: str, from_path: str):
        t = target.strip().strip("/").lower()
        exact = [p for p in self.vault.assets if p.lower() == t]
        if exact:
            return exact[0]
        matches = sorted(self._assets_by_basename.get(t.rsplit("/", 1)[-1], []))
        if matches:
            if len(matches) > 1:
                self.warnings.append(
                    f"{from_path}: ambiguous embed '{target}' matches {matches}; using {matches[0]}")
            return matches[0]
        return None

    def resolve_base(self, target: str, from_path: str):
        t = target.strip().strip("/")
        exact = [p for p in self.vault.bases if p.lower() == t.lower()]
        if exact:
            return exact[0]
        stem = t.rsplit("/", 1)[-1].lower()
        if stem.endswith(".base"):
            stem = stem[:-5]
        matches = sorted(self._base_by_basename.get(stem, []))
        if matches:
            if len(matches) > 1:
                self.warnings.append(
                    f"{from_path}: ambiguous embed '{target}' matches {matches}; "
                    f"using {matches[0]}")
            return matches[0]
        return None


def build_backlinks(vault: Vault, resolver: LinkResolver) -> dict:
    backlinks: dict = {}
    for src in sorted(vault.notes):
        seen = set()
        for target in mdtext.find_wikilink_targets(vault.notes[src].body):
            dest = resolver.resolve_note(target, src)
            if dest and dest != src and dest not in seen and dest in vault.notes:
                seen.add(dest)
                backlinks.setdefault(dest, []).append(src)
    return backlinks
