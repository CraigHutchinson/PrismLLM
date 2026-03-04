"""
Unit tests for scripts/hook_installer.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
import hook_installer as hi


def _template(tmp_path: Path) -> Path:
    """Write a minimal claude_settings template into tmp_path."""
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    tpl = {
        "_prism_version": "1.0",
        "_note": "test",
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command",
                               "command": "python {{PRISM_ROOT}}/hooks/prism_preparser.py"}],
                }
            ]
        },
    }
    p = hooks_dir / "claude_settings_template.json"
    p.write_text(json.dumps(tpl))
    return p


# ── _substitute ───────────────────────────────────────────────────────────────

def test_substitute_replaces_prism_root(tmp_path):
    text = "python {{PRISM_ROOT}}/hooks/prism_preparser.py"
    result = hi._substitute(text, tmp_path)
    assert "{{PRISM_ROOT}}" not in result
    assert str(tmp_path).replace("\\", "/") in result


# ── install_claude_hooks ──────────────────────────────────────────────────────

def test_install_creates_settings_file(tmp_path):
    tpl_path = _template(tmp_path)
    target = tmp_path / ".claude" / "settings.json"
    with patch.object(hi, "TEMPLATE_CLAUDE", tpl_path):
        hi.install_claude_hooks(prism_root=tmp_path, target=target)
    assert target.exists()
    data = json.loads(target.read_text())
    assert "_prism_version" in data
    assert "hooks" in data


def test_install_merges_existing_hooks(tmp_path):
    tpl_path = _template(tmp_path)
    target = tmp_path / ".claude" / "settings.json"
    target.parent.mkdir(parents=True)
    existing = {
        "other_setting": True,
        "hooks": {
            "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "other"}]}],
        },
    }
    target.write_text(json.dumps(existing))
    with patch.object(hi, "TEMPLATE_CLAUDE", tpl_path):
        hi.install_claude_hooks(prism_root=tmp_path, target=target)
    data = json.loads(target.read_text())
    assert data.get("other_setting") is True
    assert "Stop" in data["hooks"]
    assert "UserPromptSubmit" in data["hooks"]


def test_install_idempotent(tmp_path):
    tpl_path = _template(tmp_path)
    target = tmp_path / ".claude" / "settings.json"
    with patch.object(hi, "TEMPLATE_CLAUDE", tpl_path):
        hi.install_claude_hooks(prism_root=tmp_path, target=target)
        hi.install_claude_hooks(prism_root=tmp_path, target=target)
    data = json.loads(target.read_text())
    ups = data["hooks"].get("UserPromptSubmit", [])
    prism_blocks = [b for b in ups if hi._is_prism_hook_block(b)]
    assert len(prism_blocks) == 1


def test_install_corrupt_existing(tmp_path):
    tpl_path = _template(tmp_path)
    target = tmp_path / ".claude" / "settings.json"
    target.parent.mkdir(parents=True)
    target.write_text("NOT JSON")
    with patch.object(hi, "TEMPLATE_CLAUDE", tpl_path):
        hi.install_claude_hooks(prism_root=tmp_path, target=target)
    assert target.exists()


# ── remove_claude_hooks ───────────────────────────────────────────────────────

def test_remove_strips_prism_entries(tmp_path):
    tpl_path = _template(tmp_path)
    target = tmp_path / ".claude" / "settings.json"
    with patch.object(hi, "TEMPLATE_CLAUDE", tpl_path):
        hi.install_claude_hooks(prism_root=tmp_path, target=target)
    hi.remove_claude_hooks(target)
    data = json.loads(target.read_text())
    assert "_prism_version" not in data
    ups = data.get("hooks", {}).get("UserPromptSubmit", [])
    assert all(not hi._is_prism_hook_block(b) for b in ups)


def test_remove_missing_file(tmp_path):
    hi.remove_claude_hooks(tmp_path / "nonexistent.json")


def test_remove_corrupt_file(tmp_path):
    bad = tmp_path / "settings.json"
    bad.write_text("NOT JSON")
    hi.remove_claude_hooks(bad)


def test_remove_preserves_non_prism_hooks(tmp_path):
    tpl_path = _template(tmp_path)
    target = tmp_path / ".claude" / "settings.json"
    target.parent.mkdir(parents=True)
    existing = {
        "hooks": {
            "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "other_tool"}]}],
        }
    }
    target.write_text(json.dumps(existing))
    with patch.object(hi, "TEMPLATE_CLAUDE", tpl_path):
        hi.install_claude_hooks(prism_root=tmp_path, target=target)
    hi.remove_claude_hooks(target)
    data = json.loads(target.read_text())
    assert "Stop" in data.get("hooks", {})


# ── is_claude_hooks_active ────────────────────────────────────────────────────

def test_is_active_after_install(tmp_path):
    tpl_path = _template(tmp_path)
    target = tmp_path / ".claude" / "settings.json"
    with patch.object(hi, "TEMPLATE_CLAUDE", tpl_path):
        hi.install_claude_hooks(prism_root=tmp_path, target=target)
    assert hi.is_claude_hooks_active(target) is True


def test_is_active_after_remove(tmp_path):
    tpl_path = _template(tmp_path)
    target = tmp_path / ".claude" / "settings.json"
    with patch.object(hi, "TEMPLATE_CLAUDE", tpl_path):
        hi.install_claude_hooks(prism_root=tmp_path, target=target)
    hi.remove_claude_hooks(target)
    assert hi.is_claude_hooks_active(target) is False


def test_is_active_missing_file(tmp_path):
    assert hi.is_claude_hooks_active(tmp_path / "missing.json") is False


# ── copilot hooks ─────────────────────────────────────────────────────────────

def test_install_copilot_hooks_no_template(tmp_path):
    with patch.object(hi, "TEMPLATE_COPILOT", tmp_path / "missing.json"):
        hi.install_copilot_hooks(tmp_path, tmp_path / "prism_hooks.json")


def test_copilot_active_absent(tmp_path):
    assert hi.is_copilot_hooks_active(tmp_path / "prism_hooks.json") is False


def test_copilot_remove_absent(tmp_path):
    hi.remove_copilot_hooks(tmp_path / "prism_hooks.json")


# ── CLI main() ────────────────────────────────────────────────────────────────

def test_cli_on(tmp_path, capsys):
    tpl_path = _template(tmp_path)
    with patch("sys.argv", ["hook_installer.py", "--action", "on", "--root", str(tmp_path)]):
        with patch.object(hi, "TEMPLATE_CLAUDE", tpl_path):
            with patch.object(hi, "TEMPLATE_COPILOT", tmp_path / "missing.json"):
                hi.main()
    out = capsys.readouterr().out
    assert "enabled" in out.lower()


def test_cli_off(tmp_path, capsys):
    with patch("sys.argv", ["hook_installer.py", "--action", "off", "--root", str(tmp_path)]):
        hi.main()
    out = capsys.readouterr().out
    assert "disabled" in out.lower()


def test_cli_status(tmp_path, capsys):
    with patch("sys.argv", ["hook_installer.py", "--action", "status", "--root", str(tmp_path)]):
        hi.main()
    out = capsys.readouterr().out
    assert "inactive" in out.lower() or "active" in out.lower()
