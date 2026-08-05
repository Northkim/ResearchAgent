# R3C-R1 Post-Restart Recovery Failure Forensics

Date: 2026-08-05
Status: **PASS — PRODUCTION REMEDIATION DECISION REQUIRED**

R3C-R1 began from clean `main` at exact commit
`c794c6d86689f1d6d7912ef77e5ae0d6d8beea9b`. The real OpenAlex key variable
was absent. No owner key path, credential file, `.env`, Provider API,
documentation endpoint, production source, test, migration, contract, ADR,
Package template, frontend, or Hosted execution source was read or changed
outside the authorized forensic scope.

Tracked R3C-A-R4 evidence preserves only the high-level post-restart
status/status/replay controller, a value-free `RuntimeError`, healthy restarted
services, an active token, and the unchanged one-operation/one-call/
1,000-microusd ledger. It does not preserve the exact substep, route, function,
source line, safe category, subprocess exit, HTTP status, JSON/parser state, or
assertion/application boundary. Therefore
`EXACT_RESTART_FAILURE_PATH = NOT_PRESERVED`.

Source trace found that `CloudAPIProxyService.submit()` applies five-minute
timestamp freshness before it authenticates and searches the scoped durable
idempotency row. The client maps the resulting HTTP error to `RuntimeError`.
Committed replay/reload tests use a fixed clock equal to the request timestamp;
none tests delayed exact replay or real Proxy process/database restart.

Two fictional successes were created through the committed OpenAlex adapter,
service and SQL repository with runtime-generated synthetic credentials,
scripted transport, two fictional records, exact 1,000-microusd accounting and
`CHECKSUM_ONLY` retention. No real query, key, response, metadata, captured live
value, or external network was used.

Real loopback Uvicorn/PostgreSQL reproduction passed both status paths and
exact replay before restart. After restart and after the original timestamp
crossed five minutes, both status paths still passed; the original-equivalent
controller raised `RuntimeError`, while the explicit controller parsed HTTP
422 / `CLIENT_TIMESTAMP_OUT_OF_RANGE` at exact replay. SQL stayed one
successful operation/call and 1,000 microusd. A separate immediate restart run,
with the same protected synthetic credential in both Uvicorn generations,
passed both status paths and exact replay with unchanged result/checksum/count/
size/cost/call evidence. No network attempt, duplicate, diagnostic, Hosted row,
or Package mutation occurred.

Classification is `CLIENT_RECOVERY_DEFECT`, with `MEDIUM` confidence that this
was the precise historical R3C-A-R4 substep because that path was not preserved;
the offline predicate itself is deterministic. The recommended next route is
`APPLICATION_RECOVERY_REMEDIATION_REQUIRED`: minimally reorder exact
idempotency replay/conflict handling before freshness checks for new admission,
without changing migration/API/checksum/retention/cost semantics. Required
regression covers delayed exact replay, stale new admission, changed-content
conflict, SQL reload, and real Uvicorn/PostgreSQL restart. No further live
Provider call is necessary.

Verification: 154 focused OpenAlex tests; 216 Proxy tests; 13 isolated
Proxy/OpenAlex PostgreSQL tests with zero skip; 43 Package tests; 38 Progress
Report tests; 526 full-backend tests with four separately gated integration
skips; compileall; sole/current Alembic `20260805_0005`; no drift; diff check.

```text
R3C_R1_FORENSICS = PASS
EXACT_RESTART_FAILURE_PATH = NOT_PRESERVED
OFFLINE_RESTART_FAILURE_REPRODUCTION = PASS
SYNTHETIC_POST_RESTART_STATUS_BY_ID = PASS
SYNTHETIC_POST_RESTART_STATUS_BY_IDEMPOTENCY = PASS
SYNTHETIC_POST_RESTART_EXACT_REPLAY = PASS
RESTART_ROOT_CAUSE_CLASSIFICATION = CLIENT_RECOVERY_DEFECT
RESTART_ROOT_CAUSE_CONFIDENCE = MEDIUM
R3C_RECOMMENDED_NEXT_ROUTE = APPLICATION_RECOVERY_REMEDIATION_REQUIRED
R3C_LIVE_PROVIDER_CALL_COUNT_THIS_PHASE = 0
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3C_FINAL_RESTART_ACCEPTANCE_GATE = CLOSED
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

Detailed evidence is in
`docs/audits/R3C_POST_RESTART_RECOVERY_FAILURE_FORENSICS.md`; the owner decision
packet is `docs/decisions/R3C_POST_RESTART_RECOVERY_REMEDIATION_DECISION_PACKET.md`.
