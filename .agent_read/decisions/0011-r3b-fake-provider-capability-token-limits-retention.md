# ADR 0011: R3B Fake-Provider Capability Token, Limits, and Retention Decisions

- **Status:** Accepted
- **Date:** 2026-08-04
- **Scope:** Experimental R3B fake-provider vertical slice only
- **Governing decisions:** ADR 0009 and ADR 0010

## Context

R3A defined a teacher-aligned Cloud API Proxy boundary but deliberately left
authentication, authorization, capability, limits, idempotency recovery and
retention as `SOURCE_UNDECIDED`. The owner has now resolved those questions for
one implementation milestone only. R3B remains an experimental fake-provider
slice; this decision does not authorize a live provider, public deployment,
production authentication, multi-user production release, R3C, or Hosted
research execution.

## Decision

### 1. Phase classification

R3B is `EXPERIMENTAL_FAKE_PROVIDER_VERTICAL_SLICE`. It is disabled by default,
uses only a deterministic fake paper-search adapter, disables external network,
real providers and real provider credentials, and is unsuitable for public or
production deployment. R3C remains separately gated.

### 2. Authentication and token lifecycle

R3B uses a short-lived opaque bearer capability token with at least 256 bits of
cryptographically secure randomness. The server stores only a SHA-256 token
digest and metadata and compares digests in constant time. Plaintext tokens
must not enter PostgreSQL, artifact storage, logs, Progress Reports, Workflow
Packages, `.env` files or command-line arguments.

An operator-only CLI issues the token; there is no public issuance endpoint.
It writes the plaintext exactly once to a caller-specified file outside Git and
outside the Workflow Package, sets mode `0600`, refuses to overwrite an
existing file, and does not print the token to ordinary stdout or logs. The
local client reads the token only from the process environment variable
`REAGENT_PROXY_TOKEN`. The plaintext file is removed after acceptance.

The default lifetime is 60 minutes and the maximum is 120 minutes. R3B
acceptance may use 120 minutes. Tokens cannot be refreshed and require explicit
server-side revocation. This operator-issued identity is an R3B acceptance
mechanism, not production user authentication.

### 3. Authorization scope

Each token binds `token_id`, `tenant_id`, `subject_id`, `project_id`,
`package_id`, exact `package_checksum`, `workflow_id`, `workflow_version`, exact
`workflow_checksum`, capability `paper.search/v0.1`, the deterministic R3B fake
paper-search adapter, maximum operation count, `issued_at`, `expires_at`, and
revocation state. The server derives authorization from this token record.

Client-supplied `actor_user_id`, role, tenant, owner status or project
permission is never authorization. A project, Package, Workflow, checksum,
capability or adapter mismatch fails closed before adapter use. The client
cannot select an arbitrary provider or provider endpoint.

### 4. Request signing and transport

R3B v0.1 uses no detached request signature, request nonce or
proof-of-possession credential. It relies on the short-lived bearer token,
exact authorization scope, client timestamp and idempotency identity. R3B
acceptance binds the server to `127.0.0.1` and uses loopback HTTP only. Allowed
client timestamp skew is plus or minus five minutes. Non-loopback deployment
requires HTTPS and separate approval. These controls are not production-grade
public authentication; proof of possession remains deferred to a production
security review.

### 5. First capability

The only R3B capability is `paper.search/v0.1`. Its request parameters are:

- `query`: a UTF-8 string, outer whitespace trimmed, 1–500 characters after
  trimming;
- `max_results`: an integer, default 10, range 1–20.

The response reuses the existing normalized paper-search result model where
compatible and adds no research-interpretation field. The capability excludes
arbitrary URLs, provider endpoints, custom methods or headers, provider
credentials, full text/PDFs, local paths, cloud query generation, relevance
judgment, paper ranking, literature synthesis, report generation and LLM use.
Provider data remains untrusted data.

### 6. Resource and budget limits

R3B fixes these ceilings:

- request body: 16 KiB;
- normalized result: 512 KiB;
- operation timeout: 10 seconds;
- concurrent operations per token: 2;
- operations per token: 50;
- monetary budget: zero;
- real provider calls: zero;
- external network calls: zero.

The fake adapter must not make a network call.

### 7. Idempotency and reconciliation

The client-generated idempotency key is UUIDv4. The token plaintext is neither
an identity field nor part of canonical request content. Under the same
authorization scope, the same idempotency key and canonical request content
returns the existing Proxy operation without another adapter invocation and
preserves the original operation identity and result. The same scoped key with
different canonical request content returns HTTP 409, or the documented
equivalent, classified as `IDEMPOTENCY_CONFLICT`, before adapter use.

The local client does not perform ambiguous automatic retries. After a timeout
it performs an explicit operation-status read. The minimum states are
`RECEIVED`, `RUNNING`, `SUCCEEDED`, `FAILED`, and
`RECONCILIATION_REQUIRED`. If a process stops while an operation is `RUNNING`
and completion cannot be proved, the operation moves or reconstructs as
`RECONCILIATION_REQUIRED`; the adapter is not invoked a second time
automatically. The R3B fake adapter performs no real-provider retry.

Identity construction remains one-way and non-cyclic:

```text
canonical semantic request -> request_content_checksum
request_content_checksum + UUIDv4 idempotency key + stable server authorization scope
  -> version-namespaced operation_id
operation outcome -> response identities
```

The idempotency key is not the request-content checksum. Client credentials,
token plaintext/digest, mutable revocation state and server receipt time are
not canonical request content.

### 8. Persistence boundary

R3B uses a new Proxy operation domain and persistence boundary. It must not
reuse, fabricate or require Hosted `ProviderOperation`, `WorkflowRun`,
`WorkflowStep`/`StepRun`, `ExecutionEvent`, `Checkpoint`, or `MemoryRevision`
identity. Hosted run or step rows must not be fabricated to satisfy existing
foreign keys. R3B may add a separate additive SQL model/repository.

The Proxy route must not import or instantiate `AgentRuntime`,
`ExecutionDispatcher`, Workflow execution, Hosted research Skills or LLM
services. Canonical JSON/checksum helpers, immutable artifact storage,
provider ports/result types, safe provider failures, usage/budget arithmetic,
PostgreSQL repository patterns, FastAPI composition patterns and deterministic
fake paper-search adapters may be reused only behind the new boundary.

### 9. Acceptance-lifetime retention

R3B may retain for the acceptance environment lifetime only: canonical request
identity/checksum, safe normalized request parameters, operation state,
project/Package/Workflow scope, adapter identity, timestamps/latency, zero-cost
usage, normalized fake-provider result, response identity/checksum and safe
failure classification.

It must not persist a raw provider body, provider credential, bearer-token
plaintext, Authorization header, unsafe original payload or executable
content. Unsafe payloads are rejected before artifact persistence; only safe
metadata/checksums may be retained for rejected requests.

After R3B acceptance, stop the isolated server, stop and remove the isolated
PostgreSQL cluster, remove the isolated artifact directory, remove the
plaintext token file and retain only sanitized tracked acceptance evidence. No
real research-data retention is approved.

### 10. Progress Report relationship

R3B does not change `progress-report/v0.2` and does not automatically create,
upload or modify a Progress Report or modify local context/outputs. A local
output may record a Proxy operation ID as ordinary local provenance. A formal
Progress Report proxy-operation field requires a later additive contract
review.

### 11. R3C gate

`R3C_LIVE_PROVIDER_GATE = CLOSED`. R3C requires separate owner approval of
production user authentication, token-issuance UX, HTTPS deployment, provider
eligibility/current terms, live credentials, provider rate limits, monetary
budget, retry policy, live retention/deletion, production log/audit retention
and public-network security acceptance.

## Resolved and unresolved source decisions

For R3B only, authentication/issuance, token lifetime/revocation/storage,
project/Package/Workflow authorization binding, signing/nonce policy, first
capability, fake adapter, request/result/time/concurrency/count/cost limits,
idempotency/reconciliation, Proxy persistence separation, retention/cleanup
and the Progress Report relationship are owner-ratified.

Production authentication and multi-user authorization remain unresolved.
All live-provider eligibility, credential, terms, rate, budget, retry,
retention/deletion, logging and public-network security questions remain
`SOURCE_UNDECIDED` for R3C.

## Consequences

- R3B may implement and accept only the disabled-by-default fake-provider
  vertical slice under the exact controls above.
- The R3B implementation gate may open after this documentation ratification
  closes cleanly; no implementation is performed by this decision milestone.
- The new Proxy ledger remains separate from Hosted execution data.
- Credentials stay outside portable Workflow Packages and tracked evidence.
- R3C and production deployment remain unauthorized.

## Alternatives considered

- Long-lived project tokens were rejected for R3B because copied configuration
  or local leakage would grant durable authority.
- Full user login and device authorization remain future production UX options;
  they exceed the isolated R3B acceptance slice.
- Detached signing, nonces and proof of possession are deferred because the
  owner approved short-lived loopback-only bearer use for R3B, not public use.
- Reusing Hosted `ProviderOperation` through fabricated run/step rows is
  rejected because it violates the teacher-aligned state and execution
  boundary.
- A real provider is excluded; R3C remains a distinct owner-gated milestone.
