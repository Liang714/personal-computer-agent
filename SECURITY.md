# Security Policy

## Status

**This is pre-release software with no public distribution.** It is an agent
that executes actions against a local filesystem. Treat it accordingly:

- Do not point it at directories containing credentials, keys, or
  irreplaceable data.
- Run it only against a scoped workspace you are willing to lose.
- The default workspace is `~/Documents/AI-Agent/workspace`. Nothing outside
  the configured roots is reachable, by design and by test — but this software
  has not been independently audited.

## Threat model

The detailed threat model, the mitigations, and the specific test that proves
each one live in [`docs/SECURITY.md`](docs/SECURITY.md). That document also
records **known limitations**, which are real and current:

- The trash directory is never garbage-collected.
- A TOCTOU window exists between path resolution and use.
- Risk escalation keys on target count alone, not file sensitivity.
- The local model runs unsandboxed over HTTP to `localhost:11434`.

## Reporting a vulnerability

Open a private security advisory through GitHub's "Report a vulnerability"
flow on this repository. Please do not open a public issue for anything that
would let an agent escape its workspace, bypass the approval gate, or execute
an action without an audit record.

Include the smallest reproduction you can, ideally as a failing test in the
style of `tests/security/`.

## Scope

In scope: workspace escape, approval-gate bypass, risk-classification bypass,
audit-log tampering, prompt injection that results in an executed action.

Out of scope for now: anything requiring the attacker to already have local
code execution as the user running the agent, and the known limitations listed
above.
