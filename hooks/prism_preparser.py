"""
prism_preparser.py
------------------
Prism hook script. Handles all hook lifecycle events:
  - sessionStart   : inject Prism context + check overhead alert
  - userPromptSubmit: Stage 1 PII/injection scan → block or log
  - preToolUse     : scan tool arguments for secrets/injection
  - stop           : pattern analysis trigger + session usage log

Performance target for userPromptSubmit: < 50ms (Stage 1 is pure regex).

Platform JSON output formats:
  Cursor / Claude Code:
    continue: false  →  blocks prompt
    additionalContext: "..." → injects context (Claude Code only)
  Copilot preToolUse:
    permissionDecision: "deny"  →  blocks tool call
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Allow importing from scripts/ alongside hooks/
PRISM_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PRISM_ROOT / "scripts"))

import pii_scan
import usage_log

PRISM_DIR    = PRISM_ROOT / ".prism"
PROMPT_LOG   = PRISM_DIR / "prompt-log.jsonl"
ANALYSIS_FLAG = PRISM_DIR / ".analysis-needed"
CONFIG_PATH  = PRISM_DIR / "prism.config.json"
CONFIG_DEFAULT = PRISM_ROOT / "scripts" / "prism_config_default.json"


# ── Config ─────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    for path in (CONFIG_PATH, CONFIG_DEFAULT):
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
    return {}


def cfg_bool(config: dict, *keys: str, default: bool = True) -> bool:
    node = config
    for k in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(k)
        if node is None:
            return default
    return bool(node)


# ── First-run initialisation ───────────────────────────────────────────────────

def ensure_prism_dir(config: dict) -> None:
    """Create .prism/ structure and seed prism.config.json on first run."""
    PRISM_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists() and CONFIG_DEFAULT.exists():
        import shutil
        shutil.copy(CONFIG_DEFAULT, CONFIG_PATH)
    for fname in ("usage-log.jsonl", "usage-summary.json", "prompt-log.jsonl"):
        p = PRISM_DIR / fname
        if not p.exists():
            p.write_text("" if fname.endswith(".jsonl") else "{}", encoding="utf-8")


# ── Prompt logging ─────────────────────────────────────────────────────────────

def log_prompt(text: str, platform: str, scan_result) -> None:
    """Append a PII-scrubbed entry to prompt-log.jsonl."""
    import datetime
    config = load_config()
    if not cfg_bool(config, "hook", "log_prompts"):
        return
    threshold = config.get("analysis", {}).get("threshold", 25)
    retention = config.get("analysis", {}).get("retention", 500)

    entry = {
        "ts":             int(datetime.datetime.now(datetime.timezone.utc).timestamp()),
        "session_id":     os.environ.get("CLAUDE_SESSION_ID", "")[:16],
        "platform":       platform,
        "tokens_est":     scan_result.tokens_est,
        "filler_count":   scan_result.filler_count,
        "efficiency_ratio": round(scan_result.efficiency_ratio, 3),
        "prompt_scrubbed": scan_result.redacted_prompt[:1000],
    }

    PRISM_DIR.mkdir(parents=True, exist_ok=True)
    with PROMPT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    count = _count_log_entries()
    if count >= threshold and not ANALYSIS_FLAG.exists():
        ANALYSIS_FLAG.write_text("1", encoding="utf-8")

    if count > retention:
        _trim_log(retention)


def _count_log_entries() -> int:
    if not PROMPT_LOG.exists():
        return 0
    with PROMPT_LOG.open(encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def _trim_log(keep: int) -> None:
    if not PROMPT_LOG.exists():
        return
    lines = [l for l in PROMPT_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(lines) > keep:
        PROMPT_LOG.write_text("\n".join(lines[-keep:]) + "\n", encoding="utf-8")


# ── Event handlers ─────────────────────────────────────────────────────────────

def handle_session_start(platform: str) -> dict:
    config = load_config()
    ensure_prism_dir(config)

    output: dict = {}

    if cfg_bool(config, "hook", "session_context_injection"):
        output["additionalContext"] = (
            "Prism Mode active. Prompts are being pre-screened for structure, "
            "PII, and injection risk. Run /prism hook off to disable."
        )

    alert = usage_log.read_and_clear_alert()
    if alert:
        advisory = (
            f"⚡ Prism overhead was high last session "
            f"({alert.get('tokens', '?')}t, {alert.get('pct', 0):.1f}%). "
            "Run `/prism usage --optimize` or `/prism hook off` to reduce it."
        )
        if "additionalContext" in output:
            output["additionalContext"] += f"\n\n{advisory}"
        else:
            output["additionalContext"] = advisory

    snapshot_overhead()
    return output


def _extract_prompt(raw: str) -> str:
    """
    Cursor/Claude Code passes hook payloads as JSON objects, e.g.:
      {"prompt": "say hello", "session_id": "user@host", ...}
    Scanning the entire JSON string causes false-positive EMAIL hits on
    metadata fields (session IDs, paths, git user.email, etc.).
    Extract only the "prompt" field when the input is valid JSON with that key.
    Fall back to the raw string for plain-text input (backward compatible).
    """
    stripped = raw.strip()
    if stripped.startswith("{"):
        try:
            payload = json.loads(stripped)
            if isinstance(payload, dict) and "prompt" in payload:
                return str(payload["prompt"])
        except (json.JSONDecodeError, ValueError):
            pass
    return raw


def handle_user_prompt_submit(text: str, platform: str) -> dict:
    config = load_config()
    prompt = _extract_prompt(text)
    result = pii_scan.scan(prompt)
    log_prompt(prompt, platform, result)

    if not result.safe:
        block_message = _build_block_message(result)
        return _block_response(platform, block_message)

    return _continue_response(platform)


def handle_pre_tool_use(tool_input: str, platform: str) -> dict:
    prompt = _extract_prompt(tool_input)
    result = pii_scan.scan(prompt)
    if not result.safe:
        reason = "; ".join(result.issues[:2]) if result.issues else "PII or injection detected"
        if platform == "copilot":
            return {"permissionDecision": "deny", "reason": reason}
        return _block_response(platform, f"Prism blocked tool use: {reason}")
    return {"permissionDecision": "allow"} if platform == "copilot" else _continue_response(platform)


def handle_stop(platform: str) -> dict:
    """Session-end: trigger pattern analysis if needed; write usage entry."""
    config = load_config()

    if ANALYSIS_FLAG.exists():
        _run_pattern_analysis_background()

    _write_session_entry(platform, config)
    return {}


def snapshot_overhead() -> None:
    """Snapshot component token sizes at session start (no model)."""
    try:
        import overhead_calc
        overhead_calc.run(PRISM_ROOT)
    except Exception as exc:
        print(f"[Prism] overhead_calc failed: {exc}", file=sys.stderr)
        error_file = PRISM_DIR / ".overhead-error"
        try:
            PRISM_DIR.mkdir(parents=True, exist_ok=True)
            error_file.write_text(str(exc), encoding="utf-8")
        except OSError:
            pass


def _run_pattern_analysis_background() -> None:
    """Trigger pattern_analysis.py in a non-blocking subprocess."""
    import subprocess
    script = PRISM_ROOT / "scripts" / "pattern_analysis.py"
    if not script.exists():
        return

    cmd = [sys.executable, str(script)]

    try:
        import platform_model as _pm
        model = _pm.resolve_analysis_model()
        if model:
            cmd += ["--model", model]
    except ImportError:
        pass

    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def _write_session_entry(platform: str, config: dict) -> None:
    """Write session overhead entry to usage-log.jsonl and check alert threshold."""
    sizes_path = PRISM_DIR / "component-sizes.json"
    prism_tokens = 0
    if sizes_path.exists():
        try:
            sizes_data = json.loads(sizes_path.read_text(encoding="utf-8"))
            prism_tokens = sizes_data.get("total_prism_tokens_est", 0)
        except json.JSONDecodeError:
            pass

    session_id = os.environ.get("CLAUDE_SESSION_ID", "")[:16]
    entry = usage_log.new_session_entry(
        platform=platform,
        session_id=session_id,
        prism_tokens_est=prism_tokens,
    )

    threshold_tokens = config.get("overhead", {}).get("alert_threshold_tokens", 2000)
    threshold_pct    = config.get("overhead", {}).get("alert_threshold_pct",    20.0)
    usage_log.check_and_set_alert(entry, threshold_tokens, threshold_pct)
    usage_log.append_session(entry)


# ── Response helpers ───────────────────────────────────────────────────────────

def _build_block_message(result: pii_scan.ScanResult) -> str:
    lines = ["⚡ Prism blocked this prompt.\n"]
    if result.pii_found:
        lines.append(f"PII detected: {', '.join(result.pii_found)}")
        lines.append("Remove or replace sensitive data before submitting.")
    if result.injection_risk:
        lines.append(f"Injection risk detected: {', '.join(result.injection_categories)}")
        lines.append("Remove override/hijack phrases before submitting.")
    lines.append("\nEdit your prompt and resend, or run /prism hook off to disable.")
    return "\n".join(lines)


def _block_response(platform: str, message: str) -> dict:
    if platform == "claude_code":
        return {"decision": "block", "reason": message}
    return {"continue": False, "user_message": message}


def _continue_response(platform: str) -> dict:
    if platform == "claude_code":
        return {"decision": "continue"}
    return {"continue": True}


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Prism hook script.")
    parser.add_argument("--event", required=True,
                        choices=["sessionStart", "userPromptSubmit", "preToolUse", "stop"])
    parser.add_argument("--platform", default=None,
                        help="Platform override (claude_code|cursor|copilot)")
    parser.add_argument("--stdin", action="store_true",
                        help="Read additional input from stdin (for preToolUse)")
    args = parser.parse_args()

    # Auto-detect platform if not specified
    if args.platform:
        platform = args.platform
    else:
        try:
            import platform_model
            platform = platform_model.detect_platform()
        except ImportError:
            platform = os.environ.get("PRISM_PLATFORM", "unknown")

    if args.event == "sessionStart":
        result = handle_session_start(platform)
        if result:
            print(json.dumps(result))
        sys.exit(0)

    elif args.event == "userPromptSubmit":
        text = sys.stdin.read() if not sys.stdin.isatty() else ""
        if not text.strip():
            sys.exit(0)
        result = handle_user_prompt_submit(text, platform)
        print(json.dumps(result))
        if not result.get("continue", True) and result.get("decision") != "continue":
            sys.exit(2)
        sys.exit(0)

    elif args.event == "preToolUse":
        tool_input = sys.stdin.read() if args.stdin and not sys.stdin.isatty() else ""
        result = handle_pre_tool_use(tool_input, platform)
        print(json.dumps(result))
        if result.get("permissionDecision") == "deny":
            sys.exit(2)
        sys.exit(0)

    elif args.event == "stop":
        handle_stop(platform)
        sys.exit(0)


if __name__ == "__main__":  # pragma: no cover
    main()
