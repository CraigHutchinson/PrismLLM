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
        cwd: Path | None = None,
        skip_deps: bool = True) -> subprocess.CompletedProcess:
    """Run configure.py with extra directory arguments appended.

    ``skip_deps=True`` (default) passes ``--skip-deps`` to avoid running pip
    on every test invocation.  Set ``skip_deps=False`` to test the dep-install
    path explicitly.
    """
    cmd = [sys.executable, str(CONFIGURE), *args]
    if project_dir:
        cmd += ["--project-dir", project_dir]
    if cursor_dir:
        cmd += ["--cursor-dir", cursor_dir]
    if skip_deps:
        cmd += ["--skip-deps"]
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


def test_no_args_defaults_to_all():
    """Running configure.py with no arguments should install all platforms."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run(project_dir=tmpdir, cursor_dir=str(Path(tmpdir) / "cursor"))
        assert result.returncode == 0, result.stderr
        out = result.stdout
        # Preamble line should mention "all platforms"
        assert "all platforms" in out.lower()
        # All three platform sections should appear
        assert "cursor" in out.lower()
        assert "claude" in out.lower()
        assert "copilot" in out.lower()


def test_no_args_dry_run_makes_no_files():
    """configure.py --dry-run (no platform arg) should touch nothing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run("--dry-run",
                     project_dir=tmpdir, cursor_dir=str(Path(tmpdir) / "cursor"))
        assert result.returncode == 0
        assert not any(Path(tmpdir).iterdir())


def test_missing_target_on_remove_returns_error():
    result = run("remove")
    assert result.returncode == 1
    assert "requires" in result.stdout.lower() or "requires" in result.stderr.lower()


def test_setup_section_appears_on_install():
    """Every install should show a setup section header."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run("claude", project_dir=tmpdir)
        assert result.returncode == 0, result.stderr
        assert "setup" in result.stdout.lower()


def test_skip_deps_flag_skips_pip():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run("claude", project_dir=tmpdir, skip_deps=True)
        assert result.returncode == 0
        assert "[skip] dependency" in result.stdout.lower()


def test_deps_installed_without_skip_flag():
    """Without --skip-deps, the pip step should run (and report 'done' or similar)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run("claude", project_dir=tmpdir, skip_deps=False)
        assert result.returncode == 0, result.stderr
        # pip ran — either "done" (installed/already up-to-date) or "Installing"
        assert "installing" in result.stdout.lower() or "done" in result.stdout.lower()


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
        assert "[skip] already installed" not in result2.stdout.lower()

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

    def test_output_shows_health_check(self):
        result = run("claude", project_dir=self.tmpdir)
        assert "health check" in result.stdout.lower()


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
