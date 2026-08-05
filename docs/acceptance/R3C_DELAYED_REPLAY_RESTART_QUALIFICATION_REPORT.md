# R3C Delayed Replay Restart Qualification Report

Date: 2026-08-05

Status: **PASS — READY FOR COMPOSITE R3C OWNER REVIEW**

This was an offline production-remediation and restart-qualification phase. It
made zero live OpenAlex calls, retrieved no external documentation, read no real
OpenAlex key or `.env`, and invoked no Hosted research execution, Workflow,
LLM, Judge or automatic Progress Report path. It does not declare R3C complete
or open R3D.

## 1. Baseline and preserved evidence

The phase began from clean `main` at exact commit
`6f802e79edb4991b0256bc9db1d3a3ec49dcc831`
(`R3C-R1: diagnose post-restart recovery verification failure`). Required
ancestors were present, both Git status forms were empty, and
`git diff --check` passed. `REAGENT_OPENALEX_API_KEY` was absent.

R3C-A-R4 remains immutable. Its accepted live evidence remains exactly one
HTTP-200 OpenAlex call, five normalized Works, 8,726 canonical bytes,
`SUCCEEDED`, 1,000 reported microusd, both passing pre-restart status routes,
passing pre-restart exact replay and changed-content conflict, successful
PostgreSQL/Uvicorn restart, and a retained one-operation/one-call/
1,000-microusd SQL ledger. R3C-R1's deterministic delayed-replay diagnosis also
remains immutable.

## 2. Owner-ratified policy and production change

ADR 0015 records the accepted ordering:

1. strictly parse and validate request structure, UUIDv4, UTC timestamp,
   request checksum and sensitive-content policy;
2. authenticate a known, active, unrevoked and unexpired bearer;
3. authorize exact Project, Package, Workflow, capability and adapter scope;
4. resolve durable `(token_id, idempotency_key)` identity in the existing
   token-locked transaction;
5. replay an existing matching checksum, or conflict an existing different
   checksum;
6. enforce the unchanged plus-or-minus five-minute timestamp rule only for a
   new admission.

The production correction in `backend/cloud_api_proxy/service.py` moves the
existing timestamp-freshness call from immediately before the transaction to
immediately after the existing-operation replay/conflict branch. There is no
new repository query and no client-side retry or error hiding.

No public API, status route, schema, migration, SQL/ORM model, timestamp window,
canonical request content, checksum, operation identity, token scope,
retention, cost, normalization, structural diagnostic, Package or Progress
Report contract changed.

## 3. Focused service, API and client behavior

Focused regressions prove:

- delayed exact replay of `SUCCEEDED` and `FAILED` returns the same operation;
- delayed `RUNNING` replay does not reinvoke the adapter;
- delayed `RECONCILIATION_REQUIRED` replay remains conservative and zero-call;
- stale changed content returns HTTP 409 / `IDEMPOTENCY_CONFLICT` before
  freshness;
- a request differing only in content-bound timestamp also conflicts;
- stale and excessively future new keys remain HTTP 422 /
  `CLIENT_TIMESTAMP_OUT_OF_RANGE` with no operation;
- fresh new admission remains unchanged;
- malformed timestamp input fails structurally before service/repository use;
- expired, revoked and wrong-scope tokens cannot replay or probe an operation;
- exact replay remains available at exhausted operation budget without new
  consumption;
- concurrent delayed replays and concurrent stale changed-content submissions
  retain one operation and a stable ledger;
- the API keeps HTTP 200 for replay, 409 for conflict and 422 for stale new
  admission; both status routes are unchanged;
- the provider-neutral client accepts a valid delayed replay response, still
  converts rejected new admission into a safe error, and performs no automatic
  retry.

## 4. PostgreSQL transactional qualification

A fresh loopback-only PostgreSQL 18.1 cluster used separate test and restart-
qualification databases. Both were upgraded to sole/current revision
`20260805_0005`; `alembic check` reported no drift.

The two required Proxy/OpenAlex PostgreSQL modules executed 17 tests with zero
skip. They cover delayed replay after repository reload, both status reads,
existing-key conflict, stale new admission, concurrent delayed replay,
concurrent conflict, operation-count stability, Provider-call stability,
microusd stability and no duplicate operation. The OpenAlex ledger stayed one
operation, one call, 1,000 reserved microusd and 1,000 reported microusd.

## 5. Real PostgreSQL/Uvicorn restart qualification

A fresh external fictional Package was compiled and pristine-validated outside
Git. A synthetic OpenAlex success was created through the committed
`OpenAlexPaperSearchAdapter`, `CloudAPIProxyService`, and
`SQLProxyUnitOfWork`, using a runtime-generated synthetic credential and one
scripted transport response. It persisted:

- `SUCCEEDED`;
- two wholly fictional normalized Works;
- 1,871 canonical normalized bytes;
- request, provider-data, response-content and delivery checksums;
- `CHECKSUM_ONLY` request retention;
- one Provider-call reservation;
- exactly 1,000 reserved and 1,000 reported microusd;
- no query text, raw body or unknown synthetic response field.

The original request timestamp was constructed more than five minutes before
the real Uvicorn server clock; no sleep or production clock override was used.
Before restart, real loopback HTTP passed status by operation ID, status by
scoped idempotency identity and exact replay. SQL and boundary audits remained
stable.

Uvicorn was stopped, PostgreSQL was stopped, and the same PostgreSQL data
directory was preserved. PostgreSQL restarted with bounded readiness checks,
revision `20260805_0005` and no drift. A second Uvicorn generation started with
equivalent flags, SQL and protected synthetic credential and passed bounded
real `/health` readiness.

After restart, real loopback HTTP proved:

- status by operation ID returned the same success;
- status by scoped idempotency identity returned the same success;
- exact replay returned the existing operation with `REPLAYED`;
- timestamp-only changed content returned 409 /
  `IDEMPOTENCY_CONFLICT`;
- a distinct stale new UUIDv4 key returned 422 /
  `CLIENT_TIMESTAMP_OUT_OF_RANGE`;
- operation ID, normalized result, all stable checksums, result count and
  canonical size were unchanged;
- the ledger remained one operation, one call, 1,000 reserved microusd and
  1,000 reported microusd;
- no duplicate operation, adapter invocation or diagnostic event occurred.

## 6. Package, security and product boundary

Recursive pre/post Package manifests independently covered directory/file
kind, mode, byte length and SHA-256. They were byte-identical. The Package
remained pristine-valid and contained no token, credential, query, Provider
selector, response marker or prior acceptance state.

Protected token, synthetic credential, request, marker, manifest, state,
network-canary and diagnostic files were all mode `0600`. Private scans of SQL,
Package and tracked Git files found no synthetic credential, capability token,
request text or unknown raw-response marker. SQL retained query checksum and
length evidence only. The network-canary and structural-diagnostic logs were
both exactly zero bytes.

Hosted/runtime table counts remained zero for Workflow/Step runs, execution
events, checkpoints, memory revisions, Hosted ProviderOperations, Progress
Reports/projections and agent sessions. No AgentRuntime, ExecutionDispatcher,
Hosted Skill, LLM, structured generation, Judge, Workflow continuation,
Progress Report generation/upload or Package/context/output mutation occurred.
The teacher-aligned cloud/local/Harness boundary is unchanged.

## 7. Regression matrix

| Check | Result |
|---|---:|
| Focused OpenAlex adapter/service tests | 154 passed |
| Complete Cloud API Proxy suite | 231 passed |
| Required Proxy/OpenAlex PostgreSQL modules | 17 passed, zero skipped |
| Workflow Package suite | 43 passed |
| Progress Report suite | 38 passed |
| Full backend | 545 passed, 4 separately gated integration skips |
| `compileall` | PASS |
| Alembic heads/current/check | sole/current `20260805_0005`, no drift |
| `git diff --check` | PASS |

The four full-backend skips were the separately gated destructive demo
integration, 9B-1 contract integration, live OpenAlex integration, and 9A-2
research-v2 integration. Neither required Proxy/OpenAlex PostgreSQL module
skipped.

## 8. Cleanup and gates

The fictional capability was revoked through the committed service. Both
Uvicorn generations and the dedicated PostgreSQL cluster were stopped, both
selected ports were released, and the exact external Package, request/token/
credential files, manifests, canary/diagnostic logs, temporary controllers,
dedicated databases/data directory and PDF render files were removed. No
ProjectDB or unrelated PostgreSQL service was touched.

```text
R3C_R2_IMPLEMENTATION = PASS
R3C_REPLAY_TIMESTAMP_ORDERING_POLICY = EXISTING_OPERATION_BEFORE_FRESHNESS
R3C_DELAYED_EXACT_REPLAY = PASS
R3C_DELAYED_EXISTING_KEY_CONFLICT = PASS
R3C_STALE_NEW_ADMISSION_REJECTION = PASS
R3C_AUTHORIZATION_PRESERVATION = PASS
R3C_POST_RESTART_STATUS_BY_ID = PASS
R3C_POST_RESTART_STATUS_BY_IDEMPOTENCY = PASS
R3C_POST_RESTART_EXACT_REPLAY = PASS
R3C_SQL_REGRESSION = PASS
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
R3C_LIVE_PROVIDER_CALL_COUNT_THIS_PHASE = 0
R3C_COMPOSITE_ACCEPTANCE_READINESS = READY_FOR_OWNER_REVIEW
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3C_FINAL_RESTART_ACCEPTANCE_GATE = READY_FOR_OWNER_REVIEW
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

R3C is not declared complete. Composite acceptance and any later route require
owner review.
