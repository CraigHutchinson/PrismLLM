"""
Unit tests for scripts/agent_review.py.

Covers all five rules (agt-001 … agt-005), the apply path, clean-file
baseline, and graceful handling of non-agent / no-frontmatter markdown.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import agent_review


# ── Fixtures ──────────────────────────────────────────────────────────────────

_FM_AGENT = """\
---
name: my-agent
description: Use this agent to do things.
model: sonnet
color: blue
---
"""

_FM_VERSIONED = """\
---
name: my-agent
description: Use this agent to do things.
model: claude-sonnet-4-5
color: blue
---
"""

_BODY_CLEAN = """\
You are a helpful assistant.

Your responsibilities:
- Write clean code following project conventions.
- Add tests only when the project manager requests them.

## When clarification is needed
- Ask specific questions about scope and requirements.
"""

_BODY_NEGATIVE = """\
You are a helpful assistant.

Your responsibilities:
- Never add tests unless explicitly requested.
- Do not read files in the .agentlogs/ folder.
- Implement features exactly as specified.
"""

_BODY_DUPLICATE = """\
You are a helpful assistant.

## Responsibilities
- Add tests only when explicitly requested by the project manager.
- Implement features exactly as specified.

## Key principles
- Add tests only when explicitly requested by the project manager.
- Follow DRY and SOLID principles.
"""

_FM_EXAMPLE_XML = """\
---
name: my-agent
description: Use this agent when needed. <example>Context: A manager assigns a task. assistant: I will use the agent.</example>
model: claude-sonnet-4-5
color: blue
---
"""

_BODY_NO_CLARIFICATION = """\
You are a helpful assistant.

Your responsibilities:
- Write clean code.
- Add tests only when requested.
"""


def _write_file(tmp_path: Path, fm: str, body: str) -> Path:
    p = tmp_path / "test_agent.md"
    p.write_text(fm + body, encoding="utf-8")
    return p


# ── agt-001: negative instructions ───────────────────────────────────────────

def test_agt001_detects_never(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_NEGATIVE)
    result = agent_review.review(p)
    rules = [i.rule_id for i in result.issues]
    assert "agt-001" in rules


def test_agt001_detects_do_not(tmp_path):
    body = "You are helpful.\n- Do not read from .agentlogs/\n"
    p = _write_file(tmp_path, _FM_VERSIONED, body)
    result = agent_review.review(p)
    assert any(i.rule_id == "agt-001" for i in result.issues)


def test_agt001_no_false_positive_on_positive_line(tmp_path):
    body = "You are helpful.\n- Add tests only when the PM requests them.\n"
    p = _write_file(tmp_path, _FM_VERSIONED, body)
    result = agent_review.review(p)
    assert not any(i.rule_id == "agt-001" for i in result.issues)


def test_agt001_issue_has_before_and_after(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_NEGATIVE)
    result = agent_review.review(p)
    agt001 = [i for i in result.issues if i.rule_id == "agt-001"]
    assert len(agt001) >= 1
    for issue in agt001:
        assert issue.before != ""
        assert issue.after != ""
        assert issue.before != issue.after


# ── agt-002: duplicate instructions ──────────────────────────────────────────

def test_agt002_detects_duplicate_across_sections(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_DUPLICATE)
    result = agent_review.review(p)
    assert any(i.rule_id == "agt-002" for i in result.issues)


def test_agt002_no_false_positive_unique_lines(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_CLEAN)
    result = agent_review.review(p)
    assert not any(i.rule_id == "agt-002" for i in result.issues)


def test_agt002_after_says_remove(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_DUPLICATE)
    result = agent_review.review(p)
    agt002 = [i for i in result.issues if i.rule_id == "agt-002"]
    assert len(agt002) >= 1
    assert "remove" in agt002[0].after.lower()


# ── agt-003: unversioned model ────────────────────────────────────────────────

def test_agt003_detects_family_name(tmp_path):
    p = _write_file(tmp_path, _FM_AGENT, _BODY_CLEAN)
    result = agent_review.review(p)
    assert any(i.rule_id == "agt-003" for i in result.issues)


def test_agt003_no_issue_when_versioned(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_CLEAN)
    result = agent_review.review(p)
    assert not any(i.rule_id == "agt-003" for i in result.issues)


def test_agt003_suggests_versioned_name(tmp_path):
    p = _write_file(tmp_path, _FM_AGENT, _BODY_CLEAN)
    result = agent_review.review(p)
    agt003 = [i for i in result.issues if i.rule_id == "agt-003"]
    assert len(agt003) == 1
    assert "claude-sonnet-4-5" in agt003[0].after


def test_agt003_no_model_field_no_issue(tmp_path):
    fm = "---\nname: my-agent\ndescription: A simple agent.\n---\n"
    p = _write_file(tmp_path, fm, _BODY_CLEAN)
    result = agent_review.review(p)
    assert not any(i.rule_id == "agt-003" for i in result.issues)


# ── agt-004: inline XML in YAML description ───────────────────────────────────

def test_agt004_detects_example_xml_in_description(tmp_path):
    p = _write_file(tmp_path, _FM_EXAMPLE_XML, _BODY_CLEAN)
    result = agent_review.review(p)
    assert any(i.rule_id == "agt-004" for i in result.issues)


def test_agt004_no_issue_when_description_is_clean(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_CLEAN)
    result = agent_review.review(p)
    assert not any(i.rule_id == "agt-004" for i in result.issues)


def test_agt004_after_suggests_body_section(tmp_path):
    p = _write_file(tmp_path, _FM_EXAMPLE_XML, _BODY_CLEAN)
    result = agent_review.review(p)
    agt004 = [i for i in result.issues if i.rule_id == "agt-004"]
    assert len(agt004) == 1
    assert "Examples" in agt004[0].after or "examples" in agt004[0].after.lower()


# ── agt-005: missing clarification section ────────────────────────────────────

def test_agt005_fires_when_no_clarification_section(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_NO_CLARIFICATION)
    result = agent_review.review(p)
    assert any(i.rule_id == "agt-005" for i in result.issues)


def test_agt005_no_issue_when_clarification_present(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_CLEAN)
    result = agent_review.review(p)
    assert not any(i.rule_id == "agt-005" for i in result.issues)


def test_agt005_after_contains_suggested_section(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_NO_CLARIFICATION)
    result = agent_review.review(p)
    agt005 = [i for i in result.issues if i.rule_id == "agt-005"]
    assert len(agt005) == 1
    assert "clarification" in agt005[0].after.lower()


# ── Clean file → zero issues ─────────────────────────────────────────────────

def test_clean_file_zero_issues(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_CLEAN)
    result = agent_review.review(p)
    assert result.issues == []
    assert result.file_type == "agent"


# ── Non-agent / no-frontmatter markdown ──────────────────────────────────────

def test_no_frontmatter_handled_gracefully(tmp_path):
    p = tmp_path / "notes.md"
    p.write_text("# Just a readme\n\nSome text here.\n", encoding="utf-8")
    result = agent_review.review(p)
    assert result.file_type == "markdown"
    # Should not crash and should return a ReviewResult
    assert isinstance(result.issues, list)


def test_skill_file_type_detected(tmp_path):
    fm = "---\nname: my-skill\ndescription: A skill.\ntools:\n  - Read\n---\n"
    p = _write_file(tmp_path, fm, _BODY_CLEAN)
    result = agent_review.review(p)
    assert result.file_type == "skill"


# ── --apply rewrites the file ─────────────────────────────────────────────────

def test_apply_rewrites_model_version(tmp_path):
    p = _write_file(tmp_path, _FM_AGENT, _BODY_CLEAN)
    result = agent_review.review(p)
    applied = agent_review.apply_fixes(p, result)
    assert applied.applied is True
    content = p.read_text(encoding="utf-8")
    assert "claude-sonnet-4-5" in content
    assert "model: sonnet\n" not in content


def test_apply_rewrites_negative_instruction(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_NEGATIVE)
    result = agent_review.review(p)
    agent_review.apply_fixes(p, result)
    content = p.read_text(encoding="utf-8")
    # Original negative lines should be gone
    assert "Never add tests unless" not in content
    assert "Do not read files in" not in content


def test_apply_appends_clarification_section(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_NO_CLARIFICATION)
    result = agent_review.review(p)
    agent_review.apply_fixes(p, result)
    content = p.read_text(encoding="utf-8")
    assert "When clarification is needed" in content


def test_apply_idempotent_on_clean_file(tmp_path):
    """Applying to a clean file should not modify it."""
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_CLEAN)
    original = p.read_text(encoding="utf-8")
    result = agent_review.review(p)
    assert result.issues == []
    # With no issues, apply should be a no-op
    agent_review.apply_fixes(p, result)
    assert p.read_text(encoding="utf-8") == original


def test_apply_sets_applied_flag(tmp_path):
    p = _write_file(tmp_path, _FM_AGENT, _BODY_NEGATIVE)
    result = agent_review.review(p)
    applied = agent_review.apply_fixes(p, result)
    assert applied.applied is True


# ── to_dict / JSON serialisation ─────────────────────────────────────────────

def test_result_to_dict_shape(tmp_path):
    p = _write_file(tmp_path, _FM_AGENT, _BODY_NEGATIVE)
    result = agent_review.review(p)
    d = result.to_dict()
    assert "file" in d
    assert "file_type" in d
    assert "issues" in d
    assert isinstance(d["issues"], list)
    for issue in d["issues"]:
        for key in ("rule_id", "severity", "section", "before", "after", "explanation"):
            assert key in issue


def test_result_to_dict_is_json_serialisable(tmp_path):
    p = _write_file(tmp_path, _FM_AGENT, _BODY_NEGATIVE)
    result = agent_review.review(p)
    raw = json.dumps(result.to_dict())
    parsed = json.loads(raw)
    assert parsed["file_type"] == "agent"


# ── CLI ───────────────────────────────────────────────────────────────────────

def test_cli_missing_file_exits_1():
    with patch("sys.argv", ["agent_review.py", "--file", "/nonexistent/path.md"]):
        with pytest.raises(SystemExit) as exc:
            agent_review.main()
    assert exc.value.code == 1


def test_cli_json_flag(tmp_path, capsys):
    p = _write_file(tmp_path, _FM_AGENT, _BODY_CLEAN)
    with patch("sys.argv", ["agent_review.py", "--file", str(p), "--json"]):
        with pytest.raises(SystemExit) as exc:
            agent_review.main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    d = json.loads(captured)
    assert "issues" in d


def test_cli_apply_flag(tmp_path):
    p = _write_file(tmp_path, _FM_AGENT, _BODY_NEGATIVE)
    with patch("sys.argv", ["agent_review.py", "--file", str(p), "--apply"]):
        with pytest.raises(SystemExit) as exc:
            agent_review.main()
    assert exc.value.code == 0
    content = p.read_text(encoding="utf-8")
    assert "claude-sonnet-4-5" in content


def test_cli_human_readable_no_issues(tmp_path, capsys):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_CLEAN)
    with patch("sys.argv", ["agent_review.py", "--file", str(p)]):
        with pytest.raises(SystemExit) as exc:
            agent_review.main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    assert "No issues" in captured
