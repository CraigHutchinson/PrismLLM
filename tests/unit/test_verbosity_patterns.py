"""
Structural validation of scripts/verbosity_patterns.json.
Checks schema compliance and required fields.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VP_PATH   = REPO_ROOT / "scripts" / "verbosity_patterns.json"


@pytest.fixture(scope="module")
def verbosity_data():
    return json.loads(VP_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def patterns(verbosity_data):
    return verbosity_data["patterns"]


def test_file_exists():
    assert VP_PATH.exists()


def test_top_level_keys(verbosity_data):
    assert "version" in verbosity_data
    assert "patterns" in verbosity_data
    assert isinstance(verbosity_data["patterns"], list)


def test_minimum_pattern_count(patterns):
    assert len(patterns) >= 20, "Expected at least 20 seeded patterns"


def test_each_pattern_has_required_fields(patterns):
    required = {"phrase", "category", "terse_alt", "token_saving"}
    for p in patterns:
        missing = required - p.keys()
        assert not missing, f"Pattern '{p.get('phrase','?')}' missing fields: {missing}"


def test_phrase_is_non_empty_string(patterns):
    for p in patterns:
        assert isinstance(p["phrase"], str) and len(p["phrase"]) > 0


def test_category_is_valid(patterns):
    valid = {"royal_we", "politeness", "preamble", "filler", "hedging", "bundling", "vague"}
    for p in patterns:
        assert p["category"] in valid, f"Unknown category '{p['category']}' in pattern '{p['phrase']}'"


def test_token_saving_is_non_negative_integer(patterns):
    for p in patterns:
        assert isinstance(p["token_saving"], int)
        assert p["token_saving"] >= 0


def test_no_duplicate_phrases(patterns):
    phrases = [p["phrase"].lower() for p in patterns]
    assert len(phrases) == len(set(phrases)), "Duplicate phrases found"


def test_has_royal_we_category(patterns):
    categories = {p["category"] for p in patterns}
    assert "royal_we" in categories


def test_has_filler_category(patterns):
    categories = {p["category"] for p in patterns}
    assert "filler" in categories


def test_has_bundling_category(patterns):
    categories = {p["category"] for p in patterns}
    assert "bundling" in categories
