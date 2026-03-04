"""
pattern_analysis.py
--------------------
Reads .prism/prompt-log.jsonl, analyses personal writing patterns,
computes trend metrics, and outputs:
  - .prism/style-profile.json    : machine-readable style profile
  - .prism/analysis-YYYYMMDD.md  : human-readable report

Called by:
  - hooks/prism_preparser.py (stop/sessionEnd hook, background)
  - SKILL.md dispatch (/prism patterns)

Stage 1: Deterministic metrics from verbosity_patterns.json (no model).
Stage 2: Fast-model analysis to detect idioms beyond the seeded list
         (only when --model is provided).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

PRISM_ROOT         = Path(__file__).resolve().parent.parent
PROMPT_LOG_PATH    = PRISM_ROOT / ".prism" / "prompt-log.jsonl"
STYLE_PROFILE_PATH = PRISM_ROOT / ".prism" / "style-profile.json"
ANALYSIS_NEEDED_FLAG = PRISM_ROOT / ".prism" / ".analysis-needed"
VERBOSITY_PATTERNS_PATH = PRISM_ROOT / "scripts" / "verbosity_patterns.json"


# ── Load verbosity patterns ────────────────────────────────────────────────────

def _load_verbosity_patterns() -> list[dict]:
    if VERBOSITY_PATTERNS_PATH.exists():
        data = json.loads(VERBOSITY_PATTERNS_PATH.read_text(encoding="utf-8"))
        return data.get("patterns", [])
    return []


# ── Read prompt log ────────────────────────────────────────────────────────────

def read_prompt_log(path: Path = PROMPT_LOG_PATH, limit: int = 500) -> list[dict]:
    if not path.exists():
        return []
    entries: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries[-limit:]


# ── Deterministic analysis ─────────────────────────────────────────────────────

def build_style_profile(
    entries: list[dict],
    verbosity_patterns: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Compute pattern frequency metrics from prompt log entries.
    Returns a dict matching the pattern_output.json schema.
    """
    if verbosity_patterns is None:
        verbosity_patterns = _load_verbosity_patterns()

    if not entries:
        return {
            "detected_patterns":   [],
            "avg_efficiency_ratio": 1.0,
            "avg_token_count":     0.0,
            "trend":               "stable",
            "prompts_analysed":    0,
            "summary":             "Not enough data yet (0 prompts analysed).",
        }

    n = len(entries)
    all_text = " ".join(e.get("prompt_scrubbed", "") for e in entries)
    token_counts = [e.get("tokens_est", 0) for e in entries]
    efficiency_ratios = [e.get("efficiency_ratio", 1.0) for e in entries]

    avg_tokens = sum(token_counts) / n if n else 0.0
    avg_efficiency = sum(efficiency_ratios) / n if n else 1.0

    # Pattern frequency counting
    detected: list[dict] = []
    for pat in verbosity_patterns:
        phrase = pat.get("phrase", "")
        pattern_re = re.compile(r"\b" + re.escape(phrase) + r"\b", re.IGNORECASE)
        matches_per_prompt = [
            len(pattern_re.findall(e.get("prompt_scrubbed", ""))) for e in entries
        ]
        total_hits = sum(1 for m in matches_per_prompt if m > 0)
        freq = total_hits / n if n else 0.0
        if freq >= 0.05:
            detected.append({
                "pattern":    phrase,
                "category":   pat.get("category", "other"),
                "frequency":  round(freq, 3),
                "token_cost": pat.get("token_saving", 1),
                "suggestion": pat.get("terse_alt", "(use direct phrasing)"),
            })

    detected.sort(key=lambda x: x["frequency"], reverse=True)

    # Trend computation
    trend = _compute_efficiency_trend(efficiency_ratios)

    # Token cost of top patterns per prompt
    top_patterns_cost = sum(
        p["token_cost"] * p["frequency"] for p in detected[:5]
    )

    summary = _build_summary(n, avg_efficiency, avg_tokens, detected, trend, top_patterns_cost)

    return {
        "detected_patterns":   detected,
        "avg_efficiency_ratio": round(avg_efficiency, 3),
        "avg_token_count":     round(avg_tokens, 1),
        "trend":               trend,
        "prompts_analysed":    n,
        "summary":             summary,
    }


def _compute_efficiency_trend(ratios: list[float]) -> str:
    if len(ratios) < 6:
        return "stable"
    mid = len(ratios) // 2
    first_avg  = sum(ratios[:mid])  / mid
    second_avg = sum(ratios[mid:]) / (len(ratios) - mid)
    delta = second_avg - first_avg
    if delta > 0.03:
        return "improving"
    if delta < -0.03:
        return "declining"
    return "stable"


def _build_summary(
    n: int,
    avg_eff: float,
    avg_tokens: float,
    patterns: list[dict],
    trend: str,
    top_cost: float,
) -> str:
    eff_pct = round((1 - avg_eff) * 100, 1)
    trend_desc = {
        "improving": "improving (prompts are getting more terse)",
        "declining": "declining (prompts are getting more verbose)",
        "stable":    "stable",
    }.get(trend, "stable")

    lines = [
        f"Analysed {n} prompts. Average efficiency: {avg_eff:.2f} ({eff_pct}% estimated filler tokens). "
        f"Average token count: {avg_tokens:.0f}t. Trend: {trend_desc}."
    ]
    if patterns:
        top = patterns[0]
        lines.append(
            f"Top pattern: \"{top['pattern']}\" appears in {top['frequency']*100:.0f}% of prompts "
            f"(~{top['token_cost']}t per occurrence). "
            f"Suggestion: {top['suggestion']}."
        )
    if top_cost > 0.5:
        lines.append(
            f"Estimated savings from addressing top 5 patterns: ~{top_cost:.1f}t per prompt."
        )
    return " ".join(lines)


# ── Write outputs ──────────────────────────────────────────────────────────────

def write_style_profile(profile: dict[str, Any], path: Path = STYLE_PROFILE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")


analyse_patterns = build_style_profile  # backwards-compat alias


def write_analysis_report(
    profile: dict[str, Any],
    output_dir: Path | None = None,
) -> Path:
    if output_dir is None:
        output_dir = PRISM_ROOT / ".prism"
    output_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().strftime("%Y%m%d")
    report_path = output_dir / f"analysis-{today}.md"

    n = profile.get("prompts_analysed", 0)
    trend = profile.get("trend", "stable")
    avg_eff = profile.get("avg_efficiency_ratio", 1.0)
    avg_tok = profile.get("avg_token_count", 0.0)
    patterns = profile.get("detected_patterns", [])

    lines = [
        f"# Prism Pattern Analysis — {date.today().isoformat()}",
        "",
        f"**Prompts analysed:** {n}",
        f"**Avg efficiency ratio:** {avg_eff:.2f} ({round((1-avg_eff)*100,1)}% filler)",
        f"**Avg token count:** {avg_tok:.0f}t",
        f"**Trend:** {trend}",
        "",
        "## Top Detected Patterns",
        "",
        "| Pattern | Category | Frequency | Token Cost | Suggestion |",
        "|---------|----------|-----------|------------|------------|",
    ]

    for p in patterns[:15]:
        lines.append(
            f"| `{p['pattern']}` | {p['category']} | "
            f"{p['frequency']*100:.0f}% | ~{p['token_cost']}t | {p['suggestion']} |"
        )

    if not patterns:
        lines.append("| (none detected above 5% threshold) | | | | |")

    lines += [
        "",
        "## Summary",
        "",
        profile.get("summary", ""),
        "",
        "## Recommendations",
        "",
    ]

    if patterns:
        lines.append("Apply these suggestions via `/prism patterns --apply` to generate "
                     "a persistent `.cursor/rules/prism-personal-style.mdc` rule file.")
        for p in patterns[:5]:
            lines.append(f"- Replace **\"{p['pattern']}\"** → {p['suggestion']}")
    else:
        lines.append("No significant patterns detected. Keep writing!")

    lines += [
        "",
        "---",
        "",
        "_Run `/prism patterns --reset` to clear the log and start fresh._",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def generate_cursor_rule(profile: dict[str, Any]) -> str:
    """
    Generate the content for .cursor/rules/prism-personal-style.mdc
    from the style profile.
    """
    today = date.today().isoformat()
    patterns = profile.get("detected_patterns", [])
    avg_eff = profile.get("avg_efficiency_ratio", 1.0)

    lines = [
        "---",
        "description: Personal prompt style guidance derived from Prism pattern analysis.",
        "alwaysApply: true",
        "---",
        "",
        f"This user's detected patterns (updated {today}):",
    ]

    for p in patterns[:8]:
        lines.append(
            f'- Frequently writes "{p["pattern"]}" '
            f'(~{p["frequency"]*100:.0f}% of prompts) — {p["suggestion"]}'
        )

    lines += [
        f"- Average prompt efficiency ratio: {avg_eff:.2f} "
        f"({round((1-avg_eff)*100, 1)}% estimated filler tokens)",
        "",
        "When you notice these patterns, offer a terse rewrite before answering. "
        "Do not delay the response — keep the suggestion brief.",
    ]

    return "\n".join(lines)


def generate_claude_md_section(profile: dict[str, Any]) -> str:
    """
    Generate a CLAUDE.md personal style section from the style profile.
    Suitable for insertion between PRISM_PERSONAL_STYLE_START/END markers.
    """
    today = date.today().isoformat()
    patterns = profile.get("detected_patterns", [])
    avg_eff = profile.get("avg_efficiency_ratio", 1.0)

    lines = [
        "",
        f"### Personal Prompt Style (updated {today})",
        "",
    ]

    if patterns:
        lines.append("Detected habits:")
        for p in patterns[:8]:
            lines.append(
                f'- "{p["pattern"]}" '
                f'(~{p["frequency"]*100:.0f}% of prompts) — {p["suggestion"]}'
            )
        lines.append("")

    lines += [
        f"Average prompt efficiency ratio: {avg_eff:.2f} "
        f"({round((1-avg_eff)*100, 1)}% estimated filler tokens)",
        "",
        "Proactively offer concise rewrites when these patterns appear.",
        "",
    ]

    return "\n".join(lines)


def apply_claude_md_section(section: str, claude_md_path: Path | None = None) -> None:
    """
    Write the personal style section into CLAUDE.md between the
    PRISM_PERSONAL_STYLE_START / PRISM_PERSONAL_STYLE_END marker comments.
    """
    if claude_md_path is None:
        claude_md_path = PRISM_ROOT / "CLAUDE.md"

    if not claude_md_path.exists():
        return

    content = claude_md_path.read_text(encoding="utf-8")
    start_marker = "<!-- PRISM_PERSONAL_STYLE_START -->"
    end_marker   = "<!-- PRISM_PERSONAL_STYLE_END -->"

    if start_marker not in content:
        return

    before = content[: content.index(start_marker) + len(start_marker)]
    after  = content[content.index(end_marker):]
    claude_md_path.write_text(before + "\n" + section + after, encoding="utf-8")


def clear_analysis_needed_flag() -> None:
    ANALYSIS_NEEDED_FLAG.unlink(missing_ok=True)


# ── Main ───────────────────────────────────────────────────────────────────────

def run(
    log_path: Path = PROMPT_LOG_PATH,
    limit: int = 500,
) -> dict[str, Any]:
    entries = read_prompt_log(log_path, limit)
    profile = build_style_profile(entries)
    write_style_profile(profile)
    report_path = write_analysis_report(profile)
    clear_analysis_needed_flag()
    return profile


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Analyse Prism prompt log patterns.")
    parser.add_argument("--log",     default=str(PROMPT_LOG_PATH), help="Path to prompt-log.jsonl")
    parser.add_argument("--limit",   type=int, default=500, help="Max entries to analyse")
    parser.add_argument("--json",    action="store_true", dest="json_out", help="Output JSON profile")
    parser.add_argument("--report",  action="store_true", help="Write analysis report")
    parser.add_argument("--cursor-rule", action="store_true", dest="cursor_rule",
                        help="Print .mdc cursor rule content")
    args = parser.parse_args()

    entries = read_prompt_log(Path(args.log), args.limit)
    if not entries:
        print("No prompts logged yet. Run /prism hook on to start collecting.", file=sys.stderr)
        profile = build_style_profile([])
    else:
        profile = build_style_profile(entries)
        write_style_profile(profile)

    if args.report:
        report = write_analysis_report(profile)
        print(f"Report written: {report}", file=sys.stderr)

    if args.cursor_rule:
        print(generate_cursor_rule(profile))
    elif args.json_out:
        print(json.dumps(profile, indent=2))
    else:
        print(profile.get("summary", ""))
        if profile["detected_patterns"]:
            print("\nTop patterns:")
            for p in profile["detected_patterns"][:5]:
                print(f"  {p['frequency']*100:.0f}%  \"{p['pattern']}\"  →  {p['suggestion']}")


if __name__ == "__main__":
    main()
