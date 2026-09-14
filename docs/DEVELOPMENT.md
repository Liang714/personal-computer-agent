# Development

## Setup

```bash
python3.12 -m venv .venv          # any CPython 3.12 interpreter will do
.venv/bin/python -m pip install -e ".[dev,ollama]"
```

Python 3.12 or newer is required. On macOS the system Python is 3.9 and will
not work; use Homebrew, pyenv, python.org, or a conda environment that
provides 3.12. Verify with `.venv/bin/python --version` before continuing.

## Everyday commands

```bash
make check   # ruff + mypy + pytest — run this before every commit
make test    # tests only
make fmt     # apply formatting
```

## Optional: a real model

```bash
# install Ollama from https://ollama.com/download, then:
ollama pull qwen3:14b
.venv/bin/pytest -m ollama -v
```

CI never runs model-backed tests. The default suite uses a deterministic
scripted provider, so a failing safety test always means the safety layer
broke rather than that the model varied.

## Trying it

```bash
.venv/bin/pca tools
.venv/bin/pca run "organise my workspace"
.venv/bin/pca audit <task_id>
```
