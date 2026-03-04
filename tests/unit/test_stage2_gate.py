"""
Unit tests for scripts/stage2_gate.py
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
import stage2_gate


# ── evaluate_prompt (heuristics) ─────────────────────────────────────────────

def test_empty_prompt_passes():
    assert stage2_gate.evaluate_prompt("") == {"ok": True}
    assert stage2_gate.evaluate_prompt("   ") == {"ok": True}


def test_vague_only_blocked():
    result = stage2_gate.evaluate_prompt("make it better")
    assert result["ok"] is False
    assert "vague" in result["reason"].lower()


def test_vague_only_blocked_case_insensitive():
    result = stage2_gate.evaluate_prompt("Make It Better.")
    assert result["ok"] is False


def test_very_short_prompt_blocked():
    result = stage2_gate.evaluate_prompt("fix it")
    assert result["ok"] is False


def test_bundled_prompt_blocked():
    result = stage2_gate.evaluate_prompt(
        "add login as well as update tests additionally fix CI furthermore deploy pages"
    )
    assert result["ok"] is False
    assert "bundle" in result["reason"].lower()


def test_specific_prompt_passes():
    result = stage2_gate.evaluate_prompt(
        "Refactor the AuthService class to use dependency injection for the database adapter."
    )
    assert result["ok"] is True


def test_code_review_prompt_passes():
    result = stage2_gate.evaluate_prompt("Review the payment service for security issues")
    assert result["ok"] is True


def test_question_prompt_passes():
    result = stage2_gate.evaluate_prompt("How does JWT authentication work in Python?")
    assert result["ok"] is True


# ── _build_output ────────────────────────────────────────────────────────────

def test_build_output_ok_cursor():
    result = stage2_gate._build_output({"ok": True}, "cursor")
    assert result == {"continue": True}


def test_build_output_ok_claude_code():
    result = stage2_gate._build_output({"ok": True}, "claude_code")
    assert result == {"decision": "continue"}


def test_build_output_not_ok_cursor():
    result = stage2_gate._build_output({"ok": False, "reason": "too vague"}, "cursor")
    assert result["continue"] is True
    assert "too vague" in result["additionalContext"]


def test_build_output_not_ok_claude_code():
    result = stage2_gate._build_output({"ok": False, "reason": "too vague"}, "claude_code")
    assert result["decision"] == "continue"
    assert "too vague" in result["additionalContext"]


# ── CLI main() ───────────────────────────────────────────────────────────────

def test_cli_clean_prompt(capsys):
    with patch("sys.argv", ["stage2_gate.py", "--platform", "cursor"]):
        with patch("sys.stdin", io.StringIO("Refactor the auth module to use DI.")):
            with patch("sys.stdin.isatty", return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    stage2_gate.main()
    assert exc_info.value.code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["continue"] is True


def test_cli_vague_prompt(capsys):
    with patch("sys.argv", ["stage2_gate.py", "--platform", "cursor"]):
        with patch("sys.stdin", io.StringIO("make it better")):
            with patch("sys.stdin.isatty", return_value=False):
                with pytest.raises(SystemExit) as exc_info:
                    stage2_gate.main()
    assert exc_info.value.code == 0
    out = json.loads(capsys.readouterr().out)
    assert "additionalContext" in out


def test_cli_no_stdin(capsys):
    with patch("sys.argv", ["stage2_gate.py", "--platform", "cursor"]):
        with patch("sys.stdin.isatty", return_value=True):
            with pytest.raises(SystemExit) as exc_info:
                stage2_gate.main()
    assert exc_info.value.code == 0


def test_cli_platform_autodetect(capsys):
    with patch("sys.argv", ["stage2_gate.py"]):
        with patch("sys.stdin", io.StringIO("refactor auth")):
            with patch("sys.stdin.isatty", return_value=False):
                with pytest.raises(SystemExit):
                    stage2_gate.main()


def test_cli_platform_autodetect_import_error(capsys):
    with patch("sys.argv", ["stage2_gate.py"]):
        with patch("sys.stdin", io.StringIO("refactor auth")):
            with patch("sys.stdin.isatty", return_value=False):
                with patch.dict("sys.modules", {"platform_model": None}):
                    with pytest.raises(SystemExit):
                        stage2_gate.main()
