# Cloud API Proxy v0.1 Contract

Status: **PROPOSED — COMPLETE FOR OWNER REVIEW, NOT IMPLEMENTED**

Date: 2026-08-03

Governing decisions: ADR 0009 and proposed ADR 0010

## 1. Responsibility boundary

The API Proxy is a bounded credentialed transport capability requested by a
local Agent Harness. It is not a cloud research Agent.

```text
local Codex / Claude Code
  -> reads the Workflow Package and chooses one permitted operation
  -> constructs an explicit capability request
  -> invokes the local Package proxy client/tool
  -> authenticates to ReAgent cloud
  -> cloud validates caller, project, Package, capability, schema and limits
  -> cloud injects the server-side provider credential
  -> one fixed adapter performs one bounded provider operation
  -> cloud returns provider data plus operational provenance
  -> local Harness interprets the untrusted data
  -> local Harness visibly writes local outputs/context/Progress Report
```

The cloud may authenticate, authorize, validate a strict allowlisted operation,
reserve budget, inject a credential, invoke one fixed provider adapter, perform
bounded transport retries, normalize transport errors/data, record usage and
redact secrets. It may retain only data permitted by an approved policy.

The cloud must not select a research question, invent or expand search terms,
choose relevance criteria, rank papers, synthesize findings, invoke an LLM for
the research task, write Package files, update `memory/context.md`, generate a
Progress Report, resume a Workflow, call `AgentRuntime` or
`ExecutionDispatcher`, automatically chain provider operations, accept an
arbitrary URL, or behave as a general HTTP proxy.

## 2. Contract and capability versioning

The proposed envelope contract is `reagent.cloud-api-proxy/v0.1`. Each allowed
operation also has an independently versioned capability schema:

```text
paper.search/v0.1
```

The name follows existing repository terminology:
`ProviderCategory.PAPER_SEARCH`, `ProviderOperationKind.SEARCH`,
`PaperSearchProvider`, `ResearchQuery` and `PaperRecord`. A Package names the
capability and version, not a provider URL or vendor-specific endpoint.

The contract registry maps each capability version to exactly:

- one request schema;
- one normalized response schema;
- an allowlist of eligible adapter identities;
- a fixed server-owned endpoint policy;
- request, result, time, response-size and cost ceilings;
- retention and attribution policy;
- retry/reconciliation policy.

Adding or changing a capability schema requires a new version. Provider adapter
versions may advance independently when their normalized capability output is
backward compatible; every response records the actual adapter identity.

## 3. Proposed request envelope

`CloudProxyRequestEnvelope` is an immutable normalized command with these
fields. Names are proposed; they are not production API approval.

| Field | Semantics |
|---|---|
| `proxy_contract_version` | Exactly `reagent.cloud-api-proxy/v0.1`. |
| `operation_id` | Omitted by the client; deterministically derived by the server after validation. |
| `idempotency_key` | Required client-generated opaque key, unique within the authenticated project/package scope. It is not a secret. |
| `project_id` | Cloud project identity authorized for the caller. |
| `package_id` | Exact local Workflow Package identity. |
| `package_checksum` | Exact Package checksum known to cloud policy. |
| `workflow_id` | Pinned Workflow identity from the Package. |
| `workflow_version` | Pinned Workflow version. |
| `workflow_checksum` | Pinned Workflow checksum. |
| `capability` | Capability ID, initially proposed as `paper.search`. |
| `capability_schema_version` | Exact normalized operation contract, initially proposed as `paper.search/v0.1`. |
| `provider_preference` | Optional adapter-family preference; accepted only when project policy explicitly permits it. Never a URL. Cloud records the actual adapter. |
| `parameters` | Capability-specific immutable normalized parameters; unknown fields fail closed. |
| `request_content_checksum` | Deterministic checksum defined below. |
| `harness_type` | `CODEX`, `CLAUDE_CODE` or another allowlisted value. |
| `harness_version` | Optional client-reported Harness version. |
| `harness_session_id` | Opaque, non-secret local session correlation ID; not conversation history. |
| `client_timestamp` | Timezone-aware client creation time, bounded for unreasonable clock skew but never used as identity authority. |
| `authorization_context` | Server-populated, secret-free result of transport authentication: subject ID, project/package/capability scopes, policy version and a stable authorization-scope checksum. Clients must not supply roles or principals in the JSON body. |
| `declared_limits` | Client-requested ceilings, each less than or equal to server policy: result count, timeout, response bytes, request attempts and cost. A declaration cannot expand policy. |

The credential is presented only at the authenticated transport boundary. It is
never included in JSON, canonical bytes, checksums, logs, Package files,
Progress Reports, provider data, response envelopes or artifacts.

### First capability parameters

The proposed `paper.search/v0.1` parameters reuse the intent of
`ResearchQuery` without exposing OpenAlex syntax:

- `topic`: exact local-Harness-supplied query text;
- `keywords`: ordered explicit local-Harness-supplied terms;
- `year_from` and `year_to`, optional;
- `language`, optional advisory value;
- `max_results`;
- explicit inclusion/exclusion criteria as provenance only, not instructions
  for the cloud to judge relevance.

There is no URL, raw provider filter string, cursor, arbitrary header, script,
prompt, full-text/PDF request or server-generated query field. The adapter may
translate the exact normalized command into a fixed provider protocol. It must
not invent synonyms or research criteria. Provider-native ordering may be
returned and labelled; it is not a ReAgent relevance judgment.

## 4. Proposed response envelope

`CloudProxyResponseEnvelope` contains:

| Field | Semantics |
|---|---|
| `proxy_contract_version` | Exact proxy envelope version. |
| `operation_id` | Stable ReAgent operation identity. |
| `idempotency_result` | Delivery result: `CREATED`, `REPLAYED`, or `CONFLICT`; includes the first accepted operation ID but no secret. |
| `project_id`, `package_id`, `workflow_id` | Bound caller identities. |
| `capability`, `capability_schema_version` | Executed normalized capability. |
| `provider_adapter` | Actual provider, adapter version and model/endpoint identity; never contains a credential or credential-bearing URL. |
| `request_content_checksum` | Echoes the accepted request identity. |
| `operation_status` | `RESERVED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`, or `RECONCILIATION_REQUIRED`. |
| `response_content_checksum` | Stable semantic operation-outcome checksum. |
| `response_checksum` | Checksum of this complete delivery envelope under the rule below. |
| `transport` | Sanitized HTTP/provider class, latency, attempt count and bounded response size. No raw header/body by default. |
| `provider_data` | Strict capability-normalized data, or `null`. It is untrusted data, not research interpretation. |
| `provider_data_reference` | Optional immutable storage reference only if retention is owner-approved; never a host path. |
| `usage` | Request/attempt counts, provider rate evidence, measured latency, tokens when applicable, and cost/currency. |
| `budget` | Reserved, settled and remaining policy evidence without exposing other tenants. |
| `retry_classification` | `NEVER_RETRY`, `SAFE_SAME_OPERATION`, `RECONCILE_FIRST`, or `SERVER_POLICY_EXHAUSTED`. |
| `warnings` | Bounded secret-safe operational warnings. |
| `provenance` | Policy version, adapter identity, schema versions, provider request references when safe, timestamps and checksums. |
| `server_timestamp` | Timezone-aware response-delivery timestamp. |

The response contains no local research conclusion, relevance score generated
by ReAgent, synthesis, final report, Workflow continuation decision or local
file mutation instruction.

## 5. Canonical serialization and non-cyclic identity

All checksums use SHA-256 formatted `sha256:<64 lowercase hex>`. Canonical JSON
uses UTF-8, Unicode code points as supplied after schema validation, object keys
sorted lexicographically, no insignificant whitespace, `,` and `:` separators,
JSON booleans/null, finite numbers only, arrays in declared order and
timezone-aware RFC 3339 timestamps normalized to UTC with `Z`. Duplicate object
keys, invalid Unicode, control characters outside permitted JSON whitespace,
NaN/infinity and unknown fields are rejected before hashing.

### Request identity

1. Build the validated operation content. Exclude only:
   `operation_id`, `idempotency_key`, `request_content_checksum`, transport
   credentials, server receipt timestamps and server-populated
   `authorization_context`.
2. Compute:

   ```text
   request_content_checksum = SHA256(canonical semantic request bytes)
   ```

   This binds contract/capability versions, project, Package and Workflow
   identity, provider preference, all parameters, Harness identity, client
   timestamp and declared limits. It deliberately does not bind the separate
   idempotency identity.
3. After successful authentication, compute an
   `authorization_scope_checksum` from stable server-owned subject, tenant,
   project, Package and capability scope identifiers. It excludes token bytes,
   token issue/expiry times, policy version and mutable audit timestamps so an
   authorized token refresh does not change the operation identity. The exact
   policy version and authorization decision remain immutable operation audit
   fields.
4. Compute:

   ```text
   operation_id = "proxyop-v1-" + lower_hex(
       SHA256(canonical JSON of {
         proxy_contract_version,
         project_id,
         package_id,
         workflow_id,
         capability_schema_version,
         idempotency_key,
         request_content_checksum,
         authorization_scope_checksum
       })
   )
   ```

The arrow is one way:

```text
operation content -> request_content_checksum
                  + idempotency key
                  + authorization scope
                  -> authorization-bound operation_id
                  -> provider operation/outcome
```

No request checksum includes itself, and no request identity depends on a
response, upload time or database surrogate ID. Identical authorized semantic
requests with the same idempotency key produce the same operation ID. Changed
semantic content produces a different request checksum; reusing the key then
causes a conflict rather than a second call.

### Response identity

1. `provider_data_checksum` is SHA-256 of canonical normalized provider data,
   when data exists.
2. `response_content_checksum` hashes the immutable semantic operation outcome,
   excluding `response_content_checksum`, `response_checksum`, delivery-only
   `idempotency_result`, and delivery `server_timestamp`. It binds operation ID,
   capability, selected adapter, request checksum, terminal status, provider
   data/checksum/reference, usage, budget, retry classification, warnings and
   provenance.
3. `response_checksum` hashes the complete delivery envelope with only
   `response_checksum` omitted. A replay delivery may have a different delivery
   checksum/timestamp while retaining the exact operation ID, request checksum,
   provider-data checksum and response-content checksum.

This construction is non-cyclic and keeps cloud database IDs separate from
contract identity.

## 6. Idempotency and reconciliation

The server must durably reserve the operation identity and budget before
invoking an adapter.

| Situation | Required behavior |
|---|---|
| Same authorized scope, idempotency key and request checksum | Return the existing operation/result; do not invoke the adapter, reserve budget or store response content twice. |
| Same key, different request checksum or identity | Reject `409 IDEMPOTENCY_IDENTITY_CONFLICT`; do not call the provider. Preserve secret-safe conflict audit metadata. |
| Client times out before receiving a response | Report outcome as unknown locally. Do not automatically create a new key or retry ambiguously. Read operation status using the same project/package scope and operation ID or idempotency key. |
| Cloud restarts while `RESERVED` | No provider call is presumed. Policy may release or explicitly resume only under the same operation identity after durable reconciliation. |
| Cloud restarts while `RUNNING` | Mark/read as `RECONCILIATION_REQUIRED` unless the provider supports a trustworthy request-status/idempotency lookup. Do not issue another call merely because the process restarted. |
| Provider response arrives but artifact/settlement persistence is partial | Keep conservative budget reservation and reconciliation state. Never report success until the immutable normalized result/checksum and terminal settlement are durable. |

Conceptual API shape for R3B review, not implementation approval:

```text
POST /projects/{project_id}/proxy-operations
GET  /projects/{project_id}/proxy-operations/{operation_id}
GET  /projects/{project_id}/proxy-operations?package_id=...&idempotency_key=...
```

Status reads are authorization-scoped and return safe metadata. They never
resume a Workflow.

## 7. Provider errors and retry classification

| Provider/operation condition | Normalized result | Retry rule |
|---|---|---|
| Capability schema or provider 400 | `INVALID_REQUEST` / `INVALID_QUERY` | Never retry without changing content and idempotency key deliberately. |
| Provider 401 or 403 | `PROVIDER_AUTHENTICATION` or `PROVIDER_PERMISSION` | Never client-retry; server credential/configuration incident. Do not expose provider secret details. |
| Provider 404 | Capability-specific `NOT_FOUND` | Terminal for the same request unless the capability contract explicitly says otherwise. |
| Provider 408 | `PROVIDER_TIMEOUT` | Server may make an approved bounded attempt under the same operation identity; otherwise reconcile first. |
| Provider 429 | `PROVIDER_RATE_LIMIT` | Respect bounded server policy and safe retry-after metadata. Client does not create a replacement operation automatically. |
| Provider 500/502/503/504 | `PROVIDER_UNAVAILABLE` | Bounded adapter retry under the same operation identity only; terminal after policy exhaustion. |
| Malformed/invalid Unicode response | `MALFORMED_PROVIDER_RESPONSE` | Terminal unless a separately versioned adapter policy classifies the defect transient. |
| Response exceeds approved bytes | `RESPONSE_LIMIT_EXCEEDED` | Abort/read no further, retain no unsafe body, terminal. |
| Request/budget/cost/rate limit exceeded before call | `BUDGET_EXCEEDED` or `RATE_LIMITED` | Fail closed without provider invocation. |
| Operation state cannot be proven after interruption | `RECONCILIATION_REQUIRED` | Status read/reconciliation required; no ambiguous automatic client retry. |

Provider retries are internal bounded transport handling, not a research loop.
The proxy never changes query terms, switches methodology or automatically
chains a fallback provider. No worker, queue or lease is part of v0.1 design.

## 8. Data, provenance and Progress Report references

The minimum durable operation record may contain:

- operation, request-content and response-content identities/checksums;
- project, Package and Workflow identity;
- stable authorization-scope checksum and exact policy version, not credential
  bytes;
- capability and actual adapter identity;
- normalized request parameters;
- timestamps, status and latency;
- reserved/actual usage and cost;
- response checksum and safe error category;
- optional immutable normalized/raw response references only when an approved
  retention policy permits them.

Raw provider response retention, normalized response retention, abstract/title/
author/identifier retention, deletion timing, user deletion, rejected-response
retention and audit retention are `SOURCE_UNDECIDED`. The security default is
no raw provider body retention and minimum operational metadata only.

A local `progress-report/v0.2` may include a future additive, versioned list of
proxy operation IDs and response-content checksums. The local Harness writes
that reference after interpreting the response. The cloud does not insert the
reference, amend the report or infer research progress from the provider call.
Proxy provenance is not a Progress Report, `ExecutionEvent`, checkpoint,
memory revision or Hosted Workflow execution record.

## 9. Local Package integration

A future authorized Package template may carry only non-secret configuration:

- proxy contract/base URL;
- project, Package and Workflow identity;
- allowed capability/schema versions;
- local client version;
- credential lookup *method*, never credential value;
- approved limits and offline/fake-provider mode.

The credential must live outside the Package, preferably an OS credential store
or short-lived process environment after an explicit user action. Copying or
moving the Package must not copy proxy authority. The client validates locally,
makes one explicit request, prints only safe operation metadata, offers an
explicit status read, and never mutates Package inputs, outputs, context or
Progress Reports.

## 10. First vertical slice and limits requiring approval

Exactly one first capability is recommended:

> **`paper.search/v0.1` — bounded scholarly metadata and abstract-availability
> discovery initiated entirely by the local Harness.**

It matches the current Literature Search Package and existing provider-neutral
`ResearchQuery`/`PaperRecord` substrate. It excludes full-text/PDF retrieval,
source-content fetching, relevance judgment, ranking, synthesis and LLM use.
It must support a deterministic fake adapter in R3B.

Candidate ceilings for owner review, drawn conservatively from the existing
supervised OpenAlex substrate, are: at most 20 normalized records, at most one
bounded logical search operation, 15 seconds per provider attempt, no more than
three attempts total, at most 2 MiB provider response bytes, 90 seconds total
operation time and zero approved monetary cost. These are **not approved proxy
policy** merely because older Hosted code used similar limits.

## 11. Explicit non-goals

- production endpoint or adapter implementation in R3A;
- real provider credentials or calls;
- Hosted AgentRuntime, ExecutionDispatcher, run/resume, approval or event flow;
- server-side research planning, ranking, source selection or report writing;
- LLM, structured generation, Judge or automatic evaluation;
- arbitrary URL/header/method forwarding;
- full-text/PDF/source-content proxying;
- background workers, queues, leases or chained tools;
- automatic Progress Report upload or mutation;
- authentication, signing or multi-user policy selected without owner approval;
- frontend controls;
- R3C live-provider acceptance.
