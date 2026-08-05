# R3C-R1 Post-Restart Recovery Failure Forensics

Date: 2026-08-05

Status: **PASS — DELAYED EXACT-REPLAY DEFECT REPRODUCED OFFLINE**

This phase used no live Provider, Provider documentation, real API key, `.env`,
production-source modification, Hosted execution, Workflow execution, LLM,
Judge, or automatic Progress Report path. It does not complete R3C, perform
R3C-A-R5, or open R3D.

## 1. Baseline and immutable evidence

The phase began from clean `main` at exact commit
`c794c6d86689f1d6d7912ef77e5ae0d6d8beea9b`
(`R3C-A-R4: record incomplete post-remediation OpenAlex retry`). Required
ancestors `110f54ac7c87453a08e61ae26a5d5afbd6b77bb2`,
`a980acbc268ce96089bd93a2954a39b9491a3e94`,
`45ef6b500c61a484bd6d4b569b3d4233ab6146a2`, and
`6ba48416b4936060298b9e5fd9ce197b782b2bb1` were present. Both Git status
forms were empty and `git diff --check` passed.

`REAGENT_OPENALEX_API_KEY` was absent at the initial gate. No owner key path was
dereferenced, no credential file or `.env` was opened, and no OpenAlex or
documentation endpoint was contacted. R3C-A-R4 remains immutable audit history.
Its accepted evidence remains exactly one live HTTP 200 call, five normalized
Works, 8,726 canonical bytes, `SUCCEEDED`, 1,000 microusd, two passing
pre-restart status reads, passing pre-restart replay and conflict, unchanged
Package, successful PostgreSQL restart at `20260805_0005`, healthy restarted
Uvicorn, and a retained one-operation/one-call/1,000-microusd SQL ledger.

## 2. Preserved and missing RuntimeError evidence

The tracked R3C-A-R4 report preserves:

- the high-level step name: provider-neutral post-restart
  status/status/replay controller;
- exception class: `RuntimeError`;
- the fact that the failure was value-free and occurred before the safe
  recovery artifact was created;
- an active, unrevoked token at the time;
- healthy restarted Uvicorn and current PostgreSQL migration;
- the unchanged durable one-operation/one-call/1,000-microusd ledger.

It does not preserve:

- the exact substep or route;
- whether the failure was operation-ID status, idempotency status, or POST
  replay;
- the command/function or source line;
- a safe exception category or message beyond the class;
- subprocess exit code or stdout/stderr presence;
- HTTP status;
- whether response JSON existed or parsing began;
- whether an assertion, controller parser, client, or application raised first.

The cause therefore cannot be assigned from the word `RuntimeError` alone.

```text
EXACT_RESTART_FAILURE_PATH = NOT_PRESERVED
```

## 3. Recovery-path trace

| Stage | Committed source / controller action | Assumption and readiness behavior | Parser / possible failure | Existing coverage |
|---|---|---|---|---|
| Stop Uvicorn | external acceptance controller; app lifespan closes both containers in `backend/api/app.py:49-54` | child identity is current and shutdown is bounded | process exit/wait can fail; exact R4 command not preserved | TestClient lifespan only; no committed real-process Proxy restart test |
| Stop PostgreSQL | external `pg_ctl` step | exact dedicated data directory and port | nonzero process exit can become controller error | acceptance procedure only |
| Restart PostgreSQL | external `pg_ctl` step | same data directory, loopback port, database | launch/exit failure | acceptance procedure plus SQL repository tests, not physical restart |
| PostgreSQL readiness | bounded `pg_isready` | readiness must precede migration/application startup | exit parser/timing | not covered by unit tests |
| Migration check | Alembic `current`; models and SQL at revision `20260805_0005` | sole expected head | subprocess output/exit parser | migration and PostgreSQL suites |
| Restart Uvicorn | committed `backend.api.app:create_app`; Proxy composition at `backend/cloud_api_proxy/composition.py:55-92` | equivalent SQL, feature flag and credential environment | import/startup error, credential/config mismatch | fail-closed composition tests; no real restart test |
| Application readiness | `/health` in `backend/api/routers/health.py:10-12` after successful ASGI startup | route is liveness-only; Proxy composition nevertheless opens SQL and runs startup reconciliation before app construction completes | socket/HTTP/JSON/timing | basic health tests; not a database-readiness endpoint |
| Token rehydration | digest lookup in `backend/cloud_api_proxy/service.py:506-524` and SQL token reconstruction | same client plaintext remains available outside SQL; digest/scope/expiry persist | 401/403 or client `RuntimeError` | token reload/revocation tests |
| Status by operation ID | client `client.py:120-124`; service `service.py:463-477`; SQL `sql.py:64-66,241-273` | exact project/scope and operation identity | URL/HTTP/JSON/non-object/client assertion | API/service/SQL tests |
| Status by idempotency identity | client `client.py:127-131`; service `service.py:479-498`; SQL `sql.py:68-75` | same Package identity, token scope and UUIDv4 key | argument parse, 404/authorization, HTTP/JSON/assertion | API/service/SQL tests |
| Exact replay | client `client.py:106-117`; API `api.py:77-105`; service `service.py:183-211` | original protected request bytes remain available because SQL uses `CHECKSUM_ONLY` | timestamp, auth, scope, idempotency conflict, HTTP conversion, JSON parser, assertion | same-clock replay tests; no delayed replay test |
| Compare stable evidence | response contract and controller assertions | operation/result/checksum/count/size remain stable; delivery timestamp/checksum may differ | assertion error can be wrapped as `RuntimeError` | contract tests; exact R4 assertions not preserved |
| Verify call/cost ledger | Proxy operation/token SQL fields | one call and 1,000 microusd remain exact integers | SQL/process/controller assertion | OpenAlex PostgreSQL tests |

No process-local Provider adapter, SQL engine, session, or operation object is
required to survive restart. Composition reconstructs the engine, sessions,
credential source, adapter registry, service, and startup reconciliation. SQL
reconstructs token scope and terminal normalized operation data. The plaintext
capability and original request bytes are intentionally external transient
inputs; SQL cannot reconstruct the query-bearing request from
`CHECKSUM_ONLY` evidence.

## 4. Exact source predicate

The deterministic defect is ordering in
`backend/cloud_api_proxy/service.py:198-211`:

1. `submit()` obtains the current server time.
2. Line 199 calls `_validate_client_timestamp()`.
3. Lines 551-554 reject a request more than five minutes from that time as
   `CLIENT_TIMESTAMP_OUT_OF_RANGE`.
4. Only afterward does line 207 search for the existing scoped idempotency row.
5. Consequently, a byte-exact request accepted earlier becomes impossible to
   replay after five minutes even though the durable row, active token,
   checksum, scope, result, and budget are valid.

This contradicts the ratified Proxy rule that the same authorized scope,
idempotency key, and request checksum return the existing operation without a
new call or reservation. The contract states that `client_timestamp` is not
identity authority. It also contradicts ADR 0012's requirement that exact
replay return the existing operation without another Provider call.

`backend/cloud_api_proxy/client.py:94-100` converts any HTTP error into a
value-free `RuntimeError` containing only the HTTP status. Thus application
HTTP 422 from this predicate has the same exception class preserved by R3C-A-R4.
The client conversion explains the observed class; it is not the source of the
invalid rejection.

Committed tests cover stale/future *new* requests at
`backend/cloud_api_proxy/tests/test_service.py:111-121`. Existing exact-replay
and SQL-reload tests use a fixed service clock equal to the request timestamp.
No committed test advances the clock beyond five minutes before exact replay,
and no committed test performs the Proxy's real Uvicorn/PostgreSQL restart.

## 5. Other possible RuntimeError sites

Before reproduction, safe candidates included process launch/stop exits,
PostgreSQL or Uvicorn readiness timeout, stale base URL/port, missing client
token, Package-root validation, moved/deleted request bytes, operation or
idempotency argument mismatch, HTTP 4xx/5xx, URL failure, malformed/non-object
JSON, response-contract parsing, comparison assertion, SQL engine/session
reconstruction, and startup reconciliation.

The controlled evidence excludes these as the reproduced primary predicate:

- both GET status paths passed after restart;
- the same Package, capability token, base URL, port, request bytes and parser
  worked before restart;
- immediate post-restart exact replay passed in the qualification run;
- SQL reconstructed the same successful result and counters;
- Uvicorn was healthy only after committed composition and startup
  reconciliation completed;
- no external network attempt or diagnostic occurred;
- the explicit-stage controller parsed application HTTP 422 and the exact
  stable code `CLIENT_TIMESTAMP_OUT_OF_RANGE`.

The liveness-only health route remains a general readiness warning, but no race
was reproduced here: repeated status reads and SQL audits passed, and the
failure appeared deterministically only after crossing the timestamp boundary.

## 6. Synthetic success construction

Two isolated databases were migrated to sole/current head `20260805_0005` in
one fresh loopback-only PostgreSQL 18.1 cluster. A fresh fictional Package was
compiled and pristine-validated outside Git. Its recursive pre-manifest was
protected mode `0600`.

Each synthetic successful operation was created through the committed
`OpenAlexPaperSearchAdapter`, `CloudAPIProxyService`, and
`SQLProxyUnitOfWork`. The adapter used:

- a runtime-generated synthetic credential source;
- a one-response scripted transport;
- two wholly fictional Work-shaped records;
- formatting-control normalization in an abstract token;
- exact synthetic cost/rate evidence for 1,000 microusd.

No real response, real scholarly metadata, captured R3C-A-R4 value, real query,
real key, or external network was used. The normal service/repository path
persisted one `SUCCEEDED` operation, two normalized Works, normalized JSON and
its checksums/size, one Provider-call reservation, 1,000 reserved and 1,000
reported microusd, and `CHECKSUM_ONLY` request evidence. SQL retained query
checksum/length only, no query text, raw body, or unknown synthetic field.
No Hosted ProviderOperation or WorkflowRun was created.

## 7. Real restart qualification

Both controlled runs used real Uvicorn on literal `127.0.0.1`, the committed
ASGI application, real PostgreSQL persistence, the explicit experimental
OpenAlex Proxy flag, provider-neutral client functions, a fictional capability
token, and socket/DNS canaries that allowed only loopback/Unix connections.
Access logging was disabled. External Provider transport attempts remained
zero.

### Delayed-replay reproduction

Before restart, both status paths and exact replay passed over real HTTP. The
same PostgreSQL data directory was stopped and restarted, readiness was bounded,
revision `20260805_0005` was confirmed, and a second Uvicorn generation became
healthy. After the original timestamp became older than five minutes:

- status by operation ID passed;
- status by scoped idempotency identity passed;
- the original-equivalent controller raised `RuntimeError` on replay;
- the explicit-stage controller received HTTP 422 JSON with
  `CLIENT_TIMESTAMP_OUT_OF_RANGE` at exact replay;
- SQL remained one succeeded operation, one call, 1,000 reserved and 1,000
  reported microusd;
- no duplicate, diagnostic, Hosted row, or network attempt occurred.

### Immediate-restart qualification

A separate fresh synthetic operation exercised the same physical
PostgreSQL/Uvicorn restart while the request remained within the current
five-minute window. Both Uvicorn generations used the same protected
runtime-generated synthetic server credential and equivalent configuration.
Before and after restart:

- status by operation ID passed;
- status by scoped idempotency identity passed;
- exact request-byte replay passed;
- operation ID, normalized result, request/result/response checksums, result
  count and canonical size were unchanged;
- SQL remained one operation/call and exactly 1,000 reserved/reported
  microusd;
- no duplicate, diagnostic, Provider transport, or Hosted row appeared.

```text
OFFLINE_RESTART_FAILURE_REPRODUCTION = PASS
SYNTHETIC_POST_RESTART_STATUS_BY_ID = PASS
SYNTHETIC_POST_RESTART_STATUS_BY_IDEMPOTENCY = PASS
SYNTHETIC_POST_RESTART_EXACT_REPLAY = PASS
```

`PASS` for failure reproduction means the delayed failure was deterministic at
one source predicate. The separate exact-replay `PASS` records the immediate
real-restart qualification; it does not erase the delayed-replay defect.

## 8. Controller comparison and classification

The original-equivalent controller reconstructed the only sequence preserved
by R3C-A-R4: status by operation ID, status by scoped idempotency identity, then
exact POST replay through the committed provider-neutral client. It reproduced
the value-free `RuntimeError` after the timestamp boundary.

The explicit-stage controller used the same persisted operation, token,
Package and request bytes. It labelled each GET as passing and parsed the replay
failure as HTTP 422 / `CLIENT_TIMESTAMP_OUT_OF_RANGE`. Both controllers fail at
the same committed application predicate; this is not a controller-only parser,
path, assertion, environment, or readiness defect.

The closest required primary classification is `CLIENT_RECOVERY_DEFECT`:
the provider-neutral recovery path cannot perform a contract-valid delayed
exact replay. The defect locus is application service admission ordering, not
the HTTP client's JSON parser. Confidence is medium for identifying this as the
exact historical R3C-A-R4 substep because the historical route/HTTP status was
not preserved; confidence is high that the offline predicate itself is real
and deterministic.

```text
RESTART_ROOT_CAUSE_CLASSIFICATION = CLIENT_RECOVERY_DEFECT
RESTART_ROOT_CAUSE_CONFIDENCE = MEDIUM
```

## 9. Security and product boundary

Private scans verified that neither synthetic query nor plaintext capability
nor synthetic server credential appeared in SQL, process logs, the Package, or
tracked files. The unique unapproved synthetic response field was absent from
SQL, proving raw/unknown response content was not retained. Request parameters
were absent from `CHECKSUM_ONLY` SQL evidence. Protected transient request,
token and credential files were mode `0600` and were used only for replay and
the supervised child environment.

Hosted ProviderOperation, WorkflowRun, WorkflowStepRun, ExecutionEvent,
Checkpoint, checkpoint-record, MemoryRevision, and uploaded Progress Report
rows stayed zero. AgentRuntime, ExecutionDispatcher, Workflow execution,
Hosted Skills, LLM/structured generation, Judge/evaluation, and automatic
Progress Report generation/upload were not invoked. The external Package
post-manifest was byte-identical to its pre-manifest.

The teacher boundary remains unchanged: cloud performs bounded credentialed
transport/normalization/provenance/accounting; the local Harness owns research
selection and interpretation; local Package state remains authoritative; no
cloud research synthesis or continuation occurred.

## 10. Tests

Using Conda environment `reagent-dev`:

| Gate | Result |
|---|---|
| focused OpenAlex adapter | 154 passed |
| complete Cloud API Proxy | 216 passed |
| required Proxy/OpenAlex PostgreSQL | 13 passed, zero skipped |
| Workflow Package | 43 passed |
| Progress Report | 38 passed |
| full backend | 526 passed, 4 skipped |
| `compileall -q backend` | exit 0 |
| Alembic heads/current | sole/current `20260805_0005` |
| Alembic check | no new upgrade operations |
| `git diff --check` | pass |

The four full-backend skips were separately gated integrations: destructive
E2E PostgreSQL, 9B-1 isolated OpenAlex contract, separately live OpenAlex, and
9A-2 research-v2. No Proxy/OpenAlex PostgreSQL test skipped.

## 11. Remediation decision

```text
R3C_RECOMMENDED_NEXT_ROUTE = APPLICATION_RECOVERY_REMEDIATION_REQUIRED
```

The minimal future correction is confined to exact-replay admission ordering
in `backend/cloud_api_proxy/service.py`. After request checksum/safety and
authentication/authorization, the service should consult the scoped existing
idempotency row and return/conflict deterministically before applying freshness
only to a newly admitted request. It must not weaken UUIDv4, checksum, scope,
token expiry/revocation, safety, conflict, cost, call, or no-retry behavior.

Required regression coverage is a delayed exact replay with an advanced clock,
including SQL reload and real HTTP restart qualification, plus adjacent stale
new-request rejection and changed-content conflict. No migration, API response,
request/operation/checksum identity, retention, or cost semantic should change.
No additional live Provider call is necessary: the defect is pre-transport and
R3C-A-R4's accepted live normalization/cost evidence remains preserved. A
future owner-approved closure can qualify the corrected restart/replay path
with seeded synthetic persisted state.

No production correction was implemented in R3C-R1.

## 12. Gate state

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
