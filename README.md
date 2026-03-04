# Prism — Prompt Engineering for AI Developers

> **Treat your prompts like code.** Vague, bundled, or data-leaking prompts waste tokens, produce off-target responses, and risk exposing sensitive data. Prism catches them before they leave your editor — no new tools, no subscription, no context switch. Lives inside Cursor, Claude Code, or GitHub Copilot.

[![Tests](https://github.com/CraigHutchinson/Prism/actions/workflows/test.yml/badge.svg)](https://github.com/CraigHutchinson/Prism/actions/workflows/test.yml)
[![Coverage](https://codecov.io/gh/CraigHutchinson/Prism/graph/badge.svg)](https://codecov.io/gh/CraigHutchinson/Prism)
[![Security Coverage](https://img.shields.io/badge/security%20coverage-100%25-brightgreen)](https://github.com/CraigHutchinson/Prism/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/python-3.9%20|%203.10%20|%203.11%20|%203.12-blue)](https://github.com/CraigHutchinson/Prism/actions/workflows/test.yml)

---

## Quick Start (2 commands)

```bash
# 1. Clone
git clone https://github.com/CraigHutchinson/Prism ~/.prism-skill

# 2. Configure — installs deps, checks for updates, sets up all platforms, self-checks
python ~/.prism-skill/configure.py
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/CraigHutchinson/Prism "$env:USERPROFILE\.prism-skill"
python "$env:USERPROFILE\.prism-skill\configure.py"
```

Then run your first Prism command: `/prism hello`

> Tip: Pass a platform name to install selectively: `configure.py cursor`, `configure.py claude`, `configure.py copilot`.

### Install via AI assistant (one sentence)

Already inside Cursor, Claude Code, or Copilot Chat? Skip the terminal entirely — just tell your AI:

> Install agent skill from https://github.com/CraigHutchinson/Prism

The assistant fetches `llms.txt` from the repo, detects your platform, and runs the two commands above for you. Works in any session that can execute shell commands.

---

## Before / After

Type this into any AI chat — no project setup needed:

```
write a python function that checks if a string is a valid email also add
some unit tests and maybe handle edge cases like empty strings
```

After `/prism improve` — Markdown (default, works on all models):

```markdown
## Task
1. Write a Python function `is_valid_email(email: str) -> bool` using regex only (no third-party libs).
2. Write unit tests covering: valid address, empty string, missing `@`, multiple `@`, no domain extension.

## Constraints
- Regex only — no `email-validator` or similar packages.
- Return `False` for invalid input; do not raise.
```
```
### Why Log
- [REFRACTION] Format: markdown (portable default)                      [rule: ref-016]
- [REFRACTION] Filler "write a python function that" → typed signature  [rule: ref-002]
- [REFRACTION] Bundled task split into two numbered steps               [rule: ref-007]
- [REFRACTION] "maybe edge cases like…" → 5 specific test cases named  [rule: ref-001]
- [REFRACTION] ## Constraints added (no-library + error behaviour)      [rule: ref-001]
- [SANITIZATION]  No PII or injection patterns found
- [INTROSPECTION] Score: 18 -> 91 / 100

### Prism Overhead This Run: ~1,100t
```

On Cursor or Claude Code, Prism auto-upgrades to XML (`ref-017`):
```xml
<task>
1. Write a Python function `is_valid_email(email: str) -> bool` using regex only.
2. Write unit tests covering: valid address, empty string, missing `@`, multiple `@`, no domain extension.
</task>
<constraints>Regex only — no third-party packages. Return False for invalid input, do not raise.</constraints>
```

> Try it yourself: paste the "before" prompt into your AI chat, then run `/prism improve` on it. The output above is what Prism produces.

---

## The Three Pillars

| Pillar | What it does | Cost |
|--------|-------------|------|
| **Refraction** | Restructures prompts: XML tags, CoT triggers, output constraints, task decomposition | Fast model × 3 |
| **Sanitization** | Scans for personal data, API keys, and prompt hijacking attempts **before** any model call (PII detection — pure regex) | Zero (script) |
| **Introspection** | Scores 0–100 across 5 dimensions and learns your personal writing patterns over time | Fast model |

All analysis runs on the cheapest platform-native model within your security boundary (GPT-4.1, claude-haiku-4-5, or Cursor's built-in fast model). No data leaves your platform.

---

## Installation

**Prerequisites:** Python 3.9+.

Clone once, configure for each platform with a single command.

### Cursor

```bash
git clone https://github.com/CraigHutchinson/Prism ~/.prism-skill
python ~/.prism-skill/configure.py cursor
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/CraigHutchinson/Prism "$env:USERPROFILE\.prism-skill"
python "$env:USERPROFILE\.prism-skill\configure.py" cursor
```

Restart Cursor after running — `/prism` appears in the skill menu.

### Claude Code

Run from inside your project directory:

```bash
git clone https://github.com/CraigHutchinson/Prism ~/.prism-skill
python ~/.prism-skill/configure.py claude
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/CraigHutchinson/Prism "$env:USERPROFILE\.prism-skill"
python "$env:USERPROFILE\.prism-skill\configure.py" claude
```

`/prism` is now available as a slash command in Claude Code.

### GitHub Copilot

Run from inside your project directory:

```bash
git clone https://github.com/CraigHutchinson/Prism ~/.prism-skill
python ~/.prism-skill/configure.py copilot
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/CraigHutchinson/Prism "$env:USERPROFILE\.prism-skill"
python "$env:USERPROFILE\.prism-skill\configure.py" copilot
```

`@prism` appears in Copilot Chat's agent selector.

### All platforms at once (default)

No argument is needed — running `configure.py` with no platform installs everything:

```bash
python ~/.prism-skill/configure.py
# equivalent to:
python ~/.prism-skill/configure.py all
```

### Check what is installed

```bash
python ~/.prism-skill/configure.py status
```

### configure.py reference

| Command | What it does |
|---------|-------------|
| `configure.py` | **Install all platforms** (default — good for agnostic repos) |
| `configure.py cursor` | Install Prism skill into Cursor only (global, symlink on macOS/Linux) |
| `configure.py claude` | Copy Prism sub-skills into the current project's `.claude/skills/` only |
| `configure.py copilot` | Copy Prism agent files into the current project's `.github/` only |
| `configure.py all` | Explicit alias for the default — install all three platforms |
| `configure.py status` | Show what is installed and where |
| `configure.py remove cursor\|claude\|copilot` | Uninstall a platform |
| `--force` | Overwrite already-installed files (update) |
| `--dry-run` | Show what would happen without making changes |
| `--skip-deps` | Skip the `pip install` step (useful in CI or when deps are pre-installed) |

---

## Verify Your Installation

`configure.py` runs a health check automatically at the end of every install. You can also trigger it manually at any time:

```bash
python ~/.prism-skill/scripts/verify_install.py
```

**Windows (PowerShell):**
```powershell
python "$env:USERPROFILE\.prism-skill\scripts\verify_install.py"
```

A healthy install prints:
```
Prism Install Verifier
======================
  OK Python 3.11 (>= 3.9 required)
  OK jsonschema 4.26.0 installed
  OK All 10 core scripts present
  OK Hook script present (hooks/prism_preparser.py)
  OK All 3 data files present
  OK JSON schemas valid (4 schemas, 35 rules)
  OK pii_scan functional (clean prompt -> safe)
  OK stage2_gate functional (specific prompt -> ok=True)
  OK hook_installer --action status: ok
  OK .prism/ directory writeable

All 10 checks passed. Prism is ready.
Run: /prism hello   for an interactive introduction and live demo
```

If any check fails, a one-line fix hint is printed alongside the failure.

---

## Commands

### Getting started

| Command | What it does | Model cost |
|---------|-------------|-----------|
| `/prism hello` | Interactive intro + live Stage 1/Stage 2 demo on a sample prompt | None |

### On-demand analysis

| Command | What it does | Model cost |
|---------|-------------|-----------|
| `/prism improve "..."` | Full pipeline: sanitize → score → refract → rewrite with Why Log | Fast × 3 + Capable × 1 |
| `/prism format` | Show active structural format (markdown/xml/prefixed) for this platform | None |
| `/prism sanitize "..."` | Privacy & security scan — flags personal data, API keys, prompt hijacking (PII check) | None (script) |
| `/prism score "..."` | 5-dimension Agentic Readiness Score (0–100) + tips | Fast model |
| `/prism explain "..."` | Diagnose a prompt without rewriting it | Fast model |

### Always-on hooks

| Command | What it does | Model cost |
|---------|-------------|-----------|
| `/prism hook on` | Enable pre-flight analysis for every prompt you submit | None (Stage 1 is script-only) |
| `/prism hook off` | Disable hooks | — |
| `/prism hook status` | Show hook state and active stages | — |

### Personal patterns

| Command | What it does | Model cost |
|---------|-------------|-----------|
| `/prism patterns` | Analyse your writing habits, suggest terse rewrites | Fast model |
| `/prism patterns --apply` | Write a persistent style rule to CLAUDE.md / skills | None |
| `/prism patterns --reset` | Clear the prompt log | None |

### Usage & configuration

| Command | What it does | Model cost |
|---------|-------------|-----------|
| `/prism usage` | Show 30-session overhead history | None |
| `/prism usage --optimize` | Get suggestions to reduce overhead | Fast model |
| `/prism configure key=value` | Toggle features in prism.config.json | None |

---

## Structural Formats

Prism selects the optimal structural syntax based on the detected platform. The default is **Markdown headers** — portable across all models. Run `/prism format` to see which format is active.

| Format | Command | Best for | Auto-selected when |
|--------|---------|----------|--------------------|
| **Markdown** (default) | `## Task` / `## Context` | All models — GPT-4, Gemini, Claude | Platform unknown or Copilot |
| **XML** | `<task>` / `<context>` | Claude 3.5+ only | Cursor or Claude Code detected |
| **Prefixed** | `TASK:` / `CONTEXT:` | Constrained contexts, older models | Explicit `--format prefixed` only |

Override at any time: `/prism improve "..." --format xml`

---

## Output Format

Every `/prism improve` response follows this structure:

```
### Prism-Optimized Prompt
<system>...</system>
<context>...</context>
<task>...</task>
<constraints>...</constraints>

### Why Log
- [REFRACTION]    Added XML structure                   [rule: ref-001, source: official]
- [SANITIZATION]  No issues found ✓
- [INTROSPECTION] CoT trigger injected                  [rule: int-010]

### Agentic Readiness Score: 87/100
- Structure:           9/10
- Specificity:         8/10
- Security:           10/10
- Cache-Friendliness:  7/10
- Model Alignment:     8/10

### Prism Overhead This Run: ~1,340t
```

---

## Disabling & Uninstalling

**Disable hooks only (keep skill):**
```
/prism hook off
```

**Reduce token overhead without uninstalling:**
```
/prism configure hook.stage2_lm_gate=false             # Save ~200t/prompt
/prism configure hook.session_context_injection=false  # Save ~50t/session
/prism configure hook.log_prompts=false                # Stop logging prompts
```

**Uninstall completely:**

```bash
python ~/.prism-skill/configure.py remove cursor
python ~/.prism-skill/configure.py remove claude
python ~/.prism-skill/configure.py remove copilot
```

For Copilot, also remove hooks first:
```bash
python ~/.prism-skill/scripts/hook_installer.py --action off
```

Runtime data (local only, never committed):
```bash
rm -rf .prism/
```

---

## Architecture

```
Prism/
├── .cursor/skills/prism/
│   ├── SKILL.md                 ← Command dispatch + routing logic
│   ├── refraction-playbook.md   ← XML tags, CoT triggers, caching strategy
│   ├── sanitization-rules.md    ← PII types, injection patterns, severity levels
│   ├── introspection-scoring.md ← ARS rubric, 5 dimensions
│   └── examples.md              ← Before/after walkthroughs
│
├── .claude/skills/
│   ├── prism/SKILL.md           ← Claude Code main skill
│   ├── prism-sanitize/SKILL.md  ← Parallel subagent A (claude-haiku-4-5)
│   ├── prism-score/SKILL.md     ← Parallel subagent B (claude-haiku-4-5)
│   └── prism-refract/SKILL.md   ← Parallel subagent C (claude-haiku-4-5)
│
├── .github/agents/prism.agent.md  ← Copilot agent definition
│
├── hooks/
│   ├── prism_preparser.py           ← Hook: sessionStart, userPromptSubmit, stop
│   ├── claude_settings_template.json
│   └── prism_hooks_template.json
│
├── scripts/
│   ├── format_output.py       ← /prism format — selects markdown/xml/prefixed (no model)
│   ├── hello.py               ← /prism hello intro + live demo (no model)
│   ├── pii_scan.py            ← Regex PII + injection scanner (no model)
│   ├── stage2_gate.py         ← Stage 2 quality gate — heuristic (no model)
│   ├── hook_installer.py      ← /prism hook on|off|status (idempotent)
│   ├── kb_query.py            ← Knowledge base filter + cache
│   ├── overhead_calc.py       ← Token estimator (no model)
│   ├── pattern_analysis.py    ← Prompt log analyser
│   ├── platform_model.py      ← Platform detection + model router
│   ├── usage_log.py           ← Session overhead log management
│   ├── verify_install.py      ← Post-install health checker (10 checks)
│   ├── verbosity_patterns.json
│   ├── prism_config_default.json
│   └── schemas/               ← JSON output schemas for structured calls
│
├── knowledge-base/
│   ├── rules.json             ← 35 seeded prompt engineering rules
│   └── sources.md             ← Bibliography + prior art
│
└── tests/                     ← pytest suite — 105 tests, 100% security coverage
```

---

## Model Cost Summary

Prism is designed to pay for itself. All analysis subagents use the cheapest model available within your platform's security boundary.

| Platform | Analysis subagents | Synthesis | Hook Stage 2 |
|----------|--------------------|-----------|-------------|
| Copilot paid | GPT-4.1 | Capable | Tool budget |
| Copilot free | Goldeneye | Capable | Tool budget |
| Claude Code | claude-haiku-4-5 | Capable | Tool budget |
| Cursor | Built-in fast | Capable | Tool budget |

Cloud free APIs (Groq, Gemini, OpenRouter) are explicitly deferred from v1 — they require opt-in and are flagged as leaving the platform security boundary.

---

## Updating the Knowledge Base

The knowledge base lives in `knowledge-base/rules.json`. To add a rule:

1. Read `knowledge-base/sources.md` to check existing sources.
2. Add a new entry to `rules.json` (copy an existing entry as a template).
3. Set `apply_cost` to `script`, `fast`, or `capable`.
4. Set `model_applies` to the minimum model version where the rule applies (e.g. `["claude-3.5+"]`).

Automated URL-based rule extraction is planned for v2 (`/prism kb add`).

---

## Prior Art

Prism is not the first prompt optimization tool — but it is the first to combine IDE-native integration, pre-flight PII scanning, personal pattern learning, model-version-aware rules, and self-monitored token overhead in a single zero-subscription package.

See `knowledge-base/sources.md` for the full competitive landscape.

---

## Contributing

1. Add new rules to `knowledge-base/rules.json` and a source entry to `knowledge-base/sources.md`.
2. Write tests first (TDD — red before green).
3. Run `python scripts/ci_check.py` before opening a PR — it mirrors every CI step locally.
4. Security-critical paths (`pii_scan.py`, `prism_preparser.py`) require 100% test coverage.

---

## License

MIT
