"""
stage2_gate.py
--------------
Prism Stage 2 quality gate — called as a 'type: command' hook on UserPromptSubmit.

Reads the incoming prompt from stdin, evaluates it against soft-quality rules
(vagueness, bundling, lack of context), and outputs the platform-appropriate
JSON response. Only flags prompts that are genuinely problematic — single-focus,
specific, or code-related prompts are always allowed through.

Model routing:
  - Cursor / Claude Code: built-in fast model via subprocess (platform_model.py)
  - Fallback: deterministic heuristics only (no LLM call)

Output (Cursor / Claude Code):
  {"continue": true}                              — prompt passes
  {"continue": true, "additionalContext": "..."}  — prompt passes with suggestion
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PRISM_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))


# ── Heuristic gate (no model, deterministic) ──────────────────────────────────

_VAGUE_ONLY = [
    "make it better", "improve it", "fix it", "make it work",
    "clean it up", "do it", "make it good", "make it faster",
]

_BUNDLE_CONJUNCTIONS = [
    " and also ", " as well as ", " additionally ", " furthermore ",
    " plus ", " in addition ",
]

_MIN_WORDS_FOR_CONTEXT = 4


def _is_vague_only(text: str) -> bool:
    t = text.strip().lower().rstrip(".")
    return t in _VAGUE_ONLY or len(text.split()) <= _MIN_WORDS_FOR_CONTEXT


def _is_bundled(text: str) -> bool:
    low = text.lower()
    return sum(1 for conj in _BUNDLE_CONJUNCTIONS if conj in low) >= 3


def evaluate_prompt(text: str) -> dict:
    """
    Deterministic Stage 2 evaluation.
    Returns {"ok": True} or {"ok": False, "reason": "..."}.
    """
    if not text.strip():
        return {"ok": True}

    if _is_vague_only(text):
        return {
            "ok": False,
            "reason": (
                "Prompt is too vague. Add specific context: what file/function, "
                "what the desired outcome is, and what constraints apply. "
                "Run `/prism explain` to diagnose."
            ),
        }

    if _is_bundled(text):
        return {
            "ok": False,
            "reason": (
                "Prompt bundles multiple unrelated tasks. Split into separate prompts "
                "for better results. Run `/prism improve-prompt` to restructure."
            ),
        }

    return {"ok": True}


def _build_output(evaluation: dict, platform: str) -> dict:
    if evaluation["ok"]:
        return {"continue": True} if platform != "claude_code" else {"decision": "continue"}

    suggestion = evaluation.get("reason", "")
    if platform == "claude_code":
        return {"decision": "continue", "additionalContext": f"Prism Stage 2: {suggestion}"}
    return {"continue": True, "additionalContext": f"Prism Stage 2: {suggestion}"}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Prism Stage 2 quality gate.")
    parser.add_argument("--platform", default=None)
    args = parser.parse_args()

    platform = args.platform
    if not platform:
        try:
            import platform_model
            platform = platform_model.detect_platform()
        except ImportError:
            platform = os.environ.get("PRISM_PLATFORM", "unknown")

    text = sys.stdin.read() if not sys.stdin.isatty() else ""
    evaluation = evaluate_prompt(text)
    result = _build_output(evaluation, platform)
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
