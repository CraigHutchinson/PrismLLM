"""
Unit tests for scripts/hello.py
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
import hello


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_scan_safe():
    """Minimal ScanResult-like object representing a safe prompt."""
    r = MagicMock()
    r.safe = True
    r.pii_found = []
    r.injection_risk = False
    r.filler_count = 2
    r.efficiency_ratio = 0.67
    return r


def _fake_scan_pii():
    """ScanResult with PII."""
    r = MagicMock()
    r.safe = False
    r.pii_found = ["EMAIL"]
    r.injection_risk = False
    r.filler_count = 0
    r.efficiency_ratio = 1.0
    return r


# ---------------------------------------------------------------------------
# DEMO_PROMPT constant
# ---------------------------------------------------------------------------

def test_demo_prompt_is_string():
    assert isinstance(hello.DEMO_PROMPT, str)
    assert len(hello.DEMO_PROMPT) > 10


# ---------------------------------------------------------------------------
# _supports_unicode
# ---------------------------------------------------------------------------

def test_supports_unicode_utf8():
    with patch("sys.stdout") as mock_stdout:
        mock_stdout.encoding = "utf-8"
        assert hello._supports_unicode() is True


def test_supports_unicode_cp1252():
    with patch("sys.stdout") as mock_stdout:
        mock_stdout.encoding = "cp1252"
        assert hello._supports_unicode() is False


def test_supports_unicode_none_encoding():
    with patch("sys.stdout") as mock_stdout:
        mock_stdout.encoding = None
        # Should not raise — returns False for empty encoding
        result = hello._supports_unicode()
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# _run_stage1
# ---------------------------------------------------------------------------

def test_run_stage1_safe_prompt():
    import pii_scan
    with patch.object(pii_scan, "scan", return_value=_fake_scan_safe()):
        result = hello._run_stage1("hello world")
    assert result["ok"] is True
    assert result["safe"] is True
    assert result["pii_found"] == []
    assert result["injection_risk"] is False
    assert result["filler_count"] == 2
    assert result["efficiency_ratio"] == 0.67


def test_run_stage1_with_pii():
    import pii_scan
    with patch.object(pii_scan, "scan", return_value=_fake_scan_pii()):
        result = hello._run_stage1("email@example.com")
    assert result["ok"] is True
    assert result["safe"] is False
    assert "EMAIL" in result["pii_found"]


def test_run_stage1_import_error():
    with patch.dict("sys.modules", {"pii_scan": None}):
        result = hello._run_stage1("hello world")
    assert result["ok"] is False
    assert "error" in result


def test_run_stage1_scan_exception():
    import pii_scan
    with patch.object(pii_scan, "scan", side_effect=RuntimeError("scan failed")):
        result = hello._run_stage1("hello world")
    assert result["ok"] is False
    assert "scan failed" in result["error"]


# ---------------------------------------------------------------------------
# _run_stage2
# ---------------------------------------------------------------------------

def test_run_stage2_ok_result():
    import stage2_gate
    with patch.object(stage2_gate, "evaluate_prompt", return_value={"ok": True}):
        result = hello._run_stage2("Fix the bug")
    assert result["ok"] is True
    assert result["result"] == {"ok": True}


def test_run_stage2_with_context():
    import stage2_gate
    with patch.object(stage2_gate, "evaluate_prompt",
                      return_value={"continue": True, "additionalContext": "prompt is vague"}):
        result = hello._run_stage2("do stuff")
    assert result["ok"] is True
    assert "vague" in result["result"]["additionalContext"]


def test_run_stage2_import_error():
    with patch.dict("sys.modules", {"stage2_gate": None}):
        result = hello._run_stage2("hello world")
    assert result["ok"] is False
    assert "error" in result


def test_run_stage2_evaluate_exception():
    import stage2_gate
    with patch.object(stage2_gate, "evaluate_prompt", side_effect=RuntimeError("gate failed")):
        result = hello._run_stage2("hello")
    assert result["ok"] is False
    assert "gate failed" in result["error"]


# ---------------------------------------------------------------------------
# _build_text — human-readable output
# ---------------------------------------------------------------------------

class TestBuildText:
    def _s1_ok(self, filler=2, safe=True):
        return {
            "ok": True, "safe": safe,
            "pii_found": [] if safe else ["EMAIL"],
            "injection_risk": False,
            "filler_count": filler, "efficiency_ratio": 0.67,
        }

    def _s2_ok(self, ctx=""):
        r = {"ok": True}
        if ctx:
            r = {"continue": True, "additionalContext": ctx}
        return {"ok": True, "result": r}

    def test_contains_banner(self):
        text = hello._build_text(self._s1_ok(), self._s2_ok(), run_demo=True)
        assert "Prism" in text

    def test_contains_three_pillars(self):
        text = hello._build_text(self._s1_ok(), self._s2_ok(), run_demo=True)
        assert "Refraction" in text
        assert "Sanitization" in text
        assert "Introspection" in text

    def test_demo_runs_stage1_and_stage2(self):
        text = hello._build_text(self._s1_ok(), self._s2_ok(), run_demo=True)
        assert "Stage 1" in text
        assert "Stage 2" in text
        assert "clear" in text  # natural-language safe result

    def test_demo_skipped_message(self):
        text = hello._build_text({}, {}, run_demo=False)
        assert "demo skipped" in text.lower()
        assert "Stage 1" not in text

    def test_stage1_error_shown(self):
        text = hello._build_text(
            {"ok": False, "error": "import failed"},
            {},
            run_demo=True,
        )
        assert "privacy check" in text
        assert "error" in text.lower()
        assert "import failed" in text

    def test_stage2_error_shown(self):
        text = hello._build_text(
            self._s1_ok(),
            {"ok": False, "error": "gate broken"},
            run_demo=True,
        )
        assert "gate broken" in text

    def test_gate_no_issues_message(self):
        text = hello._build_text(self._s1_ok(), self._s2_ok(), run_demo=True)
        assert "looks good" in text

    def test_gate_vague_message(self):
        text = hello._build_text(
            self._s1_ok(),
            self._s2_ok(ctx="prompt is vague, add context"),
            run_demo=True,
        )
        assert "vague" in text.lower()

    def test_gate_bundled_message(self):
        text = hello._build_text(
            self._s1_ok(),
            self._s2_ok(ctx="bundled task detected"),
            run_demo=True,
        )
        assert "multiple tasks" in text.lower()

    def test_gate_generic_suggestions_message(self):
        text = hello._build_text(
            self._s1_ok(),
            self._s2_ok(ctx="some other issue"),
            run_demo=True,
        )
        assert "suggestions available" in text

    def test_pii_found_shows_natural_language(self):
        s1_pii = {
            "ok": True, "safe": False,
            "pii_found": ["EMAIL", "PHONE"],
            "injection_risk": False,
            "filler_count": 0, "efficiency_ratio": 1.0,
        }
        text = hello._build_text(s1_pii, self._s2_ok(), run_demo=True)
        assert "blocked" in text
        assert "found:" in text

    def test_pii_found_empty_list_shows_fallback(self):
        s1_pii = {
            "ok": True, "safe": False,
            "pii_found": [],  # unsafe but no specific types
            "injection_risk": False,
            "filler_count": 0, "efficiency_ratio": 1.0,
        }
        text = hello._build_text(s1_pii, self._s2_ok(), run_demo=True)
        assert "sensitive content detected" in text

    def test_filler_count_shown(self):
        text = hello._build_text(self._s1_ok(filler=3), self._s2_ok(), run_demo=True)
        assert "3 filler" in text

    def test_no_filler_line_when_zero(self):
        text = hello._build_text(self._s1_ok(filler=0), self._s2_ok(), run_demo=True)
        assert "filler word(s) detected" not in text

    def test_contains_first_commands(self):
        text = hello._build_text(self._s1_ok(), self._s2_ok(), run_demo=True)
        assert "/prism improve" in text
        assert "/prism hook on" in text
        assert "/prism patterns" in text

    def test_contains_demo_prompt_in_try_it(self):
        text = hello._build_text(self._s1_ok(), self._s2_ok(), run_demo=True)
        assert hello.DEMO_PROMPT in text

    def test_token_overhead_line(self):
        text = hello._build_text(self._s1_ok(), self._s2_ok(), run_demo=True)
        assert "~0t" in text

    def test_ascii_mode(self):
        with patch.object(hello, "_supports_unicode", return_value=False):
            text = hello._build_text(self._s1_ok(), self._s2_ok(), run_demo=True)
        # No unicode box-drawing characters
        assert "\u250c" not in text
        assert "\u2500" not in text


# ---------------------------------------------------------------------------
# _build_json
# ---------------------------------------------------------------------------

class TestBuildJson:
    def test_structure(self):
        s1 = {"ok": True, "safe": True}
        s2 = {"ok": True, "result": {"ok": True}}
        data = hello._build_json(s1, s2, run_demo=True)
        assert data["command"] == "hello"
        assert data["demo_prompt"] == hello.DEMO_PROMPT
        assert data["demo_ran"] is True
        assert data["stage1"] == s1
        assert data["stage2"] == s2
        assert "Refraction" in data["pillars"]
        assert len(data["commands"]) >= 5

    def test_demo_not_ran(self):
        data = hello._build_json({}, {}, run_demo=False)
        assert data["demo_ran"] is False
        assert data["stage1"] is None
        assert data["stage2"] is None


# ---------------------------------------------------------------------------
# run() public API
# ---------------------------------------------------------------------------

def test_run_with_demo():
    import pii_scan, stage2_gate
    with patch.object(pii_scan, "scan", return_value=_fake_scan_safe()), \
         patch.object(stage2_gate, "evaluate_prompt", return_value={"ok": True}):
        result = hello.run(run_demo=True)
    assert result["run_demo"] is True
    assert result["stage1"]["ok"] is True
    assert result["stage2"]["ok"] is True
    assert "Prism" in result["text"]
    assert result["json"]["command"] == "hello"


def test_run_without_demo():
    result = hello.run(run_demo=False)
    assert result["run_demo"] is False
    assert result["stage1"] == {}
    assert result["stage2"] == {}
    assert "demo skipped" in result["text"].lower()


# ---------------------------------------------------------------------------
# main() CLI
# ---------------------------------------------------------------------------

class TestMain:
    def test_exits_zero(self):
        with patch("sys.stdout", new_callable=io.StringIO):
            assert hello.main([]) == 0

    def test_json_flag(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = hello.main(["--json"])
        assert rc == 0
        data = json.loads(buf.getvalue())
        assert data["command"] == "hello"
        assert "pillars" in data

    def test_no_demo_flag(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = hello.main(["--no-demo"])
        assert rc == 0
        assert "demo skipped" in buf.getvalue().lower()

    def test_json_no_demo_combined(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = hello.main(["--json", "--no-demo"])
        assert rc == 0
        data = json.loads(buf.getvalue())
        assert data["demo_ran"] is False
        assert data["stage1"] is None

    def test_human_readable_contains_pillars(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            hello.main([])
        output = buf.getvalue()
        assert "Refraction" in output
        assert "Sanitization" in output
        assert "Introspection" in output

    def test_human_readable_contains_commands(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            hello.main([])
        output = buf.getvalue()
        assert "/prism improve" in output
        assert "/prism hook on" in output
