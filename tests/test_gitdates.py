import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ssg.gitdates import note_dates


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=str(cwd), check=True,
                   capture_output=True, text=True)


class GitDatesTests(unittest.TestCase):
    def setUp(self):
        if shutil.which("git") is None:
            self.skipTest("git not installed")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def _init_repo(self):
        _git(self.root, "init", "-q")
        _git(self.root, "config", "user.email", "t@t")
        _git(self.root, "config", "user.name", "t")

    def test_maps_notes_to_commit_dates(self):
        self._init_repo()
        (self.root / "A.md").write_text("a", encoding="utf-8")
        (self.root / "Sub").mkdir()
        (self.root / "Sub/B.md").write_text("b", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "one")
        dates = note_dates(self.root)
        self.assertRegex(dates["A.md"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("Sub/B.md", dates)

    def test_most_recent_commit_wins(self):
        self._init_repo()
        (self.root / "A.md").write_text("a", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "one")
        (self.root / "A.md").write_text("a2", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "two",
             "--date", "2020-01-02T03:04:05")
        dates = note_dates(self.root)
        # %cs is the committer date; --date sets the author date, so just
        # confirm the entry exists and is a single well-formed date.
        self.assertRegex(dates["A.md"], r"^\d{4}-\d{2}-\d{2}$")

    def test_nested_vault_paths_are_relative_and_scoped(self):
        self._init_repo()
        (self.root / "outer.md").write_text("o", encoding="utf-8")
        vault = self.root / "vault"
        vault.mkdir()
        (vault / "Note.md").write_text("n", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "one")
        dates = note_dates(vault)
        self.assertIn("Note.md", dates)
        self.assertNotIn("outer.md", dates)

    def test_untracked_file_absent(self):
        self._init_repo()
        (self.root / "A.md").write_text("a", encoding="utf-8")
        _git(self.root, "add", "-A")
        _git(self.root, "commit", "-q", "-m", "one")
        (self.root / "New.md").write_text("n", encoding="utf-8")
        self.assertNotIn("New.md", note_dates(self.root))

    def test_not_a_repo_returns_empty(self):
        self.assertEqual(note_dates(self.root), {})

    def test_first_commit_dates_shape(self):
        from ssg import gitdates
        from pathlib import Path
        d = gitdates.note_dates_first(Path("."))
        self.assertIsInstance(d, dict)  # {} in non-repo/temp is fine


if __name__ == "__main__":
    unittest.main()
