"""
overhead_calc.py
----------------
Scans all Prism component files, computes token estimates (chars ÷ 4),
and writes .prism/component-sizes.json.

Called:
  - At install/update time (by SKILL.md first-run detection)
  - By prism_preparser.py at sessionStart to snapshot the baseline overhead

No model required. Pure file-system arithmetic.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

PRISM_ROOT = Path(__file__).resolve().parent.parent

COMPONENT_PATHS: Dict[str, str] = {
    "skill_md":             ".cursor/skills/prism/SKILL.md",
    "refraction_playbook":  ".cursor/skills/prism/refraction-playbook.md",
    "sanitization_rules":   ".cursor/skills/prism/sanitization-rules.md",
    "introspection_scoring":".cursor/skills/prism/introspection-scoring.md",
    "examples":             ".cursor/skills/prism/examples.md",
    "rules_json":           "knowledge-base/rules.json",
    "pii_scan":             "scripts/pii_scan.py",
    "kb_query":             "scripts/kb_query.py",
    "pattern_analysis":     "scripts/pattern_analysis.py",
    "overhead_calc":        "scripts/overhead_calc.py",
    "platform_model":       "scripts/platform_model.py",
    "verbosity_patterns":   "scripts/verbosity_patterns.json",
    "hook_preparser":       "hooks/prism_preparser.py",
    "copilot_agent":        ".github/agents/prism.agent.md",
}

PER_COMMAND_OVERHEAD: Dict[str, list[str]] = {
    "/prism improve": [
        "skill_md", "refraction_playbook", "sanitization_rules",
        "introspection_scoring", "pii_scan", "kb_query",
    ],
    "/prism sanitize": ["skill_md", "sanitization_rules", "pii_scan"],
    "/prism score":    ["skill_md", "introspection_scoring", "kb_query"],
    "/prism explain":  ["skill_md", "refraction_playbook"],
    "/prism patterns": ["skill_md", "pattern_analysis", "verbosity_patterns"],
    "/prism usage":    ["skill_md"],
    "hook_stage1":     ["hook_preparser", "pii_scan"],
    "hook_stage2":     [],
    "session_context": [],
}

HOOK_STAGE2_TOKENS = 200
SESSION_CONTEXT_TOKENS = 50


def chars_to_tokens(chars: int) -> int:
    """Estimate token count from character count using chars ÷ 4 heuristic."""
    return max(0, chars // 4)


def scan_components(root: Path = PRISM_ROOT) -> Dict[str, Any]:
    """Scan all component files and return size info."""
    sizes: Dict[str, Any] = {}
    for name, rel_path in COMPONENT_PATHS.items():
        full_path = root / rel_path
        if full_path.exists():
            char_count = full_path.stat().st_size
            sizes[name] = {
                "path":       rel_path,
                "chars":      char_count,
                "tokens_est": chars_to_tokens(char_count),
                "exists":     True,
            }
        else:
            sizes[name] = {
                "path":       rel_path,
                "chars":      0,
                "tokens_est": 0,
                "exists":     False,
            }
    return sizes


def build_command_table(component_sizes: Dict[str, Any]) -> Dict[str, int]:
    """Build per-command token overhead estimates."""
    table: Dict[str, int] = {}
    for cmd, components in PER_COMMAND_OVERHEAD.items():
        total = sum(
            component_sizes.get(c, {}).get("tokens_est", 0)
            for c in components
        )
        if cmd == "/prism improve":
            total += 3 * 100
        table[cmd] = total
    table["hook_stage2"] = HOOK_STAGE2_TOKENS
    table["session_context"] = SESSION_CONTEXT_TOKENS
    return table


def write_component_sizes(output_path: Path, data: Dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_component_sizes(path: Path) -> Dict[str, Any] | None:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def run(root: Path = PRISM_ROOT, output_path: Path | None = None) -> Dict[str, Any]:
    """Scan components, build command table, write output, and return result."""
    if output_path is None:
        output_path = root / ".prism" / "component-sizes.json"

    component_sizes = scan_components(root)
    command_table = build_command_table(component_sizes)

    total_prism_tokens = sum(
        info["tokens_est"] for info in component_sizes.values()
    )

    result = {
        "generated_at": _now_iso(),
        "total_prism_tokens_est": total_prism_tokens,
        "components": component_sizes,
        "per_command_overhead": command_table,
    }

    write_component_sizes(output_path, result)
    return result


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Compute Prism component token estimates."
    )
    parser.add_argument(
        "--root", default=str(PRISM_ROOT),
        help="Path to Prism repo root (default: auto-detected)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output path for component-sizes.json (default: .prism/component-sizes.json)",
    )
    parser.add_argument(
        "--print", action="store_true", dest="print_result",
        help="Print summary table to stdout",
    )
    args = parser.parse_args()

    root = Path(args.root)
    output = Path(args.output) if args.output else None
    result = run(root=root, output_path=output)

    if args.print_result:
        print(f"\nPrism component token estimates (root: {root})\n")
        print(f"{'Component':<30} {'Tokens':>8}  {'Path'}")
        print("-" * 70)
        for name, info in result["components"].items():
            status = "" if info["exists"] else " [missing]"
            print(f"{name:<30} {info['tokens_est']:>8}  {info['path']}{status}")
        print(f"\n{'TOTAL':.<30} {result['total_prism_tokens_est']:>8}")
        print(f"\nPer-command overhead:")
        for cmd, tokens in result["per_command_overhead"].items():
            print(f"  {cmd:<35} ~{tokens}t")
        print(f"\nWritten to: {output or root / '.prism' / 'component-sizes.json'}")


if __name__ == "__main__":
    main()
