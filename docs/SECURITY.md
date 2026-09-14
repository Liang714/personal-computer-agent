# Security Model — Agent Core

## Threat model for this slice

| Threat | Mitigation | Proven by |
|---|---|---|
| Prompt injection via file contents | All tool output is tagged `EXTERNAL_CONTENT` and fenced before reaching a model | `tests/security/test_prompt_injection.py` |
| A compromised planner proposing a destructive action | Planner cannot import tools; every action passes the broker; HIGH risk always asks | `test_an_injected_plan_still_hits_the_approval_gate` |
| A model lowering its own risk score | Risk is computed from the resolved tool; a `risk` key in model output rejects the whole batch | `test_a_model_cannot_lower_its_own_risk` |
| Path traversal / symlink escape | `Workspace.resolve` normalises, expands, resolves symlinks, then enforces containment | `tests/security/test_path_traversal.py` (11 attack strings + symlink farm) |
| Runaway execution | Budgets on actions, wall clock, retries and model calls, enforced in the broker | `tests/agent/test_limits.py` |
| Audit tampering | `UPDATE` and `DELETE` on `events` abort via SQLite triggers | `tests/store/test_events.py` |
| Irreversible deletion | `filesystem.delete` moves to a trash batch; never unlinks | `tests/tools/test_filesystem_delete.py` |

The approval-gate test has been mutation-checked: replacing `AlwaysDeny` with
`AlwaysApprove` makes it fail. It verifies the gate rather than asserting it.

## Known limitations

- The trash directory is never garbage-collected. Deleted files accumulate.
- `Workspace` trusts the filesystem between `resolve` and use; a TOCTOU race is
  possible in principle. Not mitigated in this slice.
- The local model runs unsandboxed in-process via HTTP to `localhost:11434`.
- Risk escalation is currently driven by target count alone. It does not yet
  consider file sensitivity, size, or location within the workspace.

## Reporting

This is pre-release software with no public distribution. Do not run it against
directories containing credentials or irreplaceable data.
