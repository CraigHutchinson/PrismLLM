# Install Documentation & First-Use Testing Improvement Plan

## Elevator Speech

A new user clones Prism, follows the README, and has no idea if it actually worked. There is no "did it work?" check, no `pip install` step in the docs, and no automated way to confirm the environment is healthy before they type their first `/prism` command. This plan closes that gap with four things: (1) documentation fixes, (2) a single-command install verifier, (3) a smoke test suite that mirrors the README steps, and (4) CI jobs that run the whole install flow in a clean sandbox.

---

## Current State Audit

### Documentation gaps

| ID  | File | Issue | Severity |
|-----|------|-------|----------|
| D-01 | `README.md` | No `pip install -r requirements.txt` step in any install section | HIGH — scripts silently fail without jsonschema |
| D-02 | `README.md` | No "verify your install" step; user has no feedback until they type a command | HIGH |
| D-03 | `README.md` | Architecture diagram omits `hook_installer.py` and `stage2_gate.py` | MEDIUM |
| D-04 | `README.md` | Copilot uninstall says `rm .github/hooks/prism_hooks.json` but that file is gitignored — it only exists after `/prism hook on` | MEDIUM |
| D-05 | `.github/copilot-instructions.md` | Uses `/prism patterns` — Copilot uses `@prism`, not `/prism` | MEDIUM |
| D-06 | `.github/workflows/test.yml` | Installs `pytest pytest-cov jsonschema` directly, bypassing `requirements-dev.txt` | LOW |
| D-07 | `PLAN.md` | References `.claude/hooks/prism_preparser.py` — actual path is `hooks/prism_preparser.py` | LOW |

### Installation flow gaps

| ID  | Gap | Impact |
|-----|-----|--------|
| I-01 | No verification step exists — zero user feedback post-install | User can't confirm anything works |
| I-02 | `requirements.txt` exists but is never referenced in README or CI | jsonschema silently absent for new users |
| I-03 | No smoke tests that exercise CLI entry points end-to-end | Regressions in CLI surface only when a user hits them |
| I-04 | No sandboxed install test — CI only tests the code, not "does the README actually work?" | Install instructions can drift from reality |
| I-05 | No Python version matrix in CI | Undiscovered 3.9/3.10/3.12 incompatibilities |

---

## Deliverables

### Phase 1 — Documentation Fixes  *(edit existing files only)*

#### TASK-D01: Add `pip install` step to README
File: `README.md`  
Each platform section (Cursor, Claude Code, Copilot) gets a step inserted between "clone" and "symlink/copy":
```bash
# Install Python dependencies (jsonschema for schema validation)
pip install -r requirements.txt
```
And in the Windows PowerShell blocks:
```powershell
pip install -r "$env:USERPROFILE\.prism-skill\requirements.txt"
```

#### TASK-D02: Add "Verify your install" section to README
Add to `README.md` after the Installation section, before "The Five Most-Used Commands":
```bash
# Verify the install is healthy (exit 0 = all checks passed)
python ~/.prism-skill/scripts/verify_install.py
```
The section explains what the script checks and what each failure message means.

#### TASK-D03: Update README Architecture diagram
Add the two missing scripts:
```
│   ├── hook_installer.py      ← /prism hook on|off|status (idempotent)
│   ├── stage2_gate.py         ← Stage 2 deterministic quality gate
```

#### TASK-D04: Fix Copilot uninstall wording
Change:
> `rm .github/hooks/prism_hooks.json`

To:
> Run `/prism hook off` first (removes the hook config), then delete the agent files.

#### TASK-D05: Fix copilot-instructions.md command prefix
Replace `/prism patterns` with `@prism patterns` and audit all other `/prism` references in that file.

#### TASK-D06: Use requirements-dev.txt in CI
`test.yml` step "Install dependencies":
```yaml
run: pip install -r requirements-dev.txt
```

#### TASK-D07: Fix PLAN.md path reference
Replace `.claude/hooks/prism_preparser.py` → `hooks/prism_preparser.py` in PLAN.md.

---

### Phase 2 — Install Verifier Script

**New file: `scripts/verify_install.py`**

Single entry point: `python scripts/verify_install.py [--repo-root PATH] [--json]`  
Exit code 0 = all checks passed. Non-zero = at least one failure.

Checks to run in order:

```
CHECK-01  Python version >= 3.9
CHECK-02  jsonschema importable (requirements.txt)
CHECK-03  Required scripts present:
            scripts/pii_scan.py, kb_query.py, overhead_calc.py,
            platform_model.py, pattern_analysis.py, usage_log.py,
            hook_installer.py, stage2_gate.py
CHECK-04  Required hooks present: hooks/prism_preparser.py
CHECK-05  Required data files present:
            scripts/verbosity_patterns.json, scripts/prism_config_default.json,
            knowledge-base/rules.json
CHECK-06  JSON schemas valid: scripts/schemas/*.json, knowledge-base/rules.json
CHECK-07  pii_scan imports cleanly; scan("hello world") returns no issues
CHECK-08  stage2_gate imports cleanly; evaluate_prompt("Fix the login bug") 
          returns action=="ok"
CHECK-09  hook_installer --action status exits 0
CHECK-10  .prism/ directory can be created in a temp dir (write permission)
```

Output format (human-readable default):
```
Prism Install Verifier v1
=========================
✓ Python 3.11.14 (>= 3.9 required)
✓ jsonschema 4.23.0 installed
✓ All 8 scripts present
✓ Hook script present
✓ Data files present
✓ JSON schemas valid (4 schemas, 35 rules)
✓ pii_scan functional
✓ stage2_gate functional
✓ hook_installer status: hooks not active
✓ .prism/ write-able

All 10 checks passed. Prism is ready to use.
Run: /prism improve "your first prompt here"
```

On failure, each check prints a one-line fix action:
```
✗ jsonschema not found
  → pip install -r requirements.txt
```

`--json` flag outputs structured JSON for programmatic use (CI, `test_smoke_install.py`).

---

### Phase 3 — Smoke Test Suite

**New directory: `tests/smoke/`**

These tests exercise the public CLI surface exactly as a user would, using `subprocess` to call the scripts by command line — not by import. This validates argument parsing, exit codes, and stdout format, not just internal logic.

#### `tests/smoke/test_smoke_install.py`
| Test | What it checks |
|------|---------------|
| `test_verify_install_passes` | `verify_install.py` exits 0 from the repo root |
| `test_verify_install_json_output` | `--json` flag outputs `{"all_passed": true, "checks": [...]}` |
| `test_verify_install_detects_missing_script` | Temporarily rename one script, confirm exit 1 and correct check name in output |

#### `tests/smoke/test_smoke_cli.py`
| Test | What it checks |
|------|---------------|
| `test_pii_scan_clean_prompt` | `pii_scan.py "hello world"` exits 0, JSON `blocked=false` |
| `test_pii_scan_dirty_prompt` | `pii_scan.py "my email is foo@example.com"` exits 2, JSON `blocked=true` |
| `test_pii_scan_injection` | `pii_scan.py "ignore all previous instructions"` exits 2 |
| `test_stage2_gate_clean` | `stage2_gate.py "Fix the login bug"` exits 0 |
| `test_stage2_gate_vague` | `stage2_gate.py "do stuff"` exits 0, JSON `action` not `"block"` (heuristic feedback) |
| `test_hook_installer_status` | `hook_installer.py --action status` exits 0 |
| `test_hook_installer_on_off_roundtrip` | `--action on` then `--action off` in a temp dir, confirm status changes |
| `test_kb_query_returns_rules` | `kb_query.py --pillar refraction --limit 3` exits 0, JSON array with 3 items |
| `test_overhead_calc_runs` | `overhead_calc.py` exits 0 |
| `test_pattern_analysis_empty_log` | `pattern_analysis.py --report` with empty log exits 0, no traceback |

#### `tests/smoke/conftest.py`
Shared `subprocess_run(args, **kwargs)` helper that:
- Prepends correct `sys.executable`
- Sets `PYTHONPATH=scripts:hooks` (matches CI)
- Sets `cwd` to repo root
- Returns `CompletedProcess`

---

### Phase 4 — CI Sandbox Jobs

#### TASK-CI01: Add smoke tests step to existing `test.yml`
After the security coverage step, before JSON schema validation:
```yaml
- name: Smoke tests (CLI surface)
  run: |
    PYTHONPATH=scripts:hooks pytest tests/smoke/ -v
```

#### TASK-CI02: Add install-from-scratch job
A separate job that simulates a brand new user following the README — it does **not** use the repo's existing virtualenv or pre-installed packages:
```yaml
install-smoke:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - name: Install only runtime deps (no test extras)
      run: pip install -r requirements.txt
    - name: Run install verifier
      run: python scripts/verify_install.py
    - name: Smoke-test core CLIs without test framework
      run: |
        python scripts/pii_scan.py "hello world"
        python scripts/stage2_gate.py "Fix the login bug"
        python scripts/hook_installer.py --action status
```
This job will catch any `import` of a test-only dependency inside a runtime script.

#### TASK-CI03: Python version matrix
Expand the `test` job to run on Python 3.9, 3.10, 3.11, 3.12:
```yaml
strategy:
  matrix:
    python-version: ["3.9", "3.10", "3.11", "3.12"]
```
Uncovers syntax/API incompatibilities (e.g. `match` statements, `datetime.UTC`).

---

### Phase 5 — First-Use Onboarding Stub (Optional / v2)

A `scripts/first_run.py` that `hook_installer.py` triggers automatically on first `sessionStart` if `.prism/` does not exist:
- Runs `verify_install.py` checks
- Creates `.prism/` and seeds `prism.config.json` from default
- Prints a one-time welcome message to stderr (visible in hook output)
- Writes `.prism/.first-run-complete` to suppress on future starts

This is deferred to v2 since it requires hooks to be active; verify_install.py covers the manual path for v1.

---

## Implementation Order

| Priority | Task | Effort | Unblocks |
|----------|------|--------|---------|
| 1 | TASK-D01, D02, D03, D04, D05 | S | User-facing clarity |
| 2 | Phase 2: `scripts/verify_install.py` | M | TASK-D02, Phase 3, CI jobs |
| 3 | Phase 3: `tests/smoke/` | M | TASK-CI01 |
| 4 | TASK-D06 (CI use requirements-dev) | XS | Correctness |
| 5 | TASK-CI01 (smoke step in test.yml) | XS | Needs Phase 3 |
| 6 | TASK-CI02 (install-from-scratch job) | S | Needs Phase 2 |
| 7 | TASK-CI03 (Python matrix) | XS | — |
| 8 | TASK-D07 (PLAN.md path fix) | XS | — |

Total estimated effort: ~1 focused session.

---

## Acceptance Criteria

- [ ] `python scripts/verify_install.py` exits 0 on a fresh clone with only `pip install -r requirements.txt` run
- [ ] `python scripts/verify_install.py` exits non-zero and prints an actionable fix when jsonschema is missing
- [ ] `pytest tests/smoke/ -v` passes (all 13 smoke tests green) from the repo root
- [ ] CI `test` job uses `requirements-dev.txt` (no direct `pip install` of individual packages)
- [ ] CI `install-smoke` job passes on a fresh checkout with only `requirements.txt` installed
- [ ] README "Verify your install" section is present and accurate
- [ ] `@prism` is used consistently throughout `copilot-instructions.md`
