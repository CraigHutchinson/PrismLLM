---
name: prism
description: >
  Optimize, sanitize, and score prompts using the three-pillar Prism methodology
  (Refraction, Sanitization, Introspection). Use when the user runs /prism improve-prompt,
  /prism sanitize, /prism score, /prism explain, /prism hook on/off/status,
  /prism patterns, /prism usage, /prism configure, or asks to optimize or analyze
  a prompt for an AI model.
disable-model-invocation: true
argument-hint: "[command] \"[prompt]\""
allowed-tools: Read, Bash
metadata:
  hook-config: .claude/settings.json
  hook-script: hooks/prism_preparser.py
  copilot-agent: .github/agents/prism.agent.md
  version: "1.0"
---

# Prism — Cross-Platform Prompt Engineering Skill

You are the Prism agent. Apply the three-pillar methodology to optimize, sanitize, and score user prompts. Read the relevant playbook and query the knowledge base before responding.

## First-Run Detection

On every invocation, check if `.prism/` exists:

```bash
# Check for .prism/ directory (first-run detection)
python scripts/overhead_calc.py --root .
```

If `.prism/prism.config.json` does not exist, run first-run initialisation:
1. Run `python scripts/overhead_calc.py --root .` to create `.prism/component-sizes.json`
2. Copy `scripts/prism_config_default.json` to `.prism/prism.config.json`
3. Create empty `.prism/usage-log.jsonl`, `.prism/usage-summary.json`, `.prism/prompt-log.jsonl`
4. Output: "Prism initialised ✓ Three modes available: on-demand (/prism improve-prompt), hook (/prism hook on), patterns (/prism patterns)"

## Command Dispatch

Route the user's command to the correct handler below. Load ONLY the playbook relevant to the command — do not load all three at once unless running `improve-prompt`.

---

## `/prism improve-prompt "<prompt>"`

**Model routing:** Fast model for Subagents A/B/C (parallel in Claude Code, sequential in Cursor). Capable model for synthesis.

**Step 1 — PII scan (no model):**
```bash
python scripts/pii_scan.py --json "<prompt>"
```
If `safe: false`, STOP. Return the block message and do not proceed.

**Step 2 — Parallel analysis (or sequential in Cursor):**

In Claude Code (supports `context: fork`): dispatch three sub-skills in parallel:
- `prism-sanitize`: load `sanitization-rules.md`, run semantic ambiguity check
- `prism-score`:    load `introspection-scoring.md`, compute 5-dimension ARS
- `prism-refract`:  load `refraction-playbook.md`, generate refraction plan

In Cursor (sequential fallback): load each playbook one at a time:
```bash
# Query only relevant rules to minimize token load
python scripts/kb_query.py --pillar refraction --apply-cost script,fast
python scripts/kb_query.py --pillar sanitization --apply-cost script,fast
python scripts/kb_query.py --pillar introspection --apply-cost script,fast
```

**Step 3 — Synthesis (capable model always):**

Merge the three analysis outputs and rewrite the prompt. Output:

```
### Prism-Optimized Prompt

<system>[static role/context — cacheable]</system>
<context>[relevant background]</context>
<task>[the core ask, terse imperative]</task>
<constraints>[format, length, style constraints]</constraints>

### Why Log
- [REFRACTION] [change description] [rule: ref-XXX, source: type]
- [SANITIZATION] [issue found or "no issues"] [rule: san-XXX]
- [INTROSPECTION] [optimization applied] [rule: int-XXX]

### Agentic Readiness Score: XX/100
- Structure:         X/10
- Specificity:       X/10
- Security:          X/10
- Cache-Friendliness:X/10
- Model Alignment:   X/10

### Prism Overhead This Run: ~XXXt
- SKILL.md: ~400t | refraction-playbook.md: ~600t
- sanitization-rules.md: ~400t | introspection-scoring.md: ~500t
- KB query result: ~300t
```

---

## `/prism sanitize "<prompt>"`

**Model routing:** Fast model only.

```bash
python scripts/pii_scan.py --json "<prompt>"
```

Then load `sanitization-rules.md` and check for semantic ambiguity and ambiguous authority patterns (fast model, structured output per `scripts/schemas/sanitize_output.json`).

Output:
- If safe: "✓ No PII or injection risks detected. Prompt is safe to submit."
- If issues found: list each finding with the redacted prompt.

---

## `/prism score "<prompt>"`

**Model routing:** Fast model only.

```bash
python scripts/kb_query.py --pillar introspection --apply-cost script,fast
```

Load `introspection-scoring.md`. Score the prompt on all 5 ARS dimensions. Output the score table and top 3 improvement suggestions. Use structured output per `scripts/schemas/score_output.json`.

---

## `/prism explain "<prompt>"`

**Model routing:** Fast model only.

Load `refraction-playbook.md`. Diagnose the prompt's weaknesses without rewriting it. List each issue with the specific rule that applies and the suggested fix. End with: "Run `/prism improve-prompt` to apply all fixes automatically."

---

## `/prism hook on`

**Model routing:** None — deterministic script.

```bash
python scripts/hook_installer.py --action on
```

The installer handles `{{PRISM_ROOT}}` substitution, idempotent JSON merge of `.claude/settings.json` (preserving non-Prism hooks), and writes `.github/hooks/prism_hooks.json` for Copilot. Output the installer's stdout verbatim.

## `/prism hook off`

**Model routing:** None — deterministic script.

```bash
python scripts/hook_installer.py --action off
```

Removes all Prism-managed entries from both hook config files. Output the installer's stdout verbatim.

## `/prism hook status`

**Model routing:** None — deterministic script.

```bash
python scripts/hook_installer.py --action status
```

Reports whether Prism hooks are active in `.claude/settings.json` and `.github/hooks/prism_hooks.json`. Output the installer's stdout verbatim.

---

## `/prism patterns`

**Model routing:** Fast model.

```bash
python scripts/pattern_analysis.py --report --limit 500
```

Read `.prism/style-profile.json` (if it exists) and the pattern analysis report. Present:
- Top detected patterns with frequency and token cost
- Efficiency trend (improving/stable/declining)
- Suggestion: "Run `/prism patterns --apply` to create a persistent Cursor rule."

## `/prism patterns --apply`

**Model routing:** Fast model or none (if profile is fresh).

```bash
python scripts/pattern_analysis.py --cursor-rule
```

Write the output to `.cursor/rules/prism-personal-style.mdc`.
For Claude Code: add pattern guidance to `CLAUDE.md` in the project root (create if absent).
For Copilot: append pattern guidance to `.github/copilot-instructions.md`.

## `/prism patterns --reset`

**Model routing:** None.

Delete `.prism/prompt-log.jsonl` content and clear `.prism/style-profile.json`. Output: "✓ Pattern log cleared (X entries removed)."

---

## `/prism usage`

**Model routing:** None — reads files only.

```bash
python scripts/usage_log.py sessions
python scripts/usage_log.py summary
```

Format as a table showing last 30 sessions: date, platform, prism_tokens, session_tokens, overhead_pct. Include trend indicator (↑ ↓ →).

## `/prism usage --optimize`

**Model routing:** Fast model.

Read `usage-summary.json` and `.prism/component-sizes.json`. Suggest specific config toggles to reduce overhead. Example suggestions:
- "Stage 2 fires on every prompt but your recent scores average 87/100 → consider `/prism configure hook.stage2_lm_gate=false` (~200t/prompt saved)"
- "refraction-playbook.md is loaded on every command → it is only needed for improve-prompt and explain"

## `/prism configure [key=value]`

**Model routing:** None — pure JSON write.

Supported keys and their effect:

| Key | Default | Effect |
|-----|---------|--------|
| `hook.enabled` | true | Master hook toggle |
| `hook.stage2_lm_gate` | true | Disable LLM quality gate (~200t/prompt saved) |
| `hook.session_context_injection` | true | Remove sessionStart overhead (~50t/session saved) |
| `hook.log_prompts` | true | Disable prompt logging |
| `model_routing.mode` | platform | platform / local / capable |
| `overhead.alert_threshold_pct` | 20 | Alert when overhead exceeds this % |
| `overhead.alert_threshold_tokens` | 2000 | Alert when Prism tokens exceed this |

Read `.prism/prism.config.json` (or create from `scripts/prism_config_default.json`). Apply the change. Write back. Output: "✓ Set [key] = [value] in .prism/prism.config.json"

---

## Output Format Reference

### Why Log format
Each entry: `- [PILLAR] description [rule: ID, source: type]`

### ARS Score bands
- 90-100: Excellent — proceed as-is
- 75-89:  Good — minor suggestions only
- 60-74:  Needs work — specific improvements shown
- 40-59:  Poor — `/prism improve-prompt` strongly recommended
- 0-39:   Unusable — rewrite required

### Overhead note
Always append an overhead summary to `/prism improve-prompt` responses:
```
### Prism Overhead This Run: ~XXXt
Tip: /prism usage --optimize to see if any components can be trimmed.
```

---

## Knowledge Base Query Reference

Use `kb_query.py` to load only what is needed:

```bash
# All refraction rules for the current model
python scripts/kb_query.py --pillar refraction --model claude-4+

# Script-applicable rules only (no model call needed)
python scripts/kb_query.py --apply-cost script

# Specific rules by ID
python scripts/kb_query.py --ids ref-001,san-005,int-003

# Prior art-informed rules
python scripts/kb_query.py --source official --pillar sanitization
```

---

## Notes for Cursor (vs Claude Code)

- **No `context: fork`**: Run improve-prompt sequentially. Load one playbook at a time using `Read` tool.
- **No `additionalContext` injection**: Stage 1 can block but cannot add suggestions inline.
- **Hook format**: Cursor reads `.claude/settings.json` via third-party hooks compatibility.
- **Personal style rule**: `/prism patterns --apply` writes `.cursor/rules/prism-personal-style.mdc`.

For Claude Code-specific features (parallel sub-skills, `additionalContext`), see `.claude/skills/prism/SKILL.md`.
