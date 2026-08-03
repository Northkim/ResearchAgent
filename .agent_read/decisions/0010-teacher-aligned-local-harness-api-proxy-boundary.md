# ADR 0010: Teacher-Aligned Local-Harness API Proxy Boundary

- **Status:** Proposed
- **Date:** 2026-08-03
- **Governing accepted decision:** ADR 0009
- **Owner decision required:** Yes

## Context

ADR 0009 accepts a teacher-aligned initial V1 in which the local Workflow folder
is authoritative for concrete research state, an existing Codex or Claude Code
Harness performs research, and the cloud manages credentials and a bounded API
Proxy. R1 proves the Codex local-folder execution boundary; R2 proves explicit
Progress Report upload, immutable cloud history and restart recovery. The proxy
protocol, caller authentication, project/package authorization, capability,
limits and retention remain source-undecided.

The repository has useful provider ports, bounded fake/OpenAlex adapters,
immutable artifact storage, provider budgets and an auditable
`ProviderOperation`. Their current call path is Hosted Mode:
`ExecutionDispatcher -> AgentRuntime -> research Skills -> provider`. Current
SQL provider operations require a Hosted `WorkflowRun`. No authenticated
principal, project ownership enforcement or Package-scoped authorization exists.

Reusing that Hosted path would let the cloud schedule Workflow steps, choose
research operations, rank sources, invoke LLM/structured generation and compose
reports. That conflicts with ADR 0009 and the teacher source.

## Proposed decision

Adopt a separate local-Harness-facing Cloud API Proxy with contract version
`reagent.cloud-api-proxy/v0.1` and these invariants:

1. The local Harness chooses and submits one explicit allowlisted capability
   request. Cloud validates authorization, identity, schema and budgets, injects
   a server-side provider credential, invokes one fixed adapter operation and
   returns provider data plus operational provenance.
2. The proxy has no import/call path to `AgentRuntime`, `ExecutionDispatcher`,
   run/resume, research Skills, LLM/structured generation, report generation,
   local Package mutation or Progress Report mutation.
3. Provider and operation allowlists plus fixed server endpoints prohibit
   arbitrary URL forwarding and automatic provider-call chaining.
4. Request identity is deterministic and non-cyclic:
   canonical semantic request -> request-content checksum -> authorization-bound
   version-namespaced operation ID. A response never participates in request
   identity.
5. Same scoped idempotency key and request checksum replays one durable
   operation. Changed content under the same key conflicts before provider use.
   Ambiguous client timeouts require a status/reconciliation read; the local
   client never retries automatically.
6. Provider credentials never enter the Package or contract payload. Provider
   responses are untrusted data and are not executed or automatically processed
   by a cloud LLM.
7. Proxy operational provenance is Cloud Project State. Research interpretation,
   local outputs, context and Progress Reports remain Local Task State.
8. Existing provider ports, fake adapter, canonical hashing, immutable artifact
   storage and budget concepts may be reused behind this boundary. Current
   Hosted `ProviderOperation` persistence requires adaptation or a separate
   Package-scoped record; no fake Hosted run may be created.

Recommend exactly one first capability for owner approval:
`paper.search/v0.1`, a bounded scholarly metadata discovery operation initiated
entirely by the local Harness. It excludes full text/PDFs, source retrieval,
ranking, relevance judgment, synthesis and LLM use.

Recommend one MVP access model for owner approval: a short-lived
project/Package capability token scoped to subject, project, exact Package
checksum, Workflow identity, capability versions and budget, stored outside the
Package. The exact token form, issuance flow, lifetime, revocation and signing
remain undecided.

## Proposed staged sequence

- **R3B:** implement and accept the provider-neutral contract using a
  deterministic fake paper-search adapter, an external Package, real loopback
  HTTP, isolated PostgreSQL, restart/reconciliation, security rejections and no
  real credential/provider.
- **R3C:** only after separate owner authorization and current official terms/
  rate/cost verification, perform one supervised live-provider acceptance with
  dedicated isolated storage and strict approved limits.

R3B and R3C do not authorize Hosted AgentRuntime or LLM execution.

## Owner decisions required before acceptance

The following remain `SOURCE_UNDECIDED`:

- authentication mechanism, issuance flow, token lifetime, refresh and
  revocation;
- authenticated principal, project/package ownership and multi-user isolation;
- Package/checksum binding and request signing/nonce/proof-of-possession;
- approval of `paper.search/v0.1` and its exact normalized fields;
- allowed provider adapter(s);
- request, response, result, timeout, attempt, concurrency and rate limits;
- request-count and cost budgets;
- raw/normalized provider data retention, access, deletion and audit schedules;
- unsafe/rejected response evidence policy;
- whether Progress Reports may add an operation-ID/checksum reference;
- separation of teacher-aligned proxy credentials from optional Hosted routes.

Until these decisions have authoritative owner approval:

```text
R3B_IMPLEMENTATION_GATE = CLOSED
```

## Consequences if accepted

- Local Harnesses can use cloud-held provider credentials without placing keys
  in portable folders.
- The proxy stays operational and provider-neutral; research interpretation and
  concrete task state stay local.
- A new application boundary and Package-scoped durable operation identity are
  required; Hosted run foreign keys cannot be reused unchanged.
- Strict auth, tenancy, budget, reconciliation, retention and security tests
  become blocking gates.
- Provider live acceptance remains separate and supervised.
- No production implementation is authorized by this Proposed ADR or R3A.

## Alternatives considered

### Reuse Hosted run/resume and research Skills

Rejected for teacher-aligned V1 because it schedules and executes cloud
research, can call LLM/report Skills and makes Hosted state authoritative.

### Put provider credentials in each Workflow Package

Rejected because folders are portable/copied task state and would leak durable
provider authority.

### General-purpose authenticated HTTP proxy

Rejected because user-controlled URLs/methods/headers create SSRF, secret
exposure, cost and policy bypass risks.

### Long-lived project API token as the MVP recommendation

Not recommended because copied configuration or local leakage grants broad,
durable authority and weak Package/user attribution.

### Device authorization as the first implementation

Deferred as a stronger future UX because it requires a full identity/browser
flow. A short-lived Package capability can be the narrower result of such a
flow later.

### Expose LLM or structured generation first

Rejected because it most directly risks turning the cloud into the research
Agent. The first slice is bounded metadata discovery only.
