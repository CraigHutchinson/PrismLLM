# Prism — Prompt Engineering for AI Developers

> **Treat your prompts like code.** Vague, bundled, or data-leaking prompts waste tokens, produce off-target responses, and risk exposing sensitive data. Prism catches them before they leave your editor — no new tools, no subscription, no context switch. Lives inside Cursor, Claude Code, or GitHub Copilot.

[![Tests](https://github.com/CraigHutchinson/PrismLLM/actions/workflows/test.yml/badge.svg)](https://github.com/CraigHutchinson/PrismLLM/actions)

---

## Quick Start (5 minutes)

```bash
# 1. Clone
git clone https://github.com/CraigHutchinson/PrismLLM ~/.prism-skill

# 2. Install dependencies
pip install -r ~/.prism-skill/requirements.txt

# 3. Link the skill (Cursor example — see platform steps below)
ln -s ~/.prism-skill/.cursor/skills/prism ~/.cursor/skills/prism  # macOS/Linux

# 4. Verify the install is healthy
python ~/.prism-skill/scripts/verify_install.py

# 5. Run your first Prism command
/prism hello
```

---

## Before / After

Without Prism:
```
we shall add a login page and also write the tests
```

After `/prism improve-prompt` — Markdown (default, works on all models):
```markdown
## Context
Auth module, existing session-management layer.

## Task
1. Add a login page: form fields, validation, POST to /auth/login.
2. Write unit tests for the login endpoint (happy path + 3 error cases).

## Constraints
No third-party auth libs. Use the existing UserSession model.
```
```
### Why Log
- [REFRACTION] Format: markdown (portable default)          [rule: ref-016]
- [REFRACTION] Bundled task split into two numbered steps   [rule: ref-007]
- [REFRACTION] Filler phrase "we shall" removed (-2 tokens) [rule: ref-002]
- [REFRACTION] ## Context and ## Constraints sections added [rule: ref-001]
- [SANITIZATION]  No PII or injection patterns found
- [INTROSPECTION] Score: 22 -> 88 / 100

### Prism Overhead This Run: ~1,340t
```

On Cursor or Claude Code, Prism auto-upgrades to XML (`ref-017`):
```xml
<context>Auth module, existing session-management layer.</context>
<task>
1. Add a login page: form fields, validation, POST to /auth/login.
2. Write unit tests for the login endpoint (happy path + 3 error cases).
</task>
<constraints>No third-party auth libs. Use the existing UserSession model.</constraints>
```

---

## The Three Pillars

| Pillar | What it does | Cost |
|--------|-------------|------|
| **Refraction** | Restructures prompts: XML tags, CoT triggers, output constraints, task decomposition | Fast model × 3 |
| **Sanitization** | Scans for PII, API keys, and injection phrases **before** any model call — pure regex | Zero (script) |
| **Introspection** | Scores 0–100 across 5 dimensions and learns your personal writing patterns over time | Fast model |

All analysis runs on the cheapest platform-native model within your security boundary (GPT-4.1, claude-haiku-4-5, or Cursor's built-in fast model). No data leaves your platform.

---

## Installation

**Prerequisites:** Python 3.9+.

### Cursor

```bash
# 1. Clone into a shared location
git clone https://github.com/CraigHutchinson/PrismLLM ~/.prism-skill

# 2. Install Python dependencies
pip install -r ~/.prism-skill/requirements.txt

# 3. Symlink the skill into your Cursor skills directory
ln -s ~/.prism-skill/.cursor/skills/prism ~/.cursor/skills/prism  # macOS/Linux
# Windows: mklink /D "%USERPROFILE%\.cursor\skills\prism" "%USERPROFILE%\.prism-skill\.cursor\skills\prism"

# 4. Restart Cursor — /prism appears in the skill menu
```

### Claude Code

**macOS / Linux:**
```bash
# 1. Clone the repo
git clone https://github.com/CraigHutchinson/PrismLLM ~/.prism-skill

# 2. Install Python dependencies
pip install -r ~/.prism-skill/requirements.txt

# 3. Copy the skill into your project's .claude/ directory
cp -r ~/.prism-skill/.claude/skills/prism .claude/skills/prism
cp -r ~/.prism-skill/.claude/skills/prism-sanitize .claude/skills/
cp -r ~/.prism-skill/.claude/skills/prism-score .claude/skills/
cp -r ~/.prism-skill/.claude/skills/prism-refract .claude/skills/

# 4. /prism is now available as a slash command in Claude Code
```

**Windows (PowerShell):**
```powershell
# 1. Clone the repo
git clone https://github.com/CraigHutchinson/PrismLLM "$env:USERPROFILE\.prism-skill"

# 2. Install Python dependencies
pip install -r "$env:USERPROFILE\.prism-skill\requirements.txt"

# 3. Copy the skill files into your project's .claude\ directory
$src = "$env:USERPROFILE\.prism-skill\.claude\skills"
New-Item -ItemType Directory -Force ".claude\skills" | Out-Null
Copy-Item -Recurse "$src\prism"           ".claude\skills\prism"
Copy-Item -Recurse "$src\prism-sanitize"  ".claude\skills\prism-sanitize"
Copy-Item -Recurse "$src\prism-score"     ".claude\skills\prism-score"
Copy-Item -Recurse "$src\prism-refract"   ".claude\skills\prism-refract"

# 4. /prism is now available as a slash command in Claude Code
```

### GitHub Copilot

**macOS / Linux:**
```bash
# 1. Clone the repo
git clone https://github.com/CraigHutchinson/PrismLLM ~/.prism-skill

# 2. Install Python dependencies
pip install -r ~/.prism-skill/requirements.txt

# 3. Copy platform files into your repo
cp ~/.prism-skill/.github/agents/prism.agent.md .github/agents/
cp ~/.prism-skill/.github/copilot-instructions.md .github/

# 4. The @prism agent appears in Copilot Chat's agent selector
```

**Windows (PowerShell):**
```powershell
# 1. Clone the repo
git clone https://github.com/CraigHutchinson/PrismLLM "$env:USERPROFILE\.prism-skill"

# 2. Install Python dependencies
pip install -r "$env:USERPROFILE\.prism-skill\requirements.txt"

# 3. Copy platform files into your repo
$src = "$env:USERPROFILE\.prism-skill"
New-Item -ItemType Directory -Force ".github\agents" | Out-Null
Copy-Item "$src\.github\agents\prism.agent.md" ".github\agents\prism.agent.md"
Copy-Item "$src\.github\copilot-instructions.md" ".github\copilot-instructions.md"

# 4. The @prism agent appears in Copilot Chat's agent selector
```

---

## Verify Your Installation

After installing on any platform, run the install verifier to confirm everything is in order:

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
| `/prism improve-prompt "..."` | Full pipeline: sanitize → score → refract → rewrite with Why Log | Fast × 3 + Capable × 1 |
| `/prism format` | Show active structural format (markdown/xml/prefixed) for this platform | None |
| `/prism sanitize "..."` | PII + injection scan | None (script) |
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

Override at any time: `/prism improve-prompt "..." --format xml`

---

## Output Format

Every `/prism improve-prompt` response follows this structure:

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

Cursor:
```bash
rm -rf ~/.cursor/skills/prism
rm -f .claude/settings.json  # or remove just the Prism hook entries
```

Claude Code:
```bash
rm -rf .claude/skills/prism .claude/skills/prism-sanitize \
       .claude/skills/prism-score .claude/skills/prism-refract
```

Copilot:
```bash
# Remove hooks first (cleans up .github/hooks/prism_hooks.json)
python ~/.prism-skill/scripts/hook_installer.py --action off
# Then remove agent and instructions files
rm .github/agents/prism.agent.md
rm .github/copilot-instructions.md
```

Runtime data (local only, never committed):
```bash
rm -rf .prism/
```

---

## Architecture

```
PrismLLM/
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
└── tests/                     ← pytest suite — 307 tests, 96% coverage
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
