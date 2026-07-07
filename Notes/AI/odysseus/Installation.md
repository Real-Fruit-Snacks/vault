---
tags:
  - AI
  - odysseus
---
## Github Page

> [!Resources]
> - [odysseus Github](https://web.archive.org/web/20260628180455/https://github.com/pewdiepie-archdaemon/odysseus)
## Quick Start

> `dev` is the default branch and gets the newest changes first. Use [`main`](https://web.archive.org/web/20260628180521/https://github.com/pewdiepie-archdaemon/odysseus/tree/main) if you want the more curated branch.

```shell
git clone https://web.archive.org/web/20260628180635/https://github.com/pewdiepie-archdaemon/odysseus
cd odysseus
cp .env.example .env
docker compose up -d --build
```

Open `http://localhost:7000` when the containers are healthy. The first admin password is printed in `docker compose logs odysseus`.

Native installs, GPU notes, Windows/macOS instructions, HTTPS, and configuration live in the [setup guide](https://web.archive.org/web/20260628180738/https://github.com/pewdiepie-archdaemon/odysseus/blob/dev/docs/setup.md).
## Features
- **Chat + Agents** — local/API models, tools, MCP, files, shell, skills, and memory.
- **Cookbook** — hardware-aware model recommendations, downloads, and serving.
- **Deep Research** — multi-step web research with source reading and report generation.
- **Compare** — blind side-by-side model testing and synthesis.
- **Documents** — writing-first editor with AI edits, suggestions, Markdown, HTML, CSV, and syntax highlighting.
- **Email** — IMAP/SMTP inbox with triage, tags, summaries, reminders, and reply drafts.
- **Notes, Tasks + Calendar** — reminders, todos, scheduled agent tasks, and CalDAV sync.
- **Extras** — gallery/image editor, themes, uploads, web search, presets, sessions, and 2FA.