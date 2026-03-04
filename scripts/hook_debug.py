"""
hook_debug.py
-------------
Read and pretty-print .prism/hook-debug.log.

The debug log is written by prism_preparser.py on every userPromptSubmit
and preToolUse event. Each entry records the raw stdin content, the
extracted prompt, and the scan result — essential for diagnosing why the
hook blocked (or passed) a given prompt.

Usage:
    python scripts/hook_debug.py              # show last 20 entries
    python scripts/hook_debug.py --tail 50    # show last N entries
    python scripts/hook_debug.py --all        # show everything
    python scripts/hook_debug.py --clear      # wipe the log
    python scripts/hook_debug.py --json       # raw JSON output
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PRISM_ROOT = Path(__file__).resolve().parent.parent
DEBUG_LOG  = PRISM_ROOT / ".prism" / "hook-debug.log"


def _load(n: int | None) -> list[dict]:
    if not DEBUG_LOG.exists():
        return []
    lines = [l for l in DEBUG_LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    if n is not None:
        lines = lines[-n:]
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return entries


def _fmt_table(entries: list[dict]) -> str:
    if not entries:
        return "hook-debug.log is empty — no hook events recorded yet."

    rows = []
    for e in entries:
        blocked_str = "BLOCKED" if e.get("blocked") else "pass"
        pii         = ", ".join(e.get("pii_found", [])) or "-"
        issues      = "; ".join(e.get("issues", []))[:80] or "-"
        rows.append({
            "ts":        e.get("ts", "")[:19].replace("T", " "),
            "event":     e.get("event", "?")[:18],
            "raw_len":   str(e.get("raw_len", "?")),
            "extracted": e.get("extracted", "")[:60],
            "result":    blocked_str,
            "pii":       pii[:30],
            "issues":    issues,
        })

    col_w = {k: max(len(k), max(len(r[k]) for r in rows)) for k in rows[0]}
    sep   = "  ".join("-" * col_w[k] for k in col_w)
    hdr   = "  ".join(k.upper().ljust(col_w[k]) for k in col_w)

    lines = [hdr, sep]
    for r in rows:
        lines.append("  ".join(r[k].ljust(col_w[k]) for k in col_w))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read .prism/hook-debug.log")
    parser.add_argument("--tail",  type=int, default=20, metavar="N",
                        help="Show last N entries (default: 20)")
    parser.add_argument("--all",   action="store_true",
                        help="Show all entries")
    parser.add_argument("--clear", action="store_true",
                        help="Clear the debug log")
    parser.add_argument("--json",  action="store_true", dest="json_out",
                        help="Raw JSON output")
    args = parser.parse_args()

    if args.clear:
        if DEBUG_LOG.exists():
            count = sum(1 for l in DEBUG_LOG.read_text(encoding="utf-8").splitlines() if l.strip())
            DEBUG_LOG.write_text("", encoding="utf-8")
            print(f"Cleared {count} entries from {DEBUG_LOG}")
        else:
            print("Log does not exist — nothing to clear.")
        return 0

    n = None if args.all else args.tail
    entries = _load(n)

    if args.json_out:
        print(json.dumps(entries, indent=2))
        return 0

    label = "all" if args.all else f"last {len(entries)}"
    print(f"Prism hook debug log — {label} entries  ({DEBUG_LOG})\n")
    print(_fmt_table(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
