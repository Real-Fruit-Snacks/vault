import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import build

FIXTURE = Path(__file__).resolve().parent / "fixture-vault"


class BuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls._tmp.name) / "public"
        cls.rc = build.main(["--vault", str(FIXTURE), "--out", str(cls.out)])

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def read(self, rel):
        return (self.out / rel).read_text(encoding="utf-8")

    def test_exit_code(self):
        self.assertEqual(self.rc, 0)

    def test_pages_written(self):
        for rel in ["index.html", "Home.html", "Projects/Site Plan.html",
                    "Daily/Log.html", "_tags/proj-site.html", "_tags/fixture.html",
                    "_tags/index.html"]:
            self.assertTrue((self.out / rel).is_file(), rel)

    def test_static_and_assets_copied(self):
        self.assertTrue((self.out / "site-assets/tokens.css").is_file())
        self.assertTrue((self.out / "site-assets/app.js").is_file())
        self.assertTrue((self.out / "Attachments/diagram.png").is_file())
        self.assertTrue((self.out / ".nojekyll").is_file())

    def test_homepage_is_home_note(self):
        html = self.read("index.html")
        self.assertIn("Fixture Home", html)
        self.assertIn('class="mermaid"', html)
        self.assertIn("mermaid.min.js", html)

    def test_homepage_sections(self):
        html = self.read("index.html")
        self.assertIn('class="home-sections"', html)
        # fixture notes are committed, so git dates exist for the recent list
        self.assertIn(">recently updated</span>", html)
        self.assertIn('class="home-recent"', html)
        self.assertIn('href="_tags/index.html">tags</a>', html)
        self.assertIn('href="tools/index.html">tools</a>', html)
        self.assertIn('class="home-tools"', html)
        self.assertIn('href="tools/char-analyzer.html"', html)
        # sections belong to the homepage only, not the note's own page
        self.assertNotIn('class="home-sections"', self.read("Home.html"))

    def test_backlinks_present(self):
        html = self.read("Projects/Site Plan.html")
        self.assertIn("Linked mentions", html)
        self.assertIn('code-block', html)

    def test_broken_link_rendered(self):
        self.assertIn("broken-link", self.read("Daily/Log.html"))

    def test_search_index(self):
        js = self.read("search-index.js")
        self.assertTrue(js.startswith("window.TWB_SEARCH_INDEX="))
        self.assertIn("Site Plan", js)
        # the boot splash reads this exact note count (fixture has 6 published)
        self.assertIn("window.TWB_NOTE_COUNT=6;", js)

    def test_search_index_includes_typed_tool_entries(self):
        js = self.read("search-index.js")
        array_line = js.splitlines()[0]  # note count trails on its own line
        entries = json.loads(array_line[len("window.TWB_SEARCH_INDEX="):].rstrip(";"))
        self.assertEqual({e["type"] for e in entries}, {"note", "tool"})
        ids = [e["id"] for e in entries]
        self.assertEqual(ids, list(range(len(entries))), "ids must stay unique")
        tools = {e["url"]: e for e in entries if e["type"] == "tool"}
        self.assertIn("tools/char-analyzer.html", tools)
        for e in tools.values():
            self.assertTrue(e["title"].strip())
            self.assertTrue(e["text"].strip(), f'{e["url"]} has no search text')
            # Entities like &lt;ca&gt; legitimately unescape to prose "<ca>",
            # so look for real leftover markup rather than any "<".
            self.assertNotRegex(e["text"], r"<(div|span|table|figure|a href)\b",
                                f'{e["url"]} text contains markup')

    def test_tool_pages_written(self):
        for rel in ["tools/index.html", "tools/char-analyzer.html",
                    "tools/char-analyzer/tool.js", "tools/char-analyzer/tool.css",
                    "tools/cron-parser.html", "tools/cron-parser/tool.js",
                    "tools/cron-parser/tool.css",
                    "tools/schtasks-builder.html", "tools/schtasks-builder/tool.js",
                    "tools/schtasks-builder/tool.css",
                    "tools/ip-cidr.html", "tools/ip-cidr/tool.js",
                    "tools/ip-cidr/tool.css",
                    "tools/timestamp.html", "tools/timestamp/tool.js",
                    "tools/text-codec.html", "tools/text-codec/tool.js",
                    "tools/chmod.html", "tools/chmod/tool.js",
                    "tools/ports.html", "tools/ports/tool.js",
                    "tools/char-analyzer/md5.js",
                    "tools/ovpn-inspector.html", "tools/ovpn-inspector/tool.js",
                    "tools/ovpn-inspector/x509.js",
                    "tools/windows-events.html", "tools/windows-events/tool.js",
                    "tools/windows-events/events.js", "tools/windows-events/tool.css"]:
            self.assertTrue((self.out / rel).is_file(), rel)
        we_page = self.read("tools/windows-events.html")
        self.assertIn("<h1>Windows Event ID Reference</h1>", we_page)
        self.assertIn('id="we-input"', we_page)
        self.assertIn('src="windows-events/events.js"', we_page)
        ip_page = self.read("tools/ip-cidr.html")
        self.assertIn("<h1>IP / CIDR Calculator</h1>", ip_page)
        self.assertIn('id="ip-input"', ip_page)
        st_page = self.read("tools/schtasks-builder.html")
        self.assertIn("<h1>Windows Task Builder</h1>", st_page)
        self.assertIn('id="st-output"', st_page)

    def test_tool_pages_have_learn_sections(self):
        for rel in ["tools/char-analyzer.html", "tools/cron-parser.html",
                    "tools/schtasks-builder.html", "tools/ip-cidr.html",
                    "tools/timestamp.html", "tools/text-codec.html",
                    "tools/chmod.html", "tools/ports.html",
                    "tools/ovpn-inspector.html", "tools/windows-events.html"]:
            self.assertIn('<details class="tool-learn">', self.read(rel), rel)
        cron_page = self.read("tools/cron-parser.html")
        self.assertIn("<h1>Cron Parser</h1>", cron_page)
        self.assertIn('id="cp-input"', cron_page)
        page = self.read("tools/char-analyzer.html")
        self.assertIn("<h1>Character Analyzer</h1>", page)
        self.assertIn('id="ca-input"', page)
        self.assertIn('id="ca-view"', page)
        self.assertIn('src="char-analyzer/tool.js"', page)

    def test_sidebar_has_tools_group(self):
        html = self.read("Home.html")
        self.assertIn('class="nav-tools"', html)
        self.assertIn("Character Analyzer", html)
        self.assertIn('href="tools/index.html"', html)

    def test_sidebar_has_notes_header(self):
        html = self.read("Home.html")
        self.assertIn('class="nav-notes"', html)
        self.assertIn('href="notes.html">notes</a>', html)
        sub = self.read("Daily/Log.html")
        self.assertIn('href="../notes.html">notes</a>', sub)

    def test_notes_index_page(self):
        html = self.read("notes.html")
        self.assertIn("<h1>Notes</h1>", html)
        self.assertIn(">Daily</span>", html)
        self.assertIn(">Projects</span>", html)
        self.assertIn('href="Projects/Site%20Plan.html"', html)
        self.assertIn('href="_tags/index.html">tags</a>', html)
        self.assertIn('class="tag"', html)
        # the home note is reachable via the site title, not listed here
        self.assertNotIn('href="Home.html"', html)

    def test_all_links_relative_and_offline(self):
        for page in self.out.rglob("*.html"):
            if page.name == "404.html":
                continue  # 404 page intentionally uses absolute links for self-containment
            html = page.read_text(encoding="utf-8")
            self.assertNotIn('href="/', html, page)
            self.assertNotIn('src="/', html, page)
            self.assertNotIn('src="http', html, page)
            self.assertNotIn('<link rel="stylesheet" href="http', html, page)

    def test_graph_index_emitted(self):
        js = self.read("graph-index.js")
        self.assertTrue(js.startswith("window.TWB_GRAPH="))
        payload = json.loads(js[len("window.TWB_GRAPH="):-1])
        nodes = [n["url"] for n in payload["nodes"]]
        self.assertEqual(nodes,
                         ["Daily/Log.html", "Home.html", "Library/Book A.html",
                          "Library/Book B.html", "Library/Shelf.html",
                          "Projects/Site Plan.html"])
        home_i, log_i, plan_i = nodes.index("Home.html"), nodes.index("Daily/Log.html"), \
            nodes.index("Projects/Site Plan.html")
        self.assertIn(sorted((home_i, log_i)), [sorted(e) for e in payload["edges"]])
        self.assertIn(sorted((home_i, plan_i)), [sorted(e) for e in payload["edges"]])
        self.assertIn(sorted((log_i, plan_i)), [sorted(e) for e in payload["edges"]])

    def test_note_pages_stamped_with_data_note(self):
        self.assertIn('data-note="Home.html"', self.read("Home.html"))
        self.assertIn('data-note="Home.html"', self.read("index.html"))
        self.assertIn('data-note="Daily/Log.html"', self.read("Daily/Log.html"))
        self.assertNotIn("data-note", self.read("_tags/index.html"))
        self.assertNotIn("data-note", self.read("tools/index.html"))

    def test_graph_page_and_topbar_link(self):
        html = self.read("graph.html")
        self.assertIn('id="graph-view"', html)
        self.assertIn('class="note note-full"', html)
        self.assertNotIn("data-note", html)
        home = self.read("Home.html")
        self.assertIn('class="graph-link"', home)
        self.assertIn('href="graph.html"', home)
        self.assertIn('src="site-assets/graph.js"', home)
        self.assertIn('src="graph-index.js"', home)
        sub = self.read("Daily/Log.html")
        self.assertIn('href="../graph.html"', sub)
        self.assertIn('src="../site-assets/graph.js"', sub)

    def test_search_index_has_heading_slugs(self):
        js = self.read("search-index.js")
        self.assertIn('"hs": [["Overview", "overview"], ["Details", "details"]]', js)

    def test_favicon_shipped_and_linked(self):
        self.assertTrue((self.out / "site-assets/favicon.svg").is_file())
        self.assertTrue((self.out / "site-assets/favicon.png").is_file())
        home = self.read("Home.html")
        self.assertIn('href="site-assets/favicon.svg"', home)
        self.assertIn('href="site-assets/favicon.png"', home)
        sub = self.read("Daily/Log.html")
        self.assertIn('href="../site-assets/favicon.svg"', sub)

    def test_404_page_emitted_and_self_contained(self):
        html = self.read("404.html")
        self.assertIn("This page doesn't exist.", html)
        self.assertIn('href="/"', html)
        self.assertNotIn("site-assets/", html)
        self.assertNotIn("<script defer", html)
        self.assertNotIn('src="', html)

    def test_headings_have_anchor_links(self):
        html = self.read("Projects/Site Plan.html")
        self.assertIn('<a class="h-anchor" href="#details"', html)

    def test_canvas_page_written(self):
        html = self.read("Boards/Fixture Board.html")
        self.assertIn('id="canvas-view"', html)
        self.assertIn("canvas-group-label", html)
        self.assertIn('class="canvas-edges"', html)
        self.assertIn("not published", html)
        self.assertNotIn("hidden fixture content", html)
        self.assertIn('src="../site-assets/canvas.js"', html)
        # breadcrumb strips the .canvas extension like every other surface
        self.assertIn("<span>Fixture Board</span>", html)
        self.assertNotIn("Fixture Board.canvas</span>", html)

    def test_canvas_in_nav_notes_screen_and_search(self):
        home = self.read("Home.html")
        self.assertIn('data-kind="canvas"', home)
        self.assertIn('href="Boards/Fixture%20Board.html"', home)
        notes = self.read("notes.html")
        self.assertIn(">Boards</span>", notes)
        search = self.read("search-index.js")
        self.assertIn("Fixture board", search)

    def test_canvas_asset_shipped(self):
        self.assertTrue((self.out / "site-assets" / "canvas.js").is_file())

    def test_base_page_written(self):
        html = self.read("Bases/Fixture Base.html")
        self.assertIn('class="base-table"', html)
        self.assertIn("<th>Status</th>", html)
        self.assertIn('class="base-tabs"', html)
        self.assertIn('class="base-cards"', html)
        self.assertIn("<span>Fixture Base</span>", html)  # breadcrumb, extension stripped
        # sorted DESC by rating: Book B row before Book A row within the
        # table view itself (the sidebar nav also links both notes, always
        # alphabetically, so scope the search to the table markup).
        table = html[html.find('class="base-table"'):html.find("</table>")]
        self.assertLess(table.find("Book%20B.html"), table.find("Book%20A.html"))

    def test_base_in_nav_notes_screen_and_search(self):
        home = self.read("Home.html")
        self.assertIn('data-kind="base"', home)
        self.assertIn('href="Bases/Fixture%20Base.html"', home)
        notes = self.read("notes.html")
        self.assertIn(">Bases</span>", notes)
        search = self.read("search-index.js")
        self.assertIn("Fixture Base", search)

    def test_base_embedded_in_note(self):
        html = self.read("Library/Shelf.html")
        self.assertIn('class="base-embed"', html)
        self.assertIn('class="base-table"', html)
        self.assertIn('href="../Bases/Fixture%20Base.html"', html)
        self.assertNotIn("base-tabs", html)

    def test_bases_asset_shipped(self):
        self.assertTrue((self.out / "site-assets" / "bases.js").is_file())

    def test_config_title_and_banner_applied(self):
        html = self.read("Home.html")
        self.assertIn("<title>Fixture Home · Fixture Vault</title>", html)
        self.assertIn('class="site-banner site-banner-warn"', html)
        self.assertIn("Fixture banner text", html)
        # config file itself is never published
        self.assertFalse((self.out / "site.config.json").exists())
        # 404 stays self-contained, banner-free
        self.assertNotIn("site-banner", self.read("404.html"))

    def test_pet_on_built_pages(self):
        html = self.read("Home.html")
        self.assertIn('id="site-pet"', html)
        self.assertIn("site-assets/pet.js", html)
        self.assertTrue((self.out / "site-assets" / "pet.js").is_file())
        self.assertNotIn("site-pet", self.read("404.html"))

    def test_palette_boot_shipped_and_wired(self):
        self.assertTrue((self.out / "site-assets" / "palette.js").is_file())
        self.assertTrue((self.out / "site-assets" / "boot.js").is_file())
        home = self.read("Home.html")
        self.assertIn('id="cmd-toggle"', home)
        self.assertIn('id="crt-toggle"', home)
        self.assertIn('id="random-note"', home)
        self.assertIn("site-assets/palette.js", home)
        sub = self.read("Daily/Log.html")
        self.assertIn("../site-assets/palette.js", sub)

    def test_discovery_files_emitted(self):
        for rel in ["robots.txt", "site.webmanifest", "sitemap.xml", "feed.xml"]:
            self.assertTrue((self.out / rel).is_file(), rel)
        robots = self.read("robots.txt")
        self.assertIn("User-agent: *", robots)
        self.assertIn("Allow: /", robots)
        # fixture has no site_url, so no absolute sitemap reference
        self.assertNotIn("Sitemap:", robots)
        manifest = json.loads(self.read("site.webmanifest"))
        self.assertEqual(manifest["name"], "Fixture Vault")
        self.assertEqual(manifest["theme_color"], "#090c0d")
        self.assertTrue(any(i["src"].endswith("favicon.png") for i in manifest["icons"]))

    def test_sitemap_lists_pages(self):
        xml = self.read("sitemap.xml")
        self.assertIn("<urlset", xml)
        self.assertIn("<loc>/index.html</loc>", xml)      # root-relative w/o site_url
        self.assertIn("<loc>/Home.html</loc>", xml)
        self.assertIn("<loc>/notes.html</loc>", xml)
        self.assertIn("<lastmod>", xml)                    # committed notes have git dates

    def test_feed_is_atom_with_entries(self):
        xml = self.read("feed.xml")
        self.assertIn('<feed xmlns="http://www.w3.org/2005/Atom">', xml)
        self.assertIn("<entry>", xml)
        self.assertIn("<updated>", xml)

    def test_note_prev_next_nav(self):
        # Daily/Log is first in the reading order: a "next" link, no "previous".
        log = self.read("Daily/Log.html")
        self.assertIn('class="note-nav"', log)
        self.assertIn("note-nav-gap", log)
        self.assertIn("note-nav-next", log)
        # the home note is out of the chain, so index.html has no prev/next
        self.assertNotIn('class="note-nav"', self.read("index.html"))

    def test_head_metadata_on_pages(self):
        html = self.read("Home.html")
        self.assertIn('name="description"', html)
        self.assertIn('property="og:title"', html)
        self.assertIn('name="theme-color"', html)
        self.assertIn('class="skip-link"', html)
        self.assertIn('rel="manifest"', html)
        self.assertIn('type="application/atom+xml"', html)
        self.assertIn('aria-live="polite"', html)

class TagHandlingTests(unittest.TestCase):
    def _build(self, files):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name) / "vault"
        root.mkdir()
        for rel, content in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        out = Path(tmp.name) / "public"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = build.main(["--vault", str(root), "--out", str(out)])
        self.assertEqual(rc, 0)
        return out, buf.getvalue()

    def test_case_variant_tags_merge_with_warning(self):
        out, stdout = self._build({"A.md": "about #Reading", "B.md": "about #reading"})
        page = (out / "_tags/reading.html").read_text(encoding="utf-8")
        self.assertIn("A.html", page)
        self.assertIn("B.html", page)
        self.assertIn("merges with", stdout)

    def test_tag_breadcrumb_is_escaped(self):
        out, _ = self._build({"A.md": "---\ntags: ['<em>weird</em>']\n---\nbody"})
        tag_page = next(p for p in (out / "_tags").glob("*.html") if p.name != "index.html")
        html_text = tag_page.read_text(encoding="utf-8")
        self.assertNotIn("<span><em>", html_text)

    def test_graph_page_collision_warns(self):
        out, stdout = self._build({"graph.md": "hello", "A.md": "x"})
        self.assertIn("overwritten by the graph view", stdout)

    def test_404_page_collision_warns(self):
        out, stdout = self._build({"404.md": "x", "A.md": "y"})
        self.assertIn("overwritten by the 404 page", stdout)

    def test_build_outside_a_git_repo_has_no_dates(self):
        out, _ = self._build({"A.md": "hello"})
        html = (out / "A.html").read_text(encoding="utf-8")
        self.assertNotIn("note-updated", html)

    def test_404_uses_configured_site_url(self):
        out, _ = self._build({
            "A.md": "hello",
            "site.config.json": '{"site_url": "https://example.test/vault/"}',
        })
        html = (out / "404.html").read_text(encoding="utf-8")
        self.assertIn('href="https://example.test/vault/"', html)

    def test_site_url_makes_urls_absolute(self):
        out, _ = self._build({
            "A.md": "hello",
            "site.config.json": '{"site_url": "https://example.test/vault/"}',
        })
        sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("<loc>https://example.test/vault/A.html</loc>", sitemap)
        robots = (out / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Sitemap: https://example.test/vault/sitemap.xml", robots)
        feed = (out / "feed.xml").read_text(encoding="utf-8")
        self.assertIn('<link rel="self" href="https://example.test/vault/feed.xml"/>', feed)
        page = (out / "A.html").read_text(encoding="utf-8")
        self.assertIn('rel="canonical" href="https://example.test/vault/A.html"', page)

    def test_missing_vault_dir_errors_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = build.main(["--vault", str(Path(tmp) / "no-such-vault"),
                                 "--out", str(Path(tmp) / "public")])
        self.assertEqual(rc, 1)
        self.assertIn("vault directory not found", buf.getvalue())

    def test_tool_page_collision_warns(self):
        _, stdout = self._build({"tools/char-analyzer.md": "shadow", "A.md": "x"})
        self.assertIn("overwritten by a tool page", stdout)

    def test_unpublished_note_absent_everywhere(self):
        out, stdout = self._build({
            "A.md": "---\npublish: false\n---\nSecretContent links [[B]]",
            "B.md": "links to [[A]]",
        })
        self.assertFalse((out / "A.html").exists())
        self.assertIn("(1 unpublished)", stdout)
        search = (out / "search-index.js").read_text(encoding="utf-8")
        self.assertNotIn("SecretContent", search)
        graph = (out / "graph-index.js").read_text(encoding="utf-8")
        self.assertNotIn("A.html", graph)
        b_page = (out / "B.html").read_text(encoding="utf-8")
        self.assertIn("broken-link", b_page)
        self.assertNotIn('href="A.html"', b_page)


if __name__ == "__main__":
    unittest.main()
