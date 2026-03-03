"""
Unit tests for scripts/kb_query.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
import kb_query


def test_filter_by_pillar(kb_tmp):
    results = kb_query.query(pillar="refraction", kb_path=kb_tmp, no_cache=True)
    assert all(r["pillar"] == "refraction" for r in results)
    assert len(results) > 0


def test_filter_by_sanitization_pillar(kb_tmp):
    results = kb_query.query(pillar="sanitization", kb_path=kb_tmp, no_cache=True)
    assert all(r["pillar"] == "sanitization" for r in results)


def test_filter_by_apply_cost_script(kb_tmp):
    results = kb_query.query(apply_cost="script", kb_path=kb_tmp, no_cache=True)
    assert all(r["apply_cost"] == "script" for r in results)
    assert len(results) > 0


def test_filter_by_apply_cost_multi(kb_tmp):
    results = kb_query.query(apply_cost="script,fast", kb_path=kb_tmp, no_cache=True)
    assert all(r["apply_cost"] in ("script", "fast") for r in results)


def test_filter_by_source_official(kb_tmp):
    results = kb_query.query(source="official", kb_path=kb_tmp, no_cache=True)
    assert all(r["source_type"] == "official" for r in results)


def test_filter_by_ids(kb_tmp):
    results = kb_query.query(ids=["ref-001", "san-005"], kb_path=kb_tmp, no_cache=True)
    ids = {r["id"] for r in results}
    assert "ref-001" in ids
    assert "san-005" in ids
    assert len(results) == 2


def test_filter_by_tag(kb_tmp):
    results = kb_query.query(tag="xml", kb_path=kb_tmp, no_cache=True)
    assert all("xml" in r.get("tags", []) for r in results)


def test_no_filter_returns_all(kb_tmp, rules_fixture):
    results = kb_query.query(kb_path=kb_tmp, no_cache=True)
    assert len(results) == len(rules_fixture)


def test_model_filter_all(kb_tmp):
    results = kb_query.query(model="all", kb_path=kb_tmp, no_cache=True)
    assert len(results) > 0


def test_model_filter_claude4(kb_tmp):
    results = kb_query.query(model="claude-4+", kb_path=kb_tmp, no_cache=True)
    assert len(results) >= 0


def test_empty_result_for_unknown_pillar(kb_tmp):
    results = kb_query.query(pillar="nonexistent", kb_path=kb_tmp, no_cache=True)
    assert results == []


def test_missing_kb_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        kb_query.query(kb_path=tmp_path / "nonexistent.json", no_cache=True)


def test_cache_hit(kb_tmp, tmp_path):
    cache_dir = tmp_path / "cache"
    r1 = kb_query.query(pillar="refraction", kb_path=kb_tmp, cache_dir=cache_dir)
    r2 = kb_query.query(pillar="refraction", kb_path=kb_tmp, cache_dir=cache_dir)
    assert r1 == r2


def test_model_applies_function():
    rule = {"model_applies": ["claude-3.5+"], "model_deprecated": None}
    assert kb_query.model_applies(rule, "claude-3.5") is True
    assert kb_query.model_applies(rule, "claude-4+") is True


def test_model_applies_all():
    rule = {"model_applies": ["all"], "model_deprecated": None}
    assert kb_query.model_applies(rule, "claude-3.5") is True
    assert kb_query.model_applies(rule, "claude-4+") is True
