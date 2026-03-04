# Prism — local dev commands that mirror CI exactly.
# Run `make help` to list targets.

PYTHON     ?= python
PYTHONPATH  = scripts:hooks
export PYTHONPATH

.PHONY: help test test-cov test-security test-smoke test-all ci help

help:
	@echo "Prism make targets"
	@echo "  make test           Unit + integration tests (no coverage gate)"
	@echo "  make test-cov       Unit + integration with 80% coverage gate (mirrors CI job 1)"
	@echo "  make test-security  pii_scan + prism_preparser at 100% coverage (mirrors CI job 1b)"
	@echo "  make test-smoke     Smoke / CLI tests (mirrors CI job 2)"
	@echo "  make test-all       All of the above in sequence"
	@echo "  make ci             Full CI simulation (test-cov + test-security + test-smoke)"

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
