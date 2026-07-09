# Vault

Publish an Obsidian vault as a fast static website.

The vault lives in `Notes/`. Every Markdown file inside it becomes a page,
unless its frontmatter says `publish: false` or it sits in a top-level folder
whose name starts with `_` (e.g. `_drafts/`), which is treated as private and
never published. Wikilinks, embeds, callouts,
task lists, Mermaid diagrams, tags, backlinks, and client-side search all
work. Obsidian canvases (`.canvas`) publish as read-only pan-and-zoom pages,
and Obsidian bases (`.base`) publish as build-time table, card, and list views with formulas, filters, grouping, and summaries.

The site ships with an optional toolbox of utilities (encoders, calculators,
reference tables, command builders) under `Tools`.

## Requirements

Python 3.9 or newer. Everything the build needs is included in the repository.

## Build

    python tools/build.py

The output is written to `public/`. Serve it with any static file server, for
example:

    python -m http.server -d public

or open `public/index.html` directly. Every link in the output is relative.

## Test

    python -m unittest discover -s tests -t . -v

## Configuration

All settings live in `Notes/site.config.json`. Every key is optional.

| Key | Default | Effect |
| --- | --- | --- |
| `title` | `Real-Fruit-Snacks` | Site name in the top bar and page titles |
| `homepage` | `Home.md` | Note rendered at `index.html` |
| `site_url` | *(empty)* | Absolute site URL; enables canonical and Open Graph URLs and absolute links in `sitemap.xml` and `feed.xml` |
| `description` | *(empty)* | Fallback meta description and Open Graph summary |
| `exclude` | `[]` | Vault paths to skip when publishing |
| `asset_extensions` | images, pdf, audio, video, zip | Extra file types to copy through |
| `banner_enabled` | `false` | Show a site-wide announcement banner |
| `banner_text` | *(empty)* | Banner message (plain text) |
| `banner_style` | `info` | `info` for an accent strip, `warn` for an amber strip |
| `pet_enabled` | `false` | Enable the optional cursor companion (off by default in the reader) |

When `pet_enabled` is on, readers get a small ghost companion that follows the
cursor or roams the page. It has its own management panel under the settings
cog's Pet row, with controls for mode (Roam, Cursor, or Off), size, opacity,
color, and per-quirk toggles for napping, fleeing, read-along, tricks, and
speech. The ghost can also be dragged to reposition it, and flung with a
throw in Roam mode.

Keys beginning with `_` are ignored and can be used as inline comments.

Each build also emits `robots.txt`, `site.webmanifest`, `sitemap.xml`, and an
Atom `feed.xml` (the most recently updated pages). Set `site_url` so the
sitemap and feed carry absolute URLs; without it they fall back to
root-relative paths.

Readers can adjust the theme, accent color, text size, and other preferences
from the settings menu in the top bar, or from the command palette
(`Ctrl`/`Cmd` + `K`).

## Hosting

### GitHub Pages

Push to `main` and enable Pages under Settings, Pages, Source: GitHub Actions.
The workflow in `.github/workflows/pages.yml` runs the tests, builds the site,
and deploys `public/` on every push.

### GitLab Pages

`.gitlab-ci.yml` builds and publishes `public/` on `main`. Set the
`BUILD_IMAGE` CI/CD variable to any Python 3.9+ image if you need to override
the default.

### Any static host

Run `python tools/build.py` and serve the resulting `public/` directory with
any static file server.

## Layout

| Path | Purpose |
| --- | --- |
| `Notes/` | The vault. Every Markdown file inside is published (opt out per note with `publish: false`) |
| `Notes/.obsidian/` | Obsidian configuration (dot-folders are never published) |
| `Notes/site.config.json` | Site configuration |
| `tools/` | Build system |
| `site-assets/` | Theme CSS, fonts, Mermaid, MiniSearch |
| `site-tools/` | Standalone tool pages, published under `Tools` |
| `tests/` | Unit and integration tests |
| `public/` | Build output (git-ignored) |

## License

MIT. See `LICENSE`. Bundled third-party components keep their own licenses:
markdown-it-py, mdurl, mdit-py-plugins, Pygments, and PyYAML in `tools/vendor/`;
Mermaid and MiniSearch in `site-assets/`; JetBrains Mono and Inter in
`site-assets/fonts/`.
