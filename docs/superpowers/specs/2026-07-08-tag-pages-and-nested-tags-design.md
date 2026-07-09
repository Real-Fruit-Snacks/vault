# Tag Pages & Nested-Tag Support — Design

**Date:** 2026-07-08
**Status:** Approved (pending user review of this doc)

## Goal

Give the tag surfaces a professional, cohesive look and make Obsidian nested
tags (`tag1/tag2`) behave hierarchically the way they do inside Obsidian: a
parent tag aggregates every note under it and its descendants.

## Problem

Today a nested tag such as `#networking/vpn` is treated as one opaque, flat
string:

- Its page lives at `_tags/networking-vpn.html` (slash flattened to a hyphen),
  which can collide with a literal `#networking-vpn` tag.
- Visiting `#networking` does **not** surface notes tagged only
  `#networking/vpn` — there is no aggregation and no synthesized parent page.
- The individual tag page (`pages.tag_page_content`) is a bare `<h1>` plus a
  flat `<ul>` of note titles; the index (`pages.tags_index_content`) is a plain
  bulleted list. Neither expresses hierarchy and both look unfinished next to
  the rest of the site.

## Global Constraints

- Pure-Python standard library only; no new third-party dependencies. Vendored
  deps under `tools/vendor/` remain the only externals.
- Frontend stays vanilla; tag pages are static HTML + existing `site.css`. No
  new JS is required for this feature.
- Match the existing terminal-workbench visual language (reuse `.manifest-label`,
  `.section-head`, `.tag`, and the homepage "recently updated" row styling
  rather than inventing parallel styles).
- All existing behavior for non-nested tags, inline `#tag` chips in note
  bodies, and note-header chips is preserved.
- `python -m unittest` and `python tools/build.py` both pass with no new
  warnings for the demo vault.

## Decisions (locked during brainstorming)

1. **Nesting model:** parent aggregates children. `#networking` lists every
   note tagged `#networking` or any descendant (`#networking/vpn`,
   `#networking/vpn/site`), de-duplicated. Parent pages are generated even when
   no note carries the bare parent.
2. **Parent page:** shows a sub-tags chip row (direct children) plus the
   aggregated note list.
3. **Note entries:** title + muted folder path (homepage "recently updated"
   language). No per-note date, no matched-sub-tag badge.
4. **Chip labels:** full path everywhere (`#networking/vpn`).
5. **Tags index:** grouped tree — top-level tags as headers with aggregate
   counts; descendants indented beneath as chips with their own counts.
6. **Homepage / Notes-index clouds:** top-level tags only, with aggregate
   counts, each linking to its parent page.

## Architecture

Four cooperating pieces, each independently testable:

### 1. `tools/ssg/tags.py` (new module — the hierarchy)

Turns the flat "tag → set of directly-tagged note paths" map into a tree.

```
build_tag_tree(direct: dict[str, set[str]]) -> list[TagNode]   # roots, sorted
```

`TagNode` (dataclass) fields:

- `path: str` — full tag path, e.g. `"networking/vpn"`.
- `name: str` — leaf segment, e.g. `"vpn"` (equals `path` for a root).
- `direct: set[str]` — note paths tagged with exactly this path.
- `notes: set[str]` — aggregate: `direct` unioned with every descendant's
  `direct`, de-duplicated. This set drives all counts (`len(node.notes)`).
- `children: list[TagNode]` — direct children, sorted case-insensitively by
  `name`.

Behavior:

- **Synthesized parents:** given only `networking/vpn`, the tree contains a
  `networking` node (empty `direct`, `notes` = `vpn`'s notes) whose child is the
  `vpn` node. Every prefix of every tag path becomes a node.
- **Sorting:** roots and children sorted case-insensitively by their segment.
- Splitting is on `/`; segments are the already-normalized display spellings
  from `note.tags` (leading/trailing slashes are already stripped upstream in
  `mdtext.find_inline_tags` and the frontmatter loader).

Helpers exported for callers:

```
iter_nodes(roots) -> Iterator[TagNode]     # pre-order walk over the whole tree
ancestors(path) -> list[str]               # ["networking", "networking/vpn"] for "networking/vpn"
```

### 2. `tools/ssg/urls.py` (URL scheme)

`tag_output_path` changes from a flattened single slug to per-segment nested
directories, so the hierarchy is visible in the URL and the `a/b`-vs-`a-b`
collision disappears:

```
tag_output_path("networking/vpn") -> "_tags/networking/vpn.html"
tag_output_path("networking")     -> "_tags/networking.html"
tag_output_path("Reading")        -> "_tags/reading.html"
```

Implementation: split on `/`, run the existing `tag_slug` per segment, join
slugged segments with `/`, prefix `_tags/`, suffix `.html`. `tag_slug` itself
is unchanged and still used per segment.

`rel_href` already computes correct relative paths for nested output paths, so
deeper tag pages (`_tags/networking/vpn.html`) resolve links to notes and
sibling tags correctly with no change.

**Slug-merge warnings** (two display spellings colliding on one output path,
e.g. `#Reading` vs `#reading`) move from build.py's per-tag loop to being keyed
on the full slugged output path. Case-variant merge behavior is preserved.

### 3. `tools/build.py` (orchestration)

- Build the direct `tag → set[path]` map as today (still de-duplicating
  case-variant display spellings onto one canonical spelling per output path,
  keeping the existing warning).
- Call `tags.build_tag_tree(direct)` to get the node tree.
- Iterate `tags.iter_nodes(roots)` to write **one page per node** (including
  synthesized parents), using `urls.tag_output_path(node.path)`.
- Breadcrumbs become a drill-path: `tags / networking / vpn`, each ancestor
  segment linking to its own tag page via `urls.tag_output_path`.
- Page description: `f"Notes tagged #{node.path}."`.
- Write `_tags/index.html` from the tree (grouped tree renderer).
- `all_output_paths` (the search-index / sitemap list) enumerates every node's
  output path, not just direct-tag keys.
- Homepage (`home_sections`) and Notes index (`notes_index_content`) receive
  the **root nodes** for their top-level-only clouds.

### 4. `tools/ssg/pages.py` (rendering)

Signatures change to take the tree instead of the flat map:

- `tag_page_content(node: TagNode, vault, output_path) -> str`
  - Heading: `<h1><span class="manifest-label">tag</span> #<path></h1>`.
  - Count line: muted `manifest-label` "N notes".
  - If `node.children`: a `sub-tags` section — a `<div class="tag-children">`
    of `.tag` chips, each labeled with the child's **full path** and linking to
    `urls.tag_output_path(child.path)`, with the child's aggregate count.
  - Note list: `node.notes`, sorted by title, each row rendered as title +
    muted folder path (a shared `_note_row(path, vault, output_path)` helper
    extracted from / shared with the homepage "recently updated" markup, minus
    the date).
- `tags_index_content(roots: list[TagNode], output_path) -> str`
  - `<h1>Tags</h1>` then, per root: a `.section-head` linking to the root's tag
    page showing the root label + aggregate count, followed by an indented
    block of descendant chips (full path + count). Rendered via a small
    recursive helper so arbitrary nesting depth is handled.
- `_tag_chips(...)` / `home_sections(...)` / `notes_index_content(...)` accept
  root nodes and render only top-level chips (full path + aggregate count),
  each linking to the parent tag page.
- `note_header` and the inline `#tag` renderer in `obsidian.py` are unchanged
  (already emit full-path chips to `urls.tag_output_path`, which now yields the
  nested URL automatically).

## CSS (`site-assets/site.css`)

Reuse existing classes wherever possible. New, small additions:

- `.tag-children` — flex-wrap chip row (mirror `.home-tags`) for the parent
  page's sub-tags block, under a `.manifest-label` "sub-tags" heading.
- `.tag-tree` / `.tag-tree-children` — the index's indented descendant block:
  a left border/indent under each root `.section-head`, chips laid out like
  `.home-tags`. Counts reuse `.home-count`.
- `.tag-count` — the "N notes" line on an individual tag page (muted,
  `manifest-label` sizing).
- Note rows on tag pages reuse `.home-recent` / `.home-recent-title` /
  `.home-recent-path` styling via the shared helper markup, so no new row
  styles are needed.

No dark/light-specific work beyond what these shared variables already give.

## Data Flow

```
vault.notes[*].tags  (full-path strings, e.g. "networking/vpn")
      │  build.py: direct[display] = {paths...}  (+ case-variant merge warning)
      ▼
tags.build_tag_tree(direct)  →  roots: list[TagNode]  (parents synthesized, notes aggregated)
      │
      ├─ iter_nodes → build.py writes _tags/<seg>/<seg>.html per node
      │        via pages.tag_page_content(node, ...)  + drill-path breadcrumb
      ├─ roots → pages.tags_index_content(roots, ...) → _tags/index.html
      └─ roots → pages.home_sections / notes_index_content (top-level chips)
```

## Error Handling / Edge Cases

- **Empty vault / no tags:** no `_tags/` output, no tag sections — same as today
  (guarded by `if roots:`).
- **Case-variant collision** (`#Reading` / `#reading`): merged onto one output
  path with the existing warning, now keyed on the full slugged path.
- **Segment slug collision** (`networking/vpn` vs `networking/v-p-n`): same
  merge-warning mechanism, keyed on the full output path.
- **HTML-unsafe tag text** (`<em>`): every tag path is passed through
  `html.escape` in headings, chips, and breadcrumbs (preserved from today;
  covered by `test_tag_breadcrumb_is_escaped`).
- **Deep nesting** (`a/b/c/d`): handled generically by the recursive tree build
  and recursive index renderer; each level gets its own aggregating page.
- **A root that is itself a leaf** (`#python`, no children): page has no
  sub-tags block; index shows it as a header with no indented block.

## Testing

New `tests/test_tags.py`:

- `build_tag_tree` synthesizes missing parents.
- Aggregate `notes` unions descendants and de-duplicates a note tagged with
  both parent and child.
- Counts (`len(node.notes)`) are aggregate; a parent's count ≥ any child's.
- `children` sorted case-insensitively; roots sorted.
- `ancestors("a/b/c")` == `["a", "a/b", "a/b/c"]`.
- Single-level tags produce a root with empty `children`.

Updated existing tests:

- `tests/test_urls.py::test_tag_output_path` — nested path expectations
  (`"networking/vpn"` → `"_tags/networking/vpn.html"`).
- `tests/test_pages.py::test_tag_page_and_index` — call the new
  tree-based signatures; assert count line, sub-tags block, folder-path rows,
  grouped-tree index markup.
- `tests/test_build.py` — expected output paths use nested form
  (`_tags/proj/site.html`); `test_case_variant_tags_merge_with_warning` and
  `test_tag_breadcrumb_is_escaped` updated for the nested path; add an
  assertion that a synthesized parent page exists and aggregates a child's note.

Full `python -m unittest` green; `python tools/build.py` on the demo vault
clean.

## Out of Scope

- No tag-search or tag-filtering JS.
- No changes to how tags are parsed from notes (`mdtext` / frontmatter).
- No tag renaming, aliasing, or per-tag descriptions.
- Homepage/Notes clouds intentionally do **not** show the full nested
  vocabulary (top-level only, by decision).
