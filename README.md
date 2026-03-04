# Prism — Cross-Platform Prompt Engineering Skill

> **Treat your prompts like code.** Prism is a static analysis engine for AI interactions — catching structural weaknesses, stripping sensitive data, and rewriting for precision. No new tools, no subscription, no context switch. Lives inside the IDE you already use.

[![Tests](https://github.com/CraigHutchinson/PrismLLM/actions/workflows/test.yml/badge.svg)](https://github.com/CraigHutchinson/PrismLLM/actions)

---

## The Three Pillars

| Pillar | What it does | When it runs |
|--------|-------------|-------------|
| **Refraction** | Restructures prompts: XML tags, CoT triggers, output constraints, task decomposition | On demand (`/prism improve-prompt`) or hook |
| **Sanitization** | Scans for PII, API keys, and injection phrases **before** any model call | Pre-flight — Stage 1 is pure regex, zero model cost |
| **Introspection** | Scores on 5 dimensions (Structure, Specificity, Security, Cache-Friendliness, Model Alignment) and tracks your personal writing patterns over time | On demand + background at session end |

---

## Installation

**Prerequisites:** Python 3.9+. No other dependencies for v1 (schemas use the standard library, jsonschema optional for tests).

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
✓ Python 3.11 (>= 3.9 required)
✓ jsonschema installed
✓ All 9 core scripts present
✓ Hook script present
✓ Data files present
✓ JSON schemas valid (4 schemas, 35 rules)
✓ pii_scan functional
✓ stage2_gate functional
✓ hook_installer status ok
✓ .prism/ directory writeable

All 10 checks passed. Prism is ready.
Run: /prism improve-prompt "your first prompt here"
```

If any check fails, a one-line fix hint is printed alongside the failure.

Then run your first Prism command to get an interactive introduction with a live demo:

```
/prism hello
```

---

## The Five Most-Used Commands

| Command | What it does | Model cost |
|---------|-------------|-----------|
| `/prism hello` | Interactive intro + live Stage 1/Stage 2 demo on a sample prompt | None |
| `/prism improve-prompt "..."` | Full pipeline: sanitize → score → refract → rewrite with Why Log | Fast × 3 + Capable × 1 |
| `/prism sanitize "..."` | PII + injection scan + semantic ambiguity check | Fast model |
| `/prism score "..."` | 5-dimension Agentic Readiness Score (0-100) | Fast model |
| `/prism hook on` | Enable always-on pre-flight analysis for every prompt | None |
| `/prism patterns` | Analyse your personal writing habits for terse suggestions | Fast model |

### Full Command Reference

**Getting started:**
```
/prism hello                          Interactive intro + live demo (start here)
```

**Analysis (on-demand):**
```
/prism improve-prompt "your prompt"   Full pipeline + rewrite
/prism sanitize "your prompt"         PII + injection check only
/prism score "your prompt"            ARS score + improvement tips
/prism explain "your prompt"          Diagnosis without rewrite
```

**Hook management:**
```
/prism hook on                        Enable always-on pre-flight analysis
/prism hook off                       Disable hooks
/prism hook status                    Show hook state and active stages
```

**Personal patterns:**
```
/prism patterns                       Analyse your writing habits
/prism patterns --apply               Generate a persistent style rule
/prism patterns --reset               Clear the prompt log
```

**Usage & overhead:**
```
/prism usage                          Show 30-session overhead history
/prism usage --optimize               Fast-model suggestions to reduce overhead
/prism configure key=value            Toggle features in prism.config.json
```

---

## Output Format

Every `/prism improve-prompt` response looks like this:

```
### Prism-Optimized Prompt
<system>...</system>
<context>...</context>
<task>...</task>
<constraints>...</constraints>

### Why Log
- [REFRACTION] Added XML structure ... [rule: ref-001, source: official]
- [SANITIZATION] No issues found ✓
- [INTROSPECTION] CoT trigger injected ... [rule: int-010]

### Agentic Readiness Score: 87/100
- Structure:          9/10
- Specificity:        8/10
- Security:          10/10
- Cache-Friendliness: 7/10
- Model Alignment:    8/10

### Prism Overhead This Run: ~1,340t
```

---

## Updating the Knowledge Base

The knowledge base is in `knowledge-base/rules.json`. To add a rule manually:

1. Read `knowledge-base/sources.md` to identify the source.
2. Add a new entry to `rules.json` following the schema in `knowledge-base/rules.json` (copy an existing entry as a template).
3. Set `apply_cost` to `script` (regex/deterministic), `fast` (lightweight model), or `capable` (semantic rewrite required).
4. Set `model_applies` to the minimum Claude version where the rule applies (e.g. `["claude-3.5+"]`).

A `/prism kb add` command for automated URL-based rule extraction is planned for v2.

---

## Disabling & Uninstalling

**Disable hooks only (keep skill):**
```
/prism hook off
```

**Disable specific overhead components:**
```
/prism configure hook.stage2_lm_gate=false        # Save ~200t/prompt
/prism configure hook.session_context_injection=false  # Save ~50t/session
/prism configure hook.log_prompts=false           # Stop logging prompts
```

**Uninstall completely:**

Cursor:
```bash
rm -rf ~/.cursor/skills/prism
rm -f .claude/settings.json  # or remove the Prism entries from it
```

Claude Code:
```bash
rm -rf .claude/skills/prism .claude/skills/prism-sanitize .claude/skills/prism-score .claude/skills/prism-refract
```

Copilot:
```bash
# Turn off hooks first (removes .github/hooks/prism_hooks.json if active)
python ~/.prism-skill/scripts/hook_installer.py --action off
# Then remove the agent and instructions files
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
├── .cursor/skills/prism/      ← Cursor skill (AgentSkills.io standard)
│   ├── SKILL.md               ← Command dispatch + routing logic
│   ├── refraction-playbook.md ← XML tags, CoT triggers, caching strategy
│   ├── sanitization-rules.md  ← PII types, injection patterns, severity levels
│   ├── introspection-scoring.md ← ARS rubric, 5 dimensions
│   └── examples.md            ← Before/after walkthroughs
│
├── .claude/skills/prism/      ← Claude Code variant (+ parallel sub-skills)
│   ├── prism/SKILL.md
│   ├── prism-sanitize/SKILL.md  ← Subagent A (claude-haiku-4-5)
│   ├── prism-score/SKILL.md     ← Subagent B (claude-haiku-4-5)
│   └── prism-refract/SKILL.md   ← Subagent C (claude-haiku-4-5)
│
├── .github/agents/prism.agent.md  ← Copilot agent
│
├── hooks/
│   ├── prism_preparser.py     ← Hook script: sessionStart, userPromptSubmit, stop
│   ├── claude_settings_template.json  ← Written by /prism hook on
│   └── prism_hooks_template.json      ← Copilot hook config template
│
├── scripts/
│   ├── pii_scan.py            ← Regex PII + injection scanner (no model)
│   ├── kb_query.py            ← Knowledge base filter + cache
│   ├── overhead_calc.py       ← Token estimator from file sizes (no model)
│   ├── platform_model.py      ← Platform detection + model router
│   ├── pattern_analysis.py    ← Prompt log analyser
│   ├── usage_log.py           ← Session overhead log management
│   ├── hello.py               ← /prism hello intro command + live demo (no model)
│   ├── hook_installer.py      ← /prism hook on|off|status (idempotent)
│   ├── stage2_gate.py         ← Stage 2 deterministic quality gate (no model)
│   ├── verify_install.py      ← Post-install health checker (10 checks)
│   ├── verbosity_patterns.json ← Seeded verbose → terse phrase dictionary
│   ├── prism_config_default.json ← Default configuration template
│   └── schemas/               ← JSON output schemas for structured model calls
│
├── knowledge-base/
│   ├── rules.json             ← 35 seeded prompt engineering rules
│   └── sources.md             ← Bibliography + prior art
│
└── tests/                     ← Pytest suite (TDD, 80%+ coverage target)
```

---

## Model Cost Summary

Prism is designed to pay for itself. Analysis subagents run on the cheapest models within each platform's security boundary.

| Platform | Analysis subagents | Synthesis | Hook Stage 2 |
|----------|--------------------|-----------|-------------|
| Copilot paid | GPT-4.1 (0×) | Capable | Tool budget |
| Copilot free | Goldeneye (0×) | Capable | Tool budget |
| Claude Code | claude-haiku-4-5 | Capable | Tool budget |
| Cursor | Built-in fast | Capable | Tool budget |

Cloud free APIs (Groq, Gemini, OpenRouter) are explicitly deferred from v1. They require opt-in and are flagged as leaving the platform security boundary.

---

## Prior Art

Prism is not the first prompt optimization tool — but it is the first to combine IDE-native integration, pre-flight PII scanning, personal pattern learning, model-version-aware rules, and self-monitored overhead in a single zero-subscription package.

See `knowledge-base/sources.md` for the full competitive landscape and how each prior tool informed Prism's design.

---

## Contributing

1. Add new rules to `knowledge-base/rules.json` and a source entry to `knowledge-base/sources.md`
2. Write tests first (red state) before implementing new scripts
3. Run `pytest tests/ --cov=scripts --cov=hooks` before opening a PR
4. All security-critical paths (`pii_scan.py`, `prism_preparser.py`) require 100% test coverage

---

## License

MIT
