"""
format_output.py — Prompt structure formatter for Prism.

Selects and renders the appropriate structural syntax for a prompt based on
the target platform/model. The default is Markdown headers — the most
portable format across Claude, GPT-4, Gemini, and older models.

Format Summary
--------------
  markdown  (default)  ## Task / ## Context headers — all models
  xml                  <task>/<context> tags — Claude 3.5+ upgrade
  prefixed             TASK: / CONTEXT: lines — constrained/fallback

Platform → Format defaults
--------------------------
  cursor       → xml        (Claude, native XML support)
  claude_code  → xml        (Claude, native XML support)
  copilot      → markdown   (GPT-4.1, Markdown preferred)
  copilot_free → markdown   (GPT model family)
  unknown      → markdown   (safe portable default)

Rules: ref-016, ref-017, ref-018

Usage (CLI)
-----------
  python scripts/format_output.py --task "Add a login page"
  python scripts/format_output.py --task "..." --context "..." --constraints "..."
  python scripts/format_output.py --task "..." --format xml
  python scripts/format_output.py --detect-format
  python scripts/format_output.py --detect-format --platform copilot
  python scripts/format_output.py --task "..." --json

Exit 0 always (informational).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Format constants
# ---------------------------------------------------------------------------

FORMAT_MARKDOWN = "markdown"
FORMAT_XML = "xml"
FORMAT_PREFIXED = "prefixed"

DEFAULT_FORMAT = FORMAT_MARKDOWN

# Platforms where XML is the preferred upgrade
_XML_PLATFORMS = {"cursor", "claude_code"}

# Canonical section order and display labels
SECTIONS = ["task", "context", "examples", "constraints", "format", "thinking"]

_MARKDOWN_LABELS = {
    "task": "Task",
    "context": "Context",
    "examples": "Examples",
    "constraints": "Constraints",
    "format": "Format",
    "thinking": "Thinking",
}

_XML_TAGS = {
    "task": "task",
    "context": "context",
    "examples": "examples",
    "constraints": "constraints",
    "format": "format",
    "thinking": "thinking",
}

_PREFIXED_LABELS = {
    "task": "TASK",
    "context": "CONTEXT",
    "examples": "EXAMPLES",
    "constraints": "CONSTRAINTS",
    "format": "FORMAT",
    "thinking": "THINKING",
}


# ---------------------------------------------------------------------------
# Format selection
# ---------------------------------------------------------------------------

def select_format(platform: Optional[str] = None) -> str:
    """
    Return the preferred structural format for the given platform.

    If platform is None, attempts auto-detection via platform_model.py.
    Falls back to DEFAULT_FORMAT (markdown) when platform is unknown.
    """
    if platform is None:
        platform = _detect_platform()

    if platform in _XML_PLATFORMS:
        return FORMAT_XML
    return FORMAT_MARKDOWN


def _detect_platform() -> str:
    """Import platform_model and detect, or return 'unknown' on import error."""
    scripts_dir = str(Path(__file__).resolve().parent)
    if scripts_dir not in sys.path:  # pragma: no cover
        sys.path.insert(0, scripts_dir)
    try:
        import platform_model
        return platform_model.detect_platform()
    except Exception:
        return os.environ.get("PRISM_PLATFORM", "unknown")


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def _render_markdown(sections: dict[str, str]) -> str:
    """Render sections as Markdown headers (## Section)."""
    parts: list[str] = []
    for key in SECTIONS:
        value = sections.get(key, "").strip()
        if not value:
            continue
        label = _MARKDOWN_LABELS[key]
        parts.append(f"## {label}\n{value}")
    return "\n\n".join(parts)


def _render_xml(sections: dict[str, str]) -> str:
    """Render sections as XML tags (<section>...</section>)."""
    parts: list[str] = []
    for key in SECTIONS:
        value = sections.get(key, "").strip()
        if not value:
            continue
        tag = _XML_TAGS[key]
        # Inline for single-line values, block for multi-line
        if "\n" in value:
            parts.append(f"<{tag}>\n{value}\n</{tag}>")
        else:
            parts.append(f"<{tag}>{value}</{tag}>")
    return "\n\n".join(parts)


def _render_prefixed(sections: dict[str, str]) -> str:
    """Render sections as prefixed lines (LABEL: value)."""
    parts: list[str] = []
    for key in SECTIONS:
        value = sections.get(key, "").strip()
        if not value:
            continue
        label = _PREFIXED_LABELS[key]
        # Multi-line: label on its own line, then content
        if "\n" in value:
            parts.append(f"{label}:\n{value}")
        else:
            parts.append(f"{label}: {value}")
    return "\n\n".join(parts)


_RENDERERS = {
    FORMAT_MARKDOWN: _render_markdown,
    FORMAT_XML: _render_xml,
    FORMAT_PREFIXED: _render_prefixed,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_prompt(
    sections: dict[str, str],
    *,
    format_style: Optional[str] = None,
    platform: Optional[str] = None,
) -> str:
    """
    Render a prompt from named sections using the appropriate format.

    Parameters
    ----------
    sections : dict
        Keys must be subset of SECTIONS ('task', 'context', 'examples',
        'constraints', 'format', 'thinking'). Empty/missing sections are omitted.
    format_style : str, optional
        One of FORMAT_MARKDOWN, FORMAT_XML, FORMAT_PREFIXED.
        If None, auto-selects based on platform.
    platform : str, optional
        Platform hint ('cursor', 'claude_code', 'copilot', etc.).
        Used only when format_style is None.

    Returns
    -------
    str
        Formatted prompt text.
    """
    if format_style is None:
        format_style = select_format(platform)
    if format_style not in _RENDERERS:
        raise ValueError(
            f"Unknown format_style '{format_style}'. "
            f"Choose from: {', '.join(_RENDERERS)}"
        )
    return _RENDERERS[format_style](sections)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prism prompt formatter — renders structured prompts in the "
                    "optimal syntax for the target platform.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/format_output.py --detect-format\n"
            "  python scripts/format_output.py --task 'Add login page' --context 'Auth module'\n"
            "  python scripts/format_output.py --task '...' --format xml\n"
        ),
    )
    parser.add_argument("--task",        default="", help="Primary task text")
    parser.add_argument("--context",     default="", help="Background context")
    parser.add_argument("--constraints", default="", help="Hard constraints")
    parser.add_argument("--examples",    default="", help="Few-shot examples")
    parser.add_argument("--format",      default=None,
                        choices=[FORMAT_MARKDOWN, FORMAT_XML, FORMAT_PREFIXED],
                        dest="format_style",
                        help="Override format (default: auto-detect from platform)")
    parser.add_argument("--platform",    default=None,
                        help="Override platform for format selection")
    parser.add_argument("--detect-format", action="store_true",
                        help="Print the detected/selected format name and exit")
    parser.add_argument("--json",        action="store_true", dest="json_out",
                        help="Output JSON with format name and rendered text")
    args = parser.parse_args(argv)

    # Resolve format
    fmt = args.format_style if args.format_style else select_format(args.platform)

    if args.detect_format:
        print(fmt)
        return 0

    sections: dict[str, str] = {}
    for key in ("task", "context", "constraints", "examples"):
        val = getattr(args, key, "").strip()
        if val:
            sections[key] = val

    # If no sections given via flags, read task from stdin
    if not sections and not sys.stdin.isatty():
        sections["task"] = sys.stdin.read().strip()

    if not sections:
        parser.print_help()
        return 1

    rendered = render_prompt(sections, format_style=fmt)

    if args.json_out:
        print(json.dumps({"format": fmt, "output": rendered}, indent=2))
    else:
        print(rendered)

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
