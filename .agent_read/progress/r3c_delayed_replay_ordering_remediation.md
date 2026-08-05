# R3C-R2 Delayed Exact-Replay Ordering Remediation

Date: 2026-08-05

Status: **PASS — READY FOR OWNER REVIEW**

R3C-R2 began from clean `main` at
`6f802e79edb4991b0256bc9db1d3a3ec49dcc831`. The real OpenAlex key variable
was absent. No credential file, `.env`, external documentation, live Provider,
Hosted execution, Workflow execution, LLM, Judge or automatic Progress Report
path was read or invoked.

ADR 0015 ratifies durable existing-operation resolution before timestamp
freshness. `CloudAPIProxyService.submit()` now authenticates and authorizes the
active exact-scope token, resolves `(token_id, idempotency_key)`, returns exact
replay or existing-key conflict, and only then applies the unchanged five-
minute freshness rule to a missing/new key. The production diff is a one-line
ordering move. It changes no API, migration, SQL/ORM, checksum, operation ID,
timestamp window, retention, cost, normalization, diagnostic, Package or
Progress Report semantics.

Focused service/API/client tests cover delayed `SUCCEEDED`, `FAILED`,
`RUNNING`, and `RECONCILIATION_REQUIRED` replay; changed and timestamp-only
conflict; stale/future new rejection; fresh admission; malformed timestamp;
expired/revoked/wrong-scope denial; exhausted budget; concurrency; HTTP
contract and one-attempt client behavior.

A fresh PostgreSQL 18.1 cluster at sole/current `20260805_0005` qualified SQL
reload, status, replay, conflict, stale admission and concurrent ledger
stability. A two-Work fictional OpenAlex success with 1,871 canonical bytes,
one scripted seed transport call and exact 1,000-microusd reservation/
settlement then passed real Uvicorn/PostgreSQL physical restart. The already-
aged request passed both status routes and exact replay before and after
restart. Timestamp-only changed content returned 409; a distinct stale key
returned 422. The operation/result/checksums/count/size/call/cost stayed
unchanged. Package manifests matched; external transport, diagnostics,
duplicates, Hosted/runtime rows and Package mutation remained zero.

Verification: 154 OpenAlex tests; 231 Proxy tests; 17 required PostgreSQL tests
with zero skip; 43 Package tests; 38 Progress Report tests; 545 full-backend
tests with four separately gated integration skips; compileall; Alembic
heads/current/check at `20260805_0005`; diff check. The fictional capability
was revoked, both services stopped, ports released and all dedicated temporary
state removed.

R3C-A-R4's immutable live five-Work/8,726-byte/1,000-microusd evidence remains
valid. This phase made zero live Provider calls and does not declare R3C
complete. Composite acceptance is ready for owner review; R3D remains closed.

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
