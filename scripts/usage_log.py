"""
usage_log.py
------------
Session overhead log management for Prism.

Manages two files in .prism/:
  - usage-log.jsonl    : per-session entries (append-only)
  - usage-summary.json : rolling 30-session statistics

Called by:
  - hooks/prism_preparser.py (stop/sessionEnd hook) to append session entry
  - SKILL.md dispatch (/prism usage) to read and format the summary
  - overhead_calc.py (at sessionStart) to snapshot component sizes

No model required.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRISM_ROOT  = Path(__file__).resolve().parent.parent
PRISM_DIR   = PRISM_ROOT / ".prism"
LOG_PATH    = PRISM_DIR / "usage-log.jsonl"
SUMMARY_PATH = PRISM_DIR / "usage-summary.json"
ROLLING_WINDOW = 30


# ── Schema ─────────────────────────────────────────────────────────────────────

def new_session_entry(
    platform: str = "unknown",
    session_id: str = "",
    commands_run: list[str] | None = None,
    prism_tokens_est: int = 0,
    session_tokens_est: int = 0,
    hook_stages_fired: dict | None = None,
) -> dict[str, Any]:
    overhead_pct = 0.0
    if session_tokens_est > 0:
        overhead_pct = round(prism_tokens_est / session_tokens_est * 100, 1)

    return {
        "ts":                 int(datetime.now(timezone.utc).timestamp()),
        "platform":           platform,
        "session_id":         session_id,
        "commands_run":       commands_run or [],
        "hook_stages_fired":  hook_stages_fired or {"stage1": 0, "stage2": 0},
        "prism_tokens_est":   prism_tokens_est,
        "session_tokens_est": session_tokens_est,
        "overhead_pct":       overhead_pct,
        "alert_triggered":    False,
    }


# ── Log append ─────────────────────────────────────────────────────────────────

def append_session(entry: dict[str, Any]) -> None:
    """Append a session entry to usage-log.jsonl."""
    PRISM_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    _update_summary()


def _update_summary() -> None:
    """Recompute rolling 30-session statistics from usage-log.jsonl."""
    sessions = read_last_sessions(ROLLING_WINDOW)
    if not sessions:
        summary = _empty_summary()
    else:
        prism_tokens_list = [s.get("prism_tokens_est", 0) for s in sessions]
        session_tokens_list = [s.get("session_tokens_est", 0) for s in sessions]
        overhead_pct_list = [s.get("overhead_pct", 0.0) for s in sessions]

        summary = {
            "generated_at":            _now_iso(),
            "sessions_in_window":      len(sessions),
            "total_sessions_logged":   _count_total_sessions(),
            "avg_prism_tokens":        _safe_avg(prism_tokens_list),
            "avg_session_tokens":      _safe_avg(session_tokens_list),
            "avg_overhead_pct":        round(_safe_avg(overhead_pct_list), 1),
            "max_overhead_pct":        max(overhead_pct_list) if overhead_pct_list else 0.0,
            "trend":                   _compute_trend(overhead_pct_list),
            "alerts_in_window":        sum(1 for s in sessions if s.get("alert_triggered")),
            "platforms":               _platform_breakdown(sessions),
            "commands_histogram":      _commands_histogram(sessions),
            "last_session_ts":         sessions[-1]["ts"] if sessions else None,
        }

    PRISM_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")


# ── Read helpers ───────────────────────────────────────────────────────────────

def read_last_sessions(n: int = ROLLING_WINDOW) -> list[dict]:
    if not LOG_PATH.exists():
        return []
    entries: list[dict] = []
    with LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries[-n:]


def load_summary() -> dict[str, Any]:
    if SUMMARY_PATH.exists():
        try:
            return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return _empty_summary()


read_summary = load_summary  # backwards-compat alias


def _count_total_sessions() -> int:
    if not LOG_PATH.exists():
        return 0
    count = 0
    with LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


# ── Overhead alert ─────────────────────────────────────────────────────────────

ALERT_PATH = PRISM_DIR / ".overhead-alert"


def check_and_set_alert(
    entry: dict[str, Any],
    threshold_tokens: int = 2000,
    threshold_pct: float = 20.0,
) -> bool:
    """
    If overhead exceeds thresholds, write .overhead-alert flag and return True.
    Called at the end of each session (stop hook).
    """
    triggered = (
        entry.get("prism_tokens_est", 0) > threshold_tokens
        or entry.get("overhead_pct", 0.0) > threshold_pct
    )
    if triggered:
        reason = (
            f"prism_tokens={entry.get('prism_tokens_est', 0)}, "
            f"overhead_pct={entry.get('overhead_pct', 0.0):.1f}%"
        )
        alert = {
            "ts":         entry.get("ts"),
            "session_id": entry.get("session_id", ""),
            "reason":     reason,
            "pct":        entry.get("overhead_pct", 0.0),
            "tokens":     entry.get("prism_tokens_est", 0),
        }
        PRISM_DIR.mkdir(parents=True, exist_ok=True)
        ALERT_PATH.write_text(json.dumps(alert, indent=2), encoding="utf-8")
        entry["alert_triggered"] = True
    return triggered


def read_and_clear_alert() -> dict | None:
    """
    Read .overhead-alert if it exists and clear it.
    Called at sessionStart to inject advisory if needed.
    """
    if not ALERT_PATH.exists():
        return None
    try:
        alert = json.loads(ALERT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        alert = None
    ALERT_PATH.unlink(missing_ok=True)
    return alert


# ── Summary helpers ────────────────────────────────────────────────────────────

def _empty_summary() -> dict[str, Any]:
    return {
        "generated_at":       _now_iso(),
        "sessions_in_window": 0,
        "total_sessions_logged": 0,
        "avg_prism_tokens":   0,
        "avg_session_tokens": 0,
        "avg_overhead_pct":   0.0,
        "max_overhead_pct":   0.0,
        "trend":              "stable",
        "alerts_in_window":   0,
        "platforms":          {},
        "commands_histogram": {},
        "last_session_ts":    None,
    }


def _safe_avg(lst: list[float | int]) -> float:
    return sum(lst) / len(lst) if lst else 0.0


def _compute_trend(pct_list: list[float]) -> str:
    if len(pct_list) < 4:
        return "stable"
    first_half  = _safe_avg(pct_list[: len(pct_list) // 2])
    second_half = _safe_avg(pct_list[len(pct_list) // 2:])
    delta = second_half - first_half
    if delta > 2.0:
        return "increasing"
    if delta < -2.0:
        return "decreasing"
    return "stable"


def _platform_breakdown(sessions: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in sessions:
        p = s.get("platform", "unknown")
        counts[p] = counts.get(p, 0) + 1
    return counts


def _commands_histogram(sessions: list[dict]) -> dict[str, int]:
    hist: dict[str, int] = {}
    for s in sessions:
        for cmd in s.get("commands_run", []):
            hist[cmd] = hist.get(cmd, 0) + 1
    return hist


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Manage Prism usage logs.")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("summary", help="Print usage summary")
    sub.add_parser("sessions", help="Print last 30 sessions")
    sub.add_parser("check-alert", help="Print and clear any overhead alert")

    args = parser.parse_args()

    if args.cmd == "summary":
        summary = load_summary()
        print(json.dumps(summary, indent=2))

    elif args.cmd == "sessions":
        sessions = read_last_sessions()
        if not sessions:
            print("No sessions logged yet.")
        else:
            print(f"{'Date':<20} {'Platform':<14} {'Prism t':>8} {'Session t':>10} {'Overhead':>9}")
            print("-" * 65)
            for s in sessions:
                dt = datetime.fromtimestamp(s["ts"], timezone.utc).strftime("%Y-%m-%d %H:%M")
                alert = " ⚠" if s.get("alert_triggered") else ""
                print(f"{dt:<20} {s.get('platform','?'):<14} "
                      f"{s.get('prism_tokens_est',0):>8} "
                      f"{s.get('session_tokens_est',0):>10} "
                      f"{s.get('overhead_pct',0):.1f}%{alert}")

    elif args.cmd == "check-alert":
        alert = read_and_clear_alert()
        if alert:
            print(json.dumps(alert, indent=2))
        else:
            print("No alert.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
