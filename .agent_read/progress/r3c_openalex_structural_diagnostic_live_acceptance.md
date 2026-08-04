# R3C-N2-A Live OpenAlex Structural Diagnostic Acceptance

Date: 2026-08-04

## Result

```text
R3C_N2_A_ACCEPTANCE = PASS_WITH_WARNINGS
R3C_OWNER_AUTHORIZATION = PASS
R3C_SOURCE_RECHECK = PASS
POSTGRESQL_ACCEPTANCE = PASS
EXTERNAL_PACKAGE_ACCEPTANCE = PASS
LIVE_OPENALEX_DIAGNOSTIC_HTTP_ACCEPTANCE = PASS
R3C_LIVE_OPERATION_OUTCOME = SUCCEEDED_WITH_NO_DIAGNOSTIC
R3C_STRUCTURAL_DIAGNOSTIC_EVENT = NOT_TRIGGERED_SUCCESS
R3C_DIAGNOSTIC_PRIVACY_BOUNDARY = PASS
R3C_DIAGNOSTIC_EVIDENCE = INSUFFICIENT
R3C_STATUS_AND_REPLAY = PASS
PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
R3C_LIVE_PROVIDER_CALL_COUNT_THIS_PHASE = 1
R3C_REPORTED_COST_MICROUSD = 1000
R3C_DIAGNOSTIC_LIVE_CALL_GATE = CLOSED_AFTER_ATTEMPT
R3C_I2_IMPLEMENTATION_GATE = CLOSED
R3C_FULL_LIVE_ACCEPTANCE_GATE = CLOSED
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

The phase began from exact clean `main` commit
`45ef6b500c61a484bd6d4b569b3d4233ab6146a2`. A fresh strict owner attestation
authorized one fictional public search, one Provider call, 1,000 microusd, at
most five results, no paid/prepaid overage, no Provider/raw-body retention, and
dedicated local-copy deletion.

The pre-key official-only recheck passed. Twelve objects matched prior hashes;
the pricing blog changed bytes without changing the key, free allowance,
ordinary-search price, or `search=` facts. Current Works path/selected fields,
`meta.cost_usd`, approved X-RateLimit evidence, Terms, and Privacy remained
compatible. No Provider API was contacted during that gate.

A fresh PostgreSQL 18.1 cluster on loopback used separate acceptance/test
databases at sole head `20260805_0005` with no drift. A fresh compiler-generated
fictional external Package validated and its 34-entry pre/post manifests were
byte-identical. The diagnostic flag alone mounted no Proxy; missing SQL and
missing credential failed closed. The accepted real Uvicorn process explicitly
enabled only the OpenAlex Proxy and structural diagnostic flags.

One OpenAlex-bound token was issued with one operation/call. The key was read
only by an outside-Git exec wrapper and injected as
`REAGENT_OPENALEX_API_KEY`; the client received only `REAGENT_PROXY_TOKEN`.
The single operation returned HTTP 200, exact 1,000-microusd cost, safe rate
evidence, `SUCCEEDED`, and zero normalized paper records. The diagnostic log
remained empty, as required for success.

Status by operation and scoped idempotency identity matched. Exact replay used
the same stored request bytes and returned the same operation without another
admission, call, reservation, cost settlement, or event. Query/marker/token/
URL/header/raw-body scans passed, Provider paper values were absent, normal
responses exposed no diagnostic, Hosted/runtime/progress counts remained zero,
and Package bytes remained unchanged.

Verification passed 133 focused OpenAlex tests, 195 Proxy tests, 13 Proxy/
OpenAlex SQL tests with zero skip, 43 Package tests, 38 Progress Report tests,
and 505 complete backend tests with four unrelated gated integration skips.
Compileall and Alembic heads/current/check passed.

The token was revoked. Uvicorn/PostgreSQL stopped and released their ports.
All dedicated database, Package, source, log, request/response, token, wrapper,
owner attestation, and owner key-copy material was deleted. The OpenAlex
account/key itself and unrelated services/data were untouched.

Retry 1's failure was not reproduced. A successful empty result is not root-
cause evidence and does not open normalization remediation. Wait for owner
review; do not start another call, R3C-I2, complete R3C-A, or R3D.

Detailed evidence is in
`docs/acceptance/R3C_OPENALEX_STRUCTURAL_DIAGNOSTIC_LIVE_ACCEPTANCE_REPORT.md`.
