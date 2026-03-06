"""
Automated integration tests for the Prism GSAP marketplace plugin.

Tests the full install → validate → functional pipeline via the Claude Code CLI.
Requires `claude` (Claude Code CLI ≥ 2.1) on PATH.

By default tests against the live GitHub repo so results reflect what any user
would experience after `claude plugin install prism@gsap-tools`.

Usage:
    python scripts/test_marketplace.py                          # live GitHub repo
    python scripts/test_marketplace.py --local                  # local clone (faster iteration)
    python scripts/test_marketplace.py --marketplace owner/repo # any GitHub repo slug
    python scripts/test_marketplace.py --marketplace ./path     # explicit local path
    python scripts/test_marketplace.py --tests hello,sanitize,score
    python scripts/test_marketplace.py --quick                  # skip slow /prism improve
    python scripts/test_marketplace.py --skip-cleanup
    python scripts/test_marketplace.py --no-setup               # reuse existing install
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# ---------------------------------------------------------------------------
# Paths / defaults
# ---------------------------------------------------------------------------

PRISM_REPO = Path(__file__).parent.parent
TEST_DIR = PRISM_REPO / "test_gsap-ai-marketplace"

# Live GitHub repo — what real users install from
GITHUB_MARKETPLACE = "Unity-Technologies/gsap-ai-market-place"

# Local clone — used when --local flag is passed
LOCAL_MARKETPLACE = PRISM_REPO.parent / "gsap-ai-market-place"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class Result:
    name: str
    passed: bool
    output: str = ""
    elapsed_s: float = 0.0


def _run(
    args: list[str],
    cwd: Path,
    timeout: int = 30,
) -> tuple[int, str]:
    """Run a subprocess, return (returncode, combined stdout+stderr)."""
    try:
        r = subprocess.run(
            args,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        return r.returncode, r.stdout
    except subprocess.TimeoutExpired:
        return -1, f"[TIMEOUT after {timeout}s]"
    except FileNotFoundError as exc:
        return -1, f"[NOT FOUND] {exc}"


def _claude(prompt: str, cwd: Path, timeout: int = 90) -> tuple[bool, str]:
    """Run `claude -p '<prompt>'` and return (ok, output)."""
    rc, out = _run(["claude", "-p", prompt], cwd=cwd, timeout=timeout)
    return rc == 0, out


def _contains(text: str, *fragments: str) -> bool:
    lower = text.lower()
    return all(f.lower() in lower for f in fragments)


# ---------------------------------------------------------------------------
# Setup / teardown
# ---------------------------------------------------------------------------


def _marketplace_source(marketplace: str | Path, test_dir: Path) -> str:
    """Return the source string to pass to `claude plugin marketplace add`.

    GitHub slugs (``owner/repo``) are passed through unchanged.
    Local paths are converted to a forward-slash relative path with a
    leading ``./`` so the CLI treats them as paths, not GitHub slugs.
    """
    s = str(marketplace)
    # Already a GitHub slug (no separators, no dots at start)
    if "/" in s and not s.startswith(".") and not Path(s).exists():
        return s
    # Local path — must be relative + forward-slash for the CLI
    local = Path(s).resolve()
    rel = Path(os.path.relpath(local, test_dir)).as_posix()
    if not rel.startswith("."):
        rel = "./" + rel
    return rel


def setup(marketplace: str | Path, test_dir: Path) -> tuple[bool, str]:
    """Idempotently clean, register marketplace, install plugin."""
    # Remove any stale install
    _run(["claude", "plugin", "uninstall", "prism@gsap-tools"], test_dir, timeout=15)
    _run(["claude", "plugin", "marketplace", "remove", "gsap-tools"], test_dir, timeout=15)

    source = _marketplace_source(marketplace, test_dir)
    rc, out = _run(["claude", "plugin", "marketplace", "add", source], test_dir, timeout=30)
    if rc != 0 or "Successfully added" not in out:
        return False, f"marketplace add failed (source={source!r}):\n{out}"

    rc, out = _run(["claude", "plugin", "install", "prism@gsap-tools"], test_dir, timeout=30)
    if rc != 0 or "Successfully installed" not in out:
        return False, f"plugin install failed:\n{out}"

    _, list_out = _run(["claude", "plugin", "list"], test_dir, timeout=15)
    if "enabled" not in list_out.lower():
        return False, f"plugin not enabled after install:\n{list_out}"

    return True, list_out


def teardown(test_dir: Path) -> None:
    _run(["claude", "plugin", "uninstall", "prism@gsap-tools"], test_dir, timeout=15)
    _run(["claude", "plugin", "marketplace", "remove", "gsap-tools"], test_dir, timeout=15)


# ---------------------------------------------------------------------------
# Tests registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, Callable[[Path, Path], Result]] = {}


def _test(name: str):
    def decorator(fn: Callable[[Path, Path], Result]):
        _REGISTRY[name] = fn
        return fn
    return decorator


# --- Static validation (local paths only — skipped for GitHub source) -----


@_test("validate-marketplace")
def t_validate_marketplace(mp: str | Path, td: Path) -> Result:
    local = Path(mp) if Path(str(mp)).exists() else None
    if local is None:
        return Result("validate-marketplace", True, "[skipped — GitHub source, no local clone]")
    rc, out = _run(["claude", "plugin", "validate", str(local)], td, timeout=15)
    passed = rc == 0 and "Validation passed" in out
    return Result("validate-marketplace", passed, out)


@_test("validate-plugin")
def t_validate_plugin(mp: str | Path, td: Path) -> Result:
    local = Path(mp) if Path(str(mp)).exists() else None
    if local is None:
        return Result("validate-plugin", True, "[skipped — GitHub source, no local clone]")
    rc, out = _run(["claude", "plugin", "validate", str(local / "plugins" / "prism")], td, timeout=15)
    passed = rc == 0 and "Validation passed" in out
    return Result("validate-plugin", passed, out)


@_test("plugin-list")
def t_plugin_list(mp: Path, td: Path) -> Result:
    rc, out = _run(["claude", "plugin", "list"], td, timeout=15)
    passed = rc == 0 and "prism@gsap-tools" in out and "enabled" in out.lower()
    return Result("plugin-list", passed, out)


# --- Functional (model calls) ---------------------------------------------


@_test("hello")
def t_hello(mp: Path, td: Path) -> Result:
    t0 = time.monotonic()
    ok, out = _claude("/prism hello", td, timeout=60)
    elapsed = time.monotonic() - t0
    passed = ok and _contains(out, "prompt engineering", "stage 1")
    return Result("hello", passed, out, elapsed)


@_test("sanitize")
def t_sanitize(mp: Path, td: Path) -> Result:
    t0 = time.monotonic()
    ok, out = _claude('/prism sanitize "send results to test@example.com when done"', td, timeout=60)
    elapsed = time.monotonic() - t0
    passed = ok and ("EMAIL_REDACTED" in out or _contains(out, "email", "pii"))
    return Result("sanitize", passed, out, elapsed)


@_test("score")
def t_score(mp: Path, td: Path) -> Result:
    t0 = time.monotonic()
    ok, out = _claude('/prism score "refactor the database connection pool"', td, timeout=120)
    elapsed = time.monotonic() - t0
    passed = ok and _contains(out, "agentic readiness score", "/100")
    return Result("score", passed, out, elapsed)


@_test("hook-status")
def t_hook_status(mp: Path, td: Path) -> Result:
    t0 = time.monotonic()
    ok, out = _claude("/prism hook status", td, timeout=120)
    elapsed = time.monotonic() - t0
    passed = ok and _contains(out, "hooks")
    return Result("hook-status", passed, out, elapsed)


@_test("explain")
def t_explain(mp: Path, td: Path) -> Result:
    t0 = time.monotonic()
    ok, out = _claude('/prism explain "make it better"', td, timeout=90)
    elapsed = time.monotonic() - t0
    # The explain command should diagnose issues and mention /prism improve
    passed = ok and _contains(out, "prism improve")
    return Result("explain", passed, out, elapsed)


@_test("improve")
def t_improve(mp: Path, td: Path) -> Result:
    """Full pipeline — slowest test (~90-120s). Skipped in quick mode."""
    t0 = time.monotonic()
    ok, out = _claude(
        '/prism improve "add a login page to the auth module and also write the tests"',
        td,
        timeout=180,
    )
    elapsed = time.monotonic() - t0
    passed = ok and (
        _contains(out, "why log")
        or _contains(out, "prism-optimized")
        or _contains(out, "agentic readiness")
    )
    return Result("improve", passed, out, elapsed)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

_QUICK_TESTS = ["validate-marketplace", "validate-plugin", "plugin-list", "hello", "sanitize", "score", "hook-status"]
_ALL_TESTS = list(_REGISTRY)


def _print_result(r: Result) -> None:
    skipped = r.passed and r.output.startswith("[skipped")
    if skipped:
        status = "\033[33mSKIP\033[0m"
    elif r.passed:
        status = "\033[32mPASS\033[0m"
    else:
        status = "\033[31mFAIL\033[0m"
    timing = f"  ({r.elapsed_s:.1f}s)" if r.elapsed_s else ""
    print(f"  {status}  {r.name}{timing}")
    if not r.passed:
        lines = r.output.strip().splitlines()
        for line in lines[:25]:
            print(f"       {line}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--local",
        action="store_true",
        help=f"Use local clone at {LOCAL_MARKETPLACE} instead of GitHub",
    )
    source_group.add_argument(
        "--marketplace",
        metavar="SOURCE",
        default=None,
        help="GitHub slug (owner/repo) or local path. Default: live GitHub repo",
    )
    parser.add_argument(
        "--tests",
        metavar="NAMES",
        help=f"Comma-separated test names to run. Available: {', '.join(_ALL_TESTS)}",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help=f"Run only quick tests (skip /prism improve): {', '.join(_QUICK_TESTS)}",
    )
    parser.add_argument(
        "--skip-cleanup",
        action="store_true",
        help="Leave plugin installed after tests finish",
    )
    parser.add_argument(
        "--no-setup",
        action="store_true",
        help="Skip install step (use after a prior --skip-cleanup run)",
    )
    args = parser.parse_args(argv)

    # Resolve marketplace source
    if args.local:
        if not LOCAL_MARKETPLACE.is_dir():
            print(f"Error: local clone not found: {LOCAL_MARKETPLACE}")
            return 1
        marketplace: str | Path = LOCAL_MARKETPLACE
        source_label = f"local ({LOCAL_MARKETPLACE})"
    elif args.marketplace:
        marketplace = args.marketplace
        source_label = marketplace
    else:
        marketplace = GITHUB_MARKETPLACE
        source_label = f"GitHub ({GITHUB_MARKETPLACE})"

    test_dir = TEST_DIR
    test_dir.mkdir(parents=True, exist_ok=True)

    # Determine which tests to run
    if args.tests:
        names = [t.strip() for t in args.tests.split(",")]
        unknown = [n for n in names if n not in _REGISTRY]
        if unknown:
            print(f"Error: unknown test(s): {', '.join(unknown)}")
            print(f"Available: {', '.join(_ALL_TESTS)}")
            return 1
        selected = {n: _REGISTRY[n] for n in names}
    elif args.quick:
        selected = {n: _REGISTRY[n] for n in _QUICK_TESTS if n in _REGISTRY}
    else:
        selected = _REGISTRY

    # Header
    print()
    print("  Prism Marketplace Integration Tests")
    print(f"  Source      : {source_label}")
    print(f"  Test dir    : {test_dir}")
    mode = "quick" if args.quick else ("custom" if args.tests else "full")
    print(f"  Mode        : {mode}  ({len(selected)} tests)")
    print()

    # Setup
    if not args.no_setup:
        print("  Setting up...", end="  ", flush=True)
        ok, msg = setup(marketplace, test_dir)
        if not ok:
            print("\033[31mFAIL\033[0m")
            print(f"  {msg}")
            return 1
        print("\033[32mOK\033[0m")
        print()

    # Run
    results: list[Result] = []
    for name, fn in selected.items():
        print(f"  [ {name} ] ...", end="  ", flush=True)
        r = fn(marketplace, test_dir)
        results.append(r)
        _print_result(r)

    # Teardown
    if not args.skip_cleanup:
        print()
        print("  Cleaning up...", end="  ", flush=True)
        teardown(test_dir)
        print("\033[32mOK\033[0m")

    # Summary
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    print()
    print("  " + "-" * 36)
    if passed == total:
        print(f"  \033[32mAll {total} tests passed.\033[0m")
        return 0
    else:
        failed = [r.name for r in results if not r.passed]
        print(f"  \033[31m{total - passed}/{total} tests FAILED: {', '.join(failed)}\033[0m")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
