# R3C-A-R1 OpenAlex Live Acceptance Retry 1

Date: 2026-08-04
Status: **BLOCKED AFTER ONE FAIL-CLOSED LIVE PROVIDER CALL**

## Result

Retry 1 began from exact clean `main` commit
`e381e74dac017f2466ac80b77a582ccc10cf6e78`. The previous blocked report was
preserved unchanged as attempt-0 audit evidence.

The owner input metadata and exact credential-free attestation passed. All 13
required official sources were re-retrieved only from approved documentation
domains; 12 byte hashes matched the committed ledger, and one Authentication &
Pricing reference changed bytes without changing the qualified key, price,
rate-header or `meta.cost_usd` contract. Source recheck passed before the key
was read.

A fresh loopback PostgreSQL 18.1 cluster with separate `reagent_r3ca`
acceptance/test databases reached sole head `20260805_0005` with no drift.
Direct schema inspection passed. A fresh external fictional Package validated
and its 34-entry recursive manifest remained byte-identical. Default-disabled,
missing-SQL and missing-key real Uvicorn composition gates passed. A two-call
OpenAlex-bound capability was issued digest-only; the key was injected only by
a supervised child-process wrapper.

The first and only committed-client request used a fictional public query and
`max_results=5`. OpenAlex returned HTTP 200 with the required rate evidence and
exact USD 0.001 cost, but the adapter durably settled the operation as
`FAILED / PROVIDER_INVALID_RESPONSE`. No accepted normalized result existed.
The retry stopped immediately: no second Provider call, replay, conflict,
restart, regression suite or production repair occurred.

Privacy checks found zero durable exact-query, runtime-marker or out-of-file
capability-token matches. Hosted run/step/provider/event/checkpoint/memory and
Progress Report rows remained zero. The token was revoked; Uvicorn/PostgreSQL
stopped; all dedicated runtime/database/Package/source/log material was
removed. The execution safety reviewer rejected deletion of the two external
owner files pending fresh explicit approval, so both remained protected
`0600` files outside Git.

## State

```text
R3C_A_ATTEMPT = RETRY_1
R3C_A_RETRY_1_ACCEPTANCE = BLOCKED
R3C_A_ACCEPTANCE = BLOCKED
BLOCKING_REASON = LIVE_PROVIDER_RESPONSE_FAILED_APPROVED_NORMALIZATION
R3C_OWNER_AUTHORIZATION = PASS
R3C_SOURCE_RECHECK = PASS
R3C_LIVE_PROVIDER_CALL_COUNT = 1
R3C_REPORTED_COST_MICROUSD = 1000
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3C_COMPLETE = NOT_COMPLETE
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
R3B_STATE = FAKE_PROXY_ACCEPTED
R2_STATE = UPLOAD_ACCEPTED
```

Detailed evidence:
`docs/acceptance/R3C_OPENALEX_LIVE_ACCEPTANCE_RETRY_1_REPORT.md`.

Do not repair production source in this phase. Do not begin R3D. Wait for owner
review of the live Provider/normalization mismatch and cleanup exception.
