# Contributing

## Before you write code

Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Two invariants hold the
safety argument together, and both are enforced by
`tests/test_architecture.py`:

1. `src/pca/planner/` must never import `src/pca/tools/`. The planner works
   with tool *names*; turning a name into a callable is the broker's job alone.
2. Only the broker and the CLI may hold a `ToolRegistry`.

If a change needs to break either one, that is a design discussion, not a
patch.

## The rules that are not negotiable

- **Risk is computed, never proposed.** No model output may supply, influence,
  or lower a risk level.
- **Tool output is untrusted.** Anything read from a file or a network is
  tagged `EXTERNAL_CONTENT` and fenced before it reaches a model.
- **Ambiguity stops.** When the agent cannot tell which target is meant, it
  asks. It does not pick one.
- **Nothing bypasses the broker.** Every action goes through
  resolve → permission → risk → approval → budget → execute.

## Workflow

Test-driven: write the failing test, watch it fail, then implement. A test
that has never failed has not been shown to test anything.

```bash
make check   # ruff + format + mypy + pytest; mirrors CI exactly
```

`make check` must be green before you commit. It runs the same four steps CI
runs, so a green local gate means a green CI run.

## Adding a tool

A new tool needs all of it, or it is not done:

- A `Tool` subclass with `name`, `version`, `capability`, `base_risk`, and
  strict `Input`/`Output` models (`extra="forbid"`).
- A risk classification, and an argument shape the risk engine can read.
- Unit tests including the refusal paths, not only the happy path.
- A security test if the tool touches anything outside the workspace's
  existing reach.
- An entry in `docs/SECURITY.md` if it changes the threat model.

Irreversible operations must be made reversible where possible. `filesystem.delete`
moves to a trash batch rather than unlinking; follow that precedent.

## Tests that matter

`tests/security/` is the tier that proves the claims. If you change the
policy, risk, or approval layers, mutation-check your test: break the
mitigation deliberately and confirm the test fails. A security test that
cannot fail is worse than no test, because it reports confidence it has not
earned.
