"""Resolve each note's "last updated" time.

The site orders and labels notes by when they were last updated. Git commit
dates are the reliable fallback (they survive a fresh CI checkout, unlike file
mtimes), but they only change when you commit and are day-granular — batch
commits collapse many distinct edits onto one timestamp. So a note may instead
declare its own `updated:` (or `modified:`/`date:`) frontmatter field, which an
Obsidian plugin can keep current; that wins over the git date when present.
"""
from __future__ import annotations

import datetime
import re

# First recognized field wins. `date` is last: it is often a creation date.
_FIELDS = ("updated", "modified", "last_modified", "lastmod", "date")

# YYYY-MM-DD, optionally followed by a time (T or space separated).
_ISO_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?")


def _from_frontmatter(fm: dict):
    """Return a normalized ``YYYY-MM-DDTHH:MM:SS`` string from the first
    recognized date field, or ``None``. Accepts the date/datetime objects PyYAML
    produces as well as plain strings; unrecognized values fall through."""
    for key in _FIELDS:
        if key not in fm:
            continue
        val = fm[key]
        if isinstance(val, datetime.datetime):
            return val.strftime("%Y-%m-%dT%H:%M:%S")
        if isinstance(val, datetime.date):  # datetime is a subclass, checked first
            return val.strftime("%Y-%m-%dT00:00:00")
        if isinstance(val, str):
            m = _ISO_RE.match(val.strip())
            if m:
                d, hh, mm, ss = m.group(1), m.group(2), m.group(3), m.group(4)
                return f"{d}T{hh or '00'}:{mm or '00'}:{ss or '00'}"
    return None


def resolve(vault, git_dates: dict):
    """Compute display dates and sort keys for every dated path.

    Returns ``(display, order)``:

    - ``display[path]`` = ``YYYY-MM-DD`` — a note's frontmatter date if it has
      one, else the git commit date. Shown in note headers, the homepage,
      the feed, and the sitemap.
    - ``order[path]`` = ``YYYY-MM-DDTHH:MM:SS`` — the frontmatter timestamp if
      present, else the git date at midnight. Used only for sorting, so
      same-day notes with a finer frontmatter time order correctly.

    Paths with no known date (not committed and no frontmatter date) are absent
    from both dicts. Canvas/base paths only appear in ``git_dates`` and so use
    the git date.
    """
    fm_stamp = {}
    for path, note in vault.notes.items():
        stamp = _from_frontmatter(note.frontmatter)
        if stamp:
            fm_stamp[path] = stamp

    display: dict = {}
    order: dict = {}
    for path in set(git_dates) | set(fm_stamp):
        stamp = fm_stamp.get(path)
        if stamp:
            display[path] = stamp[:10]
            order[path] = stamp
        else:
            display[path] = git_dates[path]
            order[path] = git_dates[path] + "T00:00:00"
    return display, order
