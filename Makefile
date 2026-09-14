PY := .venv/bin/python

.PHONY: test lint fmt fmt-check type check
test:
	$(PY) -m pytest -v
lint:
	$(PY) -m ruff check src tests
fmt:
	$(PY) -m ruff format src tests
fmt-check:
	$(PY) -m ruff format --check src tests
type:
	$(PY) -m mypy src
# Mirrors the CI job exactly, so a green `make check` means a green CI run.
check: lint fmt-check type test
