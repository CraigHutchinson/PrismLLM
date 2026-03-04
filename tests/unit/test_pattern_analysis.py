"""
Unit tests for scripts/pattern_analysis.py.
Focuses on deterministic metric computation (no model calls).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
import pattern_analysis


def test_empty_entries_returns_stable_trend():
    profile = pattern_analysis.build_style_profile([])
    assert profile["trend"] == "stable"
    assert profile["prompts_analysed"] == 0
    assert profile["detected_patterns"] == []


def test_efficiency_ratio_average(prompt_log_fixture):
    profile = pattern_analysis.build_style_profile(prompt_log_fixture)
    assert 0.0 < profile["avg_efficiency_ratio"] <= 1.0


def test_avg_token_count_positive(prompt_log_fixture):
    profile = pattern_analysis.build_style_profile(prompt_log_fixture)
    assert profile["avg_token_count"] > 0


def test_prompts_analysed_count(prompt_log_fixture):
    profile = pattern_analysis.build_style_profile(prompt_log_fixture)
    assert profile["prompts_analysed"] == len(prompt_log_fixture)


def test_detects_royal_we_pattern(prompt_log_fixture):
    profile = pattern_analysis.build_style_profile(prompt_log_fixture)
    patterns = {p["pattern"]: p for p in profile["detected_patterns"]}
    assert "we shall" in patterns or any(
        p["category"] == "royal_we" for p in profile["detected_patterns"]
    )


def test_detected_pattern_has_required_fields(prompt_log_fixture):
    profile = pattern_analysis.build_style_profile(prompt_log_fixture)
    for p in profile["detected_patterns"]:
        assert "pattern" in p
        assert "category" in p
        assert "frequency" in p
        assert "suggestion" in p
        assert 0.0 <= p["frequency"] <= 1.0


def test_trend_values_are_valid(prompt_log_fixture):
    profile = pattern_analysis.build_style_profile(prompt_log_fixture)
    assert profile["trend"] in ("improving", "stable", "declining")


def test_summary_is_non_empty(prompt_log_fixture):
    profile = pattern_analysis.build_style_profile(prompt_log_fixture)
    assert isinstance(profile["summary"], str)
    assert len(profile["summary"]) > 10


def test_compute_efficiency_trend_improving():
    ratios = [0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95]
    result = pattern_analysis._compute_efficiency_trend(ratios)
    assert result == "improving"


def test_compute_efficiency_trend_declining():
    ratios = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6]
    result = pattern_analysis._compute_efficiency_trend(ratios)
    assert result == "declining"


def test_compute_efficiency_trend_stable():
    ratios = [0.85, 0.86, 0.85, 0.84, 0.85, 0.86]
    result = pattern_analysis._compute_efficiency_trend(ratios)
    assert result == "stable"


def test_too_few_entries_for_trend():
    result = pattern_analysis._compute_efficiency_trend([0.8, 0.9])
    assert result == "stable"


def test_generate_cursor_rule_contains_date(prompt_log_fixture):
    profile = pattern_analysis.build_style_profile(prompt_log_fixture)
    rule = pattern_analysis.generate_cursor_rule(profile)
    assert "alwaysApply: true" in rule
    from datetime import date
    assert date.today().isoformat() in rule


def test_write_style_profile(tmp_path):
    profile = {"detected_patterns": [], "avg_efficiency_ratio": 0.9,
               "avg_token_count": 15, "trend": "stable", "prompts_analysed": 5}
    path = tmp_path / "style-profile.json"
    pattern_analysis.write_style_profile(profile, path)
    assert path.exists()
    import json
    data = json.loads(path.read_text())
    assert data["trend"] == "stable"


def test_write_analysis_report(tmp_path, prompt_log_fixture):
    profile = pattern_analysis.build_style_profile(prompt_log_fixture)
    report = pattern_analysis.write_analysis_report(profile, output_dir=tmp_path)
    assert report.exists()
    content = report.read_text()
    assert "Prism Pattern Analysis" in content


# ── read_prompt_log branches ──────────────────────────────────────────────────

def test_read_prompt_log_missing(tmp_path):
    result = pattern_analysis.read_prompt_log(tmp_path / "missing.jsonl")
    assert result == []


def test_read_prompt_log_skips_corrupt_lines(tmp_path):
    log = tmp_path / "log.jsonl"
    log.write_text('{"ts":1,"tokens_est":10,"efficiency_ratio":0.9}\nNOT_JSON\n{"ts":2,"tokens_est":15,"efficiency_ratio":0.8}\n')
    result = pattern_analysis.read_prompt_log(log)
    assert len(result) == 2


# ── generate_cursor_rule ──────────────────────────────────────────────────────

def test_generate_cursor_rule_with_patterns(prompt_log_fixture):
    profile = pattern_analysis.build_style_profile(prompt_log_fixture)
    rule = pattern_analysis.generate_cursor_rule(profile)
    assert "prism" in rule.lower() or "pattern" in rule.lower() or "---" in rule


def test_generate_cursor_rule_empty_profile():
    profile = pattern_analysis.build_style_profile([])
    rule = pattern_analysis.generate_cursor_rule(profile)
    assert isinstance(rule, str)


# ── run() ────────────────────────────────────────────────────────────────────

def test_run_with_empty_log(tmp_path):
    log = tmp_path / "prompt-log.jsonl"
    log.write_text("")
    profile_path = tmp_path / "style-profile.json"
    with patch.object(pattern_analysis, "STYLE_PROFILE_PATH", profile_path):
        with patch.object(pattern_analysis, "ANALYSIS_NEEDED_FLAG", tmp_path / ".analysis-needed"):
            profile = pattern_analysis.run(log_path=log)
    assert profile["trend"] == "stable"


# ── CLI main() ────────────────────────────────────────────────────────────────

def test_cli_main_no_entries(tmp_path, capsys):
    log = tmp_path / "prompt-log.jsonl"
    with patch("sys.argv", ["pattern_analysis.py", "--log", str(log)]):
        pattern_analysis.main()
    err = capsys.readouterr().err
    assert "No prompts logged" in err


def test_cli_main_json_output(tmp_path, capsys, prompt_log_fixture):
    log = tmp_path / "prompt-log.jsonl"
    log.write_text("\n".join(json.dumps(e) for e in prompt_log_fixture) + "\n")
    profile_path = tmp_path / "style-profile.json"
    with patch("sys.argv", ["pattern_analysis.py", "--log", str(log), "--json"]):
        with patch.object(pattern_analysis, "STYLE_PROFILE_PATH", profile_path):
            pattern_analysis.main()
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "trend" in data


def test_cli_main_report(tmp_path, capsys, prompt_log_fixture):
    log = tmp_path / "prompt-log.jsonl"
    log.write_text("\n".join(json.dumps(e) for e in prompt_log_fixture) + "\n")
    profile_path = tmp_path / "style-profile.json"
    with patch("sys.argv", ["pattern_analysis.py", "--log", str(log), "--report"]):
        with patch.object(pattern_analysis, "STYLE_PROFILE_PATH", profile_path):
            with patch.object(pattern_analysis, "PRISM_ROOT", tmp_path):
                pattern_analysis.main()
    err = capsys.readouterr().err
    assert "Report written" in err


def test_cli_main_cursor_rule(tmp_path, capsys, prompt_log_fixture):
    log = tmp_path / "prompt-log.jsonl"
    log.write_text("\n".join(json.dumps(e) for e in prompt_log_fixture) + "\n")
    profile_path = tmp_path / "style-profile.json"
    with patch("sys.argv", ["pattern_analysis.py", "--log", str(log), "--cursor-rule"]):
        with patch.object(pattern_analysis, "STYLE_PROFILE_PATH", profile_path):
            pattern_analysis.main()
    out = capsys.readouterr().out
    assert isinstance(out, str)


def test_cli_main_default_output(tmp_path, capsys, prompt_log_fixture):
    log = tmp_path / "prompt-log.jsonl"
    log.write_text("\n".join(json.dumps(e) for e in prompt_log_fixture) + "\n")
    profile_path = tmp_path / "style-profile.json"
    with patch("sys.argv", ["pattern_analysis.py", "--log", str(log)]):
        with patch.object(pattern_analysis, "STYLE_PROFILE_PATH", profile_path):
            pattern_analysis.main()
    out = capsys.readouterr().out
    assert isinstance(out, str)
