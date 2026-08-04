# R3C-I OpenAlex Proxy Implementation Acceptance Plan

Status: **FUTURE IMPLEMENTATION/QUALIFICATION PLAN — NOT STARTED**
Live Provider/API key/Internet: **PROHIBITED**
Required terminal state: `R3C_STATE = LIVE_ACCEPTANCE_PENDING`

## 1. Purpose and baseline gate

R3C-I implements the ADR 0012 adapter behind the already separate
`backend/cloud_api_proxy/` domain and qualifies it with scripted transport and
isolated PostgreSQL. It is not live-provider acceptance.

Before work, require the exact owner-approved R3C-D commit, `main`, clean Git,
one Alembic head, ignored `.env`/`runtime_data/`, and no runtime evidence. Stop
on a dirty or unexplained baseline without cleaning, restoring or discarding
files.

Read ADRs 0009–0012, the current source/adapter audit, the OpenAlex adapter
contract, security policy, Cloud Proxy contract/threat model and R3B-I/R3B-A
evidence. Recheck that no later authoritative decision supersedes limits.

## 2. Permitted implementation

R3C-I may add only what is necessary for one disabled-by-default OpenAlex
`paper.search/v0.1` adapter:

- a scripted-transport-friendly live adapter behind the existing Proxy port;
- server-only `REAGENT_OPENALEX_API_KEY` configuration with redaction;
- `REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED`, false by default;
- OpenAlex adapter token scope/issuance for an operator-only experimental CLI;
- exact decimal cost/call evidence and safe Provider status metadata;
- additive Proxy SQL fields/migration only if current columns cannot represent
  exact live usage safely;
- fixed-origin transport and safe error normalization;
- network-free unit/API/client/SQL/security/boundary tests;
- documentation and an R3C-A handoff update.

It must not change `paper.search/v0.1`, Progress Reports, local Package task
state, frontend, Hosted Runtime, research Skills or LLM behavior.

## 3. Scripted Provider contract qualification

All adapter tests use an injected scripted/mock transport. A network canary
must fail on any socket, HTTPX, urllib, requests or Hosted OpenAlex transport
attempt.

Verify exact outbound mapping:

```text
GET https://api.openalex.org/works
search=<unchanged trimmed query>
per_page=<1..20>
select=id,doi,display_name,authorships,abstract_inverted_index,publication_year,primary_location,language
api_key=<injected synthetic test secret, absent from evidence>
```

Assert no filter/sort/page/cursor/group/sample/semantic/content parameter, no
query rewrite, one call, redirects disabled, TLS required, ambient proxies
disabled, bounded timeout and actual 512-KiB response cap.

Use wholly fictional response records to test every mapped field, missing
optional fields, malformed IDs/DOIs/authorships/abstract positions, duplicate
identity, unsafe Unicode/control/script-like data, too many results, malformed
JSON/root/meta/results, unsupported encoding and raw-body non-retention.

## 4. Usage, cost and budget qualification

Test exact non-rounded `$0.001` reservation/settlement and the current safe
headers plus `meta.cost_usd`. Cover missing, malformed, negative, excessive and
contradictory cost/credit evidence; changed official price classification;
operation/call cap 20; total cap `$0.05`; absent key; and prepaid use prohibited.

An exact replay and idempotency conflict must consume no scripted Provider call
or additional cost. A new UUIDv4 key for the same query is a new admitted
operation and one scripted call. No `/rate-limit` or other second request is
allowed.

## 5. Error and retry matrix

Script the safe classifications for authentication, authorization, rate limit,
budget exhaustion, timeout, unavailable/DNS/TLS/5xx, malformed response,
oversized response, contract/cost change and reconciliation required.

No case retries automatically. Raw error bodies, HTML, credential URL, key and
traceback never enter API response, SQL, stdout/stderr or logs. The response
does not expose Provider-specific fields beyond the approved safe provenance.

## 6. Idempotency and reconciliation

Reuse the accepted R3B non-cyclic request/operation/response identities and SQL
scoped uniqueness. With scripted call counters prove:

- sequential and concurrent exact replay: one effective ProxyOperation and one
  Provider call;
- same scoped key with changed content: `IDEMPOTENCY_CONFLICT`, zero new call;
- process loss before call: conservative persisted state, no call;
- uncertain timeout after request dispatch: `RECONCILIATION_REQUIRED`;
- repository reload/startup: no automatic Provider invocation;
- status by operation ID and scoped idempotency identity;
- exact POST replay of every terminal/uncertain state never reissues the call.

Do not add worker, queue, lease, fallback or retry engine.

## 7. Persistence qualification

Use a fresh loopback-only PostgreSQL cluster, never ProjectDB, with separate
R3C-I migration and test databases. If an additive revision is required:

- preserve one head and reversible one-revision downgrade/re-upgrade;
- add only Proxy-domain fields/tables;
- store no Hosted WorkflowRun/step/provider-operation foreign key;
- store no key, credential URL, raw body or query text;
- preserve exact request/result/response identity, live adapter ID, call count,
  decimal cost, safe Provider evidence and reconciliation status;
- qualify real concurrent idempotency and budget admission;
- prove restart/repository reload reconstructs exact operation data.

Run `alembic heads`, upgrade, current, check, one-revision downgrade/re-upgrade,
and inspect constraints/columns. New Proxy PostgreSQL tests may not skip.

## 8. Token, API and client behavior

R3C-I may extend the operator CLI only to issue an experimental OpenAlex-
adapter scope with maximum 20 operations. It retains R3B’s digest-only,
short-lived, revocable, loopback token lifecycle; the Provider key is never part
of that token.

The external request/route and local client remain provider-neutral. The client
accepts no Provider/key/URL argument and performs no ambiguous retry or Package
mutation. Status reconciliation stays explicit. OpenAlex remains disabled by
default and cannot be selected through client JSON.

## 9. Boundary and secret evidence

Static imports and runtime canaries must prove the live Proxy route cannot call
or instantiate AgentRuntime, ExecutionDispatcher, Workflow/Skill execution,
Hosted ProviderOperation, OpenAlex Hosted composition, LLM, Judge, Progress
Report upload or local Package mutation.

Capture a synthetic credential canary and prove it is absent from database,
result persistence, logs, stdout/stderr, errors, API responses and generated
Package files. Assert no complete outbound URL is logged and no raw body is
retained.

## 10. Required test classes

At minimum:

- OpenAlex request mapping and fixed field allowlist;
- response normalization and untrusted-data handling;
- current `meta.cost_usd` and rate-header parsing;
- exact call/cost budgets and sub-cent precision;
- key absence/injection/redaction;
- fixed origin, redirects, TLS, ambient proxy and timeout;
- body/record/result limits and malformed response;
- all stable error categories;
- sequential/concurrent idempotency and changed-content conflict;
- uncertain timeout/reconciliation and reload without call;
- token scope/count/revocation;
- API/client/provider-neutral behavior;
- default-disabled/fail-closed composition;
- zero network/Hosted/LLM/Workflow/Progress/local mutation;
- isolated PostgreSQL migration, concurrency and restart/reload;
- existing fake Proxy, Package, Progress Report and full-backend regression.

Every test uses fictional data. No API key, real Provider response or private
research query may be committed.

## 11. Documentation and Git closure

Record exact module paths, feature flag, adapter ID, migration, SQL storage,
field mapping, cost arithmetic, tests/skips and known warnings in one R3C-I
progress report and context update. Do not create a live-acceptance report or
claim R3C-A passed.

Review the complete diff, require only approved implementation/tests/docs,
create one clean R3C-I commit, do not push, and end with a clean tree.

R3C-I passes only if all network-free and PostgreSQL gates pass and the final
state is:

```text
R3C_I_IMPLEMENTATION = PASS_WITH_WARNINGS or PASS
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3C_A_LIVE_ACCEPTANCE_GATE = CLOSED
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```
