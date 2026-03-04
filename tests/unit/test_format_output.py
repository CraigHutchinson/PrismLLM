"""
Unit tests for scripts/format_output.py
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
import format_output as fo


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

def test_format_constants():
    assert fo.FORMAT_MARKDOWN == "markdown"
    assert fo.FORMAT_XML == "xml"
    assert fo.FORMAT_PREFIXED == "prefixed"
    assert fo.DEFAULT_FORMAT == "markdown"


def test_sections_list():
    assert "task" in fo.SECTIONS
    assert "context" in fo.SECTIONS
    assert "constraints" in fo.SECTIONS
    assert len(fo.SECTIONS) >= 4


# ---------------------------------------------------------------------------
# select_format
# ---------------------------------------------------------------------------

class TestSelectFormat:
    def test_cursor_returns_xml(self):
        assert fo.select_format("cursor") == fo.FORMAT_XML

    def test_claude_code_returns_xml(self):
        assert fo.select_format("claude_code") == fo.FORMAT_XML

    def test_copilot_returns_markdown(self):
        assert fo.select_format("copilot") == fo.FORMAT_MARKDOWN

    def test_copilot_free_returns_markdown(self):
        assert fo.select_format("copilot_free") == fo.FORMAT_MARKDOWN

    def test_unknown_returns_markdown(self):
        assert fo.select_format("unknown") == fo.FORMAT_MARKDOWN

    def test_none_uses_auto_detect(self):
        with patch.object(fo, "_detect_platform", return_value="copilot"):
            result = fo.select_format(None)
        assert result == fo.FORMAT_MARKDOWN

    def test_none_auto_detects_claude(self):
        with patch.object(fo, "_detect_platform", return_value="cursor"):
            result = fo.select_format(None)
        assert result == fo.FORMAT_XML


# ---------------------------------------------------------------------------
# _detect_platform
# ---------------------------------------------------------------------------

class TestDetectPlatform:
    def test_delegates_to_platform_model(self):
        mock_pm = MagicMock()
        mock_pm.detect_platform.return_value = "copilot"
        with patch.dict("sys.modules", {"platform_model": mock_pm}):
            result = fo._detect_platform()
        assert result == "copilot"

    def test_falls_back_to_env_var_on_import_error(self, monkeypatch):
        monkeypatch.setenv("PRISM_PLATFORM", "copilot")
        with patch.dict("sys.modules", {"platform_model": None}):
            result = fo._detect_platform()
        assert result == "copilot"

    def test_falls_back_to_unknown_when_no_env(self, monkeypatch):
        monkeypatch.delenv("PRISM_PLATFORM", raising=False)
        with patch.dict("sys.modules", {"platform_model": None}):
            result = fo._detect_platform()
        assert result == "unknown"

    def test_falls_back_on_exception_from_detect(self):
        mock_pm = MagicMock()
        mock_pm.detect_platform.side_effect = RuntimeError("broken")
        with patch.dict("sys.modules", {"platform_model": mock_pm}):
            result = fo._detect_platform()
        assert result in ("unknown", "cursor", "copilot", "claude_code")


# ---------------------------------------------------------------------------
# _render_markdown
# ---------------------------------------------------------------------------

class TestRenderMarkdown:
    def test_single_section(self):
        out = fo._render_markdown({"task": "Add login page"})
        assert "## Task" in out
        assert "Add login page" in out

    def test_multiple_sections_in_order(self):
        out = fo._render_markdown({
            "constraints": "No libs",
            "task": "Add login",
            "context": "Flask app",
        })
        task_pos = out.index("## Task")
        ctx_pos = out.index("## Context")
        con_pos = out.index("## Constraints")
        assert task_pos < ctx_pos < con_pos

    def test_empty_sections_omitted(self):
        out = fo._render_markdown({"task": "Do X", "context": ""})
        assert "## Context" not in out

    def test_multiline_value(self):
        out = fo._render_markdown({"task": "Line 1\nLine 2"})
        assert "Line 1\nLine 2" in out

    def test_all_sections(self):
        sections = {k: f"value-{k}" for k in fo.SECTIONS}
        out = fo._render_markdown(sections)
        for k in fo.SECTIONS:
            assert fo._MARKDOWN_LABELS[k] in out


# ---------------------------------------------------------------------------
# _render_xml
# ---------------------------------------------------------------------------

class TestRenderXml:
    def test_single_section_inline(self):
        out = fo._render_xml({"task": "Add login page"})
        assert "<task>Add login page</task>" in out

    def test_multiline_value_block(self):
        out = fo._render_xml({"task": "Line 1\nLine 2"})
        assert "<task>\nLine 1\nLine 2\n</task>" in out

    def test_multiple_sections(self):
        out = fo._render_xml({"task": "Do X", "context": "Background"})
        assert "<task>" in out
        assert "<context>" in out

    def test_empty_sections_omitted(self):
        out = fo._render_xml({"task": "Do X", "context": ""})
        assert "<context>" not in out

    def test_section_order(self):
        out = fo._render_xml({
            "constraints": "No libs",
            "task": "Do X",
            "context": "Background",
        })
        assert out.index("<task>") < out.index("<context>") < out.index("<constraints>")


# ---------------------------------------------------------------------------
# _render_prefixed
# ---------------------------------------------------------------------------

class TestRenderPrefixed:
    def test_single_section_inline(self):
        out = fo._render_prefixed({"task": "Add login page"})
        assert "TASK: Add login page" in out

    def test_multiline_value_block(self):
        out = fo._render_prefixed({"task": "Line 1\nLine 2"})
        assert "TASK:\nLine 1\nLine 2" in out

    def test_multiple_sections(self):
        out = fo._render_prefixed({"task": "Do X", "constraints": "No libs"})
        assert "TASK:" in out
        assert "CONSTRAINTS:" in out

    def test_empty_sections_omitted(self):
        out = fo._render_prefixed({"task": "Do X", "context": ""})
        assert "CONTEXT" not in out


# ---------------------------------------------------------------------------
# render_prompt (public API)
# ---------------------------------------------------------------------------

class TestRenderPrompt:
    def test_markdown_format(self):
        out = fo.render_prompt({"task": "Do X"}, format_style="markdown")
        assert "## Task" in out

    def test_xml_format(self):
        out = fo.render_prompt({"task": "Do X"}, format_style="xml")
        assert "<task>" in out

    def test_prefixed_format(self):
        out = fo.render_prompt({"task": "Do X"}, format_style="prefixed")
        assert "TASK:" in out

    def test_auto_select_via_platform(self):
        out = fo.render_prompt({"task": "X"}, platform="cursor")
        assert "<task>" in out

    def test_auto_select_unknown_gives_markdown(self):
        out = fo.render_prompt({"task": "X"}, platform="unknown")
        assert "## Task" in out

    def test_format_style_takes_priority_over_platform(self):
        # format_style=xml but platform=copilot (would give markdown)
        out = fo.render_prompt({"task": "X"}, format_style="xml", platform="copilot")
        assert "<task>" in out

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Unknown format_style"):
            fo.render_prompt({"task": "X"}, format_style="yaml")

    def test_empty_sections_still_renders(self):
        out = fo.render_prompt({"task": "X", "context": ""}, format_style="markdown")
        assert "## Task" in out
        assert "## Context" not in out

    def test_all_sections_rendered(self):
        sections = {k: f"val-{k}" for k in fo.SECTIONS}
        out = fo.render_prompt(sections, format_style="markdown")
        for key in fo.SECTIONS:
            assert fo._MARKDOWN_LABELS[key] in out


# ---------------------------------------------------------------------------
# main() CLI
# ---------------------------------------------------------------------------

class TestMain:
    def test_detect_format_only(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf), \
             patch.object(fo, "select_format", return_value="markdown"):
            rc = fo.main(["--detect-format"])
        assert rc == 0
        assert buf.getvalue().strip() == "markdown"

    def test_detect_format_with_platform(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = fo.main(["--detect-format", "--platform", "cursor"])
        assert rc == 0
        assert buf.getvalue().strip() == "xml"

    def test_task_arg_renders(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = fo.main(["--task", "Add login", "--format", "markdown"])
        assert rc == 0
        assert "## Task" in buf.getvalue()
        assert "Add login" in buf.getvalue()

    def test_xml_format_flag(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = fo.main(["--task", "Do X", "--format", "xml"])
        assert rc == 0
        assert "<task>" in buf.getvalue()

    def test_prefixed_format_flag(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = fo.main(["--task", "Do X", "--format", "prefixed"])
        assert rc == 0
        assert "TASK:" in buf.getvalue()

    def test_multiple_sections(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = fo.main([
                "--task", "Add login",
                "--context", "Flask app",
                "--constraints", "No third-party libs",
                "--format", "markdown",
            ])
        assert rc == 0
        output = buf.getvalue()
        assert "## Task" in output
        assert "## Context" in output
        assert "## Constraints" in output

    def test_json_output(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = fo.main(["--task", "Do X", "--format", "markdown", "--json"])
        assert rc == 0
        data = json.loads(buf.getvalue())
        assert data["format"] == "markdown"
        assert "## Task" in data["output"]

    def test_no_sections_returns_one(self):
        fake_stdin = io.StringIO("")
        fake_stdin.isatty = lambda: True  # simulate interactive terminal
        with patch("sys.stdin", fake_stdin):
            rc = fo.main([])
        assert rc == 1

    def test_stdin_used_when_no_task_arg(self):
        buf = io.StringIO()
        fake_stdin = io.StringIO("Build a login page")
        with patch("sys.stdout", buf), patch("sys.stdin", fake_stdin):
            rc = fo.main(["--format", "markdown"])
        assert rc == 0
        assert "Build a login page" in buf.getvalue()

    def test_examples_section(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = fo.main([
                "--task", "Summarize",
                "--examples", "Input: foo\nOutput: bar",
                "--format", "markdown",
            ])
        assert rc == 0
        assert "## Examples" in buf.getvalue()
