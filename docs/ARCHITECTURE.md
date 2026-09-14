# Architecture — Agent Core

Implements sub-project 1 of the plan in
[`docs/superpowers/specs/2026-09-14-agent-core-design.md`](superpowers/specs/2026-09-14-agent-core-design.md).

## Layers

```text
 cli                  pca/cli.py, pca/config.py
   ↓
 agent/machine        the §10 state machine, budgets
   ↓
 broker               THE chokepoint — the only holder of registry + executor
   ↙     ↓     ↘
 policy tools verify        store/  (append-only SQLite event log)
   ↓
 models/gateway       leaf; scripted fake + Ollama/Qwen
```

## Why a broker instead of middleware

Ordering is the security property. In a middleware chain, a component
registered in the wrong position silently disables a check and nothing fails
at compile time. The broker fixes the stage order in one readable method:
resolve → permission → risk → approval → budget → execute.

## Why the event log is the state

`store/events.py` is append-only, enforced by SQLite triggers rather than by
convention. Task state is derived by reading the log, which means the audit
trail, crash recovery, and future benchmark replay are one mechanism rather
than three.

## Why the planner cannot import tools

The planner emits `ActionProposal` values — a tool *name* plus arguments. It
holds no callables and no registry handle, so there is no expressible path
from model output to execution that skips the broker. This is enforced by
`tests/test_architecture.py`, not by convention.

## What is deliberately absent

No shell tool, no browser, no Accessibility, no network egress, and no Swift.
Those are later sub-projects. Shell in particular is deferred until the policy
engine has been proven by a safer capability.
