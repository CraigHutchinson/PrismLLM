#!/usr/bin/env python3
"""
configure.py — Prism platform installer.

Run from the Prism skill directory (~/.prism-skill) to install Prism
into your IDE or project in a single command.

Usage
-----
  python configure.py cursor          Install Prism skill for Cursor (global)
  python configure.py claude          Install Prism sub-skills for Claude Code (project)
  python configure.py copilot         Install Prism agent for GitHub Copilot (project)
  python configure.py all             Install for all three platforms
  python configure.py status          Show what is installed
  python configure.py remove cursor   Remove Cursor install
  python configure.py remove claude   Remove Claude Code install
  python configure.py remove copilot  Remove Copilot install

Options
-------
  --project-dir DIR   Target project directory for Claude Code / Copilot
                      (default: current working directory)
  --cursor-dir DIR    Cursor global skills directory
                      (default: ~/.cursor/skills)
  --force             Overwrite already-installed files
  --dry-run           Print what would happen without making changes

Exit codes: 0 = success, 1 = error
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

PRISM_ROOT = Path(__file__).resolve().parent


def _supports_unicode() -> bool:
    encoding = getattr(sys.stdout, "encoding", "") or ""
    try:
        "\u2014".encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


# ---------------------------------------------------------------------------
# Sub-skills installed for each platform
# ---------------------------------------------------------------------------

_CLAUDE_SUB_SKILLS = ["prism", "prism-sanitize", "prism-score", "prism-refract"]

_CURSOR_SKILL_NAME = "prism"

_COPILOT_FILES = [
    (".github/agents/prism.agent.md",       ".github/agents/prism.agent.md"),
    (".github/copilot-instructions.md",      ".github/copilot-instructions.md"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_dry(msg: str) -> None:
    print(f"  [dry-run] {msg}")


def _print_action(action: str, src: Path, dst: Path) -> None:
    print(f"  [{action}] {dst}")


def _confirm_source(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Source not found: {path}\n"
            "Run this script from the Prism skill directory "
            "(e.g. python ~/.prism-skill/configure.py)."
        )


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------

def install_cursor(
    cursor_dir: Optional[Path] = None,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """Install Prism skill into the Cursor global skills directory."""
    src = PRISM_ROOT / ".cursor" / "skills" / _CURSOR_SKILL_NAME
    _confirm_source(src)

    if cursor_dir is None:
        cursor_dir = Path.home() / ".cursor" / "skills"
    dst = cursor_dir / _CURSOR_SKILL_NAME

    if dst.exists() and not force:
        print(f"  [skip] already installed at {dst}  (use --force to overwrite)")
        return True

    if dry_run:
        action = "symlink" if sys.platform != "win32" else "copy"
        _print_dry(f"{action} {src} -> {dst}")
        return True

    cursor_dir.mkdir(parents=True, exist_ok=True)

    if dst.exists():
        # --force: remove old install first
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)

    if sys.platform != "win32":
        os.symlink(src, dst)
        _print_action("link", src, dst)
    else:
        shutil.copytree(str(src), str(dst))
        _print_action("copy", src, dst)

    return True


def remove_cursor(cursor_dir: Optional[Path] = None, dry_run: bool = False) -> bool:
    """Remove the Cursor Prism skill."""
    if cursor_dir is None:
        cursor_dir = Path.home() / ".cursor" / "skills"
    dst = cursor_dir / _CURSOR_SKILL_NAME

    if not dst.exists():
        print(f"  [skip] not installed at {dst}")
        return True

    if dry_run:
        _print_dry(f"remove {dst}")
        return True

    if dst.is_symlink() or dst.is_file():
        dst.unlink()
    else:
        shutil.rmtree(dst)
    _print_action("remove", dst, dst)
    return True


def status_cursor(cursor_dir: Optional[Path] = None) -> dict:
    if cursor_dir is None:
        cursor_dir = Path.home() / ".cursor" / "skills"
    dst = cursor_dir / _CURSOR_SKILL_NAME
    installed = dst.exists()
    return {
        "platform": "Cursor",
        "installed": installed,
        "path": str(dst),
        "hint": f"python {PRISM_ROOT / 'configure.py'} cursor",
    }


# ---------------------------------------------------------------------------
# Claude Code
# ---------------------------------------------------------------------------

def install_claude(
    project_dir: Optional[Path] = None,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """Copy Prism sub-skills into the current project's .claude/skills/ directory."""
    if project_dir is None:
        project_dir = Path.cwd()

    skills_src = PRISM_ROOT / ".claude" / "skills"
    skills_dst = project_dir / ".claude" / "skills"

    all_ok = True
    for skill in _CLAUDE_SUB_SKILLS:
        src = skills_src / skill
        dst = skills_dst / skill
        _confirm_source(src)

        if dst.exists() and not force:
            print(f"  [skip] already installed: {dst.relative_to(project_dir)}  (use --force to overwrite)")
            continue

        if dry_run:
            _print_dry(f"copy {src} -> {dst}")
            continue

        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(src), str(dst))
        _print_action("copy", src, dst)

    return all_ok


def remove_claude(project_dir: Optional[Path] = None, dry_run: bool = False) -> bool:
    """Remove Prism sub-skills from the project .claude/skills/ directory."""
    if project_dir is None:
        project_dir = Path.cwd()

    skills_dst = project_dir / ".claude" / "skills"
    removed_any = False
    for skill in _CLAUDE_SUB_SKILLS:
        dst = skills_dst / skill
        if not dst.exists():
            continue
        if dry_run:
            _print_dry(f"remove {dst}")
            removed_any = True
            continue
        shutil.rmtree(dst)
        _print_action("remove", dst, dst)
        removed_any = True

    if not removed_any:
        print("  [skip] no Claude Code install found in current project")
    return True


def status_claude(project_dir: Optional[Path] = None) -> dict:
    if project_dir is None:
        project_dir = Path.cwd()
    skills_dst = project_dir / ".claude" / "skills"
    installed = all((skills_dst / s).exists() for s in _CLAUDE_SUB_SKILLS)
    partial = (
        any((skills_dst / s).exists() for s in _CLAUDE_SUB_SKILLS) and not installed
    )
    return {
        "platform": "Claude Code",
        "installed": installed,
        "partial": partial,
        "path": str(skills_dst),
        "hint": f"python {PRISM_ROOT / 'configure.py'} claude",
    }


# ---------------------------------------------------------------------------
# GitHub Copilot
# ---------------------------------------------------------------------------

def install_copilot(
    project_dir: Optional[Path] = None,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """Copy Prism agent files into the current project's .github/ directory."""
    if project_dir is None:
        project_dir = Path.cwd()

    for src_rel, dst_rel in _COPILOT_FILES:
        src = PRISM_ROOT / src_rel
        dst = project_dir / dst_rel
        _confirm_source(src)

        if dst.exists() and not force:
            print(f"  [skip] already installed: {dst.relative_to(project_dir)}  (use --force to overwrite)")
            continue

        if dry_run:
            _print_dry(f"copy {src} -> {dst}")
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        _print_action("copy", src, dst)

    return True


def remove_copilot(project_dir: Optional[Path] = None, dry_run: bool = False) -> bool:
    """Remove Prism agent files from the project .github/ directory."""
    if project_dir is None:
        project_dir = Path.cwd()

    removed_any = False
    for _, dst_rel in _COPILOT_FILES:
        dst = project_dir / dst_rel
        if not dst.exists():
            continue
        if dry_run:
            _print_dry(f"remove {dst}")
            removed_any = True
            continue
        dst.unlink()
        _print_action("remove", dst, dst)
        removed_any = True

    if not removed_any:
        print("  [skip] no Copilot install found in current project")
    return True


def status_copilot(project_dir: Optional[Path] = None) -> dict:
    if project_dir is None:
        project_dir = Path.cwd()
    installed = all((project_dir / dst_rel).exists() for _, dst_rel in _COPILOT_FILES)
    return {
        "platform": "GitHub Copilot",
        "installed": installed,
        "path": str(project_dir / ".github"),
        "hint": f"python {PRISM_ROOT / 'configure.py'} copilot",
    }


# ---------------------------------------------------------------------------
# Status (all platforms)
# ---------------------------------------------------------------------------

def show_status(project_dir: Optional[Path] = None, cursor_dir: Optional[Path] = None) -> None:
    entries = [
        status_cursor(cursor_dir),
        status_claude(project_dir),
        status_copilot(project_dir),
    ]
    width = max(len(e["platform"]) for e in entries) + 2
    print()
    for e in entries:
        if e["installed"]:
            flag = "installed  "
            detail = e["path"]
        elif e.get("partial"):
            flag = "partial    "
            detail = f"{e['path']}  (run: {e['hint']})"
        else:
            flag = "not installed"
            detail = f"run: {e['hint']}"
        platform_label = e["platform"].ljust(width)
        print(f"  {platform_label}  {flag}  {detail}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="configure.py",
        description="Prism platform installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python configure.py cursor          Install for Cursor\n"
            "  python configure.py claude          Install for Claude Code\n"
            "  python configure.py copilot         Install for GitHub Copilot\n"
            "  python configure.py all             Install all platforms\n"
            "  python configure.py status          Show installation status\n"
            "  python configure.py remove claude   Uninstall Claude Code\n"
        ),
    )
    parser.add_argument(
        "command",
        choices=["cursor", "claude", "copilot", "all", "status", "remove"],
        help="What to do",
    )
    parser.add_argument(
        "target",
        nargs="?",
        choices=["cursor", "claude", "copilot", "all"],
        help="Platform to remove (required with 'remove')",
    )
    parser.add_argument(
        "--project-dir",
        default=None,
        help="Project directory for Claude Code / Copilot installs (default: cwd)",
    )
    parser.add_argument(
        "--cursor-dir",
        default=None,
        help="Cursor global skills directory (default: ~/.cursor/skills)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite already-installed files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )

    args = parser.parse_args(argv)

    project_dir = Path(args.project_dir) if args.project_dir else None
    cursor_dir = Path(args.cursor_dir) if args.cursor_dir else None
    force = args.force
    dry_run = args.dry_run

    try:
        if args.command == "status":
            print("Prism install status")
            print("=" * 40)
            show_status(project_dir, cursor_dir)
            return 0

        if args.command == "remove":
            if not args.target:
                print("Error: 'remove' requires a platform: cursor, claude, or copilot")
                return 1
            platform = args.target
            dash = "\u2014" if _supports_unicode() else "--"
            print(f"Prism configure {dash} remove {platform}")
            print("-" * 40)
            if platform in ("cursor", "all"):
                remove_cursor(cursor_dir, dry_run)
            if platform in ("claude", "all"):
                remove_claude(project_dir, dry_run)
            if platform in ("copilot", "all"):
                remove_copilot(project_dir, dry_run)
            print("Done.")
            return 0

        platforms = (
            ["cursor", "claude", "copilot"]
            if args.command == "all"
            else [args.command]
        )

        dash = "\u2014" if _supports_unicode() else "--"
        for platform in platforms:
            print(f"Prism configure {dash} {platform}")
            print("-" * 40)
            if platform == "cursor":
                install_cursor(cursor_dir, force, dry_run)
                if not dry_run:
                    print("Done. Restart Cursor to activate /prism.")
            elif platform == "claude":
                install_claude(project_dir, force, dry_run)
                if not dry_run:
                    print("Done. Run /prism hello to verify.")
            elif platform == "copilot":
                install_copilot(project_dir, force, dry_run)
                if not dry_run:
                    print("Done. Use @prism in Copilot Chat to activate.")
            if len(platforms) > 1 and platform != platforms[-1]:
                print()

    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
