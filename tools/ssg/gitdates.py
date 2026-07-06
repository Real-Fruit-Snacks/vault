from __future__ import annotations

import re
import subprocess
from pathlib import Path

_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}$")


def note_dates(vault_root: Path) -> dict:
    """Map vault-relative posix paths to the ISO date (YYYY-MM-DD) of their
    most recent commit. Returns {} on any failure: the build must work on
    machines without git, in non-repos, and in temp-dir test builds."""
    try:
        proc = subprocess.run(
            ["git", "-c", "core.quotepath=false", "log", "--relative",
             "--format=%x00%cs", "--name-only"],
            cwd=str(vault_root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if proc.returncode != 0:
        return {}
    dates: dict = {}
    current = None
    for line in proc.stdout.splitlines():
        if line.startswith("\x00"):
            current = line[1:].strip()
            if not _DATE_RE.match(current):
                current = None
        elif line and current:
            dates.setdefault(line.strip(), current)
    return dates
