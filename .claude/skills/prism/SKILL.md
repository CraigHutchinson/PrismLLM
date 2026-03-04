---
name: prism
description: >
  Optimize, sanitize, and score prompts using the three-pillar Prism methodology
  (Refraction, Sanitization, Introspection). Use when the user runs /prism hello,
  /prism improve, /prism sanitize, /prism score, /prism explain,
  /prism format, /prism hook [on/off/status — defaults to on], /prism patterns, /prism usage,
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

1. **Parallel sub-skill dispatch** via `context: fork` for `/prism improve`
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

## `/prism improve <file_path>` — Agent File Analysis Mode

**Model routing:** None — deterministic script only.

**File Detection:** Before Prompt Resolution, check whether the argument looks like a file path (contains `/`, `\`, or ends in `.md`, `.txt`, `.yaml`, `.json`). If the `Read` tool confirms the file exists, use this mode instead of the prompt pipeline.

**Step 1 — Analyse (no model):**
```bash
python scripts/agent_review.py --file "<file_path>" --json
```

**Step 2 — Present findings:**

Display a numbered table (rule ID, severity, section, before, after) for every issue found.

**Step 3 — Apply all fixes automatically:**
```bash
python scripts/agent_review.py --file "<file_path>" --apply
```

**Step 4 — Report outcome:**
```
[N] issue(s) found, [N] fix(es) applied.
File rewritten: <file_path>
```

If no issues are found, output: "No issues detected in `<file_path>`. The file meets all agent design guidelines."

---

## Prompt Resolution (all platforms)

**Run this before any other step when handling `/prism improve`:**

If no `"<prompt>"` argument was supplied (i.e. the user typed `/prism improve` with nothing after it):
1. Look back at the conversation to find the most recent user message that is not a `/prism` command.
2. Extract the full text of that message as the inferred prompt.
3. Output this notice before proceeding (do not skip it):
   > No prompt supplied — inferring from your last message:
   > *"[inferred prompt text]"*
   >
   > Run `/prism improve "..."` with an explicit prompt to override.
4. Continue the full pipeline using the inferred prompt as `<prompt>`.

If no prior non-Prism message exists, output: "No prompt supplied and no prior message found. Please run `/prism improve \"your prompt\"`." and stop.

---

## Claude Code-Specific: Parallel Sub-skills

When running `/prism improve`, use Claude Code's Task tool to spawn three sub-skills in parallel:

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
