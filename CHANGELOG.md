# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **Benchmark harness (sub-project 5)** — `pca bench`: five tasks with
  deterministic fixtures, success predicates and safety invariants; metrics
  computed from the audit log. First baselines in `docs/BENCHMARK.md`.

### Fixed

- Six defects found by the benchmark, described in `docs/BENCHMARK.md`.

Sub-projects 2–4 (macOS capability layer, browser tools and the SwiftUI app)
are not yet started.

## [0.1.0] — 2026-09-14

First implemented slice: the headless agent core. No macOS integration, no
browser, no shell, no UI.

### Added

- **Capability broker** — the single chokepoint. Every action passes
  resolve → permission → risk → approval → budget → execute, in that fixed
  order, with each stage appended to the audit log before the next begins.
- **Trust lattice** — content entering a model carries the trust level of its
  origin. Untrusted tiers are fenced and can never be promoted.
- **Policy layer** — workspace path containment with traversal, symlink, tilde
  and unicode-confusable defence; capability permissions (denied/ask/allowed);
  deterministic risk classification the model cannot influence.
- **Filesystem tools** — `list`, `stat`, `search`, `read_text`, `mkdir`,
  `copy`, `move`, `delete`. Deletes move to a timestamped trash batch rather
  than unlinking, and a batch containing any bad target is refused whole.
- **Append-only event log** — SQLite, with `UPDATE` and `DELETE` blocked by
  database triggers rather than convention. The log is the task state.
- **Verification** — postconditions checked against re-read filesystem state.
  An unstated postcondition reports `ambiguous`, never `success`.
- **Recovery** — typed failure classification. Retries only follow a fresh
  observation and never apply to non-idempotent actions.
- **Model gateway** — provider-agnostic, with a deterministic scripted
  provider for CI and a local Qwen provider via Ollama.
- **State machine, budgets, CLI** — `pca run`, `pca audit`, `pca tools`.
- **Test suite** — 141 tests including a path-traversal corpus, a
  prompt-injection corpus, and automated architecture import invariants.

### Security

- A fully compromised planner cannot delete a file or read outside the
  workspace. Both are proven end to end in `tests/security/`.
- A model-supplied `risk` field rejects the entire proposal batch.
- The approval-gate test is mutation-checked: disabling the gate makes it fail.

### Known limitations

See [`docs/SECURITY.md`](docs/SECURITY.md). The trash directory is never
garbage-collected, a TOCTOU window exists between path resolution and use, and
risk escalation keys on target count alone.

[Unreleased]: https://github.com/Liang714/personal-computer-agent/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Liang714/personal-computer-agent/releases/tag/v0.1.0
