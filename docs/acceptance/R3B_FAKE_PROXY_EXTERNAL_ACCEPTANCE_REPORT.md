# R3B-A Fake Proxy External Acceptance Report

Status: **PASS_WITH_WARNINGS**

Date: 2026-08-04

Baseline: `6a64d5827f18ee24e8fe2d71f66e78b26a9fcc44`
(`R3B-I: implement experimental fake cloud API proxy`), branch `main`, with
an initially clean working tree.

This report records external runtime acceptance of the already committed R3B
experimental fake-provider slice. It does not authorize R3C, a real provider,
public deployment, production authentication, Hosted research execution or a
Progress Report contract change.

## Acceptance verdict

The full teacher-aligned path passed:

```text
external fictional Workflow Package
  -> operator-issued short-lived capability token
  -> explicit local client
  -> real HTTP on 127.0.0.1
  -> real Uvicorn/FastAPI process
  -> isolated PostgreSQL 18.1
  -> deterministic fake paper-search adapter
  -> durable ProxyOperation and explicit status reads
  -> Uvicorn and PostgreSQL stop/start
  -> exact recovery
```

The cloud authenticated, authorized, validated, bounded, persisted and returned
fictional provider data. It did not select or interpret a research question,
rank papers, synthesize literature, run a Workflow, modify the Package or
generate/upload a Progress Report.

Final acceptance states:

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

## Isolated PostgreSQL and migration

- PostgreSQL: 18.1, initialized as a fresh data-checksummed temporary cluster.
- Binding: loopback only, unique port `55483`; the cluster was controlled only
  by this acceptance.
- Acceptance database: `reagent_r3ba_acceptance_20260804_55483`.
- Test database: `reagent_r3ba_tests_20260804_55483`.
- Sanitized URLs:
  `postgresql+psycopg://127.0.0.1:55483/<database>?password=<password-omitted>`.
- `ProjectDB` was absent from the cluster catalog and was neither connected to
  nor modified.

The acceptance database upgraded from empty state to the sole Alembic head
`20260804_0004`. `alembic current` returned that head and `alembic check`
reported no new upgrade operations. Direct catalog inspection confirmed
`proxy_capability_tokens` and `proxy_operations`, SHA-256 token-digest
uniqueness, scoped `(token_id, idempotency_key)` uniqueness and the expected
indexes/check constraints. There is no plaintext-token column and the only
Proxy-operation foreign key targets the Proxy token table, not Hosted
WorkflowRun or step state.

## External Package evidence

A fresh fictional package was compiled outside Git with the committed
compiler/template and validated from its external location:

- project: `fictional-r3ba-proxy-20260804`;
- package ID: `literature-search-fictional-r3ba-proxy-20260804-v0.2`;
- package checksum:
  `sha256:d56d21165507a8bc8a7e74471269a902d77c5224a3ec505b2d29baae7cbab39b`;
- package-manifest checksum:
  `sha256:8afd38a78dcf551406b4f025094db9f00398b2c8bfa28145b7e5250f039a84cc`;
- Workflow: `literature-search-local-experimental`, version `0.1.0`;
- Workflow checksum:
  `sha256:8d25d7cd32a89e84ba8885454782cb923e93224df4637ddf6183af2a16f3980c`;
- ZIP checksum:
  `sha256:ef48d5f13c449004ae2a1483df3d6ac3c7d14a17ce28a96b34cf2a1838c2f50a`.

The Package declared the proxy disabled, no credential, no real provider and
no external network. Both initial and final pristine self-validation passed.
It contained fictional inputs only and no R1 execution evidence, private
research data, token, database URL or machine path.

The recursive manifest covered 34 relative path entries with file type, byte
size and content SHA-256. Before and after acceptance it had the same canonical
checksum:
`sha256:0d149b2090b2b4f85aa6f44ad7bbff35529ff3e181ca99c071c2bc168ce0a459`.
The complete manifest files were byte-identical, with file checksum
`9854c5c5756de727e87f467dd7184ce86712f5275ca25648c151e047fe40c062`.

## Capability-token lifecycle

The operator CLI issued four fictional, independently scoped acceptance token
records: primary, three-operation limited, revocation and equivalent-scope
comparison. Every plaintext file was created outside Git and the Package with
mode exactly `0600` and 44 bytes of URL-safe token material. Issuance printed
safe metadata only; stdout, stderr and logs contained no plaintext. An attempt
to overwrite the primary token file failed closed and did not alter the file.

Sanitized issuance shape:

```text
REAGENT_DATABASE_URL=<isolated-acceptance-database> \
conda run --no-capture-output -n reagent-dev python -m \
  backend.cloud_api_proxy.operator_cli issue \
  --project-id fictional-r3ba-proxy-20260804 \
  --package-root <external-package-root> \
  --tenant-id fictional-r3ba-tenant \
  --subject-id fictional-r3ba-owner \
  --output-file <token-file> \
  --lifetime-minutes 120 --maximum-operations <bounded-count>
```

All records bound tenant, subject, project, exact Package and Workflow
identity/checksums, `paper.search/v0.1`, adapter
`deterministic-fake-paper-search/v0.1`, lifetime and operation count. The
acceptance lifetime was 120 minutes. SQL contained digest-only values; API
responses exposed neither digest nor plaintext. Revocation through the
operator CLI persisted `revoked=true` and a revocation timestamp, and live HTTP
returned `401 UNAUTHORIZED` without admission or adapter use. The revoked state
survived restart.

A private comparison against every issued plaintext scanned 1,955 acceptance
files excluding the four designated token files, all Git-tracked files and the
text/JSON form of both Proxy SQL tables. Match counts were zero in every area.
The remaining tokens were revoked before cleanup, and all plaintext files were
deleted.

## Feature flag, server and loopback transport

With `REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED` absent, a real Uvicorn process
served ordinary health but the Proxy route returned `404`; no ProxyOperation
row or fake operation was created. With the flag enabled and an intentionally
invalid isolated loopback SQL target, application composition failed during
startup and did not expose an operational route or fall back to in-memory,
SQLite or another database.

The accepted server used the committed `backend.api.app:app` entrypoint, the
explicit feature flag, the isolated acceptance database and literal
`127.0.0.1` on unique HTTP port `58431`. Uvicorn was launched with proxy-header
parsing disabled, so the application authorized the actual peer rather than an
untrusted forwarded value. A non-approved Host failed closed; an
`X-Forwarded-For` canary could not override the real peer. Point-in-time socket
inspection showed only the loopback Uvicorn listener and its loopback
PostgreSQL connection. This was combined with static imports, adapter canaries,
absent provider credentials and logs; it is not represented as packet capture.

Sanitized accepted launch shape:

```text
REAGENT_DATABASE_URL=<isolated-acceptance-database> \
REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED=1 \
REAGENT_ARTIFACT_ROOT=<isolated-artifact-root> \
conda run --no-capture-output -n reagent-dev \
  uvicorn backend.api.app:app --host 127.0.0.1 --port 58431 \
  --no-proxy-headers
```

The committed fake Proxy persisted its approved normalized result in
PostgreSQL; it did not create a provider-response artifact. The isolated
artifact setting existed only to prevent any unrelated application fallback
from reaching repository or user data.

The local client accepted only literal `http://127.0.0.1:<port>` and rejected
`localhost`, a remote IP, userinfo, a credentialed URL and fragments. No token
appeared in a URL or response.

## Native successful operation and checksums

The primary operation succeeded through the committed CLI and live HTTP:

- operation ID:
  `proxyop-v1-f790d889e15ac436842c637a705d4d687d702a068b75bfc480b9dd34b1f5b827`;
- request-content checksum:
  `sha256:b4f31224c8d3068d18ad8b9e8dd4db28551ba7e2920943d22d4035cd48f40d78`;
- provider-data checksum:
  `sha256:02e3063d88fb287dfac5f5077dfa35796315fa9ba48a99675f01a804f55c5792`;
- response-content checksum:
  `sha256:26180060efe3f19fda06951cb4a5b07264bdbdedb6a9926f34db7ecb1a072f6b`;
- delivery checksum:
  `sha256:ee6d9404bd35de0b72b204f429787017e3edb8233d1f1803aa41026504da2230`;
- result size: 4,518 canonical bytes; five fictional paper records;
- monetary cost and real-provider usage: zero.

An independent canonical reconstruction verified request, authorization-scope,
operation, provider-data, response-content and delivery checksums. It also
verified that operation ID, idempotency key, credentials, token plaintext and
server-generated delivery time are excluded from request content as specified.
Reads by operation ID and by scoped idempotency identity returned the same
durable operation. SQL contained one Proxy row referencing the correct token,
safe normalized fake data and no raw provider body or Authorization header.

The same normalized query under a new UUIDv4 produced a distinct operation
identity and admission but the same deterministic provider-data checksum.
After restart the same behavior remained deterministic.

## Legitimate-query and rejection matrices

Seven ordinary scholarly-query forms passed over live HTTP: Chinese UTF-8,
English with hyphens, colon/parentheses, quoted phrases, DOI-shaped text, an
exactly 500-character query, and digits/version-like text. Outer whitespace was
trimmed; no valid text was truncated; results remained fictional and
deterministic.

Authentication/authorization matrix: 19 of 19 cases produced the committed
safe response with no count or adapter change. Missing/malformed/unknown or
revoked bearer credentials returned HTTP 401 with `UNAUTHORIZED`. Wrong project
path or body, Package ID/checksum, Workflow ID/version/checksum returned HTTP
403 with `AUTHORIZATION_SCOPE_MISMATCH`. Wrong capability/adapter and
client-supplied actor, role, tenant, subject or ownership claims returned HTTP
422 with `INVALID_REQUEST` before admission.

Schema/size/timestamp/unsafe-content matrix: 32 of 32 cases were safely
rejected without admission or result persistence. Coverage included empty and
overlong query, invalid and boolean `max_results`, unknown/provider/URL/header/
credential/path/full-text/PDF/prompt/ranking fields, malformed JSON, missing or
invalid/stale/future timestamp, invalid or non-v4 idempotency key, control
characters and fictional secret/script/path canaries. Actual over-16-KiB and
chunked over-16-KiB bodies returned `413 REQUEST_BODY_TOO_LARGE`; a false
undersized Content-Length did not bypass validation. A body exactly 16 KiB
passed the byte gate and was then rejected by the strict schema. Unsafe
canaries returned `UNSAFE_REQUEST_CONTENT`. Canary values were not retained in
tracked evidence.

The focused oversized-result test also passed: over-512-KiB canonical output
becomes safe terminal failure without persisting or delivering the result.

## Idempotency, scope and operation count

Sequential exact replay returned the original operation as `REPLAYED`, with no
new row, count or fake-adapter effect. Two independent concurrent real HTTP
clients submitted exactly the same bytes and key; one received `201 CREATED`
and one `200 REPLAYED`, both referring to the single operation:
`proxyop-v1-cf006c96cdf5a887e0257756e491a5375b6e4030aae685e7c541f4d77ed3b123`.
Primary rows/admissions moved from 17 to 18 exactly once. Changed valid content
under that key returned `409 IDEMPOTENCY_CONFLICT`; the original row and count
were unchanged. A changed client timestamp is content change and likewise
conflicted.

The contract and implementation include `token_id` in the stable authorization
scope. Two tokens with otherwise identical claims, the same request content
and the same idempotency UUID therefore created distinct valid operations, with
the same provider-data checksum and different operation IDs. This observed
behavior confirms the committed scoped-idempotency meaning; it does not redefine
it.

The limited token admitted exactly three distinct operations. Exact replay,
content conflict, status reads and pre-admission rejection consumed no extra
count. A fourth new operation returned `429 OPERATION_LIMIT_EXHAUSTED` before
adapter use; SQL remained three rows and `3/3` admitted. Admitted terminal and
reconciliation operations remained counted.

Live active-slot saturation was not induced because the committed deterministic
adapter has no acceptance delay/fault mode. The real PostgreSQL concurrency
test `test_sql_concurrent_active_limit_is_transactionally_enforced` executed
and passed; this is retained as a warning, not represented as live-Uvicorn
saturation evidence.

## Disconnect, reconciliation and restart

A bounded raw loopback client sent a complete authenticated POST and closed
before reading. No POST retry occurred. Scoped status found one durable
`SUCCEEDED` operation:
`proxyop-v1-ee39da52b66b916d72e121b9455ba790e9b357022740ec424859173a9ec28f19`.
Later exact replay returned that operation without another row or admission.

For interrupted-work reconstruction, a temporary acceptance script used the
committed domain and SQL Unit of Work—not Hosted records and not adapter
execution—to persist one identity-valid `RUNNING` ProxyOperation. Fresh server
startup transitioned it to `RECONCILIATION_REQUIRED` with unchanged operation,
request and idempotency identities, no fabricated result and no second adapter
call:

- operation ID:
  `proxyop-v1-f4b0a45095edde25522207b330be3659d91d5c3cb40f3036058b6c73e7581f85`;
- request checksum:
  `sha256:7dba9c3f2bc381138680d39b0b321dafd0715545faae7adf91060e25df8fc949`;
- error: `INTERRUPTED_OPERATION`;
- evidence: `PROCESS_RESTART_NO_LIVE_ADAPTER_EXECUTION`.

Reads by operation ID and idempotency key returned that state. Exact POST replay
returned the existing reconciliation record and did not invoke the adapter.

Before the combined restart, the canonical SQL snapshot contained four token
records and 26 operation records; all Hosted and Progress Report comparison
tables were empty. Its checksum was
`sha256:f949899bbedd588f27a1430a69aeabea9ca1d35afe1d016fee5e5f7c079a938a`.
Uvicorn and the dedicated PostgreSQL cluster were stopped cleanly, then the
same database data was restarted at revision `20260804_0004` and Uvicorn was
started against it. The canonical snapshot was byte-identical. A pre-restart
success record and its normalized JSON/checksums were unchanged; exact replay
remained idempotent; the revoked token remained revoked; the interrupted row
remained `RECONCILIATION_REQUIRED`; no Hosted row appeared. A new-key request
after restart produced a new operation with the same deterministic fake-data
checksum.

The operation-count audit reconciled to the SQL rows: before restart, primary
had 22, limited had 3, equivalent-scope had 1 and revocation had 0 operations
(26 total). The byte-identical post-restart snapshot retained those counts. The
single intentional new-key request after restart advanced primary to 23 and
the total to 27. Replays, conflicts, status reads, authentication/schema
rejections and revocation did not add rows.

## Runtime/provider/Hosted boundary

Hosted `provider_operations`, Workflow runs/steps, execution events,
checkpoints, memory revisions and Progress Report rows were zero before and
after the accepted Proxy path. The Proxy SQL model has no Hosted foreign key.
Production import inspection found no AgentRuntime, ExecutionDispatcher,
OpenAlex, LLM, structured-generation or Hosted-state dependency in the Proxy
service/fake-adapter path. The fake-adapter socket/HTTP canary passed. No
provider credential was configured or read, and accepted server logs contained
no token, Authorization header, Package path or research body.

No real provider, OpenAlex, non-loopback Internet, LLM, structured generation,
Judge, Workflow execution/resume, automatic Progress Report action or local
Package mutation occurred.

## Automated validation

All commands used Conda environment `reagent-dev`:

| Command | Exit | Result |
|---|---:|---|
| `python -m pytest -q backend/cloud_api_proxy/tests` | 0 | 53 passed |
| `python -m pytest -q backend/database/tests/test_cloud_api_proxy_postgresql.py` | 0 | 7 passed, 0 skipped |
| `python -m pytest -q backend/workflow_packages/tests` | 0 | 43 passed |
| `python -m pytest -q backend/progress_reports/tests` | 0 | 38 passed |
| `python -m pytest -q -rs backend` | 0 | 357 passed, 4 skipped |
| `python -m compileall -q backend` | 0 | passed, no output |
| `alembic heads` | 0 | sole head `20260804_0004` |
| `alembic current` | 0 | current `20260804_0004` |
| `alembic check` | 0 | no new upgrade operations |
| `git diff --check` | 0 | clean |

The Proxy PostgreSQL suite initially could not open the isolated loopback socket
under the command sandbox (`Operation not permitted`). The identical test was
rerun with explicit loopback permission and passed all seven tests with no
skip; this was environment isolation, not an application or PostgreSQL failure.

The four full-suite skips are unrelated and explicitly gated:

1. destructive isolated PostgreSQL HTTP demo requires
   `REAGENT_E2E_DATABASE_URL` and reset opt-in;
2. historical 9B-1 OpenAlex contract acceptance requires its isolated
   database/artifact root;
3. live OpenAlex acceptance requires explicit live authorization;
4. historical 9A-2 hosted-research acceptance requires its isolated settings.

None is an R3B Proxy PostgreSQL test, and no live-provider gate was enabled.

## Cleanup and remaining warnings

After all recovery and leakage evidence was captured, remaining acceptance
tokens were revoked, Uvicorn and the dedicated PostgreSQL cluster were stopped,
ports were released, and the token files, external Package, database data,
logs, raw HTTP fixtures and other acceptance-created temporary files were
removed. No database, log, token or Package runtime evidence is tracked.

Remaining warnings:

- live active-operation-slot saturation was not separately induced through
  Uvicorn; the real SQL concurrency gate passed;
- external wall-clock expiry was not repeated; focused revoked/expired token
  tests passed;
- Claude Code remains untested and the optional Progress UI remains deferred;
- bearer proof of possession, HTTPS/public deployment, production
  authentication and multi-user authorization remain unapproved;
- real-provider eligibility, credentials, rate/cost/retry and retention remain
  unresolved, so R3C stays closed;
- existing R2 missing-predecessor/no-op-context and explicit-upload warnings
  are unchanged.

R3B-A proves only the owner-approved, fake-only, loopback experimental Proxy.
It is not production authentication or live-provider acceptance.
