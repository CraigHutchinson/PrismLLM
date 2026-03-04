"""
hook_installer.py
-----------------
Deterministic installer for Prism hooks.

Handles /prism hook on, /prism hook off, /prism hook status.

Actions:
  on     — substitute {{PRISM_ROOT}}, idempotently merge Prism hooks into
           .claude/settings.json and write .github/hooks/prism_hooks.json
  off    — remove all Prism-managed entries from both files (preserves non-Prism hooks)
  status — report whether Prism hooks are active in both config files

Called by SKILL.md dispatch via:
  python scripts/hook_installer.py --action on
  python scripts/hook_installer.py --action off
  python scripts/hook_installer.py --action status
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PRISM_ROOT = Path(__file__).resolve().parent.parent
PRISM_MARKER = "_prism_version"
TEMPLATE_CLAUDE = PRISM_ROOT / "hooks" / "claude_settings_template.json"
TEMPLATE_COPILOT = PRISM_ROOT / "hooks" / "prism_hooks_template.json"
TARGET_CLAUDE = PRISM_ROOT / ".claude" / "settings.json"
TARGET_COPILOT = PRISM_ROOT / ".github" / "hooks" / "prism_hooks.json"


# ── Template substitution ─────────────────────────────────────────────────────

def _substitute(text: str, prism_root: Path) -> str:
    return text.replace("{{PRISM_ROOT}}", str(prism_root).replace("\\", "/"))


def _load_template(path: Path, prism_root: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    return json.loads(_substitute(raw, prism_root))


# ── Claude / Cursor settings.json merge ──────────────────────────────────────

def _is_prism_hook_block(block: dict) -> bool:
    """Return True if a hook config block was written by Prism."""
    hooks = block.get("hooks", [])
    return any(PRISM_MARKER in h or "prism_preparser" in h.get("command", "") or
               "stage2_gate" in h.get("command", "")
               for h in hooks)


def _remove_prism_blocks(event_list: list[dict]) -> list[dict]:
    return [b for b in event_list if not _is_prism_hook_block(b)]


def install_claude_hooks(prism_root: Path = PRISM_ROOT,
                         target: Path = TARGET_CLAUDE) -> None:
    template = _load_template(TEMPLATE_CLAUDE, prism_root)
    target.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, Any] = {}
    if target.exists():
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    merged_hooks: dict[str, list] = {}
    existing_hooks = existing.get("hooks", {})
    template_hooks = template.get("hooks", {})

    all_events = set(existing_hooks) | set(template_hooks)
    for event in all_events:
        existing_blocks = existing_hooks.get(event, [])
        cleaned = _remove_prism_blocks(existing_blocks)
        prism_blocks = template_hooks.get(event, [])
        merged_hooks[event] = cleaned + prism_blocks

    result = {**existing, "hooks": merged_hooks, PRISM_MARKER: template.get(PRISM_MARKER, "1.0")}
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")


def remove_claude_hooks(target: Path = TARGET_CLAUDE) -> None:
    if not target.exists():
        return
    try:
        existing = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    cleaned_hooks: dict[str, list] = {}
    for event, blocks in existing.get("hooks", {}).items():
        cleaned = _remove_prism_blocks(blocks)
        if cleaned:
            cleaned_hooks[event] = cleaned

    result = {k: v for k, v in existing.items()
              if k not in ("hooks", PRISM_MARKER)}
    if cleaned_hooks:
        result["hooks"] = cleaned_hooks
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")


def is_claude_hooks_active(target: Path = TARGET_CLAUDE) -> bool:
    if not target.exists():
        return False
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return PRISM_MARKER in data
    except json.JSONDecodeError:
        return False


# ── Copilot hooks file ────────────────────────────────────────────────────────

def install_copilot_hooks(prism_root: Path = PRISM_ROOT,
                          target: Path = TARGET_COPILOT) -> None:
    if not TEMPLATE_COPILOT.exists():
        return
    template = _load_template(TEMPLATE_COPILOT, prism_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(template, indent=2), encoding="utf-8")


def remove_copilot_hooks(target: Path = TARGET_COPILOT) -> None:
    if target.exists():
        target.unlink()


def is_copilot_hooks_active(target: Path = TARGET_COPILOT) -> bool:
    return target.exists()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Install or remove Prism hooks.")
    parser.add_argument("--action", choices=["on", "off", "status"], required=True)
    parser.add_argument("--root", default=str(PRISM_ROOT),
                        help="PrismLLM repo root (default: auto-detected)")
    args = parser.parse_args()

    prism_root = Path(args.root)
    claude_target  = prism_root / ".claude" / "settings.json"
    copilot_target = prism_root / ".github" / "hooks" / "prism_hooks.json"

    if args.action == "on":
        install_claude_hooks(prism_root, claude_target)
        install_copilot_hooks(prism_root, copilot_target)
        print("Prism hooks enabled.")
        print(f"  Written: {claude_target} (Cursor + Claude Code)")
        if copilot_target.exists():
            print(f"  Written: {copilot_target} (GitHub Copilot)")
        print("  Restart your IDE to activate the hooks.")
        print("")
        print("  Stage 1 (deterministic PII scan): active on every prompt")
        print("  Stage 2 (quality gate): active on every prompt (no model)")
        print("  Run: python scripts/hook_installer.py --action off  to disable")

    elif args.action == "off":
        remove_claude_hooks(claude_target)
        remove_copilot_hooks(copilot_target)
        print("Prism hooks disabled.")

    elif args.action == "status":
        claude_active  = is_claude_hooks_active(claude_target)
        copilot_active = is_copilot_hooks_active(copilot_target)
        print(f"Cursor/Claude Code hooks: {'active' if claude_active else 'inactive'}")
        print(f"Copilot hooks:            {'active' if copilot_active else 'inactive'}")


if __name__ == "__main__":
    main()
