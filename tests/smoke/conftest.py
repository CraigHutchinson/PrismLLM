"""
conftest.py — shared helpers for Prism smoke tests.

Smoke tests exercise the public CLI surface end-to-end via subprocess,
mirroring exactly what a user would do after following the README.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO_ROOT / "scripts"
HOOKS = REPO_ROOT / "hooks"

# PYTHONPATH to pass to subprocesses so bare-import scripts can find their siblings
_PYTHONPATH = f"{SCRIPTS}{':' if sys.platform != 'win32' else ';'}{HOOKS}"


def run_script(script_name: str, *args: str, input_text: str | None = None, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a script from scripts/ or hooks/ via subprocess and return the result."""
    # Resolve the script — check scripts/ first, then hooks/
    script_path = SCRIPTS / script_name
    if not script_path.exists():
        script_path = HOOKS / script_name
    return subprocess.run(
        [sys.executable, str(script_path), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(REPO_ROOT),
        env={
            **_base_env(),
            "PYTHONPATH": _PYTHONPATH,
        },
        input=input_text,
    )


def _base_env() -> dict:
    import os
    # Start from the current environment so PATH etc. are inherited, then
    # override only what we need.
    env = dict(os.environ)
    # Remove any existing PRISM_PLATFORM override so tests are platform-neutral
    env.pop("PRISM_PLATFORM", None)
    return env


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT
