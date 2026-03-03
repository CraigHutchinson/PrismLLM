"""
Integration tests for scripts/schemas/*.json.
Validates that schemas correctly accept valid payloads and reject invalid ones.
Requires: pip install jsonschema
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "schemas"

pytestmark = pytest.mark.skipif(
    not HAS_JSONSCHEMA, reason="jsonschema not installed"
)


def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


# ── score_output.json ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def score_schema():
    return load_schema("score_output.json")


def test_score_schema_accepts_valid(score_schema):
    payload = {
        "structure": 8, "specificity": 7, "security": 10,
        "cache_friendliness": 6, "model_alignment": 8
    }
    jsonschema.validate(payload, score_schema)


def test_score_schema_accepts_with_notes(score_schema):
    payload = {
        "structure": 5, "specificity": 4, "security": 9,
        "cache_friendliness": 3, "model_alignment": 6,
        "notes": ["Structure could use XML tags", "Specificity: add measurable goal"]
    }
    jsonschema.validate(payload, score_schema)


def test_score_schema_rejects_out_of_range_high(score_schema):
    payload = {
        "structure": 11, "specificity": 5, "security": 5,
        "cache_friendliness": 5, "model_alignment": 5
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, score_schema)


def test_score_schema_rejects_out_of_range_low(score_schema):
    payload = {
        "structure": -1, "specificity": 5, "security": 5,
        "cache_friendliness": 5, "model_alignment": 5
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, score_schema)


def test_score_schema_rejects_missing_required(score_schema):
    payload = {"structure": 8, "specificity": 7}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, score_schema)


# ── sanitize_output.json ───────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sanitize_schema():
    return load_schema("sanitize_output.json")


def test_sanitize_schema_accepts_safe(sanitize_schema):
    payload = {"pii_found": [], "injection_risk": False, "safe": True}
    jsonschema.validate(payload, sanitize_schema)


def test_sanitize_schema_accepts_unsafe_with_pii(sanitize_schema):
    payload = {
        "pii_found": ["EMAIL"],
        "injection_risk": False,
        "safe": False,
        "redacted_prompt": "send to [EMAIL_REDACTED]",
        "issues": ["EMAIL detected"]
    }
    jsonschema.validate(payload, sanitize_schema)


def test_sanitize_schema_rejects_missing_required(sanitize_schema):
    payload = {"injection_risk": False}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, sanitize_schema)


# ── refract_plan.json ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def refract_schema():
    return load_schema("refract_plan.json")


def test_refract_schema_accepts_valid(refract_schema):
    payload = {
        "structure_changes": ["Add <task> XML tag", "Add <context> XML tag"],
        "rules_applied": ["ref-001", "ref-003"]
    }
    jsonschema.validate(payload, refract_schema)


def test_refract_schema_accepts_full(refract_schema):
    payload = {
        "structure_changes": ["Add XML tags"],
        "xml_tags_suggested": ["task", "context"],
        "cot_trigger": True,
        "cot_phrase": "Think step by step:",
        "pre_fill_header": "Here is the analysis:\n\n",
        "cache_candidates": ["system prompt"],
        "rules_applied": ["ref-001", "ref-005"],
        "verbosity_flags": ["we shall"]
    }
    jsonschema.validate(payload, refract_schema)


def test_refract_schema_rejects_missing_required(refract_schema):
    payload = {"xml_tags_suggested": ["task"]}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, refract_schema)


# ── pattern_output.json ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def pattern_schema():
    return load_schema("pattern_output.json")


def test_pattern_schema_accepts_valid(pattern_schema):
    payload = {
        "detected_patterns": [
            {"pattern": "we shall", "category": "royal_we",
             "frequency": 0.4, "token_cost": 2, "suggestion": "use imperative verb"}
        ],
        "avg_efficiency_ratio": 0.87,
        "trend": "stable"
    }
    jsonschema.validate(payload, pattern_schema)


def test_pattern_schema_rejects_invalid_trend(pattern_schema):
    payload = {
        "detected_patterns": [],
        "avg_efficiency_ratio": 0.9,
        "trend": "unknown_value"
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, pattern_schema)


def test_pattern_schema_rejects_ratio_out_of_range(pattern_schema):
    payload = {
        "detected_patterns": [],
        "avg_efficiency_ratio": 1.5,
        "trend": "stable"
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload, pattern_schema)
