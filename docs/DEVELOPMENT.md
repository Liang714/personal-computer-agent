# Development

## Setup

```bash
/opt/anaconda3/envs/personal-agent/bin/python -m venv .venv
.venv/bin/python -m pip install -e ".[dev,ollama]"
```

Python 3.12 is required. The system Python (3.9) is not supported.

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
