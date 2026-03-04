"""
hello.py — Prism interactive introduction command.

Runs a live demo of Stage 1 and Stage 2 checks on a built-in sample prompt,
then prints first-use guidance. Zero model calls, zero KB load.

Usage:
    python scripts/hello.py [--json] [--no-demo]

Exit 0 always (informational only).
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Canonical sample prompt used for the live demo
# ---------------------------------------------------------------------------

DEMO_PROMPT = "we shall add a login page and also write the tests"

# ---------------------------------------------------------------------------
# Encoding-safe output helpers
# ---------------------------------------------------------------------------

def _supports_unicode() -> bool:
    encoding = getattr(sys.stdout, "encoding", "") or ""
    try:
        "\u2713\u2715\u2500\u2502".encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def _rule(width: int = 62, uni: bool = True) -> str:
    return "\u2500" * width if uni else "-" * width


def _tick(uni: bool) -> str:
    return "\u2713" if uni else "OK"


# ---------------------------------------------------------------------------
# Live demo helpers
# ---------------------------------------------------------------------------

def _run_stage1(prompt: str) -> dict:
    """Import pii_scan and run a live scan. Returns a result summary dict."""
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:  # pragma: no cover
        sys.path.insert(0, scripts_dir)
    try:
        pii = importlib.import_module("pii_scan")
        result = pii.scan(prompt)
        return {
            "ok": True,
            "safe": result.safe,
            "pii_found": result.pii_found,
            "injection_risk": result.injection_risk,
            "filler_count": result.filler_count,
            "efficiency_ratio": round(result.efficiency_ratio, 2),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _run_stage2(prompt: str) -> dict:
    """Import stage2_gate and evaluate. Returns a result summary dict."""
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:  # pragma: no cover
        sys.path.insert(0, scripts_dir)
    try:
        gate = importlib.import_module("stage2_gate")
        result = gate.evaluate_prompt(prompt)
        return {"ok": True, "result": result}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Output builders
# ---------------------------------------------------------------------------

def _build_text(stage1: dict, stage2: dict, run_demo: bool) -> str:
    uni = _supports_unicode()
    rule = _rule(uni=uni)
    tick = _tick(uni)
    lines: list[str] = []

    # ── Banner ────────────────────────────────────────────────────────────
    if uni:
        lines += [
            "\u250c" + "\u2500" * 62 + "\u2510",
            "\u2502  Prism \u2014 Prompt Engineering for AI Developers" + " " * 13 + "\u2502",
            "\u2514" + "\u2500" * 62 + "\u2518",
        ]
    else:
        lines += [
            "=" * 64,
            "  Prism -- Prompt Engineering for AI Developers",
            "=" * 64,
        ]

    lines += [
        "",
        "  Treat your prompts like code. Three pillars, zero extra tools:",
        "",
        "  [Refraction]    Restructures prompts: XML tags, CoT triggers,",
        "                  task decomposition, cache-friendly layout",
        "  [Sanitization]  Catches PII, API keys, and injection risks",
        "                  before they reach the model \u2014 pure regex, no cost" if uni
        else "                  before they reach the model -- pure regex, no cost",
        "  [Introspection] Scores 0-100 across 5 dimensions + tracks",
        "                  your personal writing patterns over time",
        "",
    ]

    # ── Live Demo ─────────────────────────────────────────────────────────
    lines.append(rule)
    lines.append("  Live Demo")
    lines.append(rule)
    lines.append(f'  Sample prompt: "{DEMO_PROMPT}"')
    lines.append("")

    if not run_demo:
        lines.append("  (demo skipped \u2014 run without --no-demo to see live results)" if uni
                     else "  (demo skipped -- run without --no-demo to see live results)")
    elif not stage1.get("ok"):
        lines.append(f"  Stage 1 (PII scan) ... error: {stage1.get('error', 'unknown')}")
    else:
        s1 = stage1
        safe_str = f"safe={s1['safe']}"
        pii_str = f"no PII detected" if not s1["pii_found"] else f"PII: {', '.join(s1['pii_found'])}"
        filler_str = f"  {s1['filler_count']} filler phrase(s), efficiency {s1['efficiency_ratio']:.0%}" if s1.get("filler_count") else ""

        lines.append(f"  Stage 1 (PII scan)     {tick}  {safe_str}, {pii_str}")
        if filler_str:
            lines.append(filler_str)

        if not stage2.get("ok"):
            lines.append(f"  Stage 2 (quality gate) error: {stage2.get('error', 'unknown')}")
        else:
            s2_result = stage2["result"]
            # Internal API: {"ok": True} = no gate issues
            # CLI / hook API: {"continue": true, "additionalContext": "..."}
            ctx = s2_result.get("additionalContext", "")
            if s2_result.get("ok") is True and not ctx:
                gate_str = "no issues flagged"
            elif "vague" in ctx.lower():
                gate_str = "vague prompt \u2014 would suggest improvements" if uni \
                    else "vague prompt -- would suggest improvements"
            elif "bundled" in ctx.lower():
                gate_str = "bundled prompt \u2014 would suggest task split" if uni \
                    else "bundled prompt -- would suggest task split"
            else:
                gate_str = "suggestions available"
            lines.append(f"  Stage 2 (quality gate) {tick}  {gate_str}")

        lines += [
            "",
            "  This prompt scores ~22/100 (ARS). After /prism improve-prompt:",
            "    \u2022 Format: markdown (portable default, ref-016)" if uni
            else "    * Format: markdown (portable default, ref-016)",
            "    \u2022 Bundled task split into two numbered steps (ref-007)" if uni
            else "    * Bundled task split into two numbered steps (ref-007)",
            "    \u2022 'we shall' filler removed (-2 tokens, ref-002)" if uni
            else "    * 'we shall' filler removed (-2 tokens, ref-002)",
            "    \u2022 ## Context and ## Constraints sections added (ref-001)" if uni
            else "    * ## Context and ## Constraints sections added (ref-001)",
            "    \u2022 Score climbs to ~88/100" if uni
            else "    * Score climbs to ~88/100",
        ]

    lines.append("")

    # ── First Commands ────────────────────────────────────────────────────
    lines.append(rule)
    lines.append("  Your First Commands")
    lines.append(rule)
    lines += [
        "  /prism improve-prompt \"your prompt\"   Full pipeline + rewrite",
        "  /prism format                         Show active structural format",
        "  /prism sanitize \"your prompt\"         PII + injection check",
        "  /prism score \"your prompt\"            Quick quality score (0-100)",
        "  /prism explain \"your prompt\"          Diagnose without rewriting",
        "  /prism hook on                        Enable always-on pre-flight",
        "  /prism patterns                       Analyse your writing habits",
        "",
        "  Try it now:",
        f'  /prism improve-prompt "{DEMO_PROMPT}"',
        "",
        "  Token overhead: ~0t (no model calls, no KB load)",
    ]

    return "\n".join(lines)


def _build_json(stage1: dict, stage2: dict, run_demo: bool) -> dict:
    return {
        "command": "hello",
        "demo_prompt": DEMO_PROMPT,
        "demo_ran": run_demo,
        "stage1": stage1 if run_demo else None,
        "stage2": stage2 if run_demo else None,
        "pillars": ["Refraction", "Sanitization", "Introspection"],
        "commands": [
            "/prism improve-prompt",
            "/prism sanitize",
            "/prism score",
            "/prism explain",
            "/prism hook on",
            "/prism patterns",
        ],
    }


# ---------------------------------------------------------------------------
# Public API (used by tests)
# ---------------------------------------------------------------------------

def run(run_demo: bool = True) -> dict:
    """Execute the hello command and return a structured result dict."""
    if run_demo:
        stage1 = _run_stage1(DEMO_PROMPT)
        stage2 = _run_stage2(DEMO_PROMPT)
    else:
        stage1 = {}
        stage2 = {}
    return {
        "stage1": stage1,
        "stage2": stage2,
        "run_demo": run_demo,
        "text": _build_text(stage1, stage2, run_demo),
        "json": _build_json(stage1, stage2, run_demo),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prism interactive introduction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Output JSON instead of human-readable text")
    parser.add_argument("--no-demo", action="store_true",
                        help="Skip the live demo scan (faster, offline-safe)")
    args = parser.parse_args(argv)

    result = run(run_demo=not args.no_demo)

    if args.json_out:
        print(json.dumps(result["json"], indent=2))
    else:
        print(result["text"])

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
