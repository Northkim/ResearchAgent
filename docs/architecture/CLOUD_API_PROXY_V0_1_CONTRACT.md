# Cloud API Proxy v0.1 Contract

Status: **R3B EXPERIMENTAL PROFILE RATIFIED — NOT IMPLEMENTED**

Date: 2026-08-04

Governing decisions: ADR 0009, proposed ADR 0010, and accepted ADR 0011

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
reserve budget, inject a credential for a separately authorized live provider,
invoke one fixed adapter, normalize transport errors/data, record usage and
redact secrets. Any future transport retry requires an approved policy; R3B
performs none. It may retain only data permitted by an approved policy.

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

### Ratified R3B profile

R3B is `EXPERIMENTAL_FAKE_PROVIDER_VERTICAL_SLICE`. It is disabled by default,
limited to `paper.search/v0.1` through one deterministic fake paper-search
adapter, and permits zero real-provider, provider-credential or external-
network calls. It is not suitable for public or production deployment. The
contract below freezes that experimental profile; broader production and live-
provider choices remain unapproved for R3C.

## 3. Proposed request envelope

`CloudProxyRequestEnvelope` is an immutable normalized command with these
fields. Names are proposed; they are not production API approval.

| Field | Semantics |
|---|---|
| `proxy_contract_version` | Exactly `reagent.cloud-api-proxy/v0.1`. |
| `operation_id` | Omitted by the client; deterministically derived by the server after validation. |
| `idempotency_key` | Required client-generated UUIDv4, unique within the authenticated authorization scope. It is not a secret or request checksum. |
| `project_id` | Cloud project identity authorized for the caller. |
| `package_id` | Exact local Workflow Package identity. |
| `package_checksum` | Exact Package checksum known to cloud policy. |
| `workflow_id` | Pinned Workflow identity from the Package. |
| `workflow_version` | Pinned Workflow version. |
| `workflow_checksum` | Pinned Workflow checksum. |
| `capability` | Fixed to the ratified R3B capability `paper.search/v0.1`; a separate unversioned client capability field is not required. |
| `adapter` | Omitted by the client. The server derives the only allowed deterministic fake adapter from the token record and capability registry. |
| `parameters` | Capability-specific immutable normalized parameters; unknown fields fail closed. |
| `request_content_checksum` | Deterministic checksum defined below. |
| `harness_type` | `CODEX`, `CLAUDE_CODE` or another allowlisted value. |
| `harness_version` | Optional client-reported Harness version. |
| `harness_session_id` | Opaque, non-secret local session correlation ID; not conversation history. |
| `client_timestamp` | Timezone-aware client creation time; R3B permits at most plus or minus five minutes of skew and never treats it as identity authority. |
| `authorization_context` | Server-derived, secret-free result of bearer-token authentication: token, tenant, subject, project, exact Package/Workflow, capability/adapter and maximum-operation scopes plus a stable authorization-scope checksum. It is not accepted from the request body. |
| `declared_limits` | Not accepted in R3B. Fixed server policy supplies every ceiling; the client can request only `max_results` within the capability schema. |

The credential is a short-lived opaque bearer capability token presented only
at the transport boundary through the `REAGENT_PROXY_TOKEN` process environment
variable. It is never a command-line argument or `.env` file value and is never
included in JSON, canonical bytes, checksums, logs, Package files, Progress
Reports, provider data, response envelopes or artifacts.

### First capability parameters

The ratified `paper.search/v0.1` request accepts exactly:

- `query`: UTF-8 text supplied by the local Harness, with outer whitespace
  trimmed, minimum 1 and maximum 500 characters after trimming;
- `max_results`: integer, default 10, minimum 1 and maximum 20.

There is no URL, raw provider filter string, cursor, arbitrary header, script,
prompt, provider endpoint/credential, custom method, local filesystem path,
full-text/PDF request or server-generated query field. The response reuses the
existing normalized paper-search result model where compatible, contains no
research-interpretation field, and treats fake provider data as untrusted.

## 4. Proposed response envelope

`CloudProxyResponseEnvelope` contains:

| Field | Semantics |
|---|---|
| `proxy_contract_version` | Exact proxy envelope version. |
| `operation_id` | Stable ReAgent operation identity. |
| `idempotency_result` | Delivery result: `CREATED`, `REPLAYED`, or `CONFLICT`; includes the first accepted operation ID but no secret. |
| `project_id`, `package_id`, `workflow_id` | Bound caller identities. |
| `capability` | Executed versioned normalized capability, exactly `paper.search/v0.1` in R3B. |
| `provider_adapter` | Actual provider, adapter version and model/endpoint identity; never contains a credential or credential-bearing URL. |
| `request_content_checksum` | Echoes the accepted request identity. |
| `operation_status` | R3B states are `RECEIVED`, `RUNNING`, `SUCCEEDED`, `FAILED`, or `RECONCILIATION_REQUIRED`. |
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

   This binds the contract/capability version, project, exact Package and
   Workflow identity, all normalized parameters, Harness identity and client
   timestamp. It deliberately does not bind the separate idempotency identity,
   token plaintext/digest, server-derived authorization context or transport
   metadata.
3. After successful authentication, compute an
   `authorization_scope_checksum` from the server-owned `token_id`, tenant,
   subject, project, exact Package ID/checksum, exact Workflow ID/version/
   checksum, capability, fixed adapter and maximum-operation scope. It excludes
   token plaintext/digest, issue/expiry timestamps, mutable revocation state and
   mutable audit timestamps. The full token metadata and authorization decision
   remain immutable audit fields; they are not client assertions.
4. Compute:

   ```text
   operation_id = "proxyop-v1-" + lower_hex(
       SHA256(canonical JSON of {
         proxy_contract_version,
         project_id,
         package_id,
         workflow_id,
         capability,
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

The server must durably record `RECEIVED`, the operation identity and operation-
count reservation before invoking the fake adapter.

| Situation | Required behavior |
|---|---|
| Same authorized scope, idempotency key and request checksum | Return the existing operation/result; do not invoke the adapter, reserve budget or store response content twice. |
| Same key, different canonical request content/checksum under the same scope | Reject HTTP 409 as `IDEMPOTENCY_CONFLICT`; do not call the adapter. Preserve only secret-safe conflict audit metadata. |
| Client times out before receiving a response | Report outcome as unknown locally. Do not automatically create a new key or retry ambiguously. Read operation status using the same project/package scope and operation ID or idempotency key. |
| Cloud restarts while `RECEIVED` | No adapter call is presumed unless durable evidence says otherwise. State recovery follows the same operation identity. |
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
| Simulated provider 408 | `PROVIDER_TIMEOUT` | R3B performs no adapter retry; client reconciles through status read. |
| Simulated provider 429 | `PROVIDER_RATE_LIMIT` | R3B performs no adapter retry and the client does not create a replacement operation automatically. |
| Simulated provider 500/502/503/504 | `PROVIDER_UNAVAILABLE` | R3B performs no adapter retry; return the safe terminal/reconciliation state dictated by durable evidence. |
| Malformed/invalid Unicode response | `MALFORMED_PROVIDER_RESPONSE` | Terminal for R3B; retain no unsafe body. |
| Response exceeds approved bytes | `RESPONSE_LIMIT_EXCEEDED` | Abort/read no further, retain no unsafe body, terminal. |
| Request/budget/cost/rate limit exceeded before call | `BUDGET_EXCEEDED` or `RATE_LIMITED` | Fail closed without provider invocation. |
| Operation state cannot be proven after interruption | `RECONCILIATION_REQUIRED` | Status read/reconciliation required; no ambiguous automatic client retry. |

The R3B fake adapter performs no provider retry. The proxy never changes query
terms, switches methodology or automatically chains a fallback provider. No
worker, queue or lease is part of the v0.1 design.

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

For R3B, retention lasts only for the isolated acceptance environment. It may
include safe canonical request identity/checksum, normalized request
parameters, Proxy operation state/scope/adapter/timestamps/latency, zero-cost
usage, normalized fake-provider results, response identities/checksums and safe
failure categories. It excludes raw provider bodies, credentials, bearer-token
plaintext, Authorization headers, unsafe original payloads and executable
content. Unsafe data is rejected before artifact persistence; only safe
metadata/checksums may be retained for a rejection. The isolated database,
artifact directory and plaintext token file are removed after acceptance, with
only sanitized tracked evidence retained. Live-provider retention remains
`SOURCE_UNDECIDED` for R3C.

R3B does not modify `progress-report/v0.2`. A local output may record a Proxy
operation ID as ordinary local provenance, but the proxy neither creates nor
uploads/amends a Progress Report and never changes local context or outputs. A
formal Progress Report proxy-operation field requires a later additive
contract review. Proxy provenance is not a Progress Report, `ExecutionEvent`,
checkpoint, memory revision or Hosted Workflow execution record.

## 9. Local Package integration

A future R3B-authorized Package may carry only non-secret configuration:

- proxy contract/base URL;
- project, Package and Workflow identity;
- allowed capability/schema versions;
- local client version;
- credential lookup method (`REAGENT_PROXY_TOKEN` process environment only),
  never a credential value or plaintext token file;
- approved limits and offline/fake-provider mode.

The token plaintext file lives outside Git and the Package, and the operator
removes it after acceptance. The client receives the token only through the
process environment, validates locally, makes one explicit request, prints
only safe operation metadata, offers an explicit status read, performs no
ambiguous automatic retry, and never mutates Package inputs, outputs, context
or Progress Reports.

## 10. Ratified first vertical slice and limits

Exactly one R3B capability is approved:

> **`paper.search/v0.1` — bounded scholarly metadata and abstract-availability
> discovery initiated entirely by the local Harness.**

It matches the current Literature Search Package and existing provider-neutral
paper-search result substrate. It excludes full-text/PDF retrieval,
source-content fetching, relevance judgment, ranking, synthesis and LLM use.
R3B fixes the request body at 16 KiB, normalized result at 512 KiB, operation
timeout at 10 seconds, concurrent operations per token at 2, total operations
per token at 50, monetary budget at zero, real-provider calls at zero and
external-network calls at zero. Only the deterministic fake adapter is allowed.

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
- production authentication, signing, proof of possession or multi-user policy;
- frontend controls;
- R3C live-provider acceptance or any production/public deployment.

## 12. Gate state

ADR 0011 resolves the formerly `SOURCE_UNDECIDED` controls only for the
experimental fake-provider slice. `R3B_IMPLEMENTATION_GATE = OPEN` after the
documentation-only ratification commit closes cleanly.

`R3C_LIVE_PROVIDER_GATE = CLOSED`. Production authentication, token issuance
UX, HTTPS deployment, provider eligibility/current terms, live credentials,
rate limits, monetary budget, retry policy, live data retention/deletion,
production logging/audit retention and public-network security remain subject
to separate owner approval.
