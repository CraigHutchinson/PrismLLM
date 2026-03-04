"""
Smoke tests for configure.py — the Prism platform installer.

Every test runs configure.py via subprocess (as an end user would) and checks
real filesystem side-effects in isolated temporary directories.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIGURE = REPO_ROOT / "configure.py"


def run(*args: str, project_dir: str | None = None,
        cursor_dir: str | None = None,
        cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run configure.py with extra directory arguments appended."""
    cmd = [sys.executable, str(CONFIGURE), *args]
    if project_dir:
        cmd += ["--project-dir", project_dir]
    if cursor_dir:
        cmd += ["--cursor-dir", cursor_dir]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd or REPO_ROOT),
    )


# ---------------------------------------------------------------------------
# Basic sanity checks
# ---------------------------------------------------------------------------

def test_configure_script_exists():
    assert CONFIGURE.exists(), "configure.py must exist at the repository root"


def test_status_exits_zero():
    result = run("status")
    assert result.returncode == 0, result.stderr


def test_status_mentions_all_platforms():
    result = run("status")
    assert result.returncode == 0
    out = result.stdout
    assert "Cursor" in out
    assert "Claude Code" in out
    assert "GitHub Copilot" in out


def test_dry_run_exits_zero():
    result = run("all", "--dry-run")
    assert result.returncode == 0, result.stderr


def test_dry_run_makes_no_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run("all", "--dry-run",
                     project_dir=tmpdir, cursor_dir=str(Path(tmpdir) / "cursor"))
        assert result.returncode == 0
        # Nothing should have been created
        assert not any(Path(tmpdir).iterdir())


def test_missing_target_on_remove_returns_error():
    result = run("remove")
    assert result.returncode == 1
    assert "requires" in result.stdout.lower() or "requires" in result.stderr.lower()


# ---------------------------------------------------------------------------
# Claude Code install
# ---------------------------------------------------------------------------

class TestInstallClaude:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_install_exits_zero(self):
        result = run("claude", project_dir=self.tmpdir)
        assert result.returncode == 0, result.stderr

    def test_install_copies_all_sub_skills(self):
        run("claude", project_dir=self.tmpdir)
        skills_dir = Path(self.tmpdir) / ".claude" / "skills"
        for skill in ("prism", "prism-sanitize", "prism-score", "prism-refract"):
            assert (skills_dir / skill).is_dir(), f"Missing sub-skill: {skill}"

    def test_install_each_skill_has_skill_md(self):
        run("claude", project_dir=self.tmpdir)
        skills_dir = Path(self.tmpdir) / ".claude" / "skills"
        for skill in ("prism", "prism-sanitize", "prism-score", "prism-refract"):
            assert (skills_dir / skill / "SKILL.md").exists(), \
                f"SKILL.md missing in {skill}"

    def test_install_idempotent(self):
        """Running twice should not raise or change existing files."""
        run("claude", project_dir=self.tmpdir)
        result2 = run("claude", project_dir=self.tmpdir)
        assert result2.returncode == 0
        assert "skip" in result2.stdout.lower()

    def test_install_force_overwrites(self):
        run("claude", project_dir=self.tmpdir)
        result2 = run("claude", "--force", project_dir=self.tmpdir)
        assert result2.returncode == 0
        assert "skip" not in result2.stdout.lower()

    def test_remove_cleans_up(self):
        run("claude", project_dir=self.tmpdir)
        result = run("remove", "claude", project_dir=self.tmpdir)
        assert result.returncode == 0
        skills_dir = Path(self.tmpdir) / ".claude" / "skills"
        for skill in ("prism", "prism-sanitize", "prism-score", "prism-refract"):
            assert not (skills_dir / skill).exists(), f"Not removed: {skill}"

    def test_remove_when_not_installed_is_ok(self):
        result = run("remove", "claude", project_dir=self.tmpdir)
        assert result.returncode == 0
        assert "skip" in result.stdout.lower()

    def test_output_mentions_done(self):
        result = run("claude", project_dir=self.tmpdir)
        assert "done" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Copilot install
# ---------------------------------------------------------------------------

class TestInstallCopilot:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_install_exits_zero(self):
        result = run("copilot", project_dir=self.tmpdir)
        assert result.returncode == 0, result.stderr

    def test_install_creates_agent_file(self):
        run("copilot", project_dir=self.tmpdir)
        assert (Path(self.tmpdir) / ".github" / "agents" / "prism.agent.md").exists()

    def test_install_creates_instructions_file(self):
        run("copilot", project_dir=self.tmpdir)
        assert (Path(self.tmpdir) / ".github" / "copilot-instructions.md").exists()

    def test_install_creates_github_dir(self):
        run("copilot", project_dir=self.tmpdir)
        assert (Path(self.tmpdir) / ".github").is_dir()

    def test_install_idempotent(self):
        run("copilot", project_dir=self.tmpdir)
        result2 = run("copilot", project_dir=self.tmpdir)
        assert result2.returncode == 0
        assert "skip" in result2.stdout.lower()

    def test_install_force_overwrites(self):
        run("copilot", project_dir=self.tmpdir)
        result2 = run("copilot", "--force", project_dir=self.tmpdir)
        assert result2.returncode == 0

    def test_remove_cleans_up(self):
        run("copilot", project_dir=self.tmpdir)
        result = run("remove", "copilot", project_dir=self.tmpdir)
        assert result.returncode == 0
        assert not (Path(self.tmpdir) / ".github" / "agents" / "prism.agent.md").exists()

    def test_remove_when_not_installed_is_ok(self):
        result = run("remove", "copilot", project_dir=self.tmpdir)
        assert result.returncode == 0
        assert "skip" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Cursor install
# ---------------------------------------------------------------------------

class TestInstallCursor:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cursor_dir = Path(self.tmpdir) / "cursor-skills"

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_install_exits_zero(self):
        result = run("cursor", cursor_dir=str(self.cursor_dir))
        assert result.returncode == 0, result.stderr

    def test_install_creates_skill_directory(self):
        run("cursor", cursor_dir=str(self.cursor_dir))
        assert (self.cursor_dir / "prism").exists()

    def test_install_skill_has_skill_md(self):
        run("cursor", cursor_dir=str(self.cursor_dir))
        assert (self.cursor_dir / "prism" / "SKILL.md").exists()

    def test_install_idempotent(self):
        run("cursor", cursor_dir=str(self.cursor_dir))
        result2 = run("cursor", cursor_dir=str(self.cursor_dir))
        assert result2.returncode == 0
        assert "skip" in result2.stdout.lower()

    def test_remove_cleans_up(self):
        run("cursor", cursor_dir=str(self.cursor_dir))
        result = run("remove", "cursor", cursor_dir=str(self.cursor_dir))
        assert result.returncode == 0
        assert not (self.cursor_dir / "prism").exists()

    def test_remove_when_not_installed_is_ok(self):
        result = run("remove", "cursor", cursor_dir=str(self.cursor_dir))
        assert result.returncode == 0
        assert "skip" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Install all
# ---------------------------------------------------------------------------

class TestInstallAll:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cursor_dir = Path(self.tmpdir) / "cursor-skills"

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_install_all_exits_zero(self):
        result = run("all",
                     project_dir=self.tmpdir,
                     cursor_dir=str(self.cursor_dir))
        assert result.returncode == 0, result.stderr

    def test_install_all_creates_cursor_skill(self):
        run("all", project_dir=self.tmpdir, cursor_dir=str(self.cursor_dir))
        assert (self.cursor_dir / "prism").exists()

    def test_install_all_creates_claude_skills(self):
        run("all", project_dir=self.tmpdir, cursor_dir=str(self.cursor_dir))
        skills_dir = Path(self.tmpdir) / ".claude" / "skills"
        assert (skills_dir / "prism").is_dir()

    def test_install_all_creates_copilot_files(self):
        run("all", project_dir=self.tmpdir, cursor_dir=str(self.cursor_dir))
        assert (Path(self.tmpdir) / ".github" / "agents" / "prism.agent.md").exists()

    def test_status_after_install_all(self):
        run("all", project_dir=self.tmpdir, cursor_dir=str(self.cursor_dir))
        result = run("status",
                     project_dir=self.tmpdir, cursor_dir=str(self.cursor_dir))
        assert result.returncode == 0
        out = result.stdout
        # All three should show as installed
        assert out.count("installed") >= 3
