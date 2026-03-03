"""
conftest.py — shared fixtures for all Prism tests.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

# ── Path setup ─────────────────────────────────────────────────────────────────

REPO_ROOT  = Path(__file__).resolve().parent.parent
SCRIPTS    = REPO_ROOT / "scripts"
HOOKS      = REPO_ROOT / "hooks"
FIXTURES   = Path(__file__).parent / "fixtures"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HOOKS))


# ── Fixture files ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def rules_fixture() -> list[dict]:
    path = FIXTURES / "rules_fixture.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def prompt_log_fixture() -> list[dict]:
    path = FIXTURES / "prompt_log_fixture.jsonl"
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


@pytest.fixture(scope="session")
def hook_payload_clean() -> dict:
    return json.loads((FIXTURES / "hook_payloads" / "clean_prompt.json").read_text())


@pytest.fixture(scope="session")
def hook_payload_pii() -> dict:
    return json.loads((FIXTURES / "hook_payloads" / "pii_prompt.json").read_text())


@pytest.fixture(scope="session")
def hook_payload_injection() -> dict:
    return json.loads((FIXTURES / "hook_payloads" / "injection_prompt.json").read_text())


@pytest.fixture(scope="session")
def hook_payload_bundled() -> dict:
    return json.loads((FIXTURES / "hook_payloads" / "bundled_prompt.json").read_text())


# ── Temp .prism dir ────────────────────────────────────────────────────────────

@pytest.fixture
def prism_tmp(tmp_path: Path) -> Path:
    """Creates a temporary .prism/ directory for tests that write state."""
    prism_dir = tmp_path / ".prism"
    prism_dir.mkdir()
    # Seed a default config
    default_cfg = REPO_ROOT / "scripts" / "prism_config_default.json"
    if default_cfg.exists():
        import shutil
        shutil.copy(default_cfg, prism_dir / "prism.config.json")
    return prism_dir


@pytest.fixture
def kb_tmp(tmp_path: Path, rules_fixture: list[dict]) -> Path:
    """Write rules fixture to a temporary rules.json and return the path."""
    kb_dir = tmp_path / "knowledge-base"
    kb_dir.mkdir()
    kb_path = kb_dir / "rules.json"
    kb_path.write_text(json.dumps(rules_fixture), encoding="utf-8")
    return kb_path
