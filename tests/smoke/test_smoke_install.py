"""
test_smoke_install.py — Smoke tests for verify_install.py.

These tests confirm the install verifier itself is functional and produces
the correct output on a healthy repo and on a repo with a simulated fault.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, run_script


# ---------------------------------------------------------------------------
# Basic health
# ---------------------------------------------------------------------------

def test_verify_install_script_exists():
    """The verifier script must be present in scripts/."""
    assert (REPO_ROOT / "scripts" / "verify_install.py").exists()


def test_verify_install_passes():
    """verify_install.py exits 0 on a healthy repo."""
    result = run_script("verify_install.py")
    assert result.returncode == 0, (
        f"verify_install.py failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "checks passed" in result.stdout.lower() or "all" in result.stdout.lower()


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def test_verify_install_json_output():
    """--json flag produces valid JSON with all_passed=True."""
    result = run_script("verify_install.py", "--json")
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert data["all_passed"] is True
    assert data["passed"] == data["total"]
    assert len(data["checks"]) == data["total"]
    for check in data["checks"]:
        assert "label" in check
        assert "passed" in check
        assert check["passed"] is True, f"Check failed: {check}"


def test_verify_install_json_check_names():
    """JSON output includes expected check labels."""
    result = run_script("verify_install.py", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    labels = [c["label"] for c in data["checks"]]
    combined = " ".join(labels).lower()
    assert "python" in combined
    assert "jsonschema" in combined
    assert "scripts" in combined
    assert "hook" in combined
    assert "pii_scan" in combined
    assert "stage2_gate" in combined


# ---------------------------------------------------------------------------
# Fault injection
# ---------------------------------------------------------------------------

def test_verify_install_detects_missing_script(tmp_path):
    """Exit 1 and actionable hint when a required script is missing."""
    # Copy repo into tmp so we can safely modify it
    tmp_repo = tmp_path / "Prism"
    shutil.copytree(str(REPO_ROOT), str(tmp_repo))

    victim = tmp_repo / "scripts" / "stage2_gate.py"
    victim.rename(victim.with_suffix(".py.bak"))

    result = run_script(
        "verify_install.py",
        "--repo-root", str(tmp_repo),
        "--json",
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["all_passed"] is False
    failed = [c for c in data["checks"] if not c["passed"]]
    assert len(failed) >= 1
    assert any("stage2_gate" in c["label"].lower() or "scripts" in c["label"].lower() for c in failed)
    assert any(c["hint"] for c in failed), "Expected a fix hint on failure"


def test_verify_install_detects_corrupt_json(tmp_path):
    """Exit 1 when a JSON data file is corrupt."""
    tmp_repo = tmp_path / "Prism"
    shutil.copytree(str(REPO_ROOT), str(tmp_repo))

    rules_file = tmp_repo / "knowledge-base" / "rules.json"
    rules_file.write_text("{ not valid json }", encoding="utf-8")

    result = run_script(
        "verify_install.py",
        "--repo-root", str(tmp_repo),
        "--json",
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["all_passed"] is False


# ---------------------------------------------------------------------------
# Custom --repo-root
# ---------------------------------------------------------------------------

def test_verify_install_custom_repo_root():
    """--repo-root flag pointing at the actual repo also passes."""
    result = run_script("verify_install.py", "--repo-root", str(REPO_ROOT), "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["all_passed"] is True
