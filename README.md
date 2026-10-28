# Personal computer-use agent: safety core and benchmark

A safety-first agent core for computer use, with a benchmark that measures task success and prompt-injection resistance from the agent's own audit log.

**Status (September 2026):** the headless agent core and the benchmark harness are built and tested. The macOS layer (Accessibility, screen capture, input), browser tools and the SwiftUI app are **not built yet**. Today the agent acts on files inside a sandboxed workspace only.

## Question

Can a small local model (qwen3:14b through Ollama) carry out file tasks safely when every action it proposes must pass a fixed policy pipeline, and when untrusted file content is fenced before it reaches the model?

## How it works

The model never executes anything. It proposes structured actions, and a single broker runs each one through a fixed sequence of checks:

```text
model proposes action → resolve → permission → risk → approval → budget → execute → verify
```

- **Trust fencing.** Text from files or tools reaches the model tagged as external content. Trust levels can never be raised.
- **Workspace containment.** Paths are checked against traversal, symlinks, `~` and look-alike Unicode characters.
- **Append-only audit log.** SQLite triggers block `UPDATE` and `DELETE`. Task state, the audit trail and the benchmark all read the same log.
- **Architecture test.** The planner cannot import tools, so no code path skips the broker.

More detail is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/SECURITY.md](docs/SECURITY.md).

## Results

Five tasks (three file tasks and two with injected instructions), three repeats each, qwen3:14b at temperature 0, measured on 2026-09-14:

| Metric | Result |
|---|---|
| Task success | 15 of 15 runs (100%) |
| Unsafe actions | 0% |
| Injected payloads obeyed | 0 of 6 adversarial runs |
| Latency p50 / p90 | 4.2 s / 26.3 s |

**What these numbers support, and what they do not.** Five tasks is a small suite. The six injection trials use one attack style, written by the same person who wrote the defence, so this is a real signal but a weak one, and it does not show the agent is injection-proof. Benchmark runs turn the human approval step off, so they measure the planner alone.

Building the benchmark found six defects that the passing unit tests had missed. One example: the injected text never reached the model at all, so an early "0% injection success" was true for the wrong reason. All six are written up in [docs/BENCHMARK.md](docs/BENCHMARK.md), together with the threats to validity.

## Run it

Requires Python 3.12 or newer.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,ollama]"
pytest                                    # 203 tests (97% line coverage), no model or network needed
pca bench --model scripted --repeats 3    # control run: checks every task is correctly specified
```

To reproduce the model results, install [Ollama](https://ollama.com) and run:

```bash
ollama pull qwen3:14b
pca bench --model ollama --ollama-model qwen3:14b --repeats 3 --max-seconds 600
```

`pca run "<goal>"` runs one task and `pca audit` prints its log. CI runs lint, strict type checks, the tests and the control benchmark on every push.

## Repository layout

| Path | Contents |
|---|---|
| `src/pca/broker/` | The broker: the only place actions are executed |
| `src/pca/policy/` | Path containment, permissions and risk rules |
| `src/pca/agent/` | State machine and budgets |
| `src/pca/models/` | Model gateway: scripted provider for CI, Ollama provider |
| `src/pca/tools/` | File tools (`list`, `read_text`, `move`, `delete` to a trash folder, and more) |
| `src/pca/store/` | Append-only event log |
| `src/pca/bench/` | Benchmark tasks, fixtures, invariants and metrics |
| `tests/` | Unit, security (path traversal, prompt injection), architecture and end-to-end tests |
| `docs/DESIGN_SPEC.md` | The full design target, most of which is not built yet |

## Next steps

- Harder tasks and an injection corpus not written by the author.
- More models, to separate the effect of the policy pipeline from the effect of the model.
- The macOS capability layer and browser tools, which the benchmark already lists as uncovered.

## License

See [LICENSE](LICENSE).
