"""
Unit tests for scripts/platform_model.py.
Uses environment variable mocking to test platform detection.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
import platform_model


def _clean_env(monkeypatch):
    """Remove all platform signal env vars to ensure clean detection state."""
    for key in [
        "CLAUDE_CODE_ENTRYPOINT", "ANTHROPIC_API_KEY", "CLAUDECODE",
        "CURSOR_TRACE_ID", "CURSOR_SESSION_ID", "CURSOR_USER_ID",
        "GITHUB_TOKEN", "CODESPACES", "GITHUB_COPILOT_TOKEN",
        "GITHUB_COPILOT_PLAN", "PRISM_PLATFORM",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_detect_claude_code(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "1")
    assert platform_model.detect_platform() == "claude_code"


def test_detect_cursor(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("CURSOR_TRACE_ID", "trace-abc123")
    assert platform_model.detect_platform() == "cursor"


def test_detect_copilot_paid(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN", "tok123")
    monkeypatch.setenv("GITHUB_COPILOT_PLAN", "paid")
    assert platform_model.detect_platform() == "copilot"


def test_detect_copilot_free(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN", "tok123")
    monkeypatch.setenv("GITHUB_COPILOT_PLAN", "free")
    assert platform_model.detect_platform() == "copilot_free"


def test_detect_unknown(monkeypatch):
    _clean_env(monkeypatch)
    assert platform_model.detect_platform() == "unknown"


def test_detect_explicit_env_override(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("PRISM_PLATFORM", "claude_code")
    assert platform_model.detect_platform() == "claude_code"


def test_fast_model_claude_code():
    assert platform_model.get_fast_model("claude_code") == "claude-haiku-4-5"


def test_fast_model_copilot_paid():
    assert platform_model.get_fast_model("copilot") == "gpt-4.1"


def test_fast_model_copilot_free():
    assert platform_model.get_fast_model("copilot_free") == "goldeneye"


def test_fast_model_cursor_is_none():
    assert platform_model.get_fast_model("cursor") is None


def test_fast_model_unknown_is_none():
    assert platform_model.get_fast_model("unknown") is None


def test_routing_mode_default(tmp_path):
    assert platform_model.get_routing_mode(tmp_path / "nonexistent.json") == "platform"


def test_routing_mode_from_config(tmp_path):
    config_path = tmp_path / "prism.config.json"
    config_path.write_text(json.dumps({"model_routing": {"mode": "capable"}}))
    assert platform_model.get_routing_mode(config_path) == "capable"


def test_resolve_analysis_model_platform():
    model = platform_model.resolve_analysis_model("claude_code")
    assert model == "claude-haiku-4-5"


def test_resolve_analysis_model_capable(tmp_path):
    cfg = tmp_path / "prism.config.json"
    cfg.write_text(json.dumps({"model_routing": {"mode": "capable"}}))
    model = platform_model.resolve_analysis_model("claude_code", config_path=cfg)
    assert model is None


def test_ollama_model_disabled_by_default(tmp_path):
    assert platform_model.get_ollama_model(tmp_path / "nonexistent.json") is None


def test_ollama_model_when_enabled(tmp_path):
    cfg = tmp_path / "prism.config.json"
    cfg.write_text(json.dumps({
        "model_routing": {
            "ollama": {"enabled": True, "model": "llama3.2"}
        }
    }))
    assert platform_model.get_ollama_model(cfg) == "llama3.2"


def test_get_ollama_model_default_config_missing(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    result = platform_model.get_ollama_model(tmp_path / "missing.json")
    assert result is None


def test_get_ollama_model_corrupt_json(tmp_path):
    cfg = tmp_path / "prism.config.json"
    cfg.write_text("NOT JSON")
    assert platform_model.get_ollama_model(cfg) is None


def test_get_routing_mode_missing(tmp_path):
    assert platform_model.get_routing_mode(tmp_path / "missing.json") == "platform"


def test_get_routing_mode_corrupt(tmp_path):
    cfg = tmp_path / "prism.config.json"
    cfg.write_text("NOT JSON")
    assert platform_model.get_routing_mode(cfg) == "platform"


def test_get_routing_mode_valid(tmp_path):
    cfg = tmp_path / "prism.config.json"
    cfg.write_text(json.dumps({"model_routing": {"mode": "local"}}))
    assert platform_model.get_routing_mode(cfg) == "local"


def test_resolve_local_with_ollama(tmp_path):
    cfg = tmp_path / "prism.config.json"
    cfg.write_text(json.dumps({
        "model_routing": {"mode": "local", "ollama": {"enabled": True, "model": "llama3.2"}}
    }))
    result = platform_model.resolve_analysis_model("cursor", config_path=cfg)
    assert result == "llama3.2"


def test_get_fast_model_auto_detect(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("PRISM_PLATFORM", "claude_code")
    result = platform_model.get_fast_model(None)
    assert result == "claude-haiku-4-5"


def test_cli_main_plain(capsys):
    with patch("sys.argv", ["platform_model.py"]):
        platform_model.main()
    out = capsys.readouterr().out
    assert isinstance(out.strip(), str)


def test_cli_main_verbose(capsys):
    with patch("sys.argv", ["platform_model.py", "--verbose"]):
        platform_model.main()
    out = capsys.readouterr().out
    assert "Platform detected:" in out
    assert "Routing mode:" in out


def test_cli_main_platform_override(capsys):
    with patch("sys.argv", ["platform_model.py", "--platform", "copilot"]):
        platform_model.main()
    out = capsys.readouterr().out
    assert isinstance(out.strip(), str)
