"""
Unit tests for scripts/overhead_calc.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
import overhead_calc


def test_chars_to_tokens_basic():
    assert overhead_calc.chars_to_tokens(400) == 100
    assert overhead_calc.chars_to_tokens(4) == 1
    assert overhead_calc.chars_to_tokens(0) == 0


def test_chars_to_tokens_non_multiple():
    assert overhead_calc.chars_to_tokens(401) == 100
    assert overhead_calc.chars_to_tokens(7) == 1


def test_scan_components_returns_dict(tmp_path):
    result = overhead_calc.scan_components(tmp_path)
    assert isinstance(result, dict)
    for name, info in result.items():
        assert "tokens_est" in info
        assert "path" in info
        assert "exists" in info


def test_missing_component_tokens_zero(tmp_path):
    result = overhead_calc.scan_components(tmp_path)
    for name, info in result.items():
        if not info["exists"]:
            assert info["tokens_est"] == 0


def test_existing_component_tokens_nonzero(tmp_path):
    skill_dir = tmp_path / ".cursor" / "skills" / "prism"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("x" * 400, encoding="utf-8")

    result = overhead_calc.scan_components(tmp_path)
    assert result["skill_md"]["tokens_est"] == 100
    assert result["skill_md"]["exists"] is True


def test_write_and_read_component_sizes(tmp_path):
    prism_dir = tmp_path / ".prism"
    prism_dir.mkdir()
    output_path = prism_dir / "component-sizes.json"

    overhead_calc.run(root=tmp_path, output_path=output_path)

    assert output_path.exists()
    data = json.loads(output_path.read_text())
    assert "components" in data
    assert "per_command_overhead" in data
    assert "total_prism_tokens_est" in data


def test_per_command_table_has_improve_prompt(tmp_path):
    result = overhead_calc.run(root=tmp_path, output_path=tmp_path / ".prism" / "sizes.json")
    assert "/prism improve-prompt" in result["per_command_overhead"]


def test_build_command_table_returns_integers(tmp_path):
    components = overhead_calc.scan_components(tmp_path)
    table = overhead_calc.build_command_table(components)
    assert all(isinstance(v, int) for v in table.values())
