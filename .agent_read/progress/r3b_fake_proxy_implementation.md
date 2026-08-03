# R3B-I Fake Cloud API Proxy Implementation

Date: 2026-08-04

Status: **PASS_WITH_WARNINGS — EXTERNAL ACCEPTANCE PENDING**

## Authority and scope

Implemented ADR 0011 from exact clean baseline
`fd8c1cacfba41a05fef133eb44f7ef0334f62bec` on `main`. This phase implemented
and SQL-qualified the experimental fake-provider slice only. It did not start
R3B-A, a live ASGI server, external Package acceptance or R3C, and made no real
provider, OpenAlex, LLM, AgentRuntime, ExecutionDispatcher or research-
execution call.

## Implementation

The independent `backend/cloud_api_proxy/` boundary contains:

- immutable strict contracts and canonical/non-cyclic identities;
- digest-only bearer token generation, scope authentication and revocation;
- server-derived authorization for exact project, Package, Workflow,
  capability, fake adapter and count scope;
- deterministic fictional `paper.search/v0.1` adapter;
- transactionally admitted operations with exact replay/conflict behavior;
- explicit status and idempotency reconciliation reads;
- startup reconstruction of `RUNNING` as `RECONCILIATION_REQUIRED` without
  adapter reinvocation;
- a separately mounted FastAPI route, operator token CLI and local Package
  client;
- in-memory test repository and independent SQL repository/Unit of Work.

Feature flag: `REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED=1`. It is absent/off by
default. Enabling without explicit `REAGENT_DATABASE_URL` PostgreSQL
persistence fails closed. The route requires literal `127.0.0.1` peer and Host
identity and ignores `X-Forwarded-For` as identity.

API routes:

- `POST /projects/{project_id}/proxy-operations`;
- `GET /projects/{project_id}/proxy-operations/{operation_id}`;
- `GET /projects/{project_id}/proxy-operations?package_id=...&idempotency_key=...`.

CLI entry points:

- `python -m backend.cloud_api_proxy.operator_cli issue ...`;
- `python -m backend.cloud_api_proxy.operator_cli revoke --token-id ...`;
- `python -m backend.cloud_api_proxy.client submit ...`;
- `python -m backend.cloud_api_proxy.client status ...`.

The token CLI writes plaintext once to a new caller path outside Git and the
Package at mode `0600`, refuses overwrite and prints no plaintext. The client
accepts no token argument and reads only `REAGENT_PROXY_TOKEN` from its process
environment. It validates Package identity, performs one bounded request, has
no ambiguous retry and does not mutate the Package.

## Identity and limits

Canonical semantic request content excludes operation ID, idempotency key,
request checksum, token/digest/header, server authorization and server time.
It binds contract/capability, project, exact Package and Workflow identity,
query/max-results, Harness identity and client timestamp. The order is:

```text
canonical request -> request_content_checksum
request checksum + scoped UUIDv4 key + server scope checksum -> proxyop-v1 ID
fake result -> provider-data checksum -> response-content checksum
delivery -> response checksum
```

The server independently verifies a submitted request checksum. Response-
content identity excludes delivery replay state/time and both response checksum
fields; delivery identity excludes only itself.

Enforced limits are 16 KiB actual request bytes, 512 KiB canonical normalized
result, ten seconds, two active operations/token, 50 admitted operations/token,
20 results, 500 query characters, five-minute timestamp skew, zero retry, zero
money, zero real-provider call and zero external-network call.

## Persistence and migration

Additive Alembic revision `20260804_0004` creates
`proxy_capability_tokens` and `proxy_operations`. The token table stores a
unique SHA-256 digest and no plaintext column. The operation table has a unique
`(token_id, idempotency_key)` constraint and references only the new token
table, never Hosted WorkflowRun/step/event/checkpoint/memory/provider tables.

Safe normalized fictional result JSON is stored in PostgreSQL with canonical
checksum and byte size. No raw provider body or artifact is stored. The token
row is locked during admission, so count/concurrency/idempotency decisions are
transactionally serialized. Exact replay and conflicts consume no new count;
an admitted terminal failure remains counted.

## PostgreSQL qualification

Used PostgreSQL 18.1 in one fresh temporary loopback-only cluster on a unique
non-default port. Sanitized databases:

- `reagent_r3bi_migration_20260804`;
- `reagent_r3bi_tests_20260804`.

Sanitized URL form: `postgresql://127.0.0.1:<unique-port>/<database>`; no
password was used or recorded. Neither database was `ProjectDB` and no existing
service/data directory was touched.

After the final sensitive-content rejection control was added, the SQL and
full-backend suites were rerun against a second fresh disposable loopback-only
cluster/database named `reagent_r3bi_tests_final_20260804`. Both temporary
clusters were stopped, verified stopped and removed with their logs/data.

Migration qualification passed: one head `20260804_0004`; upgrade from empty;
current head; no Alembic drift; downgrade exactly one revision to
`20260803_0003`; re-upgrade to `20260804_0004`; final no-drift check. Schema
inspection verified both tables, digest-only token columns, scoped uniqueness
and no Hosted Workflow foreign key.

## Verification

- `python -m pytest -q backend/cloud_api_proxy/tests`: 53 passed, exit 0.
- `python -m pytest -q backend/database/tests/test_cloud_api_proxy_postgresql.py`:
  7 passed, no skip, exit 0.
- `python -m pytest -q backend/workflow_packages/tests`: 43 passed, exit 0.
- `python -m pytest -q backend/progress_reports/tests`: 38 passed, exit 0.
- `python -m pytest -q -rs backend`: 357 passed, 4 skipped, exit 0.
- `python -m compileall -q backend`: exit 0.
- Alembic heads/current/check/downgrade/re-upgrade/check: exit 0 throughout.

The four full-suite skips are pre-existing, separately gated hosted/live
integration suites: destructive database E2E, isolated OpenAlex contract,
explicit OpenAlex live, and historical research-v2 HTTP/PostgreSQL. No new R3B
PostgreSQL test skipped.

Focused tests cover identity, strict schema, token expiry/revocation/redaction,
scope mismatch, actual body/result/time limits, operation count/concurrency,
sequential/concurrent replay, conflict, restart repository reload,
reconciliation, default-disabled/fail-closed routing, loopback/Host enforcement,
client Package non-mutation, and zero network/Hosted import paths.

## Boundary and warnings

`backend/cloud_api_proxy/` has no import of AgentRuntime,
ExecutionDispatcher, Hosted ProviderOperation, WorkflowRun, OpenAlex or LLM/
structured generation. Runtime API tests leave Hosted workflow/event/
checkpoint/memory/provider-operation state empty. The fake adapter uses only
fictional data and no socket/HTTP transport. Progress Report v0.2 is unchanged;
the client does not write outputs, context or reports.

Remaining warnings:

- R3B-A external Package, live Uvicorn/HTTP and backend/PostgreSQL restart
  acceptance have not started;
- external token-file creation/deletion lifecycle is not yet accepted;
- Claude Code remains untested and frontend remains deferred;
- proof of possession and production authentication/multi-user security are
  deferred;
- live-provider terms, credentials, cost/retry and retention are unresolved.

States:

- `R3B_IMPLEMENTATION = PASS_WITH_WARNINGS`
- `R3B_RUNTIME_ACCEPTANCE = NOT_STARTED`
- `R3B_STATE = EXTERNAL_ACCEPTANCE_PENDING`
- `R3B_A_ENTRY_GATE = OPEN` only after clean Git closure
- `R3C_LIVE_PROVIDER_GATE = CLOSED`
- `R2_STATE = UPLOAD_ACCEPTED`
