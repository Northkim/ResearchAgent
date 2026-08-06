# 0020: Interactive Codex as the default Literature Search Harness experience

- Status: Accepted
- Date: 2026-08-06

## Context

MVP-LS1 proved a complete one-round Literature Search path, but its default
launcher treated Codex as an unattended subprocess. The owner could not see
incremental reasoning, revise the bounded search plan, inspect candidate
screening, or explicitly decide when the local round was ready to finalize.
That interaction model did not satisfy the teacher-aligned role of Codex as the
user-facing research Agent Harness.

The local folder must remain authoritative for concrete research state. The
backend must continue to provide only projects, Packages, scoped capability
transport, report intake, and progress projection. Tokens and OpenAlex
credentials must not enter the Package or Codex process.

## Decision

`python reagent_local.py run .` launches the installed Codex CLI directly in
the current terminal with inherited stdin, stdout, and stderr. It supplies one
fixed initial instruction as an argument, with untrusted topic text read only
from immutable Package data. Codex exposes three mandatory owner checkpoints:

1. confirm or revise the bounded search plan before any Provider call;
2. review candidate-screening counts, themes, and inclusion/exclusion choices;
3. type `finish` before final outputs, context, and report draft are written.

The parent launcher retains the local-session bearer and executes every Proxy
operation. A versioned `memory/round-control.json` binds the project, Package,
Workflow, mode, round, confirmed plan checksum, normalized query-result
checksums, candidate/finalization confirmations, final output/context/report
draft checksums, report, and receipt. Provider transport cannot begin until a
valid `PLAN_CONFIRMED` state exists. A zero Codex exit is insufficient:
completion requires valid artifacts and a valid `FINALIZED` control state.

`--auto` preserves the MVP-LS1 unattended path for explicit batch execution,
deterministic tests, and demos. Interactive and auto paths converge at the same
validation, report-chain, upload, receipt/projection, and session-revocation
boundary.

Signals are forwarded to the Codex child, followed by bounded graceful and
forced cleanup. The session is revoked in a cleanup path, no incomplete report
is uploaded, valid local files are preserved, and the control records a
value-safe interruption. A subsequent command performs upload-only recovery
for a completed report, refuses to repeat a verified round, or requires an
explicit `--resume` or confirmed `--restart-round` for partial work.

## Consequences

The default owner experience is visible and conversational while retaining one
bounded round and deterministic artifact gates. Codex is still a local external
Harness; it is not embedded in Next.js, invoked by FastAPI, or granted direct
credentials. No WebSocket, browser PTY, Hosted Runtime, cloud LLM, Provider,
Progress schema, or database migration is added.

Interactive execution requires a real terminal and a supported authenticated
Codex CLI. Non-interactive environments must choose `--auto`. A real OpenAlex
Literature Search still requires separate owner authorization and an explicitly
enabled server-side adapter.

## Alternatives considered

- Keeping unattended execution as the default was rejected because it hides
  research decisions and prevents owner revision.
- Scraping Codex prose for checkpoint or completion text was rejected because
  it is ambiguous and unsafe; declared artifacts are authoritative.
- Passing the bearer to Codex was rejected because the parent can perform
  scoped transport without expanding the child credential boundary.
- A browser terminal, WebSocket bridge, or backend Codex runner was rejected
  because it would add infrastructure and violate the local-Harness boundary.
- Maintaining separate interactive output contracts was rejected because both
  modes must produce identical durable research and Progress artifacts.
