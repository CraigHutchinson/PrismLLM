# Prism Manual Test Checklist

These tests cover agent reasoning, platform integration, and multi-step flows that cannot be automated with pytest.

Run these manually before each release against a live IDE session.

---

## Setup Checklist

- [ ] Prism repo cloned to local machine
- [ ] `/prism hook off` run to ensure clean state
- [ ] `.prism/` directory does not exist (fresh state)

---

## Test Group 1: Core Skill Commands

### MT-01: `/prism improve` — basic
- [ ] Run: `/prism improve "add a login page to the auth module and also write the tests"`
- [ ] Expected: Structured output with XML-tagged prompt, Why Log with at least 2 entries, ARS score out of 100
- [ ] Expected: Score includes structure, specificity, security, cache_friendliness, model_alignment dimensions

### MT-02: `/prism sanitize` — clean prompt
- [ ] Run: `/prism sanitize "add JWT authentication to the login endpoint"`
- [ ] Expected: "No PII or injection risks detected" message

### MT-03: `/prism sanitize` — PII prompt
- [ ] Run: `/prism sanitize "send results to user@example.com when done"`
- [ ] Expected: EMAIL entity flagged, redacted prompt shown

### MT-04: `/prism score` — rubric output
- [ ] Run: `/prism score "make it better"`
- [ ] Expected: ARS score with low specificity score (≤ 3/10), improvement suggestion

### MT-05: `/prism explain` — diagnosis without rewrite
- [ ] Run: `/prism explain "we shall add a login feature and also update the tests"`
- [ ] Expected: Diagnosis listing bundling issue + verbosity (royal_we pattern) — no rewrite

---

## Test Group 2: Hook Management

### MT-06: `/prism hook on`
- [ ] Run: `/prism hook on`
- [ ] Expected: `.claude/settings.json` created (or updated) with Prism hook config
- [ ] Expected: `.github/hooks/prism_hooks.json` created (or updated)
- [ ] Expected: Confirmation message listing both files

### MT-07: Hook blocks PII (requires hook on)
- [ ] Enable hook: `/prism hook on`
- [ ] Submit prompt: `send the test results to alice@example.com`
- [ ] Expected: Prompt blocked, message showing EMAIL entity detected

### MT-08: Hook passes clean prompt (requires hook on)
- [ ] Enable hook: `/prism hook on`
- [ ] Submit prompt: `add unit tests for the payment service`
- [ ] Expected: Prompt proceeds normally to the model

### MT-09: `/prism hook off`
- [ ] Run: `/prism hook off`
- [ ] Expected: Prism entries removed from `.claude/settings.json`
- [ ] Expected: Confirmation message

### MT-10: `/prism hook status`
- [ ] Run with hooks enabled: `/prism hook status`
- [ ] Expected: Shows hook active, platform detected, stages enabled

---

## Test Group 3: Pattern Analysis

### MT-11: `/prism patterns` — insufficient data
- [ ] Fresh `.prism/` state (no prompt-log.jsonl)
- [ ] Run: `/prism patterns`
- [ ] Expected: Graceful "not enough data" message (threshold: 25 prompts)

### MT-12: `/prism patterns` — with data
- [ ] Requires 25+ prompts logged (use hook for a session)
- [ ] Run: `/prism patterns`
- [ ] Expected: Style report with detected patterns and efficiency trend

### MT-13: `/prism patterns --apply`
- [ ] Run after MT-12: `/prism patterns --apply`
- [ ] Expected on Cursor: `.cursor/rules/prism-personal-style.mdc` created with `alwaysApply: true`
- [ ] Expected on Claude Code: CLAUDE.md updated or sessionStart hook updated

### MT-14: `/prism patterns --reset`
- [ ] Run: `/prism patterns --reset`
- [ ] Expected: `.prism/prompt-log.jsonl` cleared (0 entries)
- [ ] Expected: `.prism/style-profile.json` cleared

---

## Test Group 4: Usage & Overhead

### MT-15: `/prism usage` — no prior sessions
- [ ] Fresh `.prism/` state
- [ ] Run: `/prism usage`
- [ ] Expected: Graceful empty state message ("No sessions logged yet")

### MT-16: `/prism usage` — with sessions
- [ ] After several sessions with hook active
- [ ] Run: `/prism usage`
- [ ] Expected: Table of last sessions with prism_tokens, overhead_pct, platform columns

### MT-17: `/prism usage --optimize`
- [ ] Run: `/prism usage --optimize`
- [ ] Expected: Fast-model suggestion naming specific config toggles (e.g., disable Stage 2)

### MT-18: `/prism configure`
- [ ] Run: `/prism configure hook.stage2_lm_gate=false`
- [ ] Expected: `.prism/prism.config.json` updated, confirmation shown

---

## Test Group 5: Platform-Specific

### MT-19: Claude Code parallel fork (improve)
- [ ] Run `/prism improve "..."` in Claude Code
- [ ] Expected: Three subagents visible in Claude Code's reasoning trace (prism-sanitize, prism-score, prism-refract)
- [ ] Expected: Final synthesis uses capable model

### MT-20: Cursor sequential fallback (improve)
- [ ] Run `/prism improve "..."` in Cursor
- [ ] Expected: Single agent, playbooks loaded one at a time, sequential execution logged

### MT-21: Copilot agent invocation
- [ ] Invoke via `@prism improve "..."` in Copilot Chat
- [ ] Expected: Agent responds with structured analysis

### MT-22: Copilot preToolUse blocking
- [ ] Enable Copilot hooks: `/prism hook on` (in Copilot)
- [ ] Trigger a tool use with an API key in the arguments
- [ ] Expected: `permissionDecision: deny` prevents execution

---

## Test Group 6: First-Run Detection

### MT-23: First invocation initialisation
- [ ] Remove `.prism/` directory entirely
- [ ] Run any `/prism` command
- [ ] Expected: `.prism/` directory created
- [ ] Expected: `.prism/prism.config.json` seeded from defaults
- [ ] Expected: `.prism/component-sizes.json` created
- [ ] Expected: "Prism initialised" message shown

---

## Test Group 7: Error & Edge Cases

### MT-24: Empty prompt (hook)
- [ ] Submit an empty or whitespace-only prompt with hook enabled
- [ ] Expected: Passes through (not blocked)

### MT-25: Very long prompt (> 2000 tokens estimated)
- [ ] Submit a large code block (paste 8000 characters)
- [ ] Expected: Hook Stage 1 completes in < 500ms, no timeout

### MT-26: `/prism hook on` — merge with existing settings
- [ ] Create a `.claude/settings.json` with non-Prism hooks already present
- [ ] Run: `/prism hook on`
- [ ] Expected: Existing hooks preserved, Prism hooks added (not overwritten)
