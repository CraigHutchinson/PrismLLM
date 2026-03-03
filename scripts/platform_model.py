"""
platform_model.py
-----------------
Detects the current AI platform from environment variables and returns
the appropriate lightweight model name that stays within the platform's
security boundary.

Security principle: Cloud free APIs (Groq, Gemini, OpenRouter) are NOT
included in the default chain. They move data outside the platform's
security boundary and require explicit opt-in via prism.config.json.
Cloud APIs are deferred to a future release.

Supported platforms and their free/cheap models:
  Copilot (paid): gpt-4.1        — 0-multiplier on paid plans
  Copilot (free): goldeneye      — 0-multiplier on all plans
  Claude Code:    claude-haiku-4-5 — cheapest Claude within Anthropic platform
  Cursor:         None           — Cursor controls its own fast model budget
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

PLATFORM_FAST_MODELS: dict[str, Optional[str]] = {
    "copilot":       "gpt-4.1",           # 0-multiplier on paid plans
    "copilot_free":  "goldeneye",          # 0-multiplier on all plans (incl. free)
    "claude_code":   "claude-haiku-4-5",   # cheapest Claude within Anthropic platform
    "cursor":        None,                 # Cursor controls its own fast model — not configurable
}

PLATFORM_ENV_SIGNALS: dict[str, list[str]] = {
    "claude_code":   ["CLAUDE_CODE_ENTRYPOINT", "ANTHROPIC_API_KEY", "CLAUDECODE"],
    "cursor":        ["CURSOR_TRACE_ID", "CURSOR_SESSION_ID", "CURSOR_USER_ID"],
    "copilot":       ["GITHUB_TOKEN", "CODESPACES", "GITHUB_COPILOT_TOKEN"],
}


def detect_platform() -> str:
    """
    Detect the current AI platform from environment variables.

    Returns one of: 'claude_code', 'cursor', 'copilot', 'copilot_free', 'unknown'
    """
    env = os.environ

    if any(env.get(k) for k in PLATFORM_ENV_SIGNALS["claude_code"]):
        return "claude_code"

    if any(env.get(k) for k in PLATFORM_ENV_SIGNALS["cursor"]):
        return "cursor"

    if any(env.get(k) for k in PLATFORM_ENV_SIGNALS["copilot"]):
        copilot_plan = env.get("GITHUB_COPILOT_PLAN", "").lower()
        if copilot_plan == "free":
            return "copilot_free"
        return "copilot"

    explicit = env.get("PRISM_PLATFORM", "").lower()
    if explicit in PLATFORM_FAST_MODELS:
        return explicit

    return "unknown"


def get_fast_model(platform: Optional[str] = None) -> Optional[str]:
    """
    Return the appropriate lightweight model name for the given platform.

    If platform is None, auto-detect from environment.
    Returns None if the platform controls its own model budget (Cursor)
    or if the platform is unknown.
    """
    if platform is None:
        platform = detect_platform()

    return PLATFORM_FAST_MODELS.get(platform)


def get_ollama_model(config_path: Optional[Path] = None) -> Optional[str]:
    """
    Return the Ollama model if Ollama is enabled in prism.config.json.

    Ollama is fully local — no data leaves the machine. Opt-in only.
    """
    if config_path is None:
        prism_root = Path(__file__).resolve().parent.parent
        config_path = prism_root / ".prism" / "prism.config.json"

    if not config_path.exists():
        return None

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        ollama = config.get("model_routing", {}).get("ollama", {})
        if ollama.get("enabled", False):
            return ollama.get("model", "llama3.2")
    except (json.JSONDecodeError, KeyError):
        pass

    return None


def get_routing_mode(config_path: Optional[Path] = None) -> str:
    """
    Read model_routing.mode from prism.config.json.
    Returns 'platform' (default) if config is absent or unreadable.
    """
    if config_path is None:
        prism_root = Path(__file__).resolve().parent.parent
        config_path = prism_root / ".prism" / "prism.config.json"

    if not config_path.exists():
        return "platform"

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        return config.get("model_routing", {}).get("mode", "platform")
    except (json.JSONDecodeError, KeyError):
        return "platform"


def resolve_analysis_model(
    platform: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> Optional[str]:
    """
    Resolve the model to use for analysis tasks (Subagents A/B/C).

    Routing priority:
      1. If mode == 'capable': return None (let the caller use capable model)
      2. If mode == 'local' and Ollama enabled: return Ollama model
      3. Default (mode == 'platform'): return platform-native fast model
    """
    mode = get_routing_mode(config_path)

    if mode == "capable":
        return None

    if mode == "local":
        ollama = get_ollama_model(config_path)
        if ollama:
            return ollama

    return get_fast_model(platform)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect current AI platform and print the appropriate lightweight model."
    )
    parser.add_argument(
        "--platform",
        default=None,
        help="Override platform detection (claude_code|cursor|copilot|copilot_free)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show all platform signals and routing info",
    )
    args = parser.parse_args()

    platform = args.platform or detect_platform()
    fast_model = get_fast_model(platform)
    analysis_model = resolve_analysis_model(platform)
    routing_mode = get_routing_mode()

    if args.verbose:
        print(f"Platform detected:   {platform}")
        print(f"Routing mode:        {routing_mode}")
        print(f"Fast model:          {fast_model or '(platform-controlled)'}")
        print(f"Analysis model:      {analysis_model or '(use capable model)'}")
        ollama = get_ollama_model()
        print(f"Ollama model:        {ollama or '(disabled)'}")
    else:
        print(analysis_model or "")


if __name__ == "__main__":
    main()
