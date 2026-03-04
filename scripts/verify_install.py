"""
verify_install.py — Prism post-install health checker.

Usage:
    python scripts/verify_install.py [--repo-root PATH] [--json]

Exit 0  = all checks passed.
Exit 1  = one or more checks failed.
"""
from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"


def _ok(label: str) -> dict:
    return {"label": label, "passed": True, "hint": ""}


def _fail(label: str, hint: str) -> dict:
    return {"label": label, "passed": False, "hint": hint}


def _supports_unicode() -> bool:
    encoding = getattr(sys.stdout, "encoding", "") or ""
    try:
        "✓✗→".encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def _print_result(result: dict, use_colour: bool = True) -> None:
    uni = _supports_unicode()
    pass_mark = "✓" if uni else "OK"
    fail_mark = "✗" if uni else "FAIL"
    arrow = "→" if uni else "->"
    if result["passed"]:
        mark = f"{_GREEN}{pass_mark}{_RESET}" if use_colour else pass_mark
    else:
        mark = f"{_RED}{fail_mark}{_RESET}" if use_colour else fail_mark
    print(f"  {mark} {result['label']}")
    if not result["passed"]:
        print(f"      {arrow} {result['hint']}")


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_python_version() -> dict:
    major, minor = sys.version_info[:2]
    label = f"Python {major}.{minor} (>= 3.9 required)"
    if (major, minor) >= (3, 9):
        return _ok(label)
    return _fail(label, f"Upgrade Python: currently {major}.{minor}, need 3.9+")


def check_jsonschema() -> dict:
    try:
        import importlib.util
        spec = importlib.util.find_spec("jsonschema")
        if spec is None:
            raise ImportError
        import jsonschema  # noqa: F401
        try:
            import importlib.metadata as _imeta
            version = _imeta.version("jsonschema")
        except Exception:
            version = "installed"
        return _ok(f"jsonschema {version} installed")
    except (ImportError, Exception):
        return _fail(
            "jsonschema not found",
            "pip install -r requirements.txt",
        )


def check_scripts_present(repo_root: Path) -> dict:
    required = [
        "pii_scan.py", "kb_query.py", "overhead_calc.py",
        "platform_model.py", "pattern_analysis.py", "usage_log.py",
        "hook_installer.py", "stage2_gate.py",
    ]
    missing = [f for f in required if not (repo_root / "scripts" / f).exists()]
    if not missing:
        return _ok(f"All {len(required)} scripts present")
    return _fail(
        f"Missing scripts: {', '.join(missing)}",
        "Re-clone the repository: git clone https://github.com/CraigHutchinson/PrismLLM",
    )


def check_hook_script_present(repo_root: Path) -> dict:
    path = repo_root / "hooks" / "prism_preparser.py"
    if path.exists():
        return _ok("Hook script present (hooks/prism_preparser.py)")
    return _fail(
        "hooks/prism_preparser.py not found",
        "Re-clone the repository or check the hooks/ directory",
    )


def check_data_files_present(repo_root: Path) -> dict:
    required = [
        repo_root / "scripts" / "verbosity_patterns.json",
        repo_root / "scripts" / "prism_config_default.json",
        repo_root / "knowledge-base" / "rules.json",
    ]
    missing = [str(p.relative_to(repo_root)) for p in required if not p.exists()]
    if not missing:
        return _ok(f"All {len(required)} data files present")
    return _fail(
        f"Missing data files: {', '.join(missing)}",
        "Re-clone the repository",
    )


def check_json_schemas(repo_root: Path) -> dict:
    schema_dir = repo_root / "scripts" / "schemas"
    kb_file = repo_root / "knowledge-base" / "rules.json"
    checked: list[str] = []
    errors: list[str] = []

    for path in list(schema_dir.glob("*.json")) + [kb_file]:
        if not path.exists():
            errors.append(f"{path.name} missing")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if path == kb_file:
                rule_count = len(data) if isinstance(data, list) else 0
            checked.append(path.name)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: {exc}")

    if errors:
        return _fail(
            f"JSON schema errors: {'; '.join(errors)}",
            "Restore the file from the repository",
        )

    kb_rules = 0
    if kb_file.exists():
        try:
            kb_data = json.loads(kb_file.read_text(encoding="utf-8"))
            kb_rules = len(kb_data) if isinstance(kb_data, list) else 0
        except json.JSONDecodeError:
            pass

    schema_count = len(list(schema_dir.glob("*.json")))
    return _ok(f"JSON schemas valid ({schema_count} schemas, {kb_rules} rules)")


def check_pii_scan_functional(repo_root: Path) -> dict:
    scripts_dir = str(repo_root / "scripts")
    try:
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import importlib
        pii_mod = importlib.import_module("pii_scan")
        result = pii_mod.scan("hello world")
        if not result.safe:
            return _fail(
                "pii_scan returned safe=False on a clean prompt",
                "Check scripts/pii_scan.py for false-positive patterns",
            )
        return _ok("pii_scan functional (clean prompt -> safe)")
    except Exception as exc:
        return _fail(f"pii_scan import/run failed: {exc}", "Check scripts/pii_scan.py")


def check_stage2_gate_functional(repo_root: Path) -> dict:
    scripts_dir = str(repo_root / "scripts")
    try:
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import importlib
        gate_mod = importlib.import_module("stage2_gate")
        out = gate_mod.evaluate_prompt("Fix the login bug on the auth page")
        if not isinstance(out, dict) or "ok" not in out:
            return _fail(
                f"stage2_gate returned unexpected output '{out}' on a specific prompt",
                "Check scripts/stage2_gate.py evaluate_prompt()",
            )
        return _ok(f"stage2_gate functional (specific prompt -> ok={out.get('ok')})")
    except Exception as exc:
        return _fail(f"stage2_gate import/run failed: {exc}", "Check scripts/stage2_gate.py")


def check_hook_installer_status(repo_root: Path) -> dict:
    script = repo_root / "scripts" / "hook_installer.py"
    if not script.exists():
        return _fail("hook_installer.py not found", "Re-clone the repository")
    try:
        result = subprocess.run(
            [sys.executable, str(script), "--action", "status", "--root", str(repo_root)],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            return _fail(
                f"hook_installer --action status exited {result.returncode}",
                result.stderr.strip() or "Check scripts/hook_installer.py",
            )
        return _ok("hook_installer --action status: ok")
    except subprocess.TimeoutExpired:
        return _fail("hook_installer timed out", "Check scripts/hook_installer.py for hangs")
    except Exception as exc:
        return _fail(f"hook_installer failed: {exc}", "Check scripts/hook_installer.py")


def check_prism_dir_writeable() -> dict:
    try:
        with tempfile.TemporaryDirectory() as tmp:
            prism_dir = Path(tmp) / ".prism"
            prism_dir.mkdir()
            test_file = prism_dir / ".write-test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
        return _ok(".prism/ directory writeable")
    except Exception as exc:
        return _fail(f".prism/ not writeable: {exc}", "Check file system permissions")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

CHECKS = [
    ("python_version",       lambda root: check_python_version()),
    ("jsonschema",           lambda root: check_jsonschema()),
    ("scripts_present",      check_scripts_present),
    ("hook_script_present",  check_hook_script_present),
    ("data_files_present",   check_data_files_present),
    ("json_schemas",         check_json_schemas),
    ("pii_scan",             check_pii_scan_functional),
    ("stage2_gate",          check_stage2_gate_functional),
    ("hook_installer",       check_hook_installer_status),
    ("prism_dir_writeable",  lambda root: check_prism_dir_writeable()),
]


def run_checks(repo_root: Path) -> list[dict]:
    results = []
    for _name, fn in CHECKS:
        results.append(fn(repo_root))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prism post-install health checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Path to the PrismLLM repository root (default: auto-detect from this script's location)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of human-readable text",
    )
    args = parser.parse_args(argv)

    if args.repo_root:
        repo_root = Path(args.repo_root).resolve()
    else:
        repo_root = Path(__file__).resolve().parent.parent

    results = run_checks(repo_root)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    all_passed = passed == total

    if args.json:
        print(json.dumps({"all_passed": all_passed, "passed": passed, "total": total, "checks": results}, indent=2))
        return 0 if all_passed else 1

    # Human-readable output
    use_colour = sys.stdout.isatty()
    print("Prism Install Verifier")
    print("======================")
    for result in results:
        _print_result(result, use_colour=use_colour)

    print()
    if all_passed:
        print(f"All {total} checks passed. Prism is ready.")
        print('Run: /prism improve-prompt "your first prompt here"')
    else:
        failed = total - passed
        print(f"{failed} of {total} checks failed. Fix the issues above and re-run.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
