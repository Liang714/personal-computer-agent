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

## Running the benchmark

```bash
pca bench --model scripted                      # control suite; no model needed
pca bench --model ollama --repeats 3            # against the configured model
pca bench --model ollama --ollama-model qwen3:30b-a3b   # a different model
pca bench --model ollama --json run.json        # machine-readable output
pca bench --model ollama --baseline run.json    # delta table against an earlier run
```

Exit codes: `0` clean, `2` at least one safety violation. CI runs the control
suite on every push, so a task whose success predicate or invariants break is
caught immediately.

### Interpreting a run

- Start with the **control** suite. If a control run fails, the task is broken,
  not the model. Fix the task first.
- `safety_violation` outranks everything. A run that achieved its goal while
  tripping an invariant is a failure, not a success.
- `injection_success_rate` only means something when the adversarial tasks'
  **benign** half also succeeded. A model that crashes before acting scores a
  perfect rate for doing nothing; the suite guards against that, but read the
  per-task verdicts before quoting the number.
- Benchmark runs use `AlwaysApprove` deliberately, so the approval gate is
  stood down and the metric reflects the planner alone. See
  [`BENCHMARK.md`](BENCHMARK.md).

### Adding a task

A task needs a goal, a deterministic fixture, a success predicate, an oracle
plan, and safety invariants. The oracle is not optional: it is what proves the
task is satisfiable, and `tests/bench/test_suite.py` asserts every control run
passes.

State what must **not** happen, not only what must. A task without invariants
cannot distinguish "did the job" from "did the job by deleting something else".
