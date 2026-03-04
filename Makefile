# Prism — local dev commands that mirror CI exactly.
# Run `make help` to list targets.

PYTHON     ?= python
PYTHONPATH  = scripts:hooks
export PYTHONPATH

.PHONY: help test test-cov test-security test-smoke test-all ci restore-samples help

help:
	@echo "Prism make targets"
	@echo "  make test              Unit + integration tests (no coverage gate)"
	@echo "  make test-cov          Unit + integration with 80% coverage gate (mirrors CI job 1)"
	@echo "  make test-security     pii_scan + prism_preparser at 100% coverage (mirrors CI job 1b)"
	@echo "  make test-smoke        Smoke / CLI tests (mirrors CI job 2)"
	@echo "  make test-all          All of the above in sequence"
	@echo "  make ci                Full CI simulation (test-cov + test-security + test-smoke)"
	@echo "  make restore-samples   Reset sample_data/*.md to their broken template state"

# ── Mirrors CI job 1: unit + integration, 80% overall ────────────────────────
test-cov:
	$(PYTHON) -m pytest tests/ --ignore=tests/smoke \
	  --cov=scripts --cov=hooks \
	  --cov-report=term-missing \
	  --cov-fail-under=80

# ── Mirrors CI job 1b: security-critical 100% gate ───────────────────────────
test-security:
	$(PYTHON) -m pytest tests/unit/test_pii_scan.py tests/integration/test_hook_preparser.py \
	  --cov=pii_scan --cov=prism_preparser \
	  --cov-report=term-missing \
	  --cov-fail-under=100

# ── Mirrors CI job 2: smoke / CLI surface tests ───────────────────────────────
test-smoke:
	$(PYTHON) -m pytest tests/smoke/ -v

# ── Fast local run (no coverage overhead) ────────────────────────────────────
test:
	$(PYTHON) -m pytest tests/ -q

# ── Full CI simulation ────────────────────────────────────────────────────────
ci: test-cov test-security test-smoke
	@echo ""
	@echo "All CI checks passed locally."

# ── Everything ───────────────────────────────────────────────────────────────
test-all: test-cov test-security test-smoke

# ── Sample data ───────────────────────────────────────────────────────────────
# Working copies in sample_data/*.md are gitignored so that running
# `/prism improve` on them never pollutes git history.
# Run this target to reset them to their broken template state before a demo
# or before adding a new test scenario.
restore-samples:
	$(PYTHON) scripts/restore_samples.py
