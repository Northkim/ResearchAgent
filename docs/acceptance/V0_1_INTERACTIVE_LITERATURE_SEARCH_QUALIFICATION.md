# V0.1 Interactive Literature Search Qualification

Date: 2026-08-06

Status: **PASS_WITH_WARNINGS — READY FOR OWNER ACCEPTANCE**

## Baseline and excluded evidence

MVP-LS2 began from clean `main` at exact commit
`33bc1d367f7f740a211f127ab0614b7bfa87039a`
(`MVP-LS1: complete autonomous literature search workflow`).

```text
CURRENT_DEMO_RUN = ABORTED
CURRENT_DEMO_OUTPUTS = NOT_ACCEPTANCE_EVIDENCE
CURRENT_DEMO_REPORT_UPLOAD = NOT_AUTHORIZED
CURRENT_DEMO_RUN_EXCLUDED = PASS
MVP_LS1_TECHNICAL_AUTOMATION = PRESERVED
```

The manually aborted owner Demo was not opened, imported, uploaded, or counted.
All qualification used newly generated fictional Packages and deterministic
fixtures.

## Default command and checkpoints

The supported command matrix is:

```text
python reagent_local.py run .                     interactive normal/OpenAlex
python reagent_local.py run . --mode demo         interactive fictional demo
python reagent_local.py run . --auto              unattended normal/OpenAlex
python reagent_local.py run . --mode demo --auto  unattended fictional demo
```

The default path prints six launcher stages and safe project/topic, mode,
Provider, bounds, evidence limitation, workspace, and interruption guidance.
It preflights the installed Codex CLI, then executes top-level Codex with the
Package as its working directory and inherited stdin/stdout/stderr. The fixed
instruction is passed as data and directs Codex to read Package files rather
than interpolating the topic into shell syntax.

Codex must record a valid confirmed plan before the launcher sends any query.
The owner then reviews bounded candidate counts/themes and may revise screening
or request one additional query within the three-call budget. Final candidate,
selection, report, context, and report-draft files are prohibited until the
owner explicitly types `finish`.

## Machine-verifiable completion and transport boundary

The new manifest-declared `literature-search-round-control/v0.1` artifact binds
the exact identity and round, mode/execution style, plan confirmation and
checksum, one normalized result/checksum per confirmed query, candidate review,
finalization, all four output checksums, context/report-draft checksums, final
report, and receipt. The Package validator checks state-specific semantics.
Codex exit status is retained, but a zero exit with missing or inconsistent
artifacts fails closed.

The local session token remains only in launcher memory. Secret-bearing
environment variables are removed from the Codex child, and the token is never
in the Package, process arguments, logs, output, or report. The launcher alone
uses the Proxy and upload APIs. Normal mode remains OpenAlex-only with no fake
fallback; demo remains explicitly fictional.

## Interruption and recovery

`Ctrl+C`, SIGTERM, and SIGHUP enter one bounded cleanup path: signal the child,
wait briefly, terminate/kill if necessary, reap it, record a safe interruption,
revoke the local session, and upload nothing. Valid local files remain.

An untouched Package starts round 1. A partial/interrupted Package requires
`--resume` or confirmed `--restart-round`; restart deletes only declared
round-scoped mutable artifacts. A valid report without a receipt performs
upload-only idempotent recovery and never reruns Codex or search. A verified
receipt prevents repetition. Interactive and `--auto` use the same output,
report, receipt, and projection validation.

## Frontend and terminal experience

Project Quick Start now explains eight steps from Package generation through
terminal checkpoints, `finish`, upload, and browser result. Package and Guide
pages identify the default command as an interactive current-terminal session,
show demo and advanced auto commands separately, and document interruption,
resume, restart, upload-only recovery, and missing CLI/login/terminal failures.
Progress text states that upload follows explicit finalization and that the
full research artifacts remain local.

Stage-specific errors distinguish Codex absence/login/version/TTY, backend or
Provider availability, session denial/expiry, child exit, completion
validation, and upload failures without printing credentials or sensitive
URLs.

## Real-stack qualification

A fresh loopback PostgreSQL 18.1 cluster at sole/current Alembic revision
`20260806_0007`, real Uvicorn, real Next.js, Chromium, an external Package,
fake Proxy, and a deterministic PTY Codex fixture exercised:

```text
create project
-> generate/download/extract Package
-> run default interactive demo command
-> confirm plan before two fake searches
-> review candidate screening
-> type finish
-> validate four outputs and control bindings
-> upload and verify one report/receipt/projection
-> browser displays completed result/history
```

The PTY driver asserted that no normalized Provider result existed before plan
confirmation and no final output existed before `finish`. A separate explicit
auto-demo E2E passed the same artifact/upload contract. Physical PostgreSQL,
Uvicorn, and Next.js restart retained project/projection/history. A dedicated
interrupt exercise left zero report, zero receipt, zero Proxy operation, zero
active token, and no orphan fixture process; explicit resume then completed the
same round. Aggregate canaries retained zero Provider HTTP call/cost and zero
Hosted WorkflowRun, StepRun, AgentSession, ExecutionEvent, Checkpoint, or
MemoryRevision activity.

The installed `codex-cli 0.146.0` was checked locally for supported invocation,
login state, and help without starting a model session. No live OpenAlex or
OpenAI model call occurred.

## Regression evidence

- Workflow Package and local-project focused subset: 77 passed;
- broader Package/session/project/Progress/Proxy focused matrix: 351 passed;
- relevant isolated PostgreSQL tests: 21 passed, zero relevant skip;
- full backend: 587 passed, 4 unrelated gated skips;
- compileall: passed;
- frontend typecheck, Vitest, ESLint, and production build: passed;
- interactive and auto Literature Search Playwright E2E: 2 passed;
- Alembic sole/current/no-drift at `20260806_0007`: passed.

The four full-backend skips are pre-existing explicitly gated destructive/live
integration suites and do not omit Package, local-session, Progress, Proxy, or
PostgreSQL coverage.

## State and warnings

```text
MVP_LS2_IMPLEMENTATION = PASS_WITH_WARNINGS
CURRENT_DEMO_RUN_EXCLUDED = PASS
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

Warnings: no owner-authorized real OpenAlex end-to-end round was run; the
installed Codex CLI was not asked to invoke a model; OpenAlex remains
experimental/default-off; evidence remains metadata/abstract-only; Claude Code
is untested; only Literature Search round 1 exists; V0.1 is local/single-user
and not public or production deployment.

This phase does not perform final owner acceptance.
