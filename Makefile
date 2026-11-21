# One-command checks for the plugin's scripts. `make test` is what CI runs.
PY ?= python3
REDLINE := fairness-opinion-legal/scripts/redline

.PHONY: test quick fuzz-deep golden-update deps
test:            ## everything: unit, golden snapshots, fuzz (fixed seed), malformed-input matrix
	$(PY) -m pytest
quick:           ## unit + golden only, a few seconds
	HYPOTHESIS_PROFILE=dev $(PY) -m pytest -m "not fuzz"
fuzz-deep:       ## long randomized property run (new seed each time); any failure prints a reproducible example
	HYPOTHESIS_PROFILE=deep $(PY) -m pytest -m fuzz -x
golden-update:   ## rewrite tests/golden/expected from the current code; review the diff in git before committing
	$(PY) -m pytest tests/golden --update-goldens -q
deps:            ## test dependencies, and the Word renderer's npm package so the .docx checks run
	$(PY) -m pip install -r requirements-dev.txt
	cd $(REDLINE) && npm ci --silent --no-audit --no-fund
