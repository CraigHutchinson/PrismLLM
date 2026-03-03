"""
kb_query.py
-----------
CLI tool to query knowledge-base/rules.json with filters.

Filters: --pillar, --model, --category, --source, --apply-cost, --tag
Output: filtered JSON array, ready for agent or subagent consumption.
Hash-based caching: results are cached in .prism/kb-cache/ keyed by
the SHA-256 of the query parameters + rules.json mtime.

Usage:
  python scripts/kb_query.py --pillar refraction --apply-cost script
  python scripts/kb_query.py --model claude-4+ --source official
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

PRISM_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KB_PATH  = PRISM_ROOT / "knowledge-base" / "rules.json"
DEFAULT_CACHE_DIR = PRISM_ROOT / ".prism" / "kb-cache"


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_rules(kb_path: Path = DEFAULT_KB_PATH) -> list[dict[str, Any]]:
    if not kb_path.exists():
        raise FileNotFoundError(f"Knowledge base not found: {kb_path}")
    return json.loads(kb_path.read_text(encoding="utf-8"))


def cache_key(
    kb_path: Path,
    filters: dict[str, Any],
) -> str:
    """Build a cache key from KB mtime + filter parameters."""
    mtime = int(kb_path.stat().st_mtime * 1000) if kb_path.exists() else 0
    payload = json.dumps({"mtime": mtime, "filters": filters}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def read_cache(cache_dir: Path, key: str) -> list[dict] | None:
    path = cache_dir / f"{key}.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return None


def write_cache(cache_dir: Path, key: str, data: list[dict]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{key}.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


# ── Model version comparison ──────────────────────────────────────────────────

_MODEL_ORDER = {
    "all":          0,
    "claude-1":     10,
    "claude-2":     20,
    "claude-3":     30,
    "claude-3.5":   35,
    "claude-3.5+":  35,
    "claude-3.7":   37,
    "claude-3.7+":  37,
    "claude-4":     40,
    "claude-4+":    40,
}


def _model_rank(version: str) -> int:
    return _MODEL_ORDER.get(version.lower(), 0)


def model_applies(rule: dict, target: str) -> bool:
    """Return True if the rule applies to the target model version."""
    target_rank = _model_rank(target)
    if target_rank == 0:
        return True

    for applies in rule.get("model_applies", ["all"]):
        a_rank = _model_rank(applies)
        if applies == "all" or a_rank <= target_rank:
            deprecated = rule.get("model_deprecated")
            if deprecated:
                dep_rank = _model_rank(deprecated)
                if target_rank >= dep_rank:
                    return False
            return True
    return False


# ── Filter function ────────────────────────────────────────────────────────────

def filter_rules(
    rules: list[dict],
    pillar:     str | None = None,
    model:      str | None = None,
    category:   str | None = None,
    source:     str | None = None,
    apply_cost: str | None = None,
    tag:        str | None = None,
    ids:        list[str] | None = None,
) -> list[dict]:
    result = rules

    if ids:
        id_set = set(ids)
        result = [r for r in result if r.get("id") in id_set]

    if pillar:
        result = [r for r in result if r.get("pillar") == pillar]

    if category:
        result = [r for r in result if r.get("category") == category]

    if source:
        result = [r for r in result if r.get("source_type") == source]

    if apply_cost:
        # Support comma-separated list: "script,fast"
        costs = [c.strip() for c in apply_cost.split(",")]
        result = [r for r in result if r.get("apply_cost") in costs]

    if tag:
        result = [r for r in result if tag in r.get("tags", [])]

    if model:
        result = [r for r in result if model_applies(r, model)]

    return result


# ── Main query function ────────────────────────────────────────────────────────

def query(
    pillar:     str | None = None,
    model:      str | None = None,
    category:   str | None = None,
    source:     str | None = None,
    apply_cost: str | None = None,
    tag:        str | None = None,
    ids:        list[str] | None = None,
    kb_path:    Path = DEFAULT_KB_PATH,
    cache_dir:  Path = DEFAULT_CACHE_DIR,
    no_cache:   bool = False,
) -> list[dict]:
    filters = {
        "pillar":     pillar,
        "model":      model,
        "category":   category,
        "source":     source,
        "apply_cost": apply_cost,
        "tag":        tag,
        "ids":        sorted(ids) if ids else None,
    }

    if not no_cache:
        key = cache_key(kb_path, filters)
        cached = read_cache(cache_dir, key)
        if cached is not None:
            return cached

    rules = load_rules(kb_path)
    filtered = filter_rules(rules, **filters)

    if not no_cache:
        write_cache(cache_dir, key, filtered)

    return filtered


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Query the Prism knowledge base with filters.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/kb_query.py --pillar refraction
  python scripts/kb_query.py --apply-cost script,fast --model claude-4+
  python scripts/kb_query.py --source official --pillar sanitization
  python scripts/kb_query.py --ids ref-001,san-005
  python scripts/kb_query.py --tag xml --no-cache
        """,
    )
    parser.add_argument("--pillar",     choices=["refraction", "sanitization", "introspection"])
    parser.add_argument("--model",      help="Target model version (e.g. claude-4+, all)")
    parser.add_argument("--category",   help="Rule category slug (e.g. xml-structure)")
    parser.add_argument("--source",     choices=["official", "community", "research"])
    parser.add_argument("--apply-cost", dest="apply_cost",
                        help="Comma-separated: script,fast,capable,free")
    parser.add_argument("--tag",        help="Filter by tag")
    parser.add_argument("--ids",        help="Comma-separated rule IDs (e.g. ref-001,san-005)")
    parser.add_argument("--no-cache",   action="store_true", dest="no_cache")
    parser.add_argument("--kb",         default=str(DEFAULT_KB_PATH), dest="kb_path",
                        help="Path to rules.json")
    parser.add_argument("--count",      action="store_true", help="Print count only")
    parser.add_argument("--titles",     action="store_true", help="Print IDs and titles only")
    args = parser.parse_args()

    ids_list = [i.strip() for i in args.ids.split(",")] if args.ids else None

    try:
        results = query(
            pillar=args.pillar,
            model=args.model,
            category=args.category,
            source=args.source,
            apply_cost=args.apply_cost,
            tag=args.tag,
            ids=ids_list,
            kb_path=Path(args.kb_path),
            no_cache=args.no_cache,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.count:
        print(len(results))
    elif args.titles:
        for r in results:
            print(f"{r['id']:<12} {r['pillar']:<15} {r['title']}")
    else:
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
