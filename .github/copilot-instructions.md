# Prism — Always-On Prompt Engineering Assistant

The **Prism** agent is available in this repository for prompt analysis, optimization, and security scanning.

## What Prism Does

Prism applies a three-pillar methodology to every prompt before it reaches the AI model:

- **Refraction** — Restructures prompts for precision: XML tags, CoT triggers, output format constraints
- **Sanitization** — Scans for PII, API keys, and injection phrases before submission
- **Introspection** — Scores prompts on a 5-dimension Agentic Readiness Scale (0–100)

## How to Use It

Invoke the Prism agent directly in Copilot Chat:

```
@prism improve-prompt "add a login page to the auth module and also write the tests"
@prism sanitize "send results to user@example.com when done"
@prism score "refactor the database connection pool"
@prism explain "make it better"
@prism hook on
@prism usage
```

## When Prism Is Most Useful

- Before submitting a complex multi-step request
- When a prompt contains potentially sensitive context (credentials, personal data)
- When a previous prompt produced a vague or off-target response
- Periodically, to analyse your personal writing habits with `@prism patterns`

## More Information

See `README.md` for full installation and command reference, or run `@prism explain` for an inline tour.
