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
        # after is a placeholder directing the user to run /prism improve for the LLM rewrite
        assert issue.after == agent_review._AGT001_PLACEHOLDER
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


def test_agt004_description_only_example_uses_fallback(tmp_path):
    """When the description text before <example> is empty, the fallback text is used."""
    # _parse_frontmatter takes the raw value after ':', so no surrounding quotes here
    fm = (
        "---\nname: my-agent\n"
        "description: <example>Context: foo. assistant: bar.</example>\n"
        "model: claude-sonnet-4-5\ncolor: blue\n---\n"
    )
    p = _write_file(tmp_path, fm, _BODY_CLEAN)
    result = agent_review.review(p)
    agt004 = [i for i in result.issues if i.rule_id == "agt-004"]
    assert len(agt004) == 1
    assert "implement specific functionality" in agt004[0].after


def test_agt004_after_suggests_body_section(tmp_path):
    p = _write_file(tmp_path, _FM_EXAMPLE_XML, _BODY_CLEAN)
    result = agent_review.review(p)
    agt004 = [i for i in result.issues if i.rule_id == "agt-004"]
    assert len(agt004) == 1
    assert "Examples" in agt004[0].after or "examples" in agt004[0].after.lower()


def test_agt004_meta_contains_examples_body(tmp_path):
    """agt-004 issue must carry extracted example content in meta['examples_body']."""
    p = _write_file(tmp_path, _FM_EXAMPLE_XML, _BODY_CLEAN)
    result = agent_review.review(p)
    agt004 = [i for i in result.issues if i.rule_id == "agt-004"][0]
    assert "examples_body" in agt004.meta
    body = agt004.meta["examples_body"]
    assert "## Examples" in body
    # Verify dialogue content is preserved, not discarded
    assert "A manager assigns a task" in body or "manager" in body.lower()


def test_agt004_meta_examples_body_has_role_labels(tmp_path):
    """Extracted examples must format context and assistant turns as markdown."""
    fm = (
        "---\nname: my-agent\n"
        "description: Use this agent. "
        "<example>Context: A PM assigns work. assistant: I will do it.</example>\n"
        "model: claude-sonnet-4-5\ncolor: blue\n---\n"
    )
    p = _write_file(tmp_path, fm, _BODY_CLEAN)
    result = agent_review.review(p)
    agt004 = [i for i in result.issues if i.rule_id == "agt-004"][0]
    body = agt004.meta["examples_body"]
    assert "**Context:**" in body
    assert "**assistant:**" in body or "assistant" in body.lower()


def test_agt004_meta_empty_when_no_example_content(tmp_path):
    """If <example> blocks have no parseable content, meta may be empty or minimal."""
    fm = (
        "---\nname: my-agent\n"
        "description: <example></example>\n"
        "model: claude-sonnet-4-5\ncolor: blue\n---\n"
    )
    p = _write_file(tmp_path, fm, _BODY_CLEAN)
    result = agent_review.review(p)
    agt004 = [i for i in result.issues if i.rule_id == "agt-004"]
    # Issue is still raised; meta may or may not have examples_body
    assert len(agt004) == 1


def test_agt004_apply_appends_examples_section_to_body(tmp_path):
    """--apply must write a ## Examples section preserving all example content."""
    p = _write_file(tmp_path, _FM_EXAMPLE_XML, _BODY_CLEAN)
    result = agent_review.review(p)
    agent_review.apply_fixes(p, result)
    content = p.read_text(encoding="utf-8")
    assert "## Examples" in content
    # Original <example> XML must be gone from the file
    assert "<example>" not in content
    # Example dialogue content must be in the body
    assert "A manager assigns a task" in content


def test_agt004_apply_does_not_duplicate_examples_on_rerun(tmp_path):
    """Re-running apply on an already-fixed file must not add a second Examples section."""
    p = _write_file(tmp_path, _FM_EXAMPLE_XML, _BODY_CLEAN)
    result = agent_review.review(p)
    agent_review.apply_fixes(p, result)
    # Run again on the already-fixed file
    result2 = agent_review.review(p)
    agt004_issues = [i for i in result2.issues if i.rule_id == "agt-004"]
    assert len(agt004_issues) == 0  # agt-004 should not fire on already-fixed file
    content = p.read_text(encoding="utf-8")
    assert content.count("## Examples") == 1


def test_agt004_multiple_examples_numbered_with_separator(tmp_path):
    """Two <example> blocks produce numbered headings and a --- separator."""
    fm = (
        "---\nname: my-agent\n"
        "description: Use this when needed. "
        "<example>Context: First task. assistant: Done first.</example> "
        "<example>Context: Second task. assistant: Done second.</example>\n"
        "model: claude-sonnet-4-5\ncolor: blue\n---\n"
    )
    p = _write_file(tmp_path, fm, _BODY_CLEAN)
    result = agent_review.review(p)
    agt004 = [i for i in result.issues if i.rule_id == "agt-004"][0]
    body = agt004.meta["examples_body"]
    assert "**Example 1**" in body
    assert "**Example 2**" in body
    assert "---" in body  # separator between examples


def test_agt004_to_dict_includes_meta(tmp_path):
    """Issue.to_dict() must include 'meta' key when meta is non-empty."""
    p = _write_file(tmp_path, _FM_EXAMPLE_XML, _BODY_CLEAN)
    result = agent_review.review(p)
    agt004 = [i for i in result.issues if i.rule_id == "agt-004"][0]
    d = agt004.to_dict()
    assert "meta" in d
    assert "examples_body" in d["meta"]


def test_agt004_strips_trailing_examples_label(tmp_path):
    """Orphaned 'Examples:' label left after stripping <example> XML must be removed."""
    fm = (
        "---\nname: my-agent\n"
        "description: Use this agent when needed. Examples: <example>foo</example>\n"
        "model: claude-sonnet-4-5\ncolor: blue\n---\n"
    )
    p = _write_file(tmp_path, fm, _BODY_CLEAN)
    result = agent_review.review(p)
    agt004 = [i for i in result.issues if i.rule_id == "agt-004"]
    assert len(agt004) == 1
    # The 'after' description must not end with "Examples:" or any orphaned label
    after_desc = agt004[0].after.split("\n")[0]  # first line = "description: ..."
    assert not after_desc.rstrip().endswith(":")
    assert "Examples:" not in after_desc


def test_agt004_clean_description_strips_label_variants(tmp_path):
    """_clean_description handles common label variants: e.g., See:, Note:, Usage:"""
    for label in ["Examples:", "Example:", "e.g.:", "See:", "Usage:"]:
        fm = (
            "---\nname: my-agent\n"
            f"description: Use this when needed. {label} <example>foo</example>\n"
            "model: claude-sonnet-4-5\ncolor: blue\n---\n"
        )
        p = _write_file(tmp_path, fm, _BODY_CLEAN)
        result = agent_review.review(p)
        agt004 = [i for i in result.issues if i.rule_id == "agt-004"]
        assert len(agt004) == 1, f"Expected agt-004 for label {label!r}"
        after_desc = agt004[0].after.split("\n")[0]
        assert not after_desc.rstrip().endswith(":"), (
            f"Orphaned label not stripped for {label!r}: {after_desc!r}"
        )


# ── agt-006: dangling/truncated description ───────────────────────────────────

def test_agt006_detects_description_ending_with_colon(tmp_path):
    fm = (
        "---\nname: my-agent\n"
        "description: Use this agent when needed. Examples:\n"
        "model: claude-sonnet-4-5\ncolor: blue\n---\n"
    )
    p = _write_file(tmp_path, fm, _BODY_CLEAN)
    result = agent_review.review(p)
    assert any(i.rule_id == "agt-006" for i in result.issues)


def test_agt006_detects_orphaned_label_word(tmp_path):
    """Description ending in a bare label word like 'Examples' (no colon) is also flagged."""
    fm = (
        "---\nname: my-agent\n"
        "description: Use this agent when needed. See:\n"
        "model: claude-sonnet-4-5\ncolor: blue\n---\n"
    )
    p = _write_file(tmp_path, fm, _BODY_CLEAN)
    result = agent_review.review(p)
    assert any(i.rule_id == "agt-006" for i in result.issues)


def test_agt006_no_issue_on_clean_description(tmp_path):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_CLEAN)
    result = agent_review.review(p)
    assert not any(i.rule_id == "agt-006" for i in result.issues)


def test_agt006_no_issue_on_sentence_ending_with_period(tmp_path):
    fm = (
        "---\nname: my-agent\n"
        "description: Use this agent to implement features as directed.\n"
        "model: claude-sonnet-4-5\ncolor: blue\n---\n"
    )
    p = _write_file(tmp_path, fm, _BODY_CLEAN)
    result = agent_review.review(p)
    assert not any(i.rule_id == "agt-006" for i in result.issues)


def test_agt006_explanation_mentions_truncation(tmp_path):
    fm = (
        "---\nname: my-agent\n"
        "description: Use this agent when needed. Examples:\n"
        "model: claude-sonnet-4-5\ncolor: blue\n---\n"
    )
    p = _write_file(tmp_path, fm, _BODY_CLEAN)
    result = agent_review.review(p)
    agt006 = [i for i in result.issues if i.rule_id == "agt-006"]
    assert len(agt006) == 1
    assert "truncat" in agt006[0].explanation.lower() or "colon" in agt006[0].explanation.lower()


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


def test_detect_file_type_no_name_returns_markdown(tmp_path):
    """Frontmatter without a 'name' key → file_type is 'markdown'."""
    fm = "---\nauthor: someone\nversion: 1\n---\n"
    p = _write_file(tmp_path, fm, _BODY_CLEAN)
    result = agent_review.review(p)
    assert result.file_type == "markdown"


# ── --apply rewrites the file ─────────────────────────────────────────────────

def test_apply_rewrites_model_version(tmp_path):
    p = _write_file(tmp_path, _FM_AGENT, _BODY_CLEAN)
    result = agent_review.review(p)
    applied = agent_review.apply_fixes(p, result)
    assert applied.applied is True
    content = p.read_text(encoding="utf-8")
    assert "claude-sonnet-4-5" in content
    assert "model: sonnet\n" not in content


def test_apply_without_rewrite_map_preserves_agt001_lines(tmp_path):
    """Without a rewrite map, agt-001 lines must be left unchanged (no placeholders written)."""
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_NEGATIVE)
    result = agent_review.review(p)
    agent_review.apply_fixes(p, result)
    content = p.read_text(encoding="utf-8")
    # Negative lines must remain — not replaced with broken placeholder text
    assert "Never add tests unless explicitly requested" in content
    assert "Do not read files in the .agentlogs/ folder" in content
    assert agent_review._AGT001_PLACEHOLDER not in content


def test_apply_with_rewrite_map_applies_llm_rewrites(tmp_path):
    """When a rewrite_map is provided, agt-001 lines are replaced with LLM rewrites."""
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_NEGATIVE)
    result = agent_review.review(p)
    rewrite_map = {
        "- Never add tests unless explicitly requested.": (
            "- Add tests only when the project manager explicitly requests them."
        ),
        "- Do not read files in the .agentlogs/ folder.": (
            "- Restrict file access to approved directories; skip .agentlogs/ unless explicitly permitted."
        ),
    }
    agent_review.apply_fixes(p, result, rewrite_map=rewrite_map)
    content = p.read_text(encoding="utf-8")
    assert "Never add tests" not in content
    assert "Do not read files" not in content
    assert "Add tests only when" in content
    assert agent_review._AGT001_PLACEHOLDER not in content


def test_apply_removes_duplicate_instruction(tmp_path):
    """apply_fixes removes agt-002 duplicate lines from the file."""
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_DUPLICATE)
    result = agent_review.review(p)
    assert any(i.rule_id == "agt-002" for i in result.issues)
    agent_review.apply_fixes(p, result)
    content = p.read_text(encoding="utf-8")
    # The duplicate line should appear only once after apply
    count = content.count("Add tests only when explicitly requested by the project manager.")
    assert count == 1


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


def test_cli_rewrite_map_flag(tmp_path):
    """--rewrite-map applies LLM rewrites via the CLI."""
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_NEGATIVE)
    rewrite_map_json = (
        '{"- Never add tests unless explicitly requested.": '
        '"- Add tests only when the project manager explicitly requests them."}'
    )
    with patch("sys.argv", [
        "agent_review.py", "--file", str(p), "--apply",
        "--rewrite-map", rewrite_map_json,
    ]):
        with pytest.raises(SystemExit) as exc:
            agent_review.main()
    assert exc.value.code == 0
    content = p.read_text(encoding="utf-8")
    assert "Add tests only when the project manager explicitly requests them." in content


def test_cli_rewrite_map_invalid_json(tmp_path):
    """--rewrite-map with malformed JSON exits 1."""
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_NEGATIVE)
    with patch("sys.argv", [
        "agent_review.py", "--file", str(p), "--apply",
        "--rewrite-map", "not-json",
    ]):
        with pytest.raises(SystemExit) as exc:
            agent_review.main()
    assert exc.value.code == 1


def test_cli_human_readable_no_issues(tmp_path, capsys):
    p = _write_file(tmp_path, _FM_VERSIONED, _BODY_CLEAN)
    with patch("sys.argv", ["agent_review.py", "--file", str(p)]):
        with pytest.raises(SystemExit) as exc:
            agent_review.main()
    assert exc.value.code == 0
    captured = capsys.readouterr().out
    assert "No issues" in captured
