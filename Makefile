PY := .venv/bin/python

.PHONY: test lint fmt type check
test:
	$(PY) -m pytest -v
lint:
	$(PY) -m ruff check src tests
fmt:
	$(PY) -m ruff format src tests
type:
	$(PY) -m mypy src
check: lint type test
