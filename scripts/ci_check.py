"""
ci_check.py — Run all CI checks locally before pushing.

Replicates the three GitHub Actions jobs in sequence:
  1. Unit + integration tests with coverage (mirrors 'test' job)
  2. Smoke tests (mirrors 'smoke' job)
  3. Install verifier (mirrors 'install-smoke' job)

Usage:
    python scripts/ci_check.py [--fast]

  --fast  Skip smoke tests (faster inner-loop check)

Exit 0 = all checks green. Non-zero = failure.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
HOOKS = REPO_ROOT / "hooks"
SEP = ":" if sys.platform != "win32" else ";"
PYTHONPATH = f"{SCRIPTS}{SEP}{HOOKS}"


def _run(label: str, cmd: list[str], *, env_extra: dict | None = None) -> bool:
    env = dict(os.environ)
    env["PYTHONPATH"] = PYTHONPATH
    if env_extra:
        env.update(env_extra)
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, env=env, cwd=str(REPO_ROOT))
    return result.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run all CI checks locally")
    parser.add_argument("--fast", action="store_true", help="Skip smoke tests")
    args = parser.parse_args(argv)

    py = sys.executable
    results: list[tuple[str, bool]] = []

    # ── Step 1: Unit + integration tests ─────────────────────────────────────
    ok = _run(
        "Step 1: Unit + integration tests (--cov=scripts --cov=hooks, fail-under=80)",
        [py, "-m", "pytest", "tests/", "--ignore=tests/smoke",
         "--cov=scripts", "--cov=hooks", "--cov-report=term-missing",
         "--cov-fail-under=80", "-q"],
    )
    results.append(("Unit + integration tests", ok))

    # ── Step 2: Security-critical coverage at 100% ───────────────────────────
    ok = _run(
        "Step 2: Security-critical coverage (pii_scan + prism_preparser @ 100%)",
        [py, "-m", "pytest",
         "tests/unit/test_pii_scan.py",
         "tests/integration/test_hook_preparser.py",
         "--cov=pii_scan", "--cov=prism_preparser",
         "--cov-report=term-missing", "--cov-fail-under=100", "-q"],
    )
    results.append(("Security-critical coverage @ 100%", ok))

    # ── Step 3: JSON schema validation ────────────────────────────────────────
    ok = _run(
        "Step 3: Validate JSON schemas",
        [py, "-c",
         "import json, pathlib\n"
         "for f in pathlib.Path('scripts/schemas').glob('*.json'):\n"
         "    json.loads(f.read_text()); print(f'OK: {f.name}')\n"
         "for f in pathlib.Path('knowledge-base').glob('*.json'):\n"
         "    json.loads(f.read_text()); print(f'OK: {f.name}')"],
    )
    results.append(("JSON schema validation", ok))

    # ── Step 4: verbosity_patterns.json structure ─────────────────────────────
    ok = _run(
        "Step 4: Validate verbosity_patterns.json",
        [py, "-c",
         "import json\n"
         "data = json.loads(open('scripts/verbosity_patterns.json').read())\n"
         "assert 'patterns' in data\n"
         "assert len(data['patterns']) >= 20\n"
         "required = {'phrase','category','terse_alt','token_saving'}\n"
         "for p in data['patterns']:\n"
         "    missing = required - set(p.keys())\n"
         "    assert not missing, f'Pattern missing fields: {missing}'\n"
         "print(f\"OK: {len(data['patterns'])} patterns validated\")"],
    )
    results.append(("verbosity_patterns.json structure", ok))

    # ── Step 5 (optional): Smoke tests ───────────────────────────────────────
    if not args.fast:
        ok = _run(
            "Step 5: Smoke tests (CLI surface)",
            [py, "-m", "pytest", "tests/smoke/", "-v"],
        )
        results.append(("Smoke tests", ok))

    # ── Step 6: Install verifier ──────────────────────────────────────────────
    ok = _run(
        "Step 6: Install verifier (verify_install.py)",
        [py, str(SCRIPTS / "verify_install.py")],
        env_extra={"PYTHONPATH": ""},  # simulate runtime-only deps
    )
    results.append(("Install verifier", ok))

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  CI Check Summary")
    print(f"{'='*60}")
    all_passed = True
    for label, passed in results:
        mark = "OK  " if passed else "FAIL"
        print(f"  [{mark}] {label}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All checks passed. Safe to push.")
        return 0
    else:
        failed = sum(1 for _, p in results if not p)
        print(f"{failed} check(s) failed. Fix before pushing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
