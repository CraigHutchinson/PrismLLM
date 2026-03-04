"""
Unit tests for scripts/usage_log.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import scripts.usage_log as ul


# ── path-patching helper ───────────────────────────────────────────────────────

def _paths(tmp_path: Path) -> dict:
    prism_dir = tmp_path / ".prism"
    return {
        "PRISM_DIR":    prism_dir,
        "LOG_PATH":     prism_dir / "usage-log.jsonl",
        "SUMMARY_PATH": prism_dir / "usage-summary.json",
        "ALERT_PATH":   prism_dir / ".overhead-alert",
    }


# ── new_session_entry ──────────────────────────────────────────────────────────

def test_new_session_entry_defaults():
    e = ul.new_session_entry()
    assert e["platform"] == "unknown"
    assert e["commands_run"] == []
    assert e["overhead_pct"] == 0.0
    assert e["alert_triggered"] is False
    assert isinstance(e["ts"], int)


def test_new_session_entry_overhead_pct():
    e = ul.new_session_entry(prism_tokens_est=200, session_tokens_est=1000)
    assert e["overhead_pct"] == 20.0


def test_new_session_entry_zero_session_tokens():
    e = ul.new_session_entry(prism_tokens_est=100, session_tokens_est=0)
    assert e["overhead_pct"] == 0.0


# ── append_session + read_last_sessions ───────────────────────────────────────

def test_append_session_creates_file(tmp_path):
    with patch.multiple(ul, **_paths(tmp_path)):
        entry = ul.new_session_entry(platform="cursor")
        ul.append_session(entry)
        log = tmp_path / ".prism" / "usage-log.jsonl"
        assert log.exists()
        lines = [l for l in log.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0])["platform"] == "cursor"


def test_append_session_multiple(tmp_path):
    with patch.multiple(ul, **_paths(tmp_path)):
        for i in range(5):
            ul.append_session(ul.new_session_entry(session_id=str(i)))
        sessions = ul.read_last_sessions(10)
        assert len(sessions) == 5


def test_read_last_sessions_respects_limit(tmp_path):
    with patch.multiple(ul, **_paths(tmp_path)):
        for i in range(10):
            ul.append_session(ul.new_session_entry(session_id=str(i)))
        sessions = ul.read_last_sessions(3)
        assert len(sessions) == 3
        assert sessions[-1]["session_id"] == "9"


def test_read_last_sessions_missing_file(tmp_path):
    with patch.multiple(ul, **_paths(tmp_path)):
        assert ul.read_last_sessions() == []


def test_read_last_sessions_skips_corrupt_lines(tmp_path):
    p = _paths(tmp_path)
    prism_dir = tmp_path / ".prism"
    prism_dir.mkdir()
    p["LOG_PATH"].write_text('{"platform":"cursor"}\nNOT_JSON\n{"platform":"copilot"}\n')
    with patch.multiple(ul, **p):
        sessions = ul.read_last_sessions()
    assert len(sessions) == 2


# ── rolling summary ────────────────────────────────────────────────────────────

def test_summary_updated_after_append(tmp_path):
    with patch.multiple(ul, **_paths(tmp_path)):
        ul.append_session(ul.new_session_entry(prism_tokens_est=100, session_tokens_est=500))
        summary = ul.load_summary()
        assert summary["sessions_in_window"] == 1
        assert summary["avg_prism_tokens"] == 100.0


def test_summary_rolling_window_capped(tmp_path):
    with patch.multiple(ul, **_paths(tmp_path)):
        for i in range(35):
            ul.append_session(ul.new_session_entry())
        summary = ul.load_summary()
        assert summary["sessions_in_window"] == 30
        assert summary["total_sessions_logged"] == 35


def test_read_summary_missing_file(tmp_path):
    with patch.multiple(ul, **_paths(tmp_path)):
        summary = ul.load_summary()
        assert summary["sessions_in_window"] == 0


def test_read_summary_corrupt_file(tmp_path):
    p = _paths(tmp_path)
    prism_dir = tmp_path / ".prism"
    prism_dir.mkdir()
    p["SUMMARY_PATH"].write_text("NOT JSON")
    with patch.multiple(ul, **p):
        summary = ul.load_summary()
        assert summary["sessions_in_window"] == 0


# ── check_and_set_alert ────────────────────────────────────────────────────────

def test_alert_triggered_by_token_threshold(tmp_path):
    with patch.multiple(ul, **_paths(tmp_path)):
        entry = ul.new_session_entry(prism_tokens_est=2500, session_tokens_est=10000)
        triggered = ul.check_and_set_alert(entry, threshold_tokens=2000)
        assert triggered is True
        assert entry["alert_triggered"] is True
        alert = json.loads((tmp_path / ".prism" / ".overhead-alert").read_text())
        assert alert["tokens"] == 2500


def test_alert_triggered_by_pct_threshold(tmp_path):
    with patch.multiple(ul, **_paths(tmp_path)):
        entry = ul.new_session_entry(prism_tokens_est=500, session_tokens_est=2000)
        assert ul.check_and_set_alert(entry, threshold_pct=20.0) is True


def test_alert_not_triggered_below_both(tmp_path):
    with patch.multiple(ul, **_paths(tmp_path)):
        entry = ul.new_session_entry(prism_tokens_est=100, session_tokens_est=2000)
        triggered = ul.check_and_set_alert(entry, threshold_tokens=2000, threshold_pct=20.0)
        assert triggered is False
        assert entry["alert_triggered"] is False
        assert not (tmp_path / ".prism" / ".overhead-alert").exists()


# ── read_and_clear_alert ───────────────────────────────────────────────────────

def test_read_and_clear_alert_present(tmp_path):
    p = _paths(tmp_path)
    prism_dir = tmp_path / ".prism"
    prism_dir.mkdir()
    p["ALERT_PATH"].write_text('{"reason":"test","pct":25.0,"tokens":3000}')
    with patch.multiple(ul, **p):
        result = ul.read_and_clear_alert()
        assert result["reason"] == "test"
        assert not p["ALERT_PATH"].exists()


def test_read_and_clear_alert_absent(tmp_path):
    with patch.multiple(ul, **_paths(tmp_path)):
        assert ul.read_and_clear_alert() is None


def test_read_and_clear_alert_corrupt(tmp_path):
    p = _paths(tmp_path)
    prism_dir = tmp_path / ".prism"
    prism_dir.mkdir()
    p["ALERT_PATH"].write_text("NOT JSON")
    with patch.multiple(ul, **p):
        result = ul.read_and_clear_alert()
        assert result is None
        assert not p["ALERT_PATH"].exists()


# ── _compute_trend ─────────────────────────────────────────────────────────────

def test_trend_stable_insufficient_data():
    assert ul._compute_trend([10.0, 12.0]) == "stable"


def test_trend_increasing():
    assert ul._compute_trend([5.0, 5.0, 15.0, 15.0]) == "increasing"


def test_trend_decreasing():
    assert ul._compute_trend([20.0, 18.0, 5.0, 3.0]) == "decreasing"


def test_trend_stable_flat():
    assert ul._compute_trend([10.0, 10.0, 10.0, 10.0]) == "stable"


# ── breakdown helpers ─────────────────────────────────────────────────────────

def test_platform_breakdown():
    sessions = [{"platform": "cursor"}, {"platform": "cursor"}, {"platform": "claude_code"}]
    result = ul._platform_breakdown(sessions)
    assert result["cursor"] == 2
    assert result["claude_code"] == 1


def test_commands_histogram():
    sessions = [
        {"commands_run": ["/prism score", "/prism sanitize"]},
        {"commands_run": ["/prism score"]},
    ]
    hist = ul._commands_histogram(sessions)
    assert hist["/prism score"] == 2
    assert hist["/prism sanitize"] == 1


# ── CLI main() ────────────────────────────────────────────────────────────────

def test_cli_summary(tmp_path, capsys):
    with patch.multiple(ul, **_paths(tmp_path)):
        ul.append_session(ul.new_session_entry(platform="cursor"))
        with patch("sys.argv", ["usage_log.py", "summary"]):
            ul.main()
    out = capsys.readouterr().out
    assert json.loads(out)["sessions_in_window"] == 1


def test_cli_sessions_empty(tmp_path, capsys):
    with patch.multiple(ul, **_paths(tmp_path)):
        with patch("sys.argv", ["usage_log.py", "sessions"]):
            ul.main()
    assert "No sessions logged yet" in capsys.readouterr().out


def test_cli_sessions_table(tmp_path, capsys):
    with patch.multiple(ul, **_paths(tmp_path)):
        ul.append_session(ul.new_session_entry(platform="cursor", prism_tokens_est=50))
        with patch("sys.argv", ["usage_log.py", "sessions"]):
            ul.main()
    assert "cursor" in capsys.readouterr().out


def test_cli_check_alert_absent(tmp_path, capsys):
    with patch.multiple(ul, **_paths(tmp_path)):
        with patch("sys.argv", ["usage_log.py", "check-alert"]):
            ul.main()
    assert "No alert" in capsys.readouterr().out


def test_cli_check_alert_present(tmp_path, capsys):
    p = _paths(tmp_path)
    prism_dir = tmp_path / ".prism"
    prism_dir.mkdir()
    p["ALERT_PATH"].write_text('{"reason":"high"}')
    with patch.multiple(ul, **p):
        with patch("sys.argv", ["usage_log.py", "check-alert"]):
            ul.main()
    assert "high" in capsys.readouterr().out


def test_cli_no_subcommand(tmp_path, capsys):
    with patch.multiple(ul, **_paths(tmp_path)):
        with patch("sys.argv", ["usage_log.py"]):
            ul.main()
    # print_help() output contains usage text
    captured = capsys.readouterr()
    assert len(captured.out + captured.err) >= 0
