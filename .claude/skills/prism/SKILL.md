---
name: prism
description: >
  Optimize, sanitize, and score prompts using the three-pillar Prism methodology
  (Refraction, Sanitization, Introspection). Use when the user runs /prism hello,
  /prism improve-prompt, /prism sanitize, /prism score, /prism explain,
  /prism format, /prism hook on/off/status, /prism patterns, /prism usage,
  /prism configure, or asks to optimize or analyze a prompt for an AI model.
disable-model-invocation: true
argument-hint: "[command] \"[prompt]\""
allowed-tools: Read, Bash
hooks:
  SessionStart:
    - type: command
      command: "python hooks/prism_preparser.py --event sessionStart --platform claude_code"
  UserPromptSubmit:
    - type: command
      command: "python hooks/prism_preparser.py --event userPromptSubmit --platform claude_code"
  PreToolUse:
    - matcher: "Bash|Edit|Write"
      type: command
      command: "python hooks/prism_preparser.py --event preToolUse --platform claude_code --stdin"
  Stop:
    - type: command
      command: "python hooks/prism_preparser.py --event stop --platform claude_code"
metadata:
  hook-config: .claude/settings.json
  hook-script: hooks/prism_preparser.py
  copilot-agent: .github/agents/prism.agent.md
  version: "1.0"
  platform: claude_code
---

# Prism — Claude Code Skill

This is the Claude Code variant of the Prism skill. It is identical to the Cursor `SKILL.md` with two additional capabilities:

1. **Parallel sub-skill dispatch** via `context: fork` for `/prism improve-prompt`
2. **`additionalContext` injection** from `UserPromptSubmit` hook (Stage 1 can inject suggestions, not just block)

For full command documentation see `.cursor/skills/prism/SKILL.md`. All commands, routing, and output formats are identical.

## `/prism hello`

**Model routing:** None — deterministic script.

```bash
python scripts/hello.py
```

Prints a live introduction: three pillars, real-time Stage 1 + Stage 2 demo on a built-in sample prompt, and top first commands. Output the script's stdout verbatim. This is the recommended first command for new users.

---

## `/prism format`

**Model routing:** None — deterministic script.

```bash
python scripts/format_output.py --detect-format
```

Prints the structural format (`xml`, `markdown`, or `prefixed`) that Prism will use
on this platform (Claude Code always → xml). To render a sample prompt:

```bash
python scripts/format_output.py \
  --task "Add a login page" \
  --context "Flask app, UserSession model" \
  --constraints "No third-party auth libs"
```

Format rules: `ref-016` (markdown default), `ref-017` (xml for Claude), `ref-018` (prefixed fallback).
On Claude Code the format is always xml — this is the preferred Claude upgrade (ref-017).

---

## Claude Code-Specific: Parallel Sub-skills

When running `/prism improve-prompt`, use Claude Code's Task tool to spawn three sub-skills in parallel:

```
Dispatch simultaneously using Task tool (context: fork):
  1. Sub-skill: prism-sanitize  (model: claude-haiku-4-5)
  2. Sub-skill: prism-score     (model: claude-haiku-4-5)
  3. Sub-skill: prism-refract   (model: claude-haiku-4-5)
```

Wait for all three to complete, then synthesize with the capable model.

The synthesis step is always capable model regardless of `model_routing.mode` in config (`synthesis_always_capable: true`).

## Claude Code-Specific: additionalContext

The `UserPromptSubmit` hook output is added to Claude Code's context via stdout. Stage 1 (`prism_preparser.py`) can:
- Return `{"decision": "block", "reason": "..."}` to block the prompt
- Return `{"decision": "continue", "additionalContext": "..."}` to inject a soft suggestion

This allows Prism to suggest improvements without interrupting flow — e.g., "Prism: consider adding output format constraints to this prompt."

## Delegation to SKILL.md

All command handlers are defined in the shared `.cursor/skills/prism/SKILL.md`. Read it now and apply the same routing. The difference is: use `decision: block/continue` format instead of `continue: false/true` for hook responses.
