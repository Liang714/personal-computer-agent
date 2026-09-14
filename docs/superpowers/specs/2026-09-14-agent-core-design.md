# Agent Core (Headless) — Design

**Date:** 2026-09-14
**Status:** Approved, pending implementation plan
**Sub-project:** 1 of 5
**Parent spec:** [`README.md`](../../../README.md)

---

## 1. Context

The project README describes a complete macOS computer-use product across 55
sections. That is a product vision, not a single implementable spec. It names at
least five independent subsystems, and §44 explicitly forbids building most of
them yet.

The work is therefore decomposed into five sub-projects, each with its own
spec → plan → implementation cycle:

1. **Agent core (headless)** — this document.
2. macOS capability layer — Accessibility, screen capture, input events, IPC.
3. Browser tools — DOM-first automation, domain policy.
4. Native UI — SwiftUI app, permission center, activity timeline.
5. Benchmark and evaluation harness — the research component.

This ordering follows the README's own Phase 0 → Phase 1 sequence and its
closing principle: *build the smallest trustworthy agent first, then increase
autonomy*.

### Scope of this sub-project

In scope: the task state machine, typed tool registry, structured action
contract, policy engine, risk engine, approval gate, verification, recovery,
budget enforcement, SQLite audit log, model gateway, and scoped filesystem
tools, driven from a CLI.

Out of scope: Swift, SwiftUI, Accessibility, screen capture, input events,
browser automation, MCP, and the shell tool. Shell is deferred deliberately —
§12 identifies it as the highest-risk surface, and it should land only after the
policy engine has been proven by a safer capability.

### Environment constraints

Established by inspection of the target machine, not assumed:

| Fact | Consequence |
|---|---|
| Xcode absent; Command Line Tools only | Swift work is impractical now. Reinforces the headless-first ordering. |
| Swift 6.4 available via SwiftPM | Sub-project 2 remains viable later without Xcode. |
| System Python is 3.9.6 / 3.9.7 (EOL) | Not used. |
| Conda env `personal-agent` has Python 3.12.13 | Target runtime. A clean isolated `.venv` is created from this interpreter. |
| No Homebrew, no pyenv, no Node | Avoid toolchains requiring them. |
| No Ollama CLI or server | Must be installed before the Qwen provider can run. Does not block the core. |
| No `ANTHROPIC_API_KEY` or equivalent in env | Reinforces: tests must not require a model. |
| 32 GB RAM, 646 GB free disk | A 14B–27B local model at 4-bit is comfortable. |

---

## 2. Decisions

### D1 — Broker-centric, event-sourced core

**Chosen.** A single `CapabilityBroker` is the only component holding both a
tool registry and an executor. Every action flows
permission → risk → approval → execute → observe → verify, and each transition
appends to an immutable SQLite event log that *is* the task state.

*Rationale:* it makes the safety property structural rather than disciplinary.
There is no expressible code path from planner output to tool execution that
skips the broker, so "did we check policy?" is answered by module structure
rather than by reviewer vigilance. It also yields §30's audit log, crash
recovery, and §32's benchmark replay from one mechanism read three ways.

**Rejected — middleware chain.** Composing policy, risk, audit and execution as
ordered middleware is flexible, but ordering *is* security: a middleware
registered in the wrong position silently disables a check with no
compile-time signal. Unacceptable for a safety-first system.

**Rejected — plan-then-execute batch.** Validating a whole plan up front and
then running it is simpler, and §28's example JSON hints at it. But §21, §22 and
§47 all require re-observation between steps and a stop on ambiguity, which a
batch plan structurally cannot do.

**Concession borrowed from the batch approach:** the planner *may* propose
multiple steps, but the broker executes strictly one at a time, re-observing
between each and discarding the remainder whenever observation diverges from
expectation.

### D2 — Pluggable model gateway; local Qwen as first real provider

Per §26, no provider is hard-coded. The `ModelProvider` protocol has two
implementations in this slice: a deterministic `ScriptedProvider` used by all
tests and CI, and an `OllamaProvider` targeting a local Qwen 3 model.

*Rationale for the scripted default:* this slice's subject matter is the policy,
risk, approval and verification layers. If tests route through a real model, a
flaky plan becomes a failing safety test and we lose the ability to distinguish
"the policy engine is broken" from "the model had an off day." CI therefore runs
with no network, no key, and no cost.

*Rationale for local Qwen:* the requirement is a free option. Local inference is
free in perpetuity with no key and no rate limit, and it is private — which
matters for an agent that will later observe the screen and mail, and matches
§27's local-first stance. Current Qwen 3 tiers advertise both tool calling and
structured output, which is the capability the planner needs.

A cloud provider (OpenRouter, which floats rate-capped free model variants) is a
cheap later addition precisely because the gateway exists. It is not built here.

### D3 — Risk is computed, never proposed

The risk engine derives a level from the *resolved tool* and its *validated
arguments* using deterministic rules. The model cannot supply, influence, or
lower a risk score.

*Rationale:* if risk were model-supplied, a prompt-injected planner could label
`filesystem.delete` as `low` and pass straight through the approval gate. That
is precisely the §18 attack, and it must be structurally impossible.

### D4 — Planner cannot reference tools

The `planner` module does not import `tools`. Its only output type is
`ActionProposal` — a tool name plus an argument mapping. It holds no callables
and no registry handle.

### D5 — `filesystem.delete` ships in slice 1

Irreversible deletion is included despite being the riskiest filesystem action,
because it is the honest test of whether the approval gate actually works. It is
classified `HIGH`, always requires approval regardless of permission setting,
and moves files to a workspace trash directory rather than unlinking them.

---

## 3. Architecture

Dependencies point strictly inward; the dangerous surfaces sit at the edges.

```text
 cli / driver              ← human entry point
      ↓
 agent/machine             ← explicit state machine (§10), owns budgets
      ↓
 broker                    ← THE chokepoint
    ↙      ↓      ↘
 policy   tools   verify        store/  (append-only event log, SQLite)
      ↓
 models/gateway            ← leaf; scripted fake + Ollama/Qwen
```

Two invariants, both enforced by an automated architecture test:

- `planner` must not import `tools` (D4).
- Nothing outside `broker` may import both a registry and an executor.

---

## 4. Components

| Module | Responsibility |
|---|---|
| `core/types.py` | Pydantic v2 domain models: `ActionProposal`, `ToolCall`, `Observation`, `ExpectedOutcome`, `VerificationResult`, `Decision`, `RiskLevel` |
| `core/provenance.py` | §18 trust lattice: `USER_INSTRUCTION` > `SYSTEM_POLICY` > `MODEL_GENERATED_PLAN` > `TOOL_OUTPUT` > `EXTERNAL_CONTENT`. Every string reaching the model carries a tag; untrusted tiers are fenced and never promoted |
| `core/errors.py` | Typed error hierarchy (see §6) |
| `tools/registry.py` | `Tool` protocol — name, version, input schema, output schema, required permission, risk class, scope. Rejects unknown tools, unknown fields, invalid arguments |
| `tools/filesystem/` | The only real capability in this slice: `list`, `stat`, `search`, `read_text`, `mkdir`, `copy`, `move`, `rename`, `delete` |
| `policy/permissions.py` | `DENIED` / `ASK` / `ALLOWED` per capability (§15) |
| `policy/paths.py` | Path normalisation, symlink resolution, traversal rejection, scope containment, size and type limits (§13) |
| `policy/risk.py` | Deterministic action → `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` (§16) |
| `broker/broker.py` | Orchestrates the pipeline; sole holder of registry + executor |
| `broker/approval.py` | `ApprovalUI` protocol and a CLI implementation showing action, target, consequence, reversibility, and why approval is required (§17). Test doubles: always-deny, always-approve, scripted |
| `verify/` | Postcondition checks against re-observed state (§21) |
| `recovery/` | Failure classification → strategy; re-observation precedes any retry (§22) |
| `agent/machine.py` | The §10 state machine |
| `agent/limits.py` | Max actions, wall-clock time, retries, model calls; cancellation token |
| `models/gateway.py` | `ModelProvider` protocol and routing |
| `models/scripted.py` | Deterministic provider for tests and CI |
| `models/ollama.py` | Local Qwen provider |
| `store/` | SQLite append-only `events` table plus derived projections (§29, §30) |
| `cli.py` | Human entry point |

---

## 5. Data flow

The event log is not a side effect of execution — it *is* the task state.
Nothing mutates task state except by appending an event.

```text
user goal ─→ UNDERSTAND ─→ OBSERVE ─→ PLAN ─→ ActionProposal
                                                    ↓
                              resolve tool + validate args (schema)
                                                    ↓
                              permission check ──────── DENIED → stop, explain
                                                    ↓
                              risk classify (rules only)
                                                    ↓
                              approval gate ────────── refused → stop
                                                    ↓
                              execute (budget-checked, cancellable)
                                                    ↓
                              re-OBSERVE  →  VERIFY vs ExpectedOutcome
                                                    ↓
                        ┌───────────────┼───────────────┐
                     SUCCESS        RECOVERABLE       AMBIGUOUS
                        ↓                ↓                ↓
                     COMPLETE        RECOVER          ASK_USER
```

Every action carries the full §46 contract: intent, tool, arguments, expected
outcome, risk, required permission, verification method, rollback strategy.

---

## 6. Error handling

Per §47, the default on ambiguity is **stop**, not guess. Concretely: a `search`
matching two files where the plan assumed one raises `AmbiguousTargetError` and
transitions to `ASK_USER`. It does not pick the newer file.

Errors form a typed hierarchy because recovery dispatches on type:

| Error | Meaning | Recovery |
|---|---|---|
| `PolicyViolation` | Capability denied by permission setting | Stop; explain |
| `ScopeViolation` | Path outside the allowed workspace | Stop; explain |
| `ApprovalRefused` | User declined | Stop; no retry |
| `VerificationFailed` | Postcondition did not hold | Re-observe, re-plan once |
| `AmbiguousTarget` | Multiple candidates matched | `ASK_USER` |
| `BudgetExhausted` | A §10 limit was hit | Stop; report consumption |
| `ToolExecutionError` | Transient or environmental failure | Classify, re-observe, bounded retry |

Retries follow a fresh observation, are capped, and are refused outright for
non-idempotent actions. All budgets are enforced in the broker, never the
planner, so an injected plan cannot raise its own limits. `Ctrl-C` sets a
cancellation token the broker checks between every step.

---

## 7. Data model

SQLite, local-first (§29). One append-only `events` table is authoritative;
everything else is a projection rebuilt from it.

```text
events        (id, task_id, seq, ts, kind, payload_json, provenance)
tasks         (id, goal, state, created_at, finished_at, outcome)     [projection]
actions       (id, task_id, tool, args_json, risk, approved, result)  [projection]
approvals     (id, task_id, action_id, prompt, decision, ts)          [projection]
model_calls   (id, task_id, provider, model, tokens_in, tokens_out)   [projection]
```

Sensitive data is minimised at write time: file *contents* are never persisted
to the log, only paths, hashes, and sizes.

---

## 8. Testing strategy

Test-driven throughout: write the test, watch it fail, then implement.

- **Unit** — path validation, permission resolution, risk classification, schema
  rejection, state-transition legality.
- **Integration** — the full broker pipeline against a `tmp_path` workspace with
  a real SQLite store.
- **Security** — the tier that matters most here. A path-traversal corpus
  (`../`, symlink escapes, `~` expansion, unicode normalisation tricks) and a
  prompt-injection corpus asserting that instructions embedded in file contents
  never become actions.
- **Architecture** — automated enforcement of both §3 import invariants.
- **End-to-end** — the CLI running §43's MVP file-management tasks against the
  scripted provider.

CI runs entirely on the scripted provider: no network, no key, no cost, fully
deterministic. The Ollama/Qwen provider is exercised by a separate opt-in
marked suite.

---

## 9. Definition of done

Per §53, this sub-project is complete when, for each capability: the
implementation and typed interface exist; unit and integration tests exist;
error cases are handled; permission requirements and risk classification are
defined; verification and recovery exist; audit logging exists; documentation
exists; and security implications are reviewed.

Plus, specific to this slice:

- The §43 MVP file-management tasks run end to end from the CLI.
- The security corpora pass.
- `filesystem.delete` cannot execute without an explicit approval, proven by test.
- Both §3 architecture import invariants are enforced by test.
