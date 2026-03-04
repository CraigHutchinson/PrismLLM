# Prism — Always-On Prompt Engineering Assistant

## Installing Prism (first-time setup)

If you are in a **fresh session** and the `.prism/` directory does not yet exist in this workspace, Prism has not been initialised. Run the install commands below, then come back and use the commands in the next section.

**macOS / Linux:**
```bash
git clone https://github.com/CraigHutchinson/Prism ~/.prism-skill
python ~/.prism-skill/configure.py
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/CraigHutchinson/Prism "$env:USERPROFILE\.prism-skill"
python "$env:USERPROFILE\.prism-skill\configure.py"
```

`configure.py` installs for all platforms (Cursor, Claude Code, Copilot), installs Python dependencies, and runs a health check. Restart Cursor after running if installing for Cursor.

Run `/prism hello` once installed to confirm everything is working.

---

The **Prism** skill is available in this repository for prompt analysis, optimization, and security scanning.

## What Prism Does

Prism applies a three-pillar methodology to every prompt before it reaches the AI model:

- **Refraction** — Restructures prompts for precision: XML tags, CoT triggers, output format constraints
- **Sanitization** — Scans for PII, API keys, and injection phrases before submission
- **Introspection** — Scores prompts on a 5-dimension Agentic Readiness Scale (0–100)

## How to Use It

```
/prism hello                                           Interactive intro + live demo
/prism improve "add a login page to the auth module and also write the tests"
/prism sanitize "send results to user@example.com when done"
/prism score "refactor the database connection pool"
/prism explain "make it better"
/prism hook on
/prism usage
/prism patterns
```

## When Prism Is Most Useful

- Before submitting a complex multi-step request
- When a prompt contains potentially sensitive context (credentials, personal data)
- When a previous prompt produced a vague or off-target response
- Periodically, to analyse your personal writing habits with `/prism patterns`

## More Information

See `README.md` for full installation and command reference, `llms.txt` for a compact LLM-optimized install card, or run `/prism explain` for an inline tour.

<!-- PRISM_PERSONAL_STYLE_START -->
<!-- PRISM_PERSONAL_STYLE_END -->
