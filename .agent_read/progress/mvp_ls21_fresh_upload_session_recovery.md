# MVP-LS2.1 Fresh Upload Session Recovery

Date: 2026-08-06

Status: **PASS_WITH_WARNINGS — OWNER ACCEPTANCE PENDING**

## Evidence boundary

The owner-observed demo is excluded. Its local Package, outputs, report, and
failed request were not opened, imported, retried, uploaded, or committed. The
only retained fact is that local interactive/finalization gates passed and a
following automatic request returned HTTP 401. The exact upload, history, or
projection substage and application code were not preserved.

## Implementation

Accepted ADR 0021 separates the 15-minute search session from a new two-minute
upload-only session. Search scopes now have no Progress capabilities. A fresh
upload session is created only after local report-chain validation and is bound
to exact project/Package/Workflow, round, report ID, and report-content
checksum. Its neutral capability admits zero search operation, Provider call,
or Provider cost and is absent from the Codex environment, Package, report,
arguments, logs, and frontend.

First upload and pending-upload recovery use the same routine. Exact envelope
bytes are retained across one safe expiry/unknown-outcome refresh. Unsafe or
unclassified 401s fail closed. Response-loss replay returns the existing
receipt, with stable report/projection counts. Search and upload cleanup are
reported separately and cannot mask the primary exception.

The no-report Progress page now says **No Progress Report received**, explains
that the cloud cannot inspect local state, and directs the owner to rerun the
same Package rather than download a new one.

## Qualification

- focused Package/session/project/Progress/Proxy matrix: 307 passed;
- full backend with isolated PostgreSQL: 597 passed, 4 unrelated gated skips;
- compileall: passed;
- frontend typecheck, 14 Vitest tests, ESLint, and production build: passed;
- real Chromium interactive and auto demo E2E: 2 passed;
- sole/current Alembic head `20260806_0007`, no drift;
- real PostgreSQL/Uvicorn aged-search simulation: fresh upload passed;
- simulated persisted-response/local-receipt loss: exact replay restored the
  receipt with one report and one projection;
- physical PostgreSQL/Uvicorn/frontend restart: API and browser continuity
  passed;
- active qualification tokens, live OpenAlex calls, Hosted/Runtime/LLM calls:
  zero at cleanup.

The four skips require separately gated destructive or live integration
authority and do not omit local-session, Progress, Proxy, or PostgreSQL tests.

## State

```text
MVP_LS21_IMPLEMENTATION = PASS_WITH_WARNINGS
OWNER_FAILED_UPLOAD_EXCLUDED = PASS
OWNER_401_EXACT_STAGE = NOT_PRESERVED
SEPARATE_SEARCH_UPLOAD_SESSIONS = PASS
FRESH_FIRST_UPLOAD_SESSION = PASS
UPLOAD_SESSION_ZERO_SEARCH_CAPABILITY = PASS
RECOVERABLE_SESSION_REFRESH = PASS
UNSAFE_401_FAIL_CLOSED = PASS
UPLOAD_RESPONSE_LOSS_RECONCILIATION = PASS
NEXT_RUN_UPLOAD_ONLY_RECOVERY = PASS
NO_CODEX_RERUN_DURING_RECOVERY = PASS
CLOUD_STATUS_UNCERTAINTY_UX = PASS
MVP_RUNTIME_HOSTED_BOUNDARY = PASS
V0_1_STATE = OWNER_ACCEPTANCE_PENDING
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

Warnings remain: the historical owner 401 substage/code is not preserved; no
live OpenAlex or real Codex model call occurred; OpenAlex remains experimental
and default-off; Claude Code is untested; only Literature Search round 1 and
local single-user mode are in scope. Wait for owner review.
