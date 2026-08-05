# R3C Post-Restart Recovery Remediation Decision Packet

Date: 2026-08-05

Status: **OWNER REVIEW REQUIRED — NO PRODUCTION CHANGE IMPLEMENTED**

## Decision requested

Approve the next route:

```text
R3C_RECOMMENDED_NEXT_ROUTE = APPLICATION_RECOVERY_REMEDIATION_REQUIRED
```

## Proven defect boundary

`CloudAPIProxyService.submit()` validates the request's five-minute client
timestamp before authenticating and consulting the durable scoped idempotency
row. A previously accepted, byte-exact request therefore receives
`CLIENT_TIMESTAMP_OUT_OF_RANGE` after five minutes instead of returning its
existing operation. The committed client converts that HTTP 422 to a value-free
`RuntimeError`.

Both post-restart status paths and immediate exact replay pass. SQL reload,
authorization rehydration, operation/result reconstruction, cost/call counters,
Package identity, Uvicorn readiness, and PostgreSQL restart all pass. The
delayed failure is deterministic before Provider transport.

## Minimal future change

Affected production file:

- `backend/cloud_api_proxy/service.py`, `submit()` ordering around current
  lines 198-211 and `_validate_client_timestamp()` at current lines 551-554.

Required behavior:

1. retain request checksum and sensitive-content validation;
2. authenticate the active, unrevoked, unexpired token;
3. authorize the exact project/Package/Workflow/capability scope;
4. consult the token-scoped UUIDv4 idempotency row;
5. return the existing operation for the same request checksum or return
   `IDEMPOTENCY_CONFLICT` for changed content;
6. apply the five-minute timestamp freshness rule before admitting only a new
   operation.

Do not relax UUIDv4, request checksum, scope, token expiry/revocation, query
safety, changed-content conflict, cost/call budgets, strict response failure,
or no-retry semantics.

## Required regression

- service test: exact replay after advancing the clock beyond five minutes
  returns the same operation with zero adapter invocation/cost increment;
- adjacent service test: a stale new idempotency key remains
  `CLIENT_TIMESTAMP_OUT_OF_RANGE` before adapter use;
- adjacent service test: stale changed content under the existing key remains
  `IDEMPOTENCY_CONFLICT` with zero adapter use;
- PostgreSQL test: reload a successful OpenAlex operation into a service with
  an advanced clock, then pass both status paths and exact replay with unchanged
  call/cost totals;
- real HTTP qualification: committed Uvicorn plus real PostgreSQL stop/restart,
  delayed exact replay, zero external transport, and stable SQL/result evidence.

## Compatibility and live-call decision

The future correction should require no migration, API contract/response
change, request checksum change, operation identity change, response-content
checksum semantic change, query retention, raw-body retention, or cost change.

Another live Provider call is not required to prove this pre-transport
recovery correction. R3C-A-R4's immutable live normalization evidence remains
accepted; a future owner-approved restart closure can use synthetic persisted
state with hard network canaries.

R3C remains `LIVE_ACCEPTANCE_PENDING`. The final restart gate and R3D remain
closed.
