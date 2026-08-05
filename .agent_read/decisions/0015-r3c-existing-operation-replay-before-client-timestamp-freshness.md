# ADR 0015: R3C Existing-Operation Replay Before Client-Timestamp Freshness

- **Status:** Accepted
- **Date:** 2026-08-05
- **Scope:** Experimental Cloud API Proxy submission and recovery ordering
- **Governing decisions:** ADR 0009 through ADR 0014

## Context

R3C-A-R4 made exactly one authorized live OpenAlex call and durably settled a
successful operation containing five normalized Works and exact 1,000-microusd
cost. Both status reads and exact replay passed before restart. PostgreSQL and
Uvicorn restarted successfully, but the post-restart controller raised a
value-free `RuntimeError`; no second call or repair occurred.

R3C-R1 reproduced the failure deterministically without Provider or key use.
The two status routes continued to return the durable operation after restart,
but exact POST replay returned HTTP 422 / `CLIENT_TIMESTAMP_OUT_OF_RANGE` once
the original content-bound client timestamp was more than five minutes old.
`CloudAPIProxyService.submit()` enforced freshness before consulting the
authoritative `(token_id, idempotency_key)` row. This prevented recovery of an
already-admitted operation even though its scope, request checksum, result,
call count and cost remained valid.

Timestamp freshness protects new admission. It is not operation identity and
must not convert a valid durable replay into a new-admission error.

## Decision

### 1. Authentication, authorization and structure remain mandatory

Every submission, including replay, still requires a structurally valid
request, UUIDv4 idempotency key, parseable UTC timestamp, independently
verified request-content checksum, active known bearer token, exact Project,
Package, Workflow, capability and adapter scope, and all existing sensitive-
content checks. Expired or revoked tokens cannot retrieve or replay an
operation. Wrong-scope requests cannot learn whether an operation exists.

### 2. Durable scoped idempotency precedes freshness

After those checks, the service resolves the authoritative operation by
`token_id + idempotency_key` inside the existing token-locked transaction.

If an operation exists and its stored request-content checksum equals the
incoming checksum, the service returns that operation with the existing replay
delivery semantics regardless of client-timestamp age. This applies to
`RECEIVED`, `RUNNING`, `SUCCEEDED`, `FAILED`, and
`RECONCILIATION_REQUIRED`. Replay creates no operation, reservation, Provider
call, cost, adapter invocation or diagnostic event.

### 3. Existing-key conflict precedes freshness

If the scoped key exists but the checksum differs, the service returns HTTP
409 / `IDEMPOTENCY_CONFLICT` regardless of timestamp age. This includes
content that differs only in `client_timestamp`, because the timestamp remains
part of canonical request content. Conflict does not mutate the operation or
consume budget.

### 4. Freshness remains mandatory for new admission

Only when no scoped idempotency row exists does the existing plus-or-minus
five-minute freshness rule run. Stale or excessively future requests create no
operation and reserve no count, call or cost. Fresh valid requests follow the
unchanged transactional admission path.

### 5. Contract and product non-change

This is an ordering correction only. It changes no API schema/status route,
SQL/ORM model, migration, timestamp window, canonical request content, request
checksum, operation ID, token scope, retention, normalization, structural
diagnostic, reconciliation, Provider mapping, call/cost accounting, Package,
Progress Report, Hosted Runtime or teacher-aligned cloud/local/Harness
boundary.

## Consequences

- A valid exact replay remains available after process/database restart and
  after its original timestamp ages beyond five minutes.
- Timestamp freshness continues to reject stale/future new admission.
- Active-token and exact-scope checks continue to prevent replay as an
  authorization or existence oracle.
- Existing-key changed content deterministically conflicts before freshness.
- Recovery remains one-attempt and never introduces an automatic retry.
- R3C-A-R4 live normalization/cost evidence remains immutable and valid; this
  offline correction authorizes no new live Provider call.
- R3C remains `LIVE_ACCEPTANCE_PENDING` for composite owner review, and R3D
  remains closed.

## Alternatives considered

- Removing or widening timestamp freshness was rejected because new admission
  still requires bounded freshness.
- Removing `client_timestamp` from canonical request content was rejected
  because it would change request-checksum and conflict semantics.
- Hiding HTTP 422 or automatically retrying in the client was rejected because
  it would leave the service defect and create ambiguous recovery behavior.
- Adding a recovery endpoint, migration, token refresh or server clock override
  was rejected as unnecessary contract expansion.
