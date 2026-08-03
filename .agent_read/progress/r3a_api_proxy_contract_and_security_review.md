# R3A API Proxy Contract and Security Review

Date: 2026-08-03

Status: **PASS_WITH_OWNER_DECISIONS_REQUIRED**

Baseline: `592410e274b07ac6480f12419b45cd9b742ff838`

## Owner ratification addendum — 2026-08-04

The original R3A review below is preserved as the record of the decision packet
before owner approval. Accepted ADR 0011 now resolves its `SOURCE_UNDECIDED`
items for R3B only:

- R3B classification is `EXPERIMENTAL_FAKE_PROVIDER_VERTICAL_SLICE`, disabled
  by default, loopback-only, deterministic-fake-adapter-only and not suitable
  for public/production use.
- Authentication is an operator-issued opaque bearer with at least 256 random
  bits, digest-only server storage, constant-time comparison, 60-minute default
  and 120-minute maximum lifetime, no refresh and explicit revocation. The
  plaintext is written once to a new `0600` file outside Git/Package, never
  logged/printed/passed as an argument or stored in `.env`, and is supplied to
  the client only through process environment `REAGENT_PROXY_TOKEN`.
- The server token record binds token/tenant/subject/project, exact Package and
  Workflow identity/checksums, `paper.search/v0.1`, the deterministic fake
  adapter, maximum operation count, issue/expiry and revocation state. Client
  actor/role/tenant/ownership/permission claims are not authorization.
- R3B uses loopback HTTP on `127.0.0.1`, plus or minus five minutes of timestamp
  skew, and no signature/nonce/proof of possession.
- `paper.search/v0.1` accepts only a trimmed 1–500-character UTF-8 `query` and
  integer `max_results` with default 10/range 1–20.
- Limits are 16 KiB request, 512 KiB normalized result, 10-second timeout, two
  concurrent and 50 total operations per token, and zero monetary,
  real-provider and external-network use.
- UUIDv4 idempotency, deterministic exact replay, HTTP 409
  `IDEMPOTENCY_CONFLICT`, explicit status reconciliation and the states
  `RECEIVED`, `RUNNING`, `SUCCEEDED`, `FAILED` and
  `RECONCILIATION_REQUIRED` are approved. Ambiguous automatic retry is not.
- R3B uses a separate Proxy operation/persistence boundary, not Hosted
  `ProviderOperation`, run/step/event/checkpoint/memory identity.
- Retention is acceptance-environment-lifetime only with safe normalized fake
  data; cleanup removes the isolated database cluster, artifact directory and
  plaintext token file. Raw bodies, credentials, tokens, Authorization headers,
  unsafe payloads and executable content are not persisted.
- R3B does not change or automatically create/upload/amend a Progress Report or
  mutate local state.

These decisions do not approve R3C, any live provider/credential, production
authentication or multi-user/public deployment. `R3B_IMPLEMENTATION_GATE` is
open after the clean R3A-D documentation closure; `R3C_LIVE_PROVIDER_GATE`
remains closed. R3B and R3C have not started.

## Outcome

R3A defines, but does not implement, the teacher-aligned local-Harness Cloud API
Proxy boundary. The cloud may authenticate, authorize, enforce an allowlisted
operation schema and limits, inject a server-side provider credential, perform
one bounded adapter operation, return untrusted provider data and retain
approved operational provenance. The local Codex/Claude Code Harness chooses
the request, interprets results, writes local outputs/context and produces any
Progress Report.

The cloud must not choose a research question, generate queries, rank sources,
synthesize findings, invoke an LLM for research, write Package files, generate
a Progress Report, resume a Workflow, invoke `AgentRuntime` or
`ExecutionDispatcher`, chain provider calls, accept arbitrary URLs or act as a
general HTTP proxy.

## Current-state audit

The repository has reusable canonical serialization, provider ports, normalized
result/failure contracts, provider usage/budget primitives, fake providers,
bounded OpenAlex transport/mapping, immutable artifact storage, PostgreSQL
provider-operation persistence and FastAPI composition.

They are not an existing proxy. Current OpenAlex selection is wired through:

```text
Hosted run/resume or approval
  -> ExecutionDispatcher
  -> AgentRuntime
  -> research Skills
  -> PaperSearchProvider/OpenAlex
  -> cloud ranking, synthesis and report paths
```

Current SQL `ProviderOperation` records require a Hosted `WorkflowRun` and lack
Package/Workflow-package/caller/capability/response identity. No authenticated
principal, bearer-token validation, project ownership enforcement or
multi-user authorization service exists. Request fields such as
`actor_user_id` are not authentication.

The exact inventory and reuse/prohibition matrix is in
`docs/audits/R3A_API_PROXY_CURRENT_STATE_INVENTORY.md`.

## Proposed contract

`docs/architecture/CLOUD_API_PROXY_V0_1_CONTRACT.md` proposes:

- envelope version `reagent.cloud-api-proxy/v0.1`;
- independent capability schemas, initially `paper.search/v0.1`;
- exact project, Package, Workflow, capability, Harness and limit identity;
- server-populated secret-free authorization context;
- strict normalized request/response data, no arbitrary URL/provider syntax;
- canonical UTF-8 JSON and SHA-256 identities;
- a non-cyclic chain:
  semantic request -> request-content checksum -> authorization-bound
  `proxyop-v1-*` operation ID -> provider outcome -> response-content checksum;
- same-key/same-request replay without another call;
- same-key/different-request conflict before provider use;
- explicit status reconciliation after ambiguous timeout/restart;
- provider transport error mapping and bounded same-operation retries;
- local Package configuration without a credential;
- no full text/PDF, ranking, relevance judgment, synthesis or LLM in the first
  slice.

## Security and owner packet

`docs/security/CLOUD_API_PROXY_THREAT_MODEL.md` covers credential leakage, SSRF,
private/loopback/link-local access, cross-project access, Package spoofing,
stolen credentials, replay/idempotency substitution, injection, body/response
limits, cost/quota abuse, malicious provider/prompt/script/secret content, path
and log injection, tenant leakage, retention, legacy Hosted endpoint misuse,
forbidden Runtime/LLM invocation and crash reconciliation.

The recommended MVP access model was one short-lived project/Package capability
token, minted after a supervised authenticated owner action, scoped to subject,
project, exact Package checksum, Workflow/capability versions and budget, and
stored outside the Package. At original R3A closure this was a recommendation,
not approval; ADR 0011 later approved the exact experimental R3B form above.

At original R3A closure, authentication mechanism/issuance, token lifetime/
refresh/revocation, local
credential storage, Package binding, authenticated ownership, request signing,
multi-user isolation, first capability, exact request/response limits,
request/cost budget, provider eligibility, response fields, retention/deletion,
unsafe evidence and Hosted-route isolation remained `SOURCE_UNDECIDED`. ADR
0011 resolves those items only for R3B; production and live-provider forms
remain `SOURCE_UNDECIDED` for R3C.

Proposed ADR 0010 records the boundary and decisions for owner review. Its
status remains **Proposed**.

## First slice and sequence

Exactly one first capability is recommended: `paper.search/v0.1`, bounded
scholarly metadata discovery initiated entirely by the local Harness. It matches
the experimental Literature Search Package and existing `ResearchQuery`,
`PaperRecord`, `PaperSearchProvider` and fake/OpenAlex substrate. Provider order
is data/provenance, not a ReAgent relevance judgment.

- R3B: fake adapter only; external Package, real loopback HTTP, isolated
  PostgreSQL, optional persistent artifact storage under approved retention,
  idempotency/reconciliation, security rejection matrix, restart recovery,
  Package non-mutation and zero Runtime/LLM/real-provider use.
- R3C: separately authorized supervised live-provider acceptance after current
  official terms, authentication, rate, cost and retention verification.

R3B and R3C have not started. No real provider or credential was used. The R3B
gate status in the original closure was later superseded by ADR 0011.

## R2 warning backlog

R3A carries these warnings without modifying their behavior:

| Warning | Future phase |
|---|---|
| Child-first `INCOMPLETE_CHAIN` Progress Reports are not automatically re-evaluated | Later R2 maintenance/conflict-policy milestone after owner decision |
| Progress Report upload is explicit, not automatic | Later local-client/package UX milestone; not proxy implementation |
| Claude Code compatibility remains untested | Dedicated Harness compatibility acceptance |
| Optional Uploaded Local Progress Reports frontend remains deferred | Later progress UI milestone |
| Cloud cannot independently verify no-op context bytes without a supplied snapshot | Later context-snapshot/evidence policy milestone |

## Scope and validation

R3A changes only architecture/audit/security/acceptance/governance documents.
It changes no backend/frontend production source, migration, database model or
Workflow Package runtime behavior. It did not create/use a database, start
FastAPI, read `.env`, execute a Workflow, invoke a project LLM, call OpenAlex or
another provider, read a real key, or modify a local Package.

Validation at documentation closure:

- the initial Git gate was exact: clean `main` at
  `592410e274b07ac6480f12419b45cd9b742ff838`; initial `git diff --check`
  exited 0;
- `git diff --check` exited 0 after the R3A documentation changes;
- targeted route inspection found no existing proxy/proxy-operation API route;
- targeted authentication inspection found no FastAPI bearer/OAuth/security
  dependency or authenticated principal in backend API/application/domain code;
- targeted import inspection confirmed current provider composition imports
  `AgentRuntime`, `ExecutionDispatcher`, research/grounded Skills and the
  OpenAlex adapter, while the resume path submits through the dispatcher;
- contract/SQL inspection confirmed `ProviderOperation` requires
  `workflow_run_id`/`logical_step_id` and its mapping has Hosted-run foreign
  keys;
- Package inspection confirmed a disabled credential-free proxy placeholder
  with `UNDECIDED_R3_NO_CREDENTIAL_PRESENT`;
- new-file and added-line scans found no credential/private-key pattern, real
  R1B evidence marker, machine-specific absolute path or executable-content
  canary;
- `.env` and `runtime_data/` remain ignored; no `.env`, runtime-data path or
  database file is tracked;
- no repository documentation/link checker was discovered by the targeted
  script/config search;
- the final changed-file inventory contains only the approved documentation and
  `.agent_read` paths; no backend, frontend, migration, database model or
  Workflow Package runtime file changed.

No backend regression suite was run because R3A is documentation-only. Static
inspection is not runtime proxy acceptance. No database/server/Workflow was
started; `.env` was not read; no project LLM, AgentRuntime,
ExecutionDispatcher, OpenAlex or other provider call was made.

## Gate

```text
R3A_ARCHITECTURE_REVIEW = PASS_WITH_OWNER_DECISIONS_REQUIRED
R3A_PRODUCT_BOUNDARY = PASS
R3A_SECURITY_MODEL = COMPLETE_FOR_OWNER_REVIEW
R3A_PROXY_CONTRACT = COMPLETE_FOR_OWNER_REVIEW
R2_STATE = UPLOAD_ACCEPTED
R3A_OWNER_DECISIONS = RATIFIED_FOR_R3B
R3B_IMPLEMENTATION_GATE = OPEN
R3C_LIVE_PROVIDER_GATE = CLOSED
```

R3B remains unstarted pending owner review of the ratification closure. Do not
begin R3C.
