# V0.1 Post-Round Upload Session Qualification

Date: 2026-08-06

Status: **PASS_WITH_WARNINGS — OWNER ACCEPTANCE PENDING**

## Owner failure handling and attribution

The failed owner Demo is not acceptance evidence. No Package, local output,
report, receipt, token, or request from it was reused or uploaded. Tracked
evidence identifies only the automatic post-finalization upload phase and HTTP
401; it does not preserve whether the failing request was upload, history, or
projection verification, nor a safe server application code.

The pre-remediation launcher did deterministically use the original search
session for all three operations. Because that session lasted 15 minutes while
interactive owner time was not bounded to 15 minutes, the design was unsafe
regardless of the unproven historical 401 cause.

```text
OWNER_FAILED_UPLOAD_EXCLUDED = PASS
OWNER_401_EXACT_STAGE = NOT_PRESERVED
```

## Corrected security contract

The search token permits only its bounded normal OpenAlex or explicit demo fake
paper searches. It has no Progress upload/read capability and is closed after
Codex exits. An expired search token cannot prevent already valid local
artifacts from being finalized.

Every first upload and later recovery opens a fresh upload-only token after
report validation. The token binds exact project, Package checksum, Workflow
version/checksum, round, report ID, and report-content checksum. It uses a
neutral local Progress capability, two-minute lifetime, zero Proxy operations,
zero Provider calls, zero Provider cost, and only upload plus scoped receipt,
history, and projection verification.

At most one new upload session is opened for `SESSION_EXPIRED`, equivalent
explicit expiry, or an unknown response outcome. The exact original envelope
is reused. Revoked/unknown/malformed credentials, scope/report/checksum
mismatch, and unclassified 401s are never retried automatically. Cleanup
warnings remain secondary to the primary upload result.

## Idempotency and next-run recovery

If PostgreSQL accepted the report but the response or local receipt was lost,
the next exact upload returns the original receipt semantics. It does not add a
report, projection, report round, or local research output. A valid finalized
report without a receipt selects upload-only recovery and skips Codex, query
generation, Provider transport, and output generation. A verified receipt
prevents repetition.

The Progress page distinguishes cloud knowledge from local truth: **No Progress
Report received** can mean either not yet run or locally complete but pending
upload. It states that the cloud cannot inspect local files and tells the owner
to rerun the same Package; downloading a new Package is not recovery.

## Test and real-stack evidence

The focused matrix passed 307 tests. The full backend passed 597 with four
pre-existing separately gated integration skips. All required PostgreSQL tests
ran against a fresh PostgreSQL 18.1 database with zero relevant skip. Alembic
remained at sole/current head `20260806_0007` with no drift. Compileall passed.

Frontend typecheck, 14 Vitest tests, ESLint, production build, and the two-case
Chromium interactive/auto demo E2E passed. A real loopback Uvicorn/PostgreSQL
qualification deliberately aged the search token before local finalization,
then proved first upload with a new report-bound token. It removed the local
receipt after server acceptance and reconciled through another fresh token;
one report and one projection remained. Physical PostgreSQL and application
restart retained the completed state in both HTTP API and Chromium.

No live OpenAlex request, real key, owner Demo artifact, AgentRuntime,
ExecutionDispatcher, Hosted Workflow, cloud LLM, or automatic server research
execution occurred. Temporary databases, Packages, receipts, logs, and scripts
were removed, and their ports were released.

## Result

```text
MVP_LS21_IMPLEMENTATION = PASS_WITH_WARNINGS
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

This record does not perform owner acceptance or authorize deployment.
