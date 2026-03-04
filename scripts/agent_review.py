"""
agent_review.py
---------------
Deterministic analysis of agent/skill markdown files for common design
anti-patterns.  Implements five rules (agt-001 … agt-005) and can either
report issues or rewrite the file in-place.

CLI:
  python scripts/agent_review.py --file <path>            # human-readable table
  python scripts/agent_review.py --file <path> --json     # structured JSON output
  python scripts/agent_review.py --file <path> --apply    # analyse + rewrite file
  python scripts/agent_review.py --file <path> --json --apply  # both

Rules:
  agt-001  Negative instruction → rewrite as positive constraint
  agt-002  Duplicate instruction across sections → remove the copy
  agt-003  Unversioned model pin (e.g. "sonnet") → suggest versioned name
  agt-004  Inline <example> XML in YAML frontmatter description → move to body
  agt-005  Missing ambiguity-handling section → suggest adding one
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# ── Frontmatter parsing ────────────────────────────────────────────────────────

_FM_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)

# Known model family → recommended versioned alias
_MODEL_VERSIONS: dict[str, str] = {
    "sonnet":  "claude-sonnet-4-5",
    "haiku":   "claude-haiku-4-5",
    "opus":    "claude-opus-4-5",
    "claude":  "claude-sonnet-4-5",
    "gpt-4":   "gpt-4o",
    "gpt4":    "gpt-4o",
    "gpt-3.5": "gpt-3.5-turbo",
}

# Trigger phrases for agt-001 (case-insensitive, word-boundary anchored)
_NEGATIVE_TRIGGERS = [
    r"\bnever\b",
    r"\bdo not\b",
    r"\bdon'?t\b",
    r"\bavoid\b",
    r"\bdo not\b",
    r"\bnot allowed\b",
    r"\bprohibited\b",
    r"\bforbidden\b",
]
_NEGATIVE_RE = re.compile("|".join(_NEGATIVE_TRIGGERS), re.IGNORECASE)

# Phrases that indicate an ambiguity/clarification section already exists
_CLARIFICATION_SIGNALS = [
    "clarification",
    "when to ask",
    "ask for",
    "ambiguous",
    "if unclear",
    "when unclear",
]


@dataclass
class Issue:
    rule_id: str
    severity: str          # "error" | "warn" | "info"
    section: str           # where in the file the issue was found
    before: str            # the problematic text (line or field value)
    after: str             # the suggested replacement
    explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReviewResult:
    file: str
    file_type: str          # "agent" | "skill" | "markdown"
    issues: list[Issue] = field(default_factory=list)
    applied: bool = False

    def to_dict(self) -> dict:
        return {
            "file":      self.file,
            "file_type": self.file_type,
            "issues":    [i.to_dict() for i in self.issues],
            "applied":   self.applied,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """
    Return (frontmatter_dict, body) where frontmatter_dict is a simple
    key→value mapping (no nested YAML) and body is everything after the
    closing `---`.  If there is no frontmatter, returns ({}, text).
    """
    m = _FM_RE.match(text)
    if not m:
        return {}, text

    fm_raw = m.group(1)
    body   = text[m.end():]
    fm: dict[str, str] = {}
    for line in fm_raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm, body


def _detect_file_type(fm: dict[str, str]) -> str:
    if not fm:
        return "markdown"
    keys = {k.lower() for k in fm}
    if "name" in keys and ("description" in keys or "tools" in keys):
        return "skill" if "tools" in keys else "agent"
    return "markdown"


def _body_sections(body: str) -> dict[str, str]:
    """
    Split a markdown body into named sections keyed by heading text.
    The pseudo-section "_preamble" holds any text before the first heading.
    """
    sections: dict[str, str] = {}
    current = "_preamble"
    buf: list[str] = []
    for line in body.splitlines(keepends=True):
        heading = re.match(r"^#{1,3}\s+(.+)", line)
        if heading:
            sections[current] = "".join(buf)
            current = heading.group(1).strip()
            buf = [line]
        else:
            buf.append(line)
    sections[current] = "".join(buf)
    return sections


_AGT001_PLACEHOLDER = "[LLM rewrite needed — Prism will generate this]"


# ── Rule implementations ───────────────────────────────────────────────────────

def _check_agt001(body: str, sections: dict[str, str]) -> list[Issue]:
    """agt-001: Negative instruction — flags for LLM-assisted positive rewrite."""
    issues: list[Issue] = []
    for sec_name, sec_text in sections.items():
        for line in sec_text.splitlines():
            if not line.strip() or line.strip().startswith("#"):
                continue
            if _NEGATIVE_RE.search(line):
                issues.append(Issue(
                    rule_id="agt-001",
                    severity="warn",
                    section=sec_name,
                    before=line.strip(),
                    after=_AGT001_PLACEHOLDER,
                    explanation=(
                        "Negative instructions increase model error rates. "
                        "Rewrite as a positive constraint so the model "
                        "knows what to do, not what to avoid. "
                        "Run `/prism improve <file>` to generate the rewrite."
                    ),
                ))
    return issues


def _check_agt002(body: str, sections: dict[str, str]) -> list[Issue]:
    """agt-002: Duplicate instruction across sections."""
    issues: list[Issue] = []
    # Collect (normalised_line → list of (section, original_line))
    seen: dict[str, list[tuple[str, str]]] = {}
    for sec_name, sec_text in sections.items():
        for line in sec_text.splitlines():
            stripped = line.strip().lstrip("-*0123456789. ")
            if len(stripped) < 20:
                continue
            key = re.sub(r"\s+", " ", stripped.lower())
            seen.setdefault(key, []).append((sec_name, line.strip()))

    reported: set[str] = set()
    for key, occurrences in seen.items():
        if len(occurrences) > 1 and key not in reported:
            reported.add(key)
            first_sec, first_line = occurrences[0]
            for dup_sec, dup_line in occurrences[1:]:
                issues.append(Issue(
                    rule_id="agt-002",
                    severity="info",
                    section=dup_sec,
                    before=dup_line,
                    after="[remove — already stated in the '{}' section]".format(first_sec),
                    explanation=(
                        "Duplicate instructions add token overhead and can cause "
                        "inconsistency if one copy is updated later. "
                        "Keep the instruction in '{}' only.".format(first_sec)
                    ),
                ))
    return issues


def _check_agt003(fm: dict[str, str]) -> list[Issue]:
    """agt-003: Unversioned model pin."""
    issues: list[Issue] = []
    model_val = fm.get("model", "").strip()
    if not model_val:
        return issues
    key = model_val.lower()
    if key in _MODEL_VERSIONS:
        issues.append(Issue(
            rule_id="agt-003",
            severity="warn",
            section="frontmatter",
            before=f"model: {model_val}",
            after=f"model: {_MODEL_VERSIONS[key]}",
            explanation=(
                "Model family names resolve to the latest available version at "
                "runtime, which changes without notice. Pinning to an explicit "
                "version string (e.g. 'claude-sonnet-4-5') ensures reproducible "
                "behaviour across deployments."
            ),
        ))
    return issues


# Words that commonly appear as orphaned labels when <example> blocks are stripped.
_TRAILING_LABEL_RE = re.compile(
    r"[\s,;.]*\b(examples?|e\.g\.?|for example|see|usage|note|such as)\s*:?\s*$",
    re.IGNORECASE,
)


def _clean_description(desc: str) -> str:
    """
    Strip <example> blocks and any orphaned introductory label that preceded them.

    For example:
        "Use this agent when needed. Examples: <example>…</example>"
        → "Use this agent when needed."
    """
    short = re.sub(r"\s*<example[\s>].*", "", desc, flags=re.DOTALL).strip()
    # Remove trailing orphaned labels that were introducing the removed examples
    short = _TRAILING_LABEL_RE.sub("", short).strip()
    if not short:
        short = "Use this agent when you need to implement specific functionality."
    return short


def _check_agt004(fm: dict[str, str]) -> list[Issue]:
    """agt-004: Inline <example> XML in YAML frontmatter description."""
    issues: list[Issue] = []
    desc = fm.get("description", "")
    if "<example>" in desc or "<example " in desc:
        short_desc = _clean_description(desc)
        issues.append(Issue(
            rule_id="agt-004",
            severity="warn",
            section="frontmatter",
            before=f"description: {desc[:120]}{'...' if len(desc) > 120 else ''}",
            after=(
                f"description: {short_desc}\n"
                "(Move <example> blocks to a '## Examples' section in the body)"
            ),
            explanation=(
                "Inline XML inside a YAML string field is fragile: YAML parsers "
                "may misinterpret angle brackets, and the description becomes "
                "unreadable. Move examples to a '## Examples' section in the "
                "markdown body where they can be formatted clearly."
            ),
        ))
    return issues


# Common patterns indicating a truncated or dangling description value.
_DANGLING_DESC_RE = re.compile(
    r"([\s,;.]*\b(examples?|e\.g\.?|for example|see|usage|note|such as)\s*:?\s*"
    r"|[^.!?]\s*[:]\s*)$",
    re.IGNORECASE,
)


def _check_agt006(fm: dict[str, str]) -> list[Issue]:
    """agt-006: Truncated or dangling frontmatter description."""
    issues: list[Issue] = []
    desc = fm.get("description", "").strip()
    if not desc:
        return issues
    if _DANGLING_DESC_RE.search(desc):
        issues.append(Issue(
            rule_id="agt-006",
            severity="warn",
            section="frontmatter",
            before=f"description: …{desc[-60:]}",
            after=(
                "description: <complete sentence ending in punctuation, "
                "no trailing colon or orphaned label>"
            ),
            explanation=(
                "The description field ends with a colon or an orphaned label "
                "word (e.g. 'Examples:', 'See:'), which usually means an "
                "<example> block or continuation text was removed and the "
                "introductory phrase was left behind. Rewrite as a complete "
                "sentence that stands on its own."
            ),
        ))
    return issues


def _check_agt005(body: str) -> list[Issue]:
    """agt-005: Missing ambiguity/clarification-handling section."""
    issues: list[Issue] = []
    body_lower = body.lower()
    if not any(signal in body_lower for signal in _CLARIFICATION_SIGNALS):
        issues.append(Issue(
            rule_id="agt-005",
            severity="info",
            section="body",
            before="(no clarification-handling section found)",
            after=(
                "## When clarification is needed\n"
                "- Ask specific questions about requirements, constraints, or expected behaviour.\n"
                "- Confirm scope boundaries before beginning long-running tasks.\n"
                "- Verify integration points with existing systems when not documented.\n"
                "- Clarify ambiguous acceptance criteria before writing tests."
            ),
            explanation=(
                "Agents without explicit guidance on when to ask for clarification "
                "either over-ask (annoying) or under-ask (produce wrong output). "
                "A short section that defines the decision boundary reduces both failure modes."
            ),
        ))
    return issues


# ── Apply fixes ───────────────────────────────────────────────────────────────

def _apply_fixes(
    text: str,
    issues: list[Issue],
    rewrite_map: dict[str, str] | None = None,
) -> str:
    """
    Rewrite `text` by applying each issue's `before` → `after` replacement.

    Handles the special cases:
    - agt-003/agt-004: frontmatter key replacements (line-level)
    - agt-002: line removals (replace with empty string and strip blank lines later)
    - agt-005: append a new section to the body
    - agt-001: line-level LLM rewrites, applied only when `rewrite_map` provides
               a mapping for issue.before.  Without the map the original line is
               preserved so that broken placeholder text never lands in the file.
    """
    rmap = rewrite_map or {}
    lines = text.splitlines(keepends=True)
    new_lines: list[str] = []
    agt005_additions: list[str] = []
    # Track lines already emitted so agt-002 can remove later occurrences only
    lines_kept: set[str] = set()

    for issue in issues:
        if issue.rule_id == "agt-005":
            agt005_additions.append("\n" + issue.after + "\n")

    for line in lines:
        stripped = line.rstrip("\n").rstrip("\r")
        normalized = stripped.strip()
        replaced = False

        for issue in issues:
            if issue.rule_id == "agt-005":
                continue

            if issue.rule_id in ("agt-003", "agt-004"):
                # Frontmatter key replacement: match the key prefix
                key = issue.before.split(":")[0].strip()
                if re.match(rf"^\s*{re.escape(key)}\s*:", stripped):
                    after_val = issue.after.split("\n")[0]
                    new_lines.append(after_val + "\n")
                    replaced = True
                    break
            elif issue.rule_id == "agt-002":
                if normalized == issue.before.strip() and normalized in lines_kept:
                    # First occurrence is already kept; this is the duplicate → remove
                    replaced = True
                    break
            elif issue.rule_id == "agt-001":
                if stripped.strip() == issue.before.strip():
                    llm_rewrite = rmap.get(issue.before.strip())
                    if llm_rewrite:
                        indent = len(stripped) - len(stripped.lstrip())
                        new_lines.append(" " * indent + llm_rewrite.lstrip() + "\n")
                        replaced = True
                    # Without a rewrite, fall through and keep the original line
                    break

        if not replaced:
            new_lines.append(line if line.endswith("\n") else line + "\n")
            lines_kept.add(normalized)

    # Strip runs of 3+ blank lines caused by agt-002 removals
    result = "".join(new_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)

    # Append agt-005 additions at the end
    if agt005_additions:
        result = result.rstrip("\n") + "\n" + "".join(agt005_additions)

    return result


# ── Public API ─────────────────────────────────────────────────────────────────

def review(file_path: str | Path) -> ReviewResult:
    """Analyse the file and return a ReviewResult (does not write anything)."""
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")

    fm, body = _parse_frontmatter(text)
    file_type = _detect_file_type(fm)
    sections  = _body_sections(body)

    issues: list[Issue] = []
    issues.extend(_check_agt001(body, sections))
    issues.extend(_check_agt002(body, sections))
    issues.extend(_check_agt003(fm))
    issues.extend(_check_agt004(fm))
    issues.extend(_check_agt005(body))
    issues.extend(_check_agt006(fm))

    return ReviewResult(file=str(path), file_type=file_type, issues=issues)


def apply_fixes(
    file_path: str | Path,
    result: ReviewResult,
    rewrite_map: dict[str, str] | None = None,
) -> ReviewResult:
    """
    Rewrite the file in-place with all issues fixed.

    `rewrite_map` maps the original (before) text of each agt-001 issue to the
    LLM-generated positive rewrite.  agt-001 lines without a map entry are left
    unchanged to avoid writing broken placeholder text.
    """
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    fixed = _apply_fixes(text, result.issues, rewrite_map=rewrite_map)
    path.write_text(fixed, encoding="utf-8")
    return ReviewResult(
        file=result.file,
        file_type=result.file_type,
        issues=result.issues,
        applied=True,
    )


# ── Human-readable output ─────────────────────────────────────────────────────

def _out(text: str) -> None:
    """Print to stdout with a UTF-8 fallback for narrow console encodings."""
    try:
        print(text)
    except UnicodeEncodeError:  # pragma: no cover — platform-specific (Windows cp1252)
        print(text.encode("ascii", errors="replace").decode("ascii"))

def _print_table(result: ReviewResult) -> None:
    if not result.issues:
        _out(f"[OK] No issues found in {result.file}")
        return

    sev_icon = {"error": "[E]", "warn": "[W]", "info": "[I]"}
    _out(f"\nPrism Agent Review -- {result.file}  [{result.file_type}]")
    _out(f"{len(result.issues)} issue(s) found\n")
    _out(f"{'#':<3}  {'Rule':<8}  {'Sev':<5}  {'Section':<30}  Issue")
    _out("-" * 90)
    for i, issue in enumerate(result.issues, 1):
        icon = sev_icon.get(issue.severity, "?")
        sec  = issue.section[:29]
        _out(f"{i:<3}  {issue.rule_id:<8}  {icon:<5}  {sec:<30}  {issue.before[:50]}")

    _out("")
    for i, issue in enumerate(result.issues, 1):
        _out(f"Issue {i} -- {issue.rule_id} [{issue.severity}] in '{issue.section}'")
        _out(f"  Before : {issue.before}")
        _out(f"  After  : {issue.after}")
        _out(f"  Why    : {issue.explanation}")
        _out("")

    if result.applied:
        _out(f"[OK] All {len(result.issues)} fix(es) applied to {result.file}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prism agent/skill file reviewer.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--file", required=True, help="Path to the agent/skill markdown file")
    parser.add_argument("--json",  action="store_true", help="Output results as JSON")
    parser.add_argument("--apply", action="store_true", help="Rewrite the file with all fixes applied")
    parser.add_argument(
        "--rewrite-map",
        default="{}",
        metavar="JSON",
        help=(
            'JSON object mapping agt-001 "before" text to LLM-generated positive rewrites. '
            'Example: --rewrite-map \'{"- Never add tests unless requested": '
            '"- Add tests only when the project manager explicitly requests them."}\''
        ),
    )
    args = parser.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        rewrite_map: dict[str, str] = json.loads(args.rewrite_map)
    except json.JSONDecodeError as exc:
        print(f"Error: --rewrite-map is not valid JSON: {exc}", file=sys.stderr)
        sys.exit(1)

    result = review(path)

    if args.apply and result.issues:
        result = apply_fixes(path, result, rewrite_map=rewrite_map or None)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_table(result)

    sys.exit(0)


if __name__ == "__main__":  # pragma: no cover
    main()
