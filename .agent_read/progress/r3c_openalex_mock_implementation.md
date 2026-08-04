# R3C-I Mocked OpenAlex Proxy Implementation

Date: 2026-08-04

## Phase result

```text
R3C_I_IMPLEMENTATION = PASS_WITH_WARNINGS
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3C_A_ENTRY_READINESS = READY_FOR_OWNER_REVIEW
R3C_A_LIVE_ACCEPTANCE_GATE = CLOSED
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
R3C_LIVE_PROVIDER_CALL_COUNT = 0
```

This phase implemented and qualified the owner-ratified OpenAlex metadata
adapter with fictional scripted responses only. It did not perform the
separately gated R3C-A live acceptance.

## Baseline and authority

The initial gate passed on branch `main` at exact clean commit
`66cb5bc57daff79ea5a31a70661510bfed87bc5c` (`R3C-D: ratify supervised
OpenAlex provider boundary`). ADRs 0009–0012, the R3C-D source/adapter audit,
the OpenAlex adapter contract, the Cloud Proxy contract/threat model and the
teacher architecture PDF governed the work. No `.env`, real Provider key,
official documentation site or Provider API was accessed.

## Existing-adapter reuse audit

- Reused unchanged behind the Proxy: `PaperAuthor`, `PaperRecord`, canonical
  JSON/checksum primitives, the provider-neutral `paper.search/v0.1` request,
  capability-token digest/authentication, operation/idempotency identities,
  separate Proxy repository/UoW, loopback API/client and fake adapter.
- Adapted behind the separate boundary: Proxy adapter registry, token scope,
  request-retention evidence, usage/cost contract, SQL mapping, operator token
  issuance and experimental composition.
- New R3C boundary: credential source, fixed-origin transport, OpenAlex
  request mapper/normalizer and safe Provider error model.
- Retained Hosted-only and prohibited from the R3C route:
  `backend/research/adapters/openalex.py`, Hosted `ProviderOperation`,
  WorkflowRun/StepRun, research Skills, AgentRuntime, ExecutionDispatcher and
  LLM/structured-generation paths. The old Hosted adapter was not registered
  or wrapped as Proxy authority.

## Implemented boundary

`backend/cloud_api_proxy/openalex_adapter.py` implements adapter
`reagent.openalex-paper-search/v0.1`. Server-owned token scope selects it; the
client cannot submit a Provider/adapter/URL/header/method. The adapter maps the
outer-trimmed query unchanged to `search`, maps `max_results` to `per_page`,
and uses the fixed select list:

```text
id,doi,display_name,authorships,abstract_inverted_index,
publication_year,primary_location,language
```

The future transport is structurally fixed to one HTTPS `GET /works`, TLS
verification, redirects off, ambient proxies off, ten-second bounded timeouts,
512 KiB streamed decoded-response limit, and zero retry. R3C-I injected only a
scripted transport. A network canary replaced socket, DNS and common HTTP
entrypoints and observed no attempt. HTTPX request-line logging is suppressed
on the Provider-call thread so query/key parameters cannot enter its standard
URL log.

Only approved normalized `PaperRecord` metadata is returned, in Provider order.
The adapter reconstructs a bounded abstract deterministically, rejects invalid
identities/authorships/positions/control text and never follows a DOI or
Provider URL. Primary-location URLs and unknown Provider fields are discarded.
There is no relevance label, score, reranking, summary or interpretation.

## Credential, privacy and retention

`EnvironmentOpenAlexCredentialSource` is lazy and names the sole future live
source `REAGENT_OPENALEX_API_KEY`. Default-disabled startup does not call it;
enabled composition validates it before the route becomes operational. R3C-I
tests used runtime-generated synthetic values injected directly through the
credential interface. They did not read the environment variable.

OpenAlex operations use `CHECKSUM_ONLY` request retention. PostgreSQL retains:

- canonical request checksum;
- query SHA-256, UTF-8 byte length and character length;
- `max_results`, Package/Workflow scope and idempotency identity;
- adapter/version, status, latency, safe rate evidence and checksums;
- approved normalized fictional metadata.

It does not retain query text, key, complete outbound URL, raw response body,
Authorization header or Hosted identity. Runtime-generated query/key markers
were absent from the operation ledger, token rows, result/status deliveries,
captured logs and safe exception text. Their values are intentionally not in
tracked evidence.

## Exact cost and budgets

Cost uses integer microusd (`USD 1 = 1,000,000 microusd`). JSON decimal values
are decoded directly to `Decimal`; binary float is never used for identity,
persistence or comparison. The qualified reservation is 1,000 microusd per
new OpenAlex operation and the token ceiling is 50,000 microusd. Token scope is
also capped at 20 admitted operations/Provider calls.

The SQL token row is locked before admission. One call and one 1,000-microusd
reservation are persisted transactionally with the operation. Exact replay,
idempotency conflict and pre-admission rejection reserve nothing. Both reserved
and reported evidence participate in the next admission decision. Provider
credits remain a separate bounded decimal string and are not USD. Missing,
malformed, negative, non-finite, over-precise or unexpected cost fails closed;
an unexpected price is `PROVIDER_CONTRACT_CHANGED` and receives no retry.

## Error, idempotency and reconciliation

The adapter implements the ratified categories:

```text
PROVIDER_AUTHENTICATION_FAILED
PROVIDER_AUTHORIZATION_FAILED
PROVIDER_RATE_LIMITED
PROVIDER_BUDGET_EXHAUSTED
PROVIDER_TIMEOUT
PROVIDER_UNAVAILABLE
PROVIDER_INVALID_RESPONSE
PROVIDER_RESPONSE_TOO_LARGE
PROVIDER_CONTRACT_CHANGED
PROVIDER_RECONCILIATION_REQUIRED
```

HTTP 3xx is never followed. Scripted 400/401/403/408/429/500/502/503/504,
malformed JSON/schema/metadata/cost/headers, raw and normalized overflow,
connect/TLS-like failure and uncertain read-timeout paths are safe and have no
automatic retry. An uncertain dispatched request becomes
`RECONCILIATION_REQUIRED`. Exact replay and application/repository
reconstruction return the existing operation and perform no second adapter
call. Changed content under the same scoped UUIDv4 key conflicts before the
adapter.

## Persistence and migration

Additive Alembic revision `20260805_0005` extends only the separate
`proxy_capability_tokens` and `proxy_operations` tables. Token rows receive
Provider call and exact microusd limits/counters. Operation rows receive
retention/query-checksum/length, Provider call/cost, safe status/rate evidence,
response checksum and adapter-version fields. Integer types, checks and unique
indexes were inspected directly.

The schema has no plaintext-key, query-text, raw-response, credential-URL or
Hosted WorkflowRun/step/provider-operation field. The sole operation foreign
key is to `proxy_capability_tokens`; scoped idempotency remains uniquely
enforced by `(token_id, idempotency_key)`. Historical fake rows remain
`FULL_PARAMETERS` and zero Provider cost/calls.

Qualification used a fresh loopback-only PostgreSQL 18.1 cluster on a unique
non-default port, with separate databases:

- `reagent_r3ci_migration_0804`;
- `reagent_r3ci_tests_0804`.

Neither is ProjectDB. Empty upgrade reached the sole head `20260805_0005`;
`alembic check` found no drift. Downgrade exactly one revision to
`20260804_0004`, re-upgrade and final drift check passed. Real concurrent SQL
replay/budget/admission and reload tests executed without skip.

## Reviewed changed-file inventory

Adapter/domain/composition:

- `backend/cloud_api_proxy/openalex_adapter.py` (new fixed adapter/transport);
- `backend/cloud_api_proxy/contracts.py`, `ports.py`, `service.py`, `sql.py`,
  `composition.py`, `operator_cli.py`, and `__init__.py` (provider-neutral
  registry, privacy evidence, exact budgets, SQL/composition and issuance).

Persistence/migration:

- `backend/database/orm/models.py`;
- `backend/database/migrations/versions/20260805_0005_openalex_proxy_privacy_cost.py`.

Focused/regression tests:

- `backend/cloud_api_proxy/tests/test_openalex_adapter.py`;
- `backend/cloud_api_proxy/tests/test_api.py`;
- `backend/cloud_api_proxy/tests/test_client_and_security.py`;
- `backend/database/tests/test_cloud_api_proxy_openalex_postgresql.py`;
- `backend/database/tests/test_cloud_api_proxy_postgresql.py`;
- `backend/database/tests/conftest.py`;
- `backend/database/tests/test_postgresql_persistence.py`.

Architecture/security/acceptance/progress documentation:

- `.agent_read/context.md` and this progress record;
- `docs/PROJECT_DEVELOPMENT_PLAN.md`;
- `docs/architecture/CLOUD_API_PROXY_V0_1_CONTRACT.md`;
- `docs/architecture/OPENALEX_PAPER_SEARCH_V0_1_ADAPTER_CONTRACT.md`;
- `docs/security/CLOUD_API_PROXY_THREAT_MODEL.md`;
- `docs/security/R3C_OPENALEX_CREDENTIAL_PRIVACY_AND_COST_POLICY.md`;
- `docs/acceptance/R3C_OPENALEX_IMPLEMENTATION_ACCEPTANCE.md`;
- `docs/acceptance/R3C_OPENALEX_LIVE_ACCEPTANCE.md`.

All 26 files fit an approved R3C-I category. No frontend, Package runtime,
Progress Report contract, Hosted execution source, real response fixture or
private runtime-evidence file changed.

## Verification

All commands used Conda environment `reagent-dev`.

| Command/suite | Result |
|---|---|
| `python -m pytest -q backend/cloud_api_proxy/tests/test_openalex_adapter.py` | 54 passed |
| `python -m pytest -q backend/cloud_api_proxy/tests` | 110 passed |
| Proxy/OpenAlex PostgreSQL test files | 13 passed, zero skipped |
| `python -m pytest -q backend/workflow_packages/tests` | 43 passed |
| `python -m pytest -q backend/progress_reports/tests` | 38 passed |
| `python -m pytest -q -rs backend` | 420 passed, 4 skipped |
| `python -m compileall -q backend` | exit 0 |
| Alembic heads/upgrade/current/check/downgrade/re-upgrade/check | exit 0; one head; no drift |

The four full-suite skips are pre-existing, separately gated integration
scenarios: destructive HTTP/PostgreSQL demo, 9B-1 isolated OpenAlex contract,
9B-1 live OpenAlex, and 9A-2 research-v2. No R3C-I mocked adapter or Proxy SQL
test skipped.

## Boundary evidence

Static imports and runtime canaries show the R3C route has no AgentRuntime,
ExecutionDispatcher, Hosted OpenAlex composition, WorkflowRun/StepRun,
Hosted ProviderOperation, research Skill, LLM, Judge or Progress Report service.
The API/client/Package and progress-report/v0.2 contracts did not change.
No local Package, output, context or Progress Report was created or mutated.

```text
R3C_OPENALEX_ADAPTER_IMPLEMENTATION = PASS
R3C_MOCK_TRANSPORT_QUALIFICATION = PASS
R3C_CREDENTIAL_BOUNDARY = PASS
R3C_QUERY_RETENTION_BOUNDARY = PASS
R3C_COST_BUDGET_IMPLEMENTATION = PASS
R3C_IDEMPOTENCY_RECONCILIATION = PASS
R3C_SQL_QUALIFICATION = PASS
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
R3C_LIVE_PROVIDER_CALL_COUNT = 0
```

## Remaining warnings and handoff

No live Provider call, real TLS/DNS/OpenAlex availability check, real
usage-header observation, real key loading, live Uvicorn external Package run
or wall-clock Provider timeout occurred. Official authentication/pricing/
headers/terms/privacy must be rechecked before R3C-A. Claude Code, frontend,
production authentication/multi-user authorization, public HTTPS/proof of
possession, production secret management and production Provider retention
remain unresolved.

Owner review of this clean R3C-I baseline is required before a separate R3C-A
start. R3C-A and R3D remain closed.
