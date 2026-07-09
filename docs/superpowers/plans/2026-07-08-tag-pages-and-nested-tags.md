# Tag Pages & Nested-Tag Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Obsidian nested tags (`tag1/tag2`) aggregate hierarchically and give the tag pages a professional, cohesive look.

**Architecture:** A new pure-logic module (`tools/ssg/tags.py`) turns the flat "tag → notes" map into a tree with synthesized parents and aggregated note sets. `urls.py` emits nested tag URLs. `pages.py` renders individual tag pages, the grouped-tree index, and top-level-only clouds from the tree. `build.py` wires the tree into the build (per-node pages, drill-path breadcrumbs, discovery lists).

**Tech Stack:** Python 3.9+ standard library only; vanilla HTML/CSS frontend; `unittest`.

## Global Constraints

- Pure-Python standard library only; no new third-party dependencies (vendored deps under `tools/vendor/` are the only externals).
- Frontend stays vanilla; tag pages are static HTML styled by the existing `site-assets/site.css`. No new JS.
- Reuse the existing terminal-workbench visual language: `.manifest-label`, `.section-head`, `.tag`, `.home-count`, and the homepage `.home-recent` row styling. Do not invent parallel styles.
- Chip labels use the **full tag path** everywhere (`#networking/vpn`).
- All tag text is passed through `html.escape` in headings, chips, and breadcrumbs.
- `python -m unittest discover -s tests -t . -v` and `python tools/build.py` both pass with no new warnings on the demo/fixture vault.
- No AI attribution in commits; author as Real-Fruit-Snacks.

**Test command note:** tests live at repo-root `tests/`; `tests/__init__.py` adds `tools/` to `sys.path`, so `from ssg import …` and `import build` resolve. All `Run:` commands below assume CWD is the repo root `C:\Users\Matt\Documents\Obsidian - Website` (matching CI's `python -m unittest discover -s tests -t . -v`).

---

### Task 1: Tag hierarchy module (`tools/ssg/tags.py`)

Pure logic, no dependencies on other SSG modules. Turns the flat direct-tag map into a sorted tree of `TagNode`s with synthesized parents and aggregated note sets.

**Files:**
- Create: `tools/ssg/tags.py`
- Test: `tests/test_tags.py`

**Interfaces:**
- Consumes: nothing (stdlib only).
- Produces:
  - `TagNode` dataclass: `path: str`, `name: str`, `direct: set`, `notes: set`, `children: list`.
  - `build_tag_tree(direct: dict) -> list` — `direct` is `{full_tag_path: set(note_paths)}`; returns root `TagNode`s sorted case-insensitively by `name`.
  - `iter_nodes(roots) -> Iterator[TagNode]` — pre-order walk over the whole forest.
  - `ancestors(path: str) -> list` — every prefix shallowest-first, e.g. `ancestors("a/b/c") == ["a", "a/b", "a/b/c"]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tags.py`:

```python
import unittest

from ssg import tags


class AncestorsTests(unittest.TestCase):
    def test_single_segment(self):
        self.assertEqual(tags.ancestors("python"), ["python"])

    def test_multi_segment(self):
        self.assertEqual(tags.ancestors("a/b/c"), ["a", "a/b", "a/b/c"])


class BuildTagTreeTests(unittest.TestCase):
    def test_flat_tags_become_sorted_roots(self):
        roots = tags.build_tag_tree({"python": {"A.md"}, "git": {"B.md"}})
        self.assertEqual([r.path for r in roots], ["git", "python"])
        self.assertEqual([r.children for r in roots], [[], []])

    def test_root_sort_is_case_insensitive(self):
        roots = tags.build_tag_tree({"Zebra": {"A.md"}, "apple": {"B.md"}})
        self.assertEqual([r.path for r in roots], ["apple", "Zebra"])

    def test_parent_is_synthesized_when_absent(self):
        roots = tags.build_tag_tree({"proj/site": {"A.md"}})
        self.assertEqual(len(roots), 1)
        proj = roots[0]
        self.assertEqual(proj.path, "proj")
        self.assertEqual(proj.name, "proj")
        self.assertEqual(proj.direct, set())            # nothing tagged bare #proj
        self.assertEqual([c.path for c in proj.children], ["proj/site"])
        self.assertEqual(proj.children[0].name, "site")

    def test_notes_aggregate_and_dedup(self):
        # A.md carries both parent and child; B.md only the child.
        roots = tags.build_tag_tree({"proj": {"A.md"}, "proj/site": {"A.md", "B.md"}})
        proj = roots[0]
        self.assertEqual(proj.direct, {"A.md"})
        self.assertEqual(proj.notes, {"A.md", "B.md"})   # union, de-duplicated
        self.assertEqual(proj.children[0].notes, {"A.md", "B.md"})

    def test_aggregate_count_is_at_least_child_count(self):
        roots = tags.build_tag_tree(
            {"net": {"A.md"}, "net/vpn": {"B.md"}, "net/dns": {"C.md"}})
        net = roots[0]
        self.assertEqual(len(net.notes), 3)
        self.assertTrue(all(len(net.notes) >= len(c.notes) for c in net.children))

    def test_children_sorted_case_insensitively(self):
        roots = tags.build_tag_tree(
            {"net/Zulu": {"A.md"}, "net/alpha": {"B.md"}})
        self.assertEqual([c.name for c in roots[0].children], ["alpha", "Zulu"])

    def test_deep_nesting(self):
        roots = tags.build_tag_tree({"a/b/c": {"A.md"}})
        self.assertEqual([n.path for n in tags.iter_nodes(roots)],
                         ["a", "a/b", "a/b/c"])
        self.assertEqual(roots[0].notes, {"A.md"})


class IterNodesTests(unittest.TestCase):
    def test_preorder_over_forest(self):
        roots = tags.build_tag_tree(
            {"git": {"A.md"}, "net/vpn": {"B.md"}})
        self.assertEqual([n.path for n in tags.iter_nodes(roots)],
                         ["git", "net", "net/vpn"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_tags -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ssg.tags'`.

- [ ] **Step 3: Implement `tools/ssg/tags.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class TagNode:
    path: str                                   # full tag path, e.g. "net/vpn"
    name: str                                   # leaf segment, e.g. "vpn"
    direct: set = field(default_factory=set)    # notes tagged exactly this path
    notes: set = field(default_factory=set)     # aggregate: direct + all descendants
    children: list = field(default_factory=list)


def ancestors(path: str) -> list:
    """Every prefix of a tag path, shallowest first.

    ancestors("a/b/c") -> ["a", "a/b", "a/b/c"]
    """
    segs = path.split("/")
    return ["/".join(segs[: i + 1]) for i in range(len(segs))]


def build_tag_tree(direct: dict) -> list:
    """Turn a flat {full-tag-path: set(note paths)} map into a sorted tree.

    A node is materialized for every path and every ancestor prefix, so a
    parent (#net) is synthesized even when only a child (#net/vpn) is tagged.
    Each node's `notes` aggregates its own `direct` notes plus every
    descendant's, de-duplicated. Roots and children are sorted
    case-insensitively by their leaf segment.
    """
    nodes: dict = {}
    for tag in direct:
        for anc in ancestors(tag):
            if anc not in nodes:
                nodes[anc] = TagNode(path=anc, name=anc.split("/")[-1])
    for tag, paths in direct.items():
        nodes[tag].direct |= set(paths)

    roots: list = []
    for path, node in nodes.items():
        if "/" in path:
            nodes[path.rsplit("/", 1)[0]].children.append(node)
        else:
            roots.append(node)
    for node in nodes.values():
        node.children.sort(key=lambda n: n.name.lower())
    roots.sort(key=lambda n: n.name.lower())

    def aggregate(node: TagNode) -> set:
        acc = set(node.direct)
        for child in node.children:
            acc |= aggregate(child)
        node.notes = acc
        return acc

    for root in roots:
        aggregate(root)
    return roots


def iter_nodes(roots) -> Iterator:
    """Pre-order walk over the whole forest."""
    for node in roots:
        yield node
        yield from iter_nodes(node.children)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_tags -v`
Expected: PASS (all tests green).

- [ ] **Step 5: Commit**

```bash
git add tools/ssg/tags.py tests/test_tags.py
git commit -m "Tags: add hierarchy module with synthesized parents and aggregation"
```

---

### Task 2: Nested tag URLs (`tools/ssg/urls.py`)

Change `tag_output_path` from a flattened single slug to per-segment nested directories, eliminating the `a/b`-vs-`a-b` collision.

**Files:**
- Modify: `tools/ssg/urls.py:38-39`
- Test: `tests/test_urls.py:10-12`

**Interfaces:**
- Consumes: existing `tag_slug(tag) -> str` (unchanged).
- Produces: `tag_output_path("net/vpn") -> "_tags/net/vpn.html"`, `tag_output_path("Reading") -> "_tags/reading.html"`.

- [ ] **Step 1: Update the failing test**

In `tests/test_urls.py`, replace the body of `test_tag_output_path` (currently lines 10-12):

```python
    def test_tag_output_path(self):
        self.assertEqual(urls.tag_output_path("proj/site"), "_tags/proj/site.html")
        self.assertEqual(urls.tag_output_path("Reading"), "_tags/reading.html")
        # each segment is slugged independently
        self.assertEqual(urls.tag_output_path("Net Ops/DNS"), "_tags/net-ops/dns.html")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_urls.UrlTests.test_tag_output_path -v`
Expected: FAIL — got `"_tags/proj-site.html"`, expected `"_tags/proj/site.html"`.

- [ ] **Step 3: Implement the nested path**

In `tools/ssg/urls.py`, replace `tag_output_path` (currently lines 38-39):

```python
def tag_output_path(tag: str) -> str:
    slugged = "/".join(tag_slug(seg) for seg in tag.split("/"))
    return f"_tags/{slugged}.html"
```

Leave `tag_slug` unchanged.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_urls.UrlTests.test_tag_output_path -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/ssg/urls.py tests/test_urls.py
git commit -m "Tags: emit nested per-segment tag URLs"
```

---

### Task 3: Tag-page rendering + styles (`tools/ssg/pages.py`, `site-assets/site.css`)

Rewrite the tag renderers to take `TagNode`s, add the shared note-row helper, and add the small CSS blocks. This task is testable in isolation via `test_pages.py` by constructing `TagNode`s directly.

**Files:**
- Modify: `tools/ssg/pages.py` — `tag_page_content` (435-441), `tags_index_content` (444-449), `_tag_chips` (520-524), `home_sections` signature (461-508), `notes_index_content` signature (542-567); add `_note_row` and `_tag_tree_descendants` helpers.
- Modify: `site-assets/site.css` — add tag blocks after the `.notes-folder` section (~line 730).
- Test: `tests/test_pages.py` — replace `test_tag_page_and_index` (278-283); add new assertions.

**Interfaces:**
- Consumes: `ssg.tags.TagNode` (Task 1); `urls.tag_output_path` (Task 2); existing `urls.rel_href`, `urls.note_output_path`, `html_mod.escape`, `vault.notes[p].title`.
- Produces:
  - `tag_page_content(node, vault, output_path) -> str`
  - `tags_index_content(roots, output_path) -> str`
  - `_tag_chips(roots, output_path) -> str`
  - `home_sections(vault, dates, tag_roots, tools, output_path, home_note=None, canvases=(), bases=()) -> str` (param renamed `tag_map` → `tag_roots`)
  - `notes_index_content(vault, tag_roots, output_path, home_note=None, canvases=(), bases=()) -> str` (param renamed `tag_map` → `tag_roots`)

- [ ] **Step 1: Write the failing tests**

In `tests/test_pages.py`, add `from ssg import tags` near the top imports (line 3 area), then replace `test_tag_page_and_index` (currently lines 278-283) with:

```python
    def test_tag_page_leaf(self):
        vault = scan_vault(self.make_vault({"A.md": "#alpha", "B.md": "#alpha"}), SiteConfig())
        roots = tags.build_tag_tree({"alpha": {"A.md", "B.md"}})
        content = pages.tag_page_content(roots[0], vault, "_tags/alpha.html")
        self.assertIn("#alpha", content)
        self.assertIn("2 notes", content)
        self.assertIn('href="../A.html"', content)
        self.assertIn("home-recent-title", content)   # title + folder row styling
        self.assertNotIn("sub-tags", content)          # leaf has no children block

    def test_tag_page_parent_has_subtags(self):
        vault = scan_vault(
            self.make_vault({"A.md": "#net/vpn", "B.md": "#net/dns"}), SiteConfig())
        roots = tags.build_tag_tree({"net/vpn": {"A.md"}, "net/dns": {"B.md"}})
        net = roots[0]
        content = pages.tag_page_content(net, vault, "_tags/net.html")
        self.assertIn("#net", content)
        self.assertIn("2 notes", content)              # aggregated count
        self.assertIn("sub-tags", content)
        self.assertIn('href="net/dns.html"', content)  # child link, relative to _tags/net.html
        self.assertIn("#net/dns", content)             # full-path child chip

    def test_tags_index_grouped_tree(self):
        roots = tags.build_tag_tree(
            {"net": {"A.md"}, "net/vpn": {"B.md"}, "git": {"C.md"}})
        index = pages.tags_index_content(roots, "_tags/index.html")
        self.assertIn("<h1>Tags</h1>", index)
        self.assertIn('class="tag-tree"', index)
        self.assertIn(">git<", index)                  # root header label
        self.assertIn("#net/vpn", index)               # descendant chip, full path
        self.assertIn('href="net/vpn.html"', index)    # relative to _tags/index.html
```

Note: `make_vault`/`VaultCase` write notes under a temp root; `scan_vault` returns titles equal to the basename (`A`, `B`). Folder is empty for root-level fixtures, so `home-recent-title` is present while `home-recent-path` may be absent — assert only on the title class.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_pages -v`
Expected: FAIL — `tag_page_content()`/`tags_index_content()` take the old signatures (a tag string / a dict), so `TypeError` or wrong-attribute errors.

- [ ] **Step 3: Implement the renderers in `tools/ssg/pages.py`**

Replace `tag_page_content` and `tags_index_content` (currently lines 435-449) with:

```python
def _note_row(path: str, vault: Vault, output_path: str) -> str:
    """A note entry: title + muted folder path, no date. Mirrors the homepage
    'recently updated' row (minus the date) so tag pages share its styling."""
    href = urls.rel_href(output_path, urls.note_output_path(path))
    title = vault.notes[path].title
    folder = path.rsplit("/", 1)[0] if "/" in path else ""
    crumb = (f'<span class="home-recent-path">{html_mod.escape(folder)}</span>'
             if folder else "")
    return (f'<li><a class="home-recent-link" href="{href}">'
            f'<span class="home-recent-title">{html_mod.escape(title)}</span>'
            f"{crumb}</a></li>")


def tag_page_content(node, vault: Vault, output_path: str) -> str:
    n = len(node.notes)
    count = (f'<div class="tag-count manifest-label">'
             f'{n} note{"" if n == 1 else "s"}</div>')
    children = ""
    if node.children:
        chips = "".join(
            f'<a class="tag" href="{urls.rel_href(output_path, urls.tag_output_path(c.path))}">'
            f'#{html_mod.escape(c.path)}'
            f'<span class="home-count">{len(c.notes)}</span></a>'
            for c in node.children)
        children = (f'<section class="tag-children-block">'
                    f'<span class="manifest-label section-head">sub-tags</span>'
                    f'<div class="tag-children">{chips}</div></section>')
    rows = "".join(
        _note_row(p, vault, output_path)
        for p in sorted(node.notes, key=lambda p: vault.notes[p].title.lower()))
    return (f'<h1><span class="manifest-label">tag</span> '
            f'#{html_mod.escape(node.path)}</h1>'
            f'{count}{children}'
            f'<ul class="home-recent tag-notes">{rows}</ul>')


def _tag_tree_descendants(node, output_path: str) -> str:
    """Flatten a node's descendants (all levels) into full-path chips."""
    chips = []
    for child in node.children:
        chips.append(
            f'<a class="tag" href="{urls.rel_href(output_path, urls.tag_output_path(child.path))}">'
            f'#{html_mod.escape(child.path)}'
            f'<span class="home-count">{len(child.notes)}</span></a>')
        chips.append(_tag_tree_descendants(child, output_path))
    return "".join(chips)


def tags_index_content(roots, output_path: str) -> str:
    sections = []
    for root in roots:
        head = (f'<a class="manifest-label section-head" '
                f'href="{urls.rel_href(output_path, urls.tag_output_path(root.path))}">'
                f'{html_mod.escape(root.name)}'
                f'<span class="home-count">{len(root.notes)}</span></a>')
        descendants = _tag_tree_descendants(root, output_path)
        body = (f'<div class="tag-tree-children">{descendants}</div>'
                if descendants else "")
        sections.append(f'<section class="tag-tree">{head}{body}</section>')
    return f'<h1>Tags</h1>{"".join(sections)}'
```

Then replace `_tag_chips` (currently lines 520-524) with the roots-only version:

```python
def _tag_chips(roots, output_path: str) -> str:
    return "".join(
        f'<a class="tag" href="{urls.rel_href(output_path, urls.tag_output_path(r.path))}">'
        f'#{html_mod.escape(r.path)}<span class="home-count">{len(r.notes)}</span></a>'
        for r in roots)
```

In `home_sections` (currently line 461), rename the parameter `tag_map` to `tag_roots`:
- Signature line becomes: `def home_sections(vault: Vault, dates: dict, tag_roots, tools,`
- The body's `if tag_map:` (line 493) becomes `if tag_roots:`
- `_tag_chips(tag_map, output_path)` (line 496) becomes `_tag_chips(tag_roots, output_path)`

In `notes_index_content` (currently line 542), rename the parameter `tag_map` to `tag_roots`:
- Signature: `def notes_index_content(vault: Vault, tag_roots, output_path: str, home_note=None,`
- The body's `if tag_map:` (line 561) becomes `if tag_roots:`
- `_tag_chips(tag_map, output_path)` (line 566) becomes `_tag_chips(tag_roots, output_path)`

- [ ] **Step 4: Add the CSS**

In `site-assets/site.css`, immediately after the `.notes-folder` / `.folder-head` block (the block ending near line 730, right before `/* --- canvas pages --- */`), insert:

```css
/* --- tag pages --- */
.tag-count { margin: 2px 0 18px; }
.tag-children-block { margin: 0 0 26px; }
.tag-children,
.tag-tree-children { display: flex; flex-wrap: wrap; gap: 8px; }
.tag-children { margin-top: 8px; }
.tag-notes { margin-top: 4px; }
.tag-tree { margin-top: 24px; }
.tag-tree-children {
  padding: 12px 0 4px 14px; margin-left: 2px;
  border-left: 1px solid var(--twb-border);
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m unittest tests.test_pages -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/ssg/pages.py site-assets/site.css tests/test_pages.py
git commit -m "Tags: render hierarchical tag pages, grouped index, top-level clouds"
```

---

### Task 4: Build orchestration (`tools/build.py`)

Wire the tree into the build: build the direct map (with the merge warning keyed on output path), build the tree, write one page per node with a drill-path breadcrumb, write the index, and feed roots to the clouds and every node to the discovery list.

**Files:**
- Modify: `tools/build.py:15` (import), `:231-259` (tag map + page loop + index), `:267` (notes index call), `:274` (home_sections call), `:435-436` (page_paths), `:477` (summary count).
- Test: `tests/test_build.py` — `test_pages_written` (30-34), `test_case_variant_tags_merge_with_warning` (384-389), `test_tag_breadcrumb_is_escaped` (391-395); add a nested-aggregation test.

**Interfaces:**
- Consumes: `ssg.tags.build_tag_tree`, `ssg.tags.iter_nodes`, `ssg.tags.ancestors` (Task 1); `urls.tag_output_path` (Task 2); `pages.tag_page_content`, `pages.tags_index_content`, `pages.home_sections(…, tag_roots, …)`, `pages.notes_index_content(…, tag_roots, …)` (Task 3).
- Produces: nested `_tags/**` pages; `_tags/index.html`; `tag_roots` used by clouds and discovery.

- [ ] **Step 1: Add the import**

In `tools/build.py`, add `tags` to the combined `ssg` import (currently line 15):

```python
from ssg import gitdates, graphdata, mdtext, pages, tags, toolpages, urls  # noqa: E402
```

- [ ] **Step 2: Replace the tag map + page loop + index block**

Replace `tools/build.py` lines 231-259 (from `tag_map: dict = {}` through the end of the `if tag_map:` index-write block) with:

```python
    tag_direct: dict = {}    # canonical display tag -> set of note paths
    slug_display: dict = {}  # output path -> first-seen display spelling
    tag_warnings: list = []
    for path, note in sorted(vault.notes.items()):
        for tag in note.tags:
            out = urls.tag_output_path(tag)
            display = slug_display.setdefault(out, tag)
            if display != tag:
                tag_warnings.append(
                    f"tag '{tag}' merges with '{display}' (both map to {out})")
            tag_direct.setdefault(display, set()).add(path)
    tag_roots = tags.build_tag_tree(tag_direct)
    for node in tags.iter_nodes(tag_roots):
        out_path = urls.tag_output_path(node.path)
        crumbs = ['<span>tags</span>']
        for anc in tags.ancestors(node.path):
            crumbs.append('<span class="crumb-sep">/</span>')
            if anc == node.path:
                crumbs.append(f'<span>{html_mod.escape(node.name)}</span>')
            else:
                href = urls.rel_href(out_path, urls.tag_output_path(anc))
                label = html_mod.escape(anc.rsplit("/", 1)[-1])
                crumbs.append(f'<a href="{href}">{label}</a>')
        write(out / out_path, pages.render_page(
            config=config, output_path=out_path, page_title=f"#{node.path}",
            content_html=pages.tag_page_content(node, vault, out_path),
            nav_html=pages.build_nav(vault, "", out_path, tools=nav_tools, home_note=home,
                                     canvases=canvas_paths, bases=base_paths),
            breadcrumbs="".join(crumbs),
            description=f"Notes tagged #{node.path}."))
    if tag_roots:
        write(out / "_tags/index.html", pages.render_page(
            config=config, output_path="_tags/index.html", page_title="Tags",
            content_html=pages.tags_index_content(tag_roots, "_tags/index.html"),
            nav_html=pages.build_nav(vault, "", "_tags/index.html", tools=nav_tools, home_note=home,
                                     canvases=canvas_paths, bases=base_paths),
            breadcrumbs="<span>tags</span>",
            description="Every tag in the vault."))
```

- [ ] **Step 3: Update the three downstream callers**

In `tools/build.py`:

- `notes_index_content` call (currently line 267): change `tag_map` to `tag_roots`:
  ```python
        content_html=pages.notes_index_content(vault, tag_roots, "notes.html", home,
                                               canvases=canvas_paths, bases=base_paths),
  ```
- `home_sections` call (currently line 274): change `tag_map` to `tag_roots`:
  ```python
    home_extra = pages.home_sections(vault, dates, tag_roots, nav_tools, "index.html", home,
                                     canvases=canvas_paths, bases=base_paths)
  ```
- `page_paths` discovery list (currently lines 435-436): enumerate every node and gate the index on `tag_roots`:
  ```python
        + [urls.tag_output_path(n.path) for n in tags.iter_nodes(tag_roots)]
        + (["_tags/index.html"] if tag_roots else [])
  ```

- [ ] **Step 4: Update the summary count**

In `tools/build.py` (currently line 477), replace `{len(tag_map)} tags` with a node count. Change the two-line print (476-478) to:

```python
    tag_count = sum(1 for _ in tags.iter_nodes(tag_roots))
    print(f"Built {len(vault.notes)} notes{skipped}, {len(vault.assets)} assets, "
          f"{tag_count} tags, {len(tools)} tools, {len(canvases)} canvases, "
          f"{len(bases)} bases, {len(warnings)} warnings -> {out}")
```

(Insert the `tag_count = …` line just before the `print(...)`.)

- [ ] **Step 5: Update the build tests**

In `tests/test_build.py`:

Replace the tag paths in `test_pages_written` (currently line 32) so the list reads:

```python
        for rel in ["index.html", "Home.html", "Projects/Site Plan.html",
                    "Daily/Log.html", "_tags/proj/site.html", "_tags/proj.html",
                    "_tags/fixture.html", "_tags/index.html"]:
```

Replace `test_case_variant_tags_merge_with_warning` (currently lines 384-389) so the merged page path is the nested/leaf form (single-segment `reading` is unchanged here, so this test's path stays `_tags/reading.html` — keep it, just confirm):

```python
    def test_case_variant_tags_merge_with_warning(self):
        out, stdout = self._build({"A.md": "about #Reading", "B.md": "about #reading"})
        page = (out / "_tags/reading.html").read_text(encoding="utf-8")
        self.assertIn("A.html", page)
        self.assertIn("B.html", page)
        self.assertIn("merges with", stdout)
```

Update `test_tag_breadcrumb_is_escaped` (currently lines 391-395) to find the escaped tag page anywhere under `_tags/` recursively (nested dirs now exist):

```python
    def test_tag_breadcrumb_is_escaped(self):
        out, _ = self._build({"A.md": "---\ntags: ['<em>weird</em>']\n---\nbody"})
        tag_page = next(p for p in (out / "_tags").rglob("*.html")
                        if p.name != "index.html")
        html_text = tag_page.read_text(encoding="utf-8")
        self.assertNotIn("<span><em>", html_text)
        self.assertIn("&lt;em&gt;", html_text)
```

Add a new test in `BuildTests` (place it after `test_pages_written`) asserting the synthesized parent aggregates its child's note. The fixture tags `#proj/site` in both `Home.md` and `Projects/Site Plan.md`, so `_tags/proj.html` must list both and show a sub-tags block:

```python
    def test_nested_parent_aggregates_children(self):
        parent = self.read("_tags/proj.html")
        self.assertIn("sub-tags", parent)
        self.assertIn("#proj/site", parent)              # child chip, full path
        # both notes tagged #proj/site surface on the synthesized parent page
        # (hrefs are URL-quoted: "Site Plan.md" -> "Site%20Plan.html")
        self.assertIn("Site%20Plan.html", parent)
        self.assertIn("2 notes", parent)
```

- [ ] **Step 6: Run the full suite to verify it passes**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS — all tests green, including the new tag tests and the updated build tests.

- [ ] **Step 7: Build the fixture/demo vault and confirm no new warnings**

Run: `python tools/build.py`
Expected: exit 0; summary line prints a tag count; no new `WARNING:` lines beyond any pre-existing ones. Confirm `public/_tags/proj/site.html`, `public/_tags/proj.html`, and `public/_tags/index.html` exist.

- [ ] **Step 8: Commit**

```bash
git add tools/build.py tests/test_build.py
git commit -m "Tags: build nested tag pages, drill-path breadcrumbs, top-level clouds"
```

---

## Notes for the implementer

- Run all `python -m unittest …` commands from the repo root (CWD `C:\Users\Matt\Documents\Obsidian - Website`); `tests/__init__.py` puts `tools/` on `sys.path`.
- `VaultCase.make_vault` / `scan_vault` live in `tests/helpers.py`; note titles default to the file basename.
- Do not touch `tools/ssg/obsidian.py`'s inline `#tag` renderer or `pages.note_header` — they already call `urls.tag_output_path`, so they pick up nested URLs and full-path labels for free.
- The homepage and Notes-index clouds intentionally show **top-level tags only**; the full nested vocabulary lives on `_tags/index.html`.
