# R3B-A External Fake Proxy Acceptance Progress Record

Date: 2026-08-04

Status: **PASS_WITH_WARNINGS**

## Baseline and scope

- Baseline: `6a64d5827f18ee24e8fe2d71f66e78b26a9fcc44` on clean `main`.
- Scope: acceptance of committed R3B-I only; no production source, migration,
  test, fixture, frontend, Package template or Progress Report contract change.
- Runtime: fresh fictional external Package, real Uvicorn, real loopback HTTP,
  dedicated PostgreSQL 18.1, deterministic fake adapter.
- Prohibited calls: zero real provider, OpenAlex, Internet, AgentRuntime,
  ExecutionDispatcher, Workflow, LLM, Judge or automatic Progress Report use.

## Accepted evidence

- Dedicated databases `reagent_r3ba_acceptance_20260804_55483` and
  `reagent_r3ba_tests_20260804_55483` ran on a fresh loopback-only cluster;
  ProjectDB was absent and untouched.
- Migration `20260804_0004` was the sole current head with no drift. Direct SQL
  inspection confirmed the distinct Proxy token/operation schema, digest-only
  token storage, scoped idempotency uniqueness and no Hosted foreign key.
- External Package ID
  `literature-search-fictional-r3ba-proxy-20260804-v0.2` validated before and
  after acceptance. Its 34-entry recursive manifest remained byte-identical at
  `sha256:0d149b2090b2b4f85aa6f44ad7bbff35529ff3e181ca99c071c2bc168ce0a459`.
- Four operator-issued token files were `0600`; overwrite failed closed;
  revocation survived restart. A private scan found zero plaintext matches in
  1,955 non-token acceptance files, tracked Git files or Proxy SQL rows.
- The default-disabled route returned `404` and created no row. Enabled with an
  invalid isolated SQL target failed startup. Enabled with explicit SQL and
  Uvicorn bound to literal `127.0.0.1` succeeded. Secure acceptance launch used
  disabled Uvicorn proxy-header parsing so forwarded headers could not replace
  the actual loopback peer.
- One native operation independently verified the complete canonical request,
  scope, operation, provider-data, response-content and delivery checksum
  chain. Result data were fictional, deterministic, 4,518 bytes and zero cost.
- Seven legitimate scholarly syntax cases passed. Nineteen authentication/
  authorization and 32 schema/size/timestamp/unsafe-content cases produced
  safe expected outcomes with no unwanted admission or adapter use.
- Sequential replay was idempotent. Two concurrent real clients produced one
  operation (`201 CREATED` plus `200 REPLAYED`). Changed content under the same
  key returned `409 IDEMPOTENCY_CONFLICT` without count change.
- The committed authorization scope includes token instance identity. An
  equivalent-scope second token therefore created a distinct operation under
  the same key/content; `SCOPED_IDEMPOTENCY_SEMANTICS = CONFIRMED`.
- Limited-token accounting stopped exactly at `3/3`; replay, conflicts, reads
  and pre-admission failures consumed no count.
- A complete client-disconnect POST was recovered through scoped status and
  exact replay without a second operation.
- A valid `RUNNING` operation injected through committed domain/SQL UoW
  reconstructed as `RECONCILIATION_REQUIRED`, retained identity and count, and
  never invoked/re-invoked the adapter.
- A canonical four-token/26-operation SQL snapshot was byte-identical across
  Uvicorn shutdown and PostgreSQL stop/start. Result JSON, token revocation,
  reconciliation and replay behavior survived exactly; Hosted/Progress rows
  remained zero.
- Point-in-time process socket inspection showed only loopback Uvicorn and
  PostgreSQL sockets; static/runtime canaries also passed. This is not claimed
  as packet-capture evidence.

## Validation

- Proxy focused: 53 passed.
- Proxy PostgreSQL: 7 passed, zero skipped.
- Workflow Packages: 43 passed.
- Progress Reports: 38 passed.
- Full backend: 357 passed, 4 unrelated gated skips.
- Compileall: exit 0.
- Alembic: sole/current `20260804_0004`, no drift.
- `git diff --check`: exit 0.

## Warnings

- Live active-slot saturation was not induced; the real PostgreSQL concurrent
  active-limit test passed.
- Live wall-clock expiry was not repeated; focused expiration tests passed.
- Claude Code, frontend, proof of possession, HTTPS/public deployment and
  production/multi-user authentication remain unaccepted.
- Real-provider terms, credentials, cost/retry and retention remain unresolved.
- Existing R2 warnings remain unchanged.

## State

```text
R3B_A_ACCEPTANCE = PASS_WITH_WARNINGS
POSTGRESQL_ACCEPTANCE = PASS
EXTERNAL_PACKAGE_ACCEPTANCE = PASS
LIVE_HTTP_PROXY_ACCEPTANCE = PASS
TOKEN_LIFECYCLE_ACCEPTANCE = PASS
AUTHENTICATION_ACCEPTANCE = PASS
AUTHORIZATION_ACCEPTANCE = PASS
CAPABILITY_AND_LIMITS_ACCEPTANCE = PASS
IDEMPOTENCY_ACCEPTANCE = PASS
SCOPED_IDEMPOTENCY_SEMANTICS = CONFIRMED
RECONCILIATION_ACCEPTANCE = PASS
RESTART_ACCEPTANCE = PASS
PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
RUNTIME_PROVIDER_BOUNDARY = PASS
R3B_GIT_CLOSURE = PASS
R3B_STATE = FAKE_PROXY_ACCEPTED
R3B_COMPLETE = PASS_WITH_WARNINGS
R3C_LIVE_PROVIDER_GATE = CLOSED
R2_STATE = UPLOAD_ACCEPTED
```

Detailed evidence is in
`docs/acceptance/R3B_FAKE_PROXY_EXTERNAL_ACCEPTANCE_REPORT.md`.
