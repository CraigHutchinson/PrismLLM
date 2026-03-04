"""
pii_scan.py
-----------
Regex-based PII and prompt injection scanner.

Outputs a JSON report to stdout. Used by:
  - hooks/prism_preparser.py (Stage 1 hook, must run < 50ms)
  - scripts/pattern_analysis.py (pre-log scrub)
  - SKILL.md dispatch (/prism sanitize)

No model required. All detection is deterministic regex.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict, field
from typing import List, Optional

# ── PII patterns ──────────────────────────────────────────────────────────────

PII_PATTERNS: list[tuple[str, str, str, re.Pattern]] = [
    # (entity_type, replacement_token, severity, pattern)
    ("EMAIL",        "[EMAIL_REDACTED]",        "block",
     re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),

    ("PHONE",        "[PHONE_REDACTED]",         "block",
     re.compile(r"""(?x)
         (?:\+?\d{1,3}[\s\-.])?    # optional country code
         (?:\(?\d{2,4}\)?[\s\-.]?) # optional area code
         \d{3,4}[\s\-.]            # exchange
         \d{4}                     # number
     """)),

    ("SSN",          "[SSN_REDACTED]",           "block",
     re.compile(r"\b\d{3}[- ]\d{2}[- ]\d{4}\b")),

    ("CREDIT_CARD",  "[CC_REDACTED]",            "block",
     re.compile(r"\b(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|3(?:0[0-5]|[68]\d)\d{11}|6(?:011|5\d{2})\d{12})\b")),

    ("API_KEY_OPENAI",   "[API_KEY_REDACTED]",   "block",
     re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),

    ("API_KEY_ANTHROPIC","[API_KEY_REDACTED]",   "block",
     re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}\b")),

    ("API_KEY_GITHUB",   "[API_KEY_REDACTED]",   "block",
     re.compile(r"\bghp_[A-Za-z0-9]{20,}\b|\bgho_[A-Za-z0-9]{20,}\b|\bghs_[A-Za-z0-9]{20,}\b")),

    ("API_KEY_AWS",      "[API_KEY_REDACTED]",   "block",
     re.compile(r"\b(AKIA|ASIA|AROA|AIDA)[A-Z0-9]{16}\b")),

    ("SECRET_KEY",   "[SECRET_REDACTED]",        "block",
     re.compile(r"""(?xi)
         (?:password|passwd|secret|token|auth|credential|api[_\-]?key)\s*
         [:=\s"']+
         ([A-Za-z0-9!@#$%^&*()\-_+=]{8,})
     """)),

    ("BEARER_TOKEN", "[BEARER_REDACTED]",        "block",
     re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b", re.IGNORECASE)),

    ("JWT",          "[JWT_REDACTED]",            "block",
     re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b")),

    ("IP_ADDRESS",   "[IP_REDACTED]",             "warn",
     re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b")),
]

# ── Injection patterns ─────────────────────────────────────────────────────────

INJECTION_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    # (category, description, pattern)
    ("direct_override",
     "Attempts to override or ignore previous instructions",
     re.compile(r"""(?xi)
         ignore\s+(all\s+)?previous\s+(instructions?|prompts?|context)
         | forget\s+(everything|all)\s+(above|before|prior)
         | disregard\s+(the\s+)?(previous|above|prior|all)
         | override\s+(the\s+)?(previous|system|instructions?)
         | new\s+instructions?\s*:
     """)),

    ("role_hijack",
     "Attempts to hijack the AI's role or persona",
     re.compile(r"""(?xi)
         you\s+are\s+now\s+(a|an|the)\s+\w+
         | act\s+as\s+(a|an|the)\s+\w+\s+with\s+no\s+(restrictions?|limits?)
         | pretend\s+(you\s+are|to\s+be)\s+(a|an|the)\s+\w+\s+without\s+
         | your\s+new\s+(persona|role|identity)\s+is
         | from\s+now\s+on\s+you\s+(are|will\s+be|must)
     """)),

    ("data_exfiltration",
     "Attempts to extract system prompt or internal context",
     re.compile(r"""(?xi)
         repeat\s+(everything|all|the\s+text|your\s+instructions?|your\s+prompt)\s+above
         | (print|output|show|reveal|display|tell\s+me)\s+(your\s+)?(system\s+prompt|instructions?|context|full\s+prompt)
         | what\s+(are|were)\s+your\s+(exact\s+)?(instructions?|system\s+prompt)
         | translate\s+(the\s+above|everything\s+above)\s+to
     """)),

    ("jailbreak",
     "Common jailbreak bypass attempts",
     re.compile(r"""(?xi)
         (?:DAN|STAN|JAILBREAK|DEVELOPER\s+MODE|SUDO\s+MODE)\s*[:]\s*\w+
         | do\s+anything\s+now
         | enable\s+(developer|jailbreak|admin)\s+mode
         | you\s+have\s+no\s+restrictions?\s+anymore
         | bypass\s+(your\s+)?(safety|content)\s+(filters?|guidelines?|restrictions?)
     """)),

    ("indirect_injection",
     "Embedded instructions in user-supplied content (indirect injection)",
     re.compile(r"""(?xi)
         \[hidden\s+instructions?\]
         | <\s*hidden\s*>\s*.+?\s*</\s*hidden\s*>
         | <!--\s*(instructions?|prompt|note):\s*.+?-->
         | \{\{.*?(instructions?|inject|eval).*?\}\}
     """, re.DOTALL)),
]

# ── Filler/verbosity patterns (for prompt-log efficiency scoring) ─────────────

FILLER_PATTERN = re.compile(
    r"""(?xi)
    \b(
        we\s+shall | let\s+us | we\s+will | we\s+need\s+to | we\s+should
        | could\s+you\s+please | would\s+you\s+be\s+able\s+to
        | I\s+would\s+like\s+you\s+to | I\s+want\s+you\s+to
        | your\s+task\s+is\s+to | your\s+job\s+is\s+to | I\s+need\s+you\s+to
        | in\s+this\s+context | it\s+is\s+worth\s+noting\s+that
        | it\s+should\s+be\s+noted\s+that | as\s+previously\s+mentioned
        | as\s+I\s+mentioned | as\s+mentioned\s+above
        | to\s+be\s+honest | basically | essentially
        | if\s+possible | if\s+you\s+can | perhaps | maybe
        | sort\s+of | kind\s+of | a\s+bit | somewhat
        | and\s+also | while\s+you.re\s+at\s+it | while\s+you\s+are\s+at\s+it
        | additionally | furthermore
    )\b
    """,
    re.IGNORECASE,
)


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class ScanResult:
    pii_found:            List[str] = field(default_factory=list)
    pii_positions:        List[dict] = field(default_factory=list)
    injection_risk:       bool = False
    injection_phrases:    List[str] = field(default_factory=list)
    injection_categories: List[str] = field(default_factory=list)
    ambiguous_authority:  bool = False
    redacted_prompt:      str = ""
    issues:               List[str] = field(default_factory=list)
    safe:                 bool = True
    rules_triggered:      List[str] = field(default_factory=list)
    filler_count:         int = 0
    tokens_est:           int = 0
    efficiency_ratio:     float = 1.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("pii_positions", None)
        return d


# ── Core scan function ─────────────────────────────────────────────────────────

def scan(text: str) -> ScanResult:
    """
    Scan `text` for PII, injection phrases, and verbosity patterns.

    Returns a ScanResult with all findings. The `safe` field is False when
    any BLOCK-severity issue is found (PII or injection).
    """
    result = ScanResult()
    result.tokens_est = max(1, len(text) // 4)
    working = text

    # ── PII detection & redaction ────────────────────────────────────────────
    rule_map = {
        "EMAIL":          "san-001",
        "PHONE":          "san-003",
        "SSN":            "san-004",
        "CREDIT_CARD":    "san-001",
        "API_KEY_OPENAI": "san-002",
        "API_KEY_ANTHROPIC": "san-002",
        "API_KEY_GITHUB": "san-002",
        "API_KEY_AWS":    "san-002",
        "SECRET_KEY":     "san-008",
        "BEARER_TOKEN":   "san-008",
        "JWT":            "san-008",
        "IP_ADDRESS":     "san-001",
    }

    for entity_type, replacement, severity, pattern in PII_PATTERNS:
        matches = list(pattern.finditer(working))
        if matches:
            result.pii_found.append(entity_type)
            rule_id = rule_map.get(entity_type, "san-001")
            if rule_id not in result.rules_triggered:
                result.rules_triggered.append(rule_id)
            if severity == "block":
                result.safe = False
                result.issues.append(
                    f"{entity_type} detected — remove or replace with a placeholder before submitting"
                )
            else:
                result.issues.append(
                    f"{entity_type} detected — consider whether this is intentional"
                )
            working = pattern.sub(replacement, working)

    # ── Injection detection ──────────────────────────────────────────────────
    for category, description, pattern in INJECTION_PATTERNS:
        matches = list(pattern.finditer(text))
        if matches:
            result.injection_risk = True
            result.safe = False
            result.injection_categories.append(category)
            for m in matches:
                phrase = m.group(0)[:80]
                if phrase not in result.injection_phrases:
                    result.injection_phrases.append(phrase)
            if "san-005" not in result.rules_triggered:
                result.rules_triggered.append("san-005")
            result.issues.append(
                f"Injection pattern ({category}): {description}"
            )

    # ── Filler/verbosity counting ────────────────────────────────────────────
    filler_matches = FILLER_PATTERN.findall(text)
    result.filler_count = len(filler_matches)
    filler_tokens = result.filler_count * 2
    result.efficiency_ratio = max(0.0, min(1.0,
        (result.tokens_est - filler_tokens) / max(1, result.tokens_est)
    ))

    result.redacted_prompt = working
    return result


def scrub(text: str) -> str:
    """Return a PII-redacted version of the text (used before logging)."""
    return scan(text).redacted_prompt


# ── CLI interface ──────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Scan a prompt for PII and injection risks."
    )
    parser.add_argument("text", nargs="?", help="Text to scan (or read from stdin)")
    parser.add_argument("--json", action="store_true", dest="json_out",
                        help="Output JSON (default: human-readable)")
    args = parser.parse_args()

    if args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        parser.print_help()
        sys.exit(1)

    result = scan(text)

    if args.json_out:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Safe:            {result.safe}")
        print(f"PII found:       {result.pii_found or 'none'}")
        print(f"Injection risk:  {result.injection_risk}")
        if result.injection_categories:
            print(f"  Categories:    {result.injection_categories}")
        print(f"Filler count:    {result.filler_count}")
        print(f"Efficiency ratio:{result.efficiency_ratio:.2f}")
        print(f"Tokens est:      {result.tokens_est}")
        if result.issues:
            print("\nIssues:")
            for issue in result.issues:
                print(f"  • {issue}")
        if result.redacted_prompt != text:
            print(f"\nRedacted prompt:\n{result.redacted_prompt}")


if __name__ == "__main__":  # pragma: no cover
    main()
