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

**Model routing:** Two-pass analysis — deterministic script (zero cost) then LLM semantic reviewer (fast model). Capable model applies fixes.

**File Detection:** Before Prompt Resolution, check whether the argument looks like a file path (contains `/`, `\`, or ends in `.md`, `.txt`, `.yaml`, `.json`). If the `Read` tool confirms the file exists, use this mode instead of the prompt pipeline.

---

### Pass 1 — Deterministic analysis (no model)

```bash
python scripts/agent_review.py --file "<file_path>" --json
```

Captures structural issues the script can detect with certainty:

| Rule | What it catches |
|------|-----------------|
| agt-001 | Negative instructions (`never`, `do not`, `don't`) |
| agt-002 | Duplicate instructions across sections |
| agt-003 | Unversioned model pin (family name instead of version string) |
| agt-004 | Inline `<example>` XML inside YAML `description:` field |
| agt-005 | Missing ambiguity/clarification-handling section |

---

### Pass 2 — LLM semantic review (fast model)

Read the full file, then act as a senior agent-design reviewer. Check for the following six semantic anti-patterns that regex rules cannot reliably detect:

| Rule | Anti-pattern | Signals to look for |
|------|-------------|---------------------|
| llm-001 | Vague scope language | "handle edge cases", "as needed", "use your best judgement", "various situations" |
| llm-002 | Overpromising | "always", "guaranteed", "never fails", "perfect", "100%", "without exception" |
| llm-003 | Missing output format spec | No `## Output Format` or equivalent section defining structure, length, or schema |
| llm-004 | Role scope creep | 4+ unrelated domains covered without a stated primary domain |
| llm-005 | Missing error/ambiguity handling | No guidance on what to do when tasks fail, inputs are malformed, or intent is unclear |
| llm-006 | Implicit authority escalation | Destructive actions (delete, send, override) with no confirmation requirement stated |

For each issue found, produce a structured entry matching the script's Issue shape:

```json
{
  "rule_id": "llm-003",
  "severity": "warn",
  "section": "body",
  "before": "(no output format section found)",
  "after": "## Output Format\n\nRespond with …",
  "explanation": "Without an output format section the model chooses structure at runtime, leading to inconsistent responses."
}
```

Only report issues that are clearly present. Do not invent findings. If a pattern is absent or borderline, skip it.

**Claude Code parallel dispatch:** Spawn Pass 1 and Pass 2 simultaneously using `context: fork` — one sub-task runs the script, the other performs the semantic review. Merge results when both complete.

Merge the LLM issues with the script issues into a single list before presenting.

---

### Present unified findings

Display a numbered table of **all** issues (agt-* and llm-*):

| # | Rule | Sev | Section | Issue summary |
|---|------|-----|---------|---------------|
| 1 | agt-001 | warn | responsibilities | "Never add tests unless…" |
| 2 | llm-003 | warn | body | Missing output format section |

Then show each issue in full (rule ID, severity, before, after, explanation).

---

### Generate rewrites (fast model)

**For each agt-001 issue:** generate a positive-constraint rewrite of the `before` line:
- Remove negation words ("never", "do not", "don't", "avoid")
- Express what the agent *should* do, not what it must avoid
- Preserve original intent exactly; match bullet style and indentation

Build a JSON rewrite map: `{"<before text>": "<rewritten text>", ...}`

**For each llm-* issue:** prepare the suggested `after` text (already generated in Pass 2).

---

### Apply all fixes

**Script-detectable fixes (agt-002..005) + agt-001 rewrites:**
```bash
python scripts/agent_review.py --file "<file_path>" --apply --rewrite-map '<json_rewrite_map>'
```
(Omit `--rewrite-map` if there are no agt-001 issues.)

**LLM-detected fixes (llm-*):** Apply directly using the `Edit` or `Write` tool — insert new sections, reword paragraphs, or remove problematic phrases as appropriate.

---

### Post-apply validation

After all fixes are written, re-run the deterministic analysis on the modified file:

```bash
python scripts/agent_review.py --file "<file_path>" --json
```

Check the output for **induced artifacts** — new issues created by the apply step itself. Common examples:

| Artifact | Caused by | Rule that catches it |
|----------|-----------|----------------------|
| Description ending in "Examples:" | agt-004 stripped `<example>` but left the intro label | agt-006 |
| Blank frontmatter field | agt-003/agt-004 partial replacement | agt-006 |
| Duplicate line introduced by agt-005 section addition | File already had a near-match section | agt-002 |

If new issues appear, fix them before reporting. If they cannot be auto-fixed by the script, apply them directly with the `Edit` or `Write` tool.

---

### Report outcome

```
[N] issue(s) found ([M] deterministic, [K] semantic).
[N] fix(es) applied. [P] post-apply issue(s) resolved.
File rewritten: <file_path>
```

If no issues are found in either pass, output: "No issues detected in `<file_path>`. The file meets all agent design guidelines."

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
