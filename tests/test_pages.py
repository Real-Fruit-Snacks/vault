import unittest

from ssg import pages
from ssg.config import SiteConfig
from ssg.vault import scan_vault
from tests.helpers import VaultCase


class PageShellTests(VaultCase):
    def test_render_page_relative_assets(self):
        html = pages.render_page(config=SiteConfig(), output_path="a/b/x.html",
                                 page_title="X", content_html="<p>hi</p>",
                                 nav_html="<ul></ul>")
        self.assertIn('data-root="../../"', html)
        self.assertIn('href="../../site-assets/tokens.css"', html)
        self.assertIn('src="../../search-index.js"', html)
        self.assertIn("<p>hi</p>", html)
        self.assertNotIn("mermaid.min.js", html)

    def test_mermaid_included_when_flagged(self):
        html = pages.render_page(config=SiteConfig(), output_path="x.html",
                                 page_title="X", content_html="", nav_html="",
                                 has_mermaid=True)
        self.assertIn('src="site-assets/mermaid.min.js"', html)

    def test_title_includes_site_title(self):
        html = pages.render_page(config=SiteConfig(title="Vault"), output_path="x.html",
                                 page_title="Note", content_html="", nav_html="")
        self.assertIn("<title>Note · Vault</title>", html)

    def test_width_toggle_present(self):
        html = pages.render_page(config=SiteConfig(), output_path="x.html",
                                 page_title="X", content_html="", nav_html="")
        self.assertIn('id="width-toggle"', html)
        self.assertIn('localStorage.getItem("twb-width")==="full"', html)

    def test_nav_colors_toggle_present(self):
        html = pages.render_page(config=SiteConfig(), output_path="x.html",
                                 page_title="X", content_html="", nav_html="")
        self.assertIn('id="nav-colors"', html)
        self.assertIn('localStorage.getItem("twb-nav-colors")==="on"', html)

    def test_rail_collapsed_by_default(self):
        html = pages.render_page(config=SiteConfig(), output_path="x.html",
                                 page_title="X", content_html="", nav_html="")
        self.assertIn('data-rail="collapsed"', html)
        # head script only removes the attribute for an explicit opt-out
        self.assertIn('localStorage.getItem("twb-rail")==="expanded"', html)

    def test_banner_rendering(self):
        def page(**kw):
            return pages.render_page(config=SiteConfig(**kw), output_path="x.html",
                                     page_title="X", content_html="", nav_html="")
        self.assertNotIn("site-banner", page())
        self.assertNotIn("site-banner", page(banner_enabled=True, banner_text="  "))
        self.assertNotIn("site-banner", page(banner_text="hidden"))
        html = page(banner_enabled=True, banner_text="Heads <b>up</b>",
                    banner_style="warn")
        self.assertIn('class="site-banner site-banner-warn"', html)
        self.assertIn("Heads &lt;b&gt;up&lt;/b&gt;", html)
        self.assertNotIn("Heads <b>up</b>", html)
        # the banner precedes the topbar
        self.assertLess(html.find("site-banner"), html.find('class="topbar"'))
        # sticky-offset attribute rides along, and only when the banner shows
        self.assertIn('data-banner="on"', html)
        self.assertNotIn("data-banner", page())
        info = page(banner_enabled=True, banner_text="hi")
        self.assertIn("site-banner-info", info)

    def test_404_has_no_banner(self):
        html = pages.not_found_page(SiteConfig(banner_enabled=True, banner_text="hi"))
        self.assertNotIn("site-banner", html)

    def test_banner_style_is_clamped(self):
        html = pages.render_page(
            config=SiteConfig(banner_enabled=True, banner_text="hi",
                              banner_style='"><script>alert(1)</script>'),
            output_path="x.html", page_title="X", content_html="", nav_html="")
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn('class="site-banner site-banner-info"', html)

    def test_pet_emitted_only_when_enabled(self):
        off = pages.render_page(config=SiteConfig(), output_path="x.html",
                                page_title="X", content_html="", nav_html="")
        self.assertNotIn("site-pet", off)
        self.assertNotIn("pet.js", off)
        on = pages.render_page(config=SiteConfig(pet_enabled=True),
                               output_path="a/b/x.html", page_title="X",
                               content_html="", nav_html="")
        self.assertIn('id="site-pet"', on)
        self.assertIn('aria-hidden="true"', on)
        self.assertIn('src="../../site-assets/pet.js"', on)
        self.assertIn("pet-sprite", on)
        self.assertIn("pet-eyes-open", on)

    def test_404_has_no_pet(self):
        html = pages.not_found_page(SiteConfig(pet_enabled=True))
        self.assertNotIn("site-pet", html)

    def test_head_meta_and_polish(self):
        html = pages.render_page(config=SiteConfig(title="V"), output_path="a/b/x.html",
                                 page_title="X", content_html="", nav_html="",
                                 description="Hello world")
        self.assertIn('<meta name="description" content="Hello world">', html)
        self.assertIn('<meta property="og:title" content="X">', html)
        self.assertIn('<meta property="og:description" content="Hello world">', html)
        self.assertIn('<meta name="twitter:card" content="summary">', html)
        self.assertIn('name="theme-color"', html)
        self.assertIn('class="skip-link"', html)
        self.assertIn('<main class="content" id="main">', html)
        self.assertIn('rel="apple-touch-icon"', html)
        self.assertIn('rel="manifest"', html)
        self.assertIn('type="application/atom+xml"', html)
        self.assertIn('aria-live="polite"', html)
        # without site_url there are no absolute canonical/og:url tags
        self.assertNotIn('rel="canonical"', html)
        self.assertNotIn("og:url", html)

    def test_head_meta_absolute_when_site_url(self):
        html = pages.render_page(config=SiteConfig(site_url="https://ex.test/v/"),
                                 output_path="a/x.html", page_title="X",
                                 content_html="", nav_html="", description="d")
        self.assertIn('<link rel="canonical" href="https://ex.test/v/a/x.html">', html)
        self.assertIn('<meta property="og:url" content="https://ex.test/v/a/x.html">', html)
        self.assertIn('property="og:image"', html)

    def test_description_falls_back_to_config(self):
        html = pages.render_page(config=SiteConfig(description="Site tagline"),
                                 output_path="x.html", page_title="X",
                                 content_html="", nav_html="")
        self.assertIn('content="Site tagline"', html)

    def test_settings_menu_holds_toggles(self):
        html = pages.render_page(config=SiteConfig(pet_enabled=True), output_path="x.html",
                                 page_title="X", content_html="", nav_html="")
        self.assertIn('id="settings-toggle"', html)
        self.assertIn('id="settings-menu"', html)
        menu = html[html.find('id="settings-menu"'):]
        for cid in ['id="theme-toggle"', 'id="accent-color"', 'id="nav-colors"',
                    'id="width-toggle"', 'id="rail-toggle"', 'id="progress-toggle"',
                    'id="text-size"', 'id="pet-toggle"', 'id="crt-toggle"']:
            self.assertIn(cid, menu)
        # the reading-progress bar is opt-in: gated on data-progress
        self.assertIn('localStorage.getItem("twb-progress")==="on"', html)
        # text size + accent are pre-painted from storage
        self.assertIn('twb-textsize', html)
        self.assertIn('data-accent', html)
        # folder colors moved out of the sidebar's nav-controls
        self.assertNotIn(">colors</button>", html)

    def test_command_palette_and_extras_chrome(self):
        html = pages.render_page(config=SiteConfig(), output_path="x.html",
                                 page_title="X", content_html="", nav_html="")
        self.assertIn('id="cmd-toggle"', html)
        self.assertIn('id="random-note"', html)
        self.assertIn('id="crt-toggle"', html)
        self.assertIn("site-assets/palette.js", html)
        self.assertIn("site-assets/boot.js", html)
        # pre-paint applies stored CRT mode and arms the one-time boot splash
        self.assertIn('localStorage.getItem("twb-crt")==="on"', html)
        self.assertIn('data-boot', html)

    def test_build_note_nav(self):
        nav = pages.build_note_nav(("Alpha", "Alpha.md"), ("Zeta", "sub/Zeta.md"), "index.html")
        self.assertIn('class="note-nav"', nav)
        self.assertIn('href="Alpha.html"', nav)
        self.assertIn('href="sub/Zeta.html"', nav)
        self.assertIn("Alpha", nav)
        self.assertIn("Zeta", nav)
        self.assertEqual(pages.build_note_nav(None, None, "x.html"), "")
        self.assertIn("note-nav-gap", pages.build_note_nav(None, ("Z", "Z.md"), "x.html"))

    def test_pet_toggle_tracks_pet_enabled(self):
        off = pages.render_page(config=SiteConfig(), output_path="x.html",
                                page_title="X", content_html="", nav_html="")
        self.assertNotIn("pet-toggle", off)
        on = pages.render_page(config=SiteConfig(pet_enabled=True),
                               output_path="x.html", page_title="X",
                               content_html="", nav_html="")
        self.assertIn('id="pet-toggle"', on)
        # Float (roam) is the default: any stored value other than "cursor" or
        # "off" (including an absent key) resolves to roaming before paint.
        self.assertIn('if(pm!=="cursor")', on)
        self.assertIn('pm==="off"?"off":"float"', on)


class NavTests(VaultCase):
    def test_tree_structure_active_and_open(self):
        vault = scan_vault(self.make_vault({
            "Home.md": "x", "Projects/Plan.md": "y", "Projects/Sub/Deep.md": "z",
        }), SiteConfig())
        nav = pages.build_nav(vault, "Projects/Plan.md", "Projects/Plan.html")
        self.assertIn("<details open><summary>Projects</summary>", nav)
        self.assertIn('class="active"', nav)
        self.assertIn('href="../Home.html"', nav)
        self.assertIn('href="Plan.html"', nav)

    def test_folder_colors_stable_and_top_level_only(self):
        # Pinned literals: a folder's color index must never drift between
        # builds or Python versions (that is the whole point of the hash).
        self.assertEqual(pages.folder_color("Reference"), 3)
        self.assertEqual(pages.folder_color("Library"), 5)
        self.assertEqual(pages.folder_color("reference"), 3)  # case-insensitive
        vault = scan_vault(self.make_vault({
            "Projects/Plan.md": "y", "Projects/Sub/Deep.md": "z",
        }), SiteConfig())
        nav = pages.build_nav(vault, "", "index.html")
        self.assertIn(f'<li data-color="{pages.folder_color("Projects")}">', nav)
        # nested folders carry no index of their own; they inherit the branch
        self.assertEqual(nav.count("data-color"), 1)


class ChromeTests(VaultCase):
    def test_breadcrumbs(self):
        crumbs = pages.build_breadcrumbs("a/b/My Note.md")
        self.assertEqual(crumbs.count('crumb-sep'), 2)
        self.assertIn("<span>My Note</span>", crumbs)

    def test_toc(self):
        toc = pages.build_toc([(1, "One", "one"), (2, "Two", "two"), (4, "Deep", "deep")])
        self.assertIn('href="#one"', toc)
        self.assertIn('class="toc-l1"', toc)
        self.assertIn('class="toc-l2"', toc)
        self.assertIn('class="toc-l4"', toc)
        self.assertIn("Deep", toc)

    def test_toc_indents_relative_to_shallowest_heading(self):
        toc = pages.build_toc([(2, "Top", "top"), (3, "Sub", "sub"), (6, "Tiny", "tiny")])
        self.assertIn('class="toc-l1"', toc)
        self.assertIn('class="toc-l2"', toc)
        self.assertIn('class="toc-l5"', toc)
        self.assertNotIn('class="toc-l3"', toc)

    def test_toc_empty_for_single_heading(self):
        self.assertEqual(pages.build_toc([(1, "One", "one")]), "")

    def test_backlinks_panel(self):
        vault = scan_vault(self.make_vault({"A.md": "x", "B.md": "y"}), SiteConfig())
        panel = pages.build_backlinks_panel("A.md", {"A.md": ["B.md"]}, vault, "A.html")
        self.assertIn("Linked mentions (1)", panel)
        self.assertIn('href="B.html"', panel)
        self.assertEqual(pages.build_backlinks_panel("B.md", {}, vault, "B.html"), "")

    def test_note_header_has_tag_chips(self):
        vault = scan_vault(self.make_vault({"A.md": "---\ntags: [alpha]\n---\nx"}), SiteConfig())
        header = pages.note_header(vault.notes["A.md"], "A.html")
        self.assertIn("<h1>A</h1>", header)
        self.assertIn('href="_tags/alpha.html"', header)

    def test_note_header_shows_updated_date(self):
        vault = scan_vault(self.make_vault({"A.md": "x"}), SiteConfig())
        header = pages.note_header(vault.notes["A.md"], "A.html", "2026-07-05")
        self.assertIn("note-updated", header)
        self.assertIn("updated 2026-07-05", header)
        self.assertNotIn("note-updated", pages.note_header(vault.notes["A.md"], "A.html"))

    def test_tag_page_and_index(self):
        vault = scan_vault(self.make_vault({"A.md": "#alpha", "B.md": "#alpha"}), SiteConfig())
        content = pages.tag_page_content("alpha", {"A.md", "B.md"}, vault, "_tags/alpha.html")
        self.assertIn('href="../A.html"', content)
        index = pages.tags_index_content({"alpha": {"A.md", "B.md"}}, "_tags/index.html")
        self.assertIn("#alpha", index)

    def test_auto_index(self):
        vault = scan_vault(self.make_vault({"Zed.md": "x", "sub/Alpha.md": "y"}), SiteConfig())
        content = pages.auto_index_content(vault, "index.html")
        self.assertIn('href="sub/Alpha.html"', content)
        self.assertIn('href="Zed.html"', content)


if __name__ == "__main__":
    unittest.main()
