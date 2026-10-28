# Psyche: one name for each command the project runs.
#
# Every target wraps a plain command that the README lists beside it, so a reader without
# make (on Windows, for one) runs the same thing by hand. Each recipe uses python3 from PATH
# and stops at the first command that fails. GNU make is enough, 3.81 (the version macOS
# ships) included.
#
# `make` or `make help` lists the targets. The set is fixed: tools/publish/test_core.py checks
# it, recipe by recipe, so a new or renamed target is changed together with that test.

.DEFAULT_GOAL := help

.PHONY: help setup test check capture site

help:
	@echo "Psyche make targets (the README lists the plain command behind each one):"
	@echo ""
	@echo "  make help     list these targets"
	@echo "  make setup    install the CPython versions the suites sweep, with uv"
	@echo "  make test     run the substrate's suites on the interpreters found on PATH"
	@echo "  make check    run the commit gate, the plan and diagram checks and the tool suites"
	@echo "  make capture  maintainers: sweep every interpreter, rewrite docs/TEST_OUTPUT.txt and the ledger"
	@echo "  make site     serve the docs site locally from the last commit (npm ci, then npm run dev)"

setup:
	bash tools/setup_python.sh

test:
	python3 run_tests.py

check:
	python3 tools/ledger_check.py --only C1,C3,C4,C5,C6
	python3 tools/publish/ci_c2.py
	python3 tools/publish/check_copy.py
	python3 tools/publish/render_plan.py --check
	python3 tools/publish/diagrams.py --check
	python3 tools/test_ledger.py
	python3 -B tools/publish/test_core.py
	python3 -B tools/publish/test_checks.py

capture:
	python3 tools/capture_run.py

site:
	cd website && npm ci
	cd website && npm run dev
