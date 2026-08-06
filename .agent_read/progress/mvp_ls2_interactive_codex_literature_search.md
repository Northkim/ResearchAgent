# MVP-LS2 Interactive Codex Literature Search

Date: 2026-08-06

Status: **PASS_WITH_WARNINGS — READY FOR OWNER ACCEPTANCE**

## Authority and excluded run

MVP-LS2 used clean `main` at exact baseline
`33bc1d367f7f740a211f127ab0614b7bfa87039a`. Accepted MVP-LS1 Provider,
output, upload, recovery, and cloud/local boundaries are preserved.

```text
CURRENT_DEMO_RUN = ABORTED
CURRENT_DEMO_OUTPUTS = NOT_ACCEPTANCE_EVIDENCE
CURRENT_DEMO_REPORT_UPLOAD = NOT_AUTHORIZED
CURRENT_DEMO_RUN_EXCLUDED = PASS
MVP_LS1_TECHNICAL_AUTOMATION = PRESERVED
```

No artifact from that aborted owner Demo was reused or uploaded.

## Implementation

Accepted ADR 0020 makes interactive Codex the default. The generated launcher
shows six stage labels, preflights a supported/login-ready CLI, prints safe
bounds, and invokes top-level Codex in the current terminal with inherited
stdin/stdout/stderr. A fixed instruction requires the owner-confirmed search
plan, candidate review, and explicit `finish` before final writing. Topic data
is read from immutable Package input and is not concatenated into shell syntax.

The parent launcher retains all credentials and transport. It watches the
manifest-declared, versioned round-control artifact and issues Proxy requests
only after a checksum-bound plan confirmation. Completion requires confirmed
candidate review/finalization, one normalized result per confirmed query, four
valid output checksums, valid context/report draft, exactly one report, valid
chain, and no pre-existing receipt. Codex exit alone never succeeds.

`--auto` preserves the LS1 unattended path. Interactive and auto converge at
the same validator/finalizer/uploader. `Ctrl+C` and termination signals reap the
child, revoke the session, mark a safe interruption, preserve valid files, and
upload nothing. `--resume`, confirmed `--restart-round`, upload-only retry, and
verified-receipt no-repeat cover every declared next-run state.

Frontend Quick Start, Package, Progress, project Guide, and local Guide now
describe the current-terminal checkpoints, explicit finalization, auto as an
advanced mode, interruption, resume/restart, upload recovery, and safe errors.

## Qualification

Focused Package/local-project tests passed 77, and the broader Package/session/
project/Progress/Proxy focused matrix passed 351. The isolated PostgreSQL
matrix passed 21 with zero relevant skip. Full backend passed 587 with four
unrelated gated skips; compileall passed. Frontend typecheck, Vitest, ESLint,
production build, and the two-case Playwright interactive/auto Literature
Search E2E passed. Migration head/current/check remained `20260806_0007`.

The real stack used PostgreSQL 18.1, Uvicorn, Next.js, Chromium, an external
Package, fake Proxy, and a PTY Codex fixture. It proved no search before plan
confirmation, no final output before `finish`, automatic upload after valid
completion, browser-visible summary/history, restart continuity, and the same
contracts under explicit auto mode. A cancellation exercise proved one revoked
session, zero upload/Proxy operation, and no orphan process; resume preserved
the plan and completed the same round.

The installed Codex CLI version/login/help path was smoke-checked without a
model invocation. Zero OpenAlex, OpenAI model, or external research request was
made. Hosted/Runtime/LLM activity remained zero.

## State

```text
MVP_LS2_IMPLEMENTATION = PASS_WITH_WARNINGS
DEFAULT_INTERACTIVE_MODE = PASS
AUTO_MODE_PRESERVED = PASS
VISIBLE_CODEX_OUTPUT = PASS
INTERACTIVE_CODEX_INPUT = PASS
SEARCH_PLAN_CONFIRMATION = PASS
CANDIDATE_REVIEW_INTERACTION = PASS
EXPLICIT_ROUND_FINALIZATION = PASS
MACHINE_VERIFIABLE_COMPLETION = PASS
INTERRUPT_SESSION_CLEANUP = PASS
PARTIAL_ROUND_RECOVERY = PASS
AUTOMATIC_PROGRESS_UPLOAD = PASS
UPLOAD_ONLY_RETRY = PASS
PROJECT_INTERACTIVE_GUIDANCE = PASS
PACKAGE_INTERACTIVE_GUIDANCE = PASS
MVP_RUNTIME_HOSTED_BOUNDARY = PASS
MVP_LS2_INTERACTIVE_UX = READY_FOR_OWNER_ACCEPTANCE
LITERATURE_SEARCH_AUTONOMOUS_WORKFLOW = READY_FOR_OWNER_ACCEPTANCE
V0_1_STATE = OWNER_ACCEPTANCE_PENDING
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

Remaining warnings: no authorized live OpenAlex end-to-end round; no model was
invoked in the installed-Codex smoke; metadata/abstract-only evidence; OpenAlex
default-off; Claude Code untested; only round 1/Literature Search; local
single-user scope only. Wait for owner review.
