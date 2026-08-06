# V0.1 Literature Search Workflow Qualification

Date: 2026-08-06

Status: **PASS_WITH_WARNINGS — READY FOR OWNER ACCEPTANCE**

> Historical MVP-LS1 qualification. MVP-LS2 preserves these output, session,
> upload, recovery, and product-boundary results while replacing the default
> opaque/unattended Codex experience with an interactive terminal session.
> See `V0_1_INTERACTIVE_LITERATURE_SEARCH_QUALIFICATION.md`.

## Baseline and excluded evidence

MVP-LS1 began from clean `main` at exact commit
`9d76c7b89ce124829fd76741a676d7bb50a4eb43`
(`MVP-I1: load local dotenv configuration on startup`).

```text
CURRENT_OWNER_TEST = ABORTED
CURRENT_ABORTED_REPORT_UPLOAD = NOT_AUTHORIZED
ABORTED_OWNER_TEST_EXCLUDED = PASS
```

The previous external fictional Package and its report were not uploaded,
reused, imported, inspected as results, or treated as acceptance evidence.
At phase entry the governing transition was recorded as
`LITERATURE_SEARCH_AUTONOMOUS_WORKFLOW = IMPLEMENTATION_IN_PROGRESS` and
`V0_1_STATE = NOT_READY`; only the qualification below advances those states
to owner-review readiness.

## Qualified one-round contract

The generated Package contains one supported command:

```bash
python reagent_local.py run .
```

The launcher validates the immutable Package, identifies its exact project and
Workflow, obtains a bounded local session, invokes Codex for a planning stage,
issues the Codex-derived queries through the provider-neutral Proxy, invokes
Codex for screening/synthesis, validates the four outputs and report chain,
uploads the one existing report idempotently, verifies receipt/history/
projection, stores the safe receipt under the declared local path, revokes the
session, and stops after round 1.

Normal mode requires the explicitly enabled OpenAlex adapter. It has no fake
fallback. Explicit `--mode demo` uses only the deterministic fake adapter and
requires fictional labels throughout. The search policy permits two or three
query variants, at most three Provider calls, five results per call, 15 retained
candidates, and a target of three to six selected papers. Exact OpenAlex ID and
DOI deduplication preserves Provider/query/author order and retains provenance
checksums and exclusion reasons. Insufficient evidence produces an honest
incomplete result.

The four required outputs and their semantic contracts were validated:

- `outputs/search_plan.md`: topic, concepts/synonyms, queries, bounds,
  screening, and limitations;
- `outputs/candidate_papers.json`: stable/provider identities, metadata,
  available abstract, source query, provenance, and deduplication;
- `outputs/selected_papers.json`: inclusions and reasons, exclusions/summary,
  and evidence availability without fabricated precision;
- `outputs/literature_search_report.md`: summary, coverage, themes, methods,
  representative works, trends, limits, gaps, next action, and references.

Metadata/abstract-only limitations are mandatory. Full-text reading is neither
performed nor claimed.

## Local session and cloud boundary

Accepted ADR 0019 defines a 15-minute, literal-loopback, exact-project/Package/
Workflow/adapter session. It grants only `paper.search/v0.1`,
`progress.upload/v0.2`, and `progress.read/v0.1` as needed. Normal and demo
sessions allow at most three search operations. Upload-only sessions have zero
search allowance. Active/unexpired/unrevoked bearer and exact scope are checked
for every upload/read. Cross-project and changed-Package access fail closed.

Token plaintext stays in launcher memory, is removed from the Codex subprocess
environment, is never included in the ZIP, and is revoked at completion.
OpenAlex credentials remain server-side. The backend and frontend never invoke
Codex, an LLM, AgentRuntime, ExecutionDispatcher, or Hosted Workflow execution.

The full candidate library, full literature report, issued query text, and
concrete context stay local. The unchanged native Progress Report v0.2 contract
uploads a bounded round/status, counts, concise summary, evidence limitation,
artifact names/checksums, warnings, and next action.

## Upload recovery

An untouched Package starts round 1. A valid report without a local receipt
causes upload-only recovery; the search and Codex stages are not rerun. If the
server accepted the report but local receipt storage was interrupted, the
retry receives the idempotent existing receipt and verifies history/projection.
A verified receipt prevents a repeated round. Partial outputs without a valid
report fail closed without overwrite. Tests cover interruption before upload,
an upload failure, server persistence before receipt storage, and stable retry.

## Frontend qualification

The project overview now presents Start here, current step, primary action,
four-step Quick Start, expected outputs, latest summary, and technical details
below the product actions. Project creation redirects directly to that page.
The dedicated project Guide documents the command, normal/demo modes, files,
upload recovery, privacy, and errors.

The Package page prioritizes generate/download, extraction, the copyable launch
command, expected outputs, credentials boundary, and return to Progress.
Technical IDs/checksums remain available but are secondary. Validation ignores
only bounded `.DS_Store` metadata, not arbitrary undeclared files.

The Progress page presents the six requested lifecycle labels, a completed
summary, query/candidate/selection counts, evidence limitation, artifact names
and checksums, warnings/errors, next action, immutable report history, and
upload receipt. It states that complete research artifacts remain local.

## Deterministic real-stack qualification

A fresh isolated PostgreSQL 18.1 cluster used distinct test and product
databases on loopback. Sole/current Alembic revision was
`20260806_0007`, drift check passed, and downgrade to `20260805_0006` followed
by re-upgrade passed.

Real Uvicorn, Next.js, PostgreSQL, browser HTTP, and an external extracted
Package exercised:

```text
create project
-> generate/download/extract Package
-> open exact local session
-> run one deterministic fake Codex-equivalent round
-> execute two fake Proxy searches
-> create four outputs and one report
-> automatic upload and projection verification
-> browser displays COMPLETED summary and receipt history
-> repeat command reports already uploaded
```

No API response was mocked. The only research values were wholly fictional and
explicitly labelled. External HTTP/DNS paths were denied and OpenAlex was
disabled. The E2E was rerun after the final installed-Codex CLI compatibility
correction. Final aggregate SQL therefore recorded two independent local
projects, reports, projections and revoked tokens, four fake Proxy operations,
zero Provider call/cost, and zero WorkflowRun, StepRun, ExecutionEvent, Hosted
ProviderOperation, or AgentSession rows. Each Package produced one report and
its repeat command produced no second operation or report. Restart qualification
against the same PostgreSQL data retained the project, round-1 completed
projection, report history, and receipt.

## Regression evidence

- focused Package/session/project/Proxy/Progress matrix: 323 passed;
- full backend with isolated PostgreSQL: 575 passed, 4 skipped;
- all relevant local project, Package, Progress, Proxy, OpenAlex, and
  PostgreSQL tests executed with zero relevant skip;
- compileall: passed;
- frontend typecheck: passed;
- Vitest: 10 files / 13 tests passed;
- ESLint: passed;
- production build: passed;
- real-stack Playwright Literature Search E2E: 1 passed;
- Alembic sole/current/no-drift and downgrade/re-upgrade: passed.

The four full-backend skips are pre-existing separately gated destructive/live
integration suites; none is required local-session or PostgreSQL coverage. The
production build required permission for Turbopack's local helper socket in the
execution sandbox and then passed unchanged.

## Security and product boundary

This phase made zero live OpenAlex calls, read no OpenAlex key, and did not use
the aborted owner artifact. Runtime and SQL canaries showed zero AgentRuntime,
ExecutionDispatcher, Hosted Workflow/ProviderOperation, LLM, structured
generation, Judge/evaluation, cloud synthesis, automatic second round, or
server mutation of concrete local research state.

The prior R3C composite acceptance remains authoritative for the accepted
OpenAlex adapter itself. This phase qualifies the normal path statically and
with scripted transport, but a complete real OpenAlex LS1 round was not
authorized or performed.

```text
MVP_LS1_IMPLEMENTATION = PASS_WITH_WARNINGS
ABORTED_OWNER_TEST_EXCLUDED = PASS
LITERATURE_SEARCH_REAL_PROVIDER_PATH = PASS
LITERATURE_SEARCH_NO_FAKE_FALLBACK = PASS
LITERATURE_SEARCH_OUTPUTS = PASS
ONE_COMMAND_LOCAL_EXECUTION = PASS
LOCAL_SESSION_SECURITY = PASS
CODEX_ONE_ROUND_AUTOMATION = PASS
AUTOMATIC_PROGRESS_UPLOAD = PASS
UPLOAD_ONLY_RETRY = PASS
PROJECT_QUICK_START_UI = PASS
PROJECT_GUIDE_PAGE = PASS
PACKAGE_PAGE_UX = PASS
PROGRESS_RESULT_UX = PASS
MVP_RUNTIME_HOSTED_BOUNDARY = PASS
LITERATURE_SEARCH_AUTONOMOUS_WORKFLOW = READY_FOR_OWNER_ACCEPTANCE
V0_1_STATE = OWNER_ACCEPTANCE_PENDING
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

## Remaining warnings

- No owner-authorized real OpenAlex end-to-end LS1 round was performed on this
  implementation; prior experimental R3C evidence covers the adapter only.
- OpenAlex is experimental and disabled by default; Provider behavior and cost
  may change.
- Evidence is metadata/abstract-only and may be incomplete.
- Claude Code is untested; Codex CLI is the supported Harness.
- Only Literature Search round 1 is implemented.
- V0.1 remains localhost-only and single-user; public/production deployment and
  production security are not authorized.

This qualification does not perform final owner acceptance. Wait for owner
review.
