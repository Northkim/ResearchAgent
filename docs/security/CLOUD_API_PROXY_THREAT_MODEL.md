# Cloud API Proxy Threat Model

Status: **COMPLETE FOR OWNER REVIEW — CONTROLS PROPOSED, NOT IMPLEMENTED**

Date: 2026-08-03

Scope: teacher-aligned local-Harness API Proxy v0.1

## 1. Security objective

Allow an authorized local Codex or Claude Code Harness to request one bounded,
allowlisted provider operation while keeping the provider credential
server-side and preserving the local Workflow folder as concrete task-state
authority. Uploaded/requested content remains untrusted data. The cloud must
not become a research Agent or a general HTTP proxy.

## 2. Assets

- provider credentials and cloud signing/encryption keys;
- caller credentials and revocation state;
- project, Package and Workflow identity/ownership;
- provider capability and budget policy;
- idempotency keys, operation identity and settlement state;
- normalized request parameters and provider response data;
- usage, quota, cost and audit records;
- immutable response artifacts when retention is approved;
- local Package confidentiality and integrity;
- tenant isolation and service availability;
- the teacher-aligned product boundary itself.

## 3. Trust boundaries

```text
untrusted Package/provider data
  | local client validation
  v
local Harness process -- authenticated loopback/Internet transport --> cloud edge
                                                            | authn/authz
                                                            v
                                                 proxy application boundary
                                                            | fixed adapter port
                                                            v
                                                   external provider service
```

Additional boundaries exist between cloud application code and credential
storage, PostgreSQL operation metadata, immutable artifact storage, structured
logs/telemetry and any future UI. The local Package is not a credential store.
The provider is not trusted to return safe text, HTML, URLs or instructions.

## 4. Mandatory security requirements

These are requirements for any implementation; they are not evidence that R3A
implemented them.

1. Provider credentials remain server-side and are injected only inside a fixed
   provider adapter. They never enter a Package, request/response envelope,
   Progress Report, artifact metadata, URL returned to the client, exception or
   log.
2. Authentication and authorization fail closed. Authorization binds the
   authenticated subject to project, Package ID/checksum, Workflow identity,
   capability, policy version and budget.
3. No arbitrary URL, host, scheme, method, header or redirect is accepted from
   the local caller. Provider and operation allowlists select fixed server-owned
   endpoints.
4. Strict versioned capability schemas reject unknown fields, type confusion,
   injection strings, invalid Unicode/control characters and out-of-range
   values before provider invocation.
5. Request body, response body, record count, timeout, attempt count, concurrent
   operations and cost are bounded before or during processing.
6. Idempotency is authorization-scoped and request-content-bound. Key reuse
   with changed content fails before the provider call.
7. Logs are structured, length-bounded and escaped. They contain IDs, hashes,
   counts and safe categories, not credentials, authorization headers, raw
   provider bodies, unbounded query text or Package paths.
8. Provider response content is data only. It is never executed, imported,
   rendered as trusted HTML, followed as instructions or automatically passed
   to a cloud LLM.
9. Storage uses immutable checksum-bound objects and relative keys. Retention
   is minimized and enforced by an owner-approved policy.
10. Proxy routes and services have no import/call path to `AgentRuntime`,
    `ExecutionDispatcher`, Workflow resume, research Skills, LLM/structured
    generation, local Package mutation or Progress Report generation.
11. Status/reconciliation reads use the same authorization scope. Cross-project
    identifiers return no tenant information.
12. Security rejection occurs before unsafe response/request artifact retention;
    audit records contain only safe evidence.

## 5. Threat and mitigation matrix

| Threat | Abuse/failure | Required mitigation | Residual risk / decision |
|---|---|---|---|
| Provider-key leakage into a Package | Key is placed in `cloud/`, prompt, output or context and moves with the folder. | Package schema forbids secret values; proxy config contains lookup method only; provider key never reaches client; scan generated packages. | Credential source/rotation product is `SOURCE_UNDECIDED`. |
| Key leakage into logs/errors/Progress Reports | Credential-bearing URL or exception is collected. | Inject at adapter boundary; never log request URL/headers; sanitize exception chains; secret-field denylist; Progress Report validator rejects credentials/raw provider response. | Third-party observability configuration needs implementation review. |
| Arbitrary URL / SSRF | Caller asks proxy to fetch attacker, loopback, link-local, private, metadata or internal service. | No URL parameter; fixed adapter host/scheme/path; redirects disabled. If future DNS resolution is used, revalidate all resolved addresses and deny loopback, private, link-local, multicast, reserved and metadata ranges. | Any new adapter endpoint requires separate allowlist review. |
| Cross-project access | Caller submits another project/package ID or reads its operation. | Authenticated subject plus server-side ownership lookup; route ID never grants access; bind operation to authorization checksum; uniform not-found/forbidden behavior. | Project ownership model is `SOURCE_UNDECIDED`. |
| Package identity spoofing | Copied/altered Package claims an allowed identity. | Validate exact cloud-known Package ID/checksum and pinned Workflow identity; token scope binds Package checksum; no client-supplied ownership claims. | Package issuance/revocation policy requires owner decision. |
| Stolen long-lived Package credential | Copied folder or shell history grants durable access. | Recommended short-lived package-scoped capability; store outside Package; narrow capability/budget; explicit revocation; never print token. | Token lifetime, storage and refresh are `SOURCE_UNDECIDED`. |
| Replay attack | Captured request is resubmitted to consume quota or obtain data. | TLS; short-lived authorization; scoped idempotency; optional nonce/signing decision; replays return existing operation without second provider call; status reads audited. | Bearer-token replay resistance and signing are owner decisions. |
| Idempotency-key substitution | Attacker reuses another key with changed request. | Operation identity binds authorized scope, key and request checksum; conflict before call; key lookup never crosses tenant/project/package scope. | Concurrent-race behavior must be accepted in R3B. |
| Parameter/query injection | Provider-specific syntax, control characters or huge arrays alter operation. | Capability-specific schema, max lengths/counts, allowlisted enum/range fields, canonical encoding; no raw filter/header/URL; adapter uses structured parameters. | Provider query-language edge cases require adapter tests. |
| Oversized request | Memory/CPU exhaustion or log amplification. | Edge/content-length cap plus streaming bounded read; reject before JSON expansion; nested-depth/string/list limits. | Exact size limit needs owner approval. |
| Oversized provider response | Memory/storage exhaustion or malicious decompression. | Streaming byte cap, compressed/decompressed caps, record cap, timeout, abort, no partial unsafe artifact. | Exact response limit needs owner approval. |
| Provider-cost abuse | Many operations or high-cost parameters consume budget. | Reserve before call; per operation/project/package/subject/time-window count and cost caps; zero-cost first capability; fail closed on unknown price. | Budget values and funding policy are `SOURCE_UNDECIDED`. |
| Quota exhaustion / noisy neighbor | One caller consumes provider/global limits. | Tenant/project quotas, concurrency limits, rate evidence, fair rejection and operator alerting; never silently switch providers. | Multi-user/global allocation is `SOURCE_UNDECIDED`. |
| Malicious provider content | Titles/abstracts include HTML, script, terminal escapes, URLs, secrets or instructions. | Validate Unicode/size; tag as untrusted; escape on presentation; no script execution; no automatic fetching; no cloud LLM; local client prints metadata only, not raw content by default. | Local Harness can still be influenced; Package instructions must reinforce data/instruction separation. |
| Prompt injection in provider data | Provider text tells Harness/cloud to disclose secrets or change task. | Cloud never promotes provider text to instructions or LLM prompts; normalized fields labelled untrusted; local Skill instructs Harness to ignore embedded instructions. | Existing general-purpose Harness behavior remains a user-environment risk. |
| Executable/script-bearing response | Browser/client executes active content. | JSON-only normalized response for first slice; `nosniff`, attachment where applicable, strict CSP/escaping in future UI; no HTML media type; never eval/import. | Frontend is out of R3A/R3B scope. |
| Secret-bearing provider response | Provider echoes credentials or returns accidental secrets. | Field allowlist, secret-like scan, redact/reject unsafe data before retention/delivery; record checksum/category only. | False positive/negative policy needs tests; raw unsafe body should not persist. |
| Path injection/local disclosure | Request or response supplies absolute/traversal path; client reads arbitrary local file. | Proxy request has no local path; local client accepts only package-relative declared configuration; storage keys are relative and traversal/symlink-safe. | Future upload features require their own path review. |
| Log injection | Newlines/control characters forge audit events. | Structured JSON logs, encoded values, control-character rejection, length caps, stable request IDs. | Operator log sink must preserve structure. |
| Tenant data leakage | Caches, replay/status reads or error details reveal another tenant’s query/results/budget. | Scope every lookup/cache key by authenticated tenant/project/package; response DTO allowlist; no existence oracle; row-level repository predicates and tests. | Multi-user tenancy is `SOURCE_UNDECIDED`. |
| Retention beyond approval | Provider data remains indefinitely in artifacts/backups. | Data-class policy, TTL/deletion jobs after approval, deletion audit, backup policy, minimum metadata default, raw body off. | All durations/deletion/user controls are `SOURCE_UNDECIDED`. |
| Legacy Hosted endpoint misuse | Caller uses `/runs/.../resume` to execute research instead of the proxy. | Proxy credentials cannot authorize Hosted routes; teacher-aligned deployment can separately disable/hide Hosted paths; proxy service imports no Hosted graph. | Route-level mode separation needs later explicit implementation scope. |
| Accidental AgentRuntime/LLM invocation | Composition injects `ApplicationServices` or research Skills into proxy. | Dedicated proxy composition/service dependency; static forbidden-import tests and runtime provider canaries; database checks for no Hosted run/event/checkpoint/memory rows. | Required R3B acceptance gate. |
| Cloud crash/partial persistence | Provider may have completed but operation appears absent/incomplete. | Durable reservation before call; immutable result then settlement; conservative `RECONCILIATION_REQUIRED`; status read; no ambiguous auto retry. | Exactly-once is impossible without provider reconciliation/idempotency. |
| Operation-status probing | Attacker guesses operation IDs. | Authorization-scoped reads, deterministic IDs include auth binding but are not treated as secrets, uniform errors and rate limits. | Token compromise still exposes its authorized scope. |

## 6. Authentication and authorization option packet

No repository authentication implementation was found. The following options
are alternatives for owner decision, not implemented facts.

| Access model | Lifetime / revocation | Local storage and copied-folder risk | Binding / replay | Harness usability | Audit / complexity / multi-user |
|---|---|---|---|---|---|
| Long-lived project API token | Weeks/months; server denylist/rotation | If placed in Package, copying grants access; must live outside it. Shell/config leakage risk is high. | Project scope possible, Package checksum weaker unless many tokens; bearer replay window long. | Simple for Codex and Claude Code; works until revoked and can be used offline only for local validation. | Simple audit; low implementation cost; poor least privilege and multi-user attribution. |
| User bearer token from login | Session/refresh-token lifetime; user/session revocation | Stored in user credential store; Package copy need not copy it. | User/project ownership can be enforced; broad bearer token may authorize more than one Package; replay until expiry. | Familiar but requires login/browser or existing CLI session; usable by both Harnesses through client. | Strong user attribution; medium/high implementation complexity; requires full user and tenant model. |
| Short-lived project/Package capability token | Minutes/hours; expiry plus explicit server revocation | Stored outside Package in OS credential store or ephemeral process environment; copied folder has no authority. | Directly binds project, Package checksum, capability, limits and policy; short replay window; signing/nonce remains optional decision. | One supervised mint/refresh action; client can be called by Codex or Claude Code without exposing provider key. No provider operation while offline. | Strong least privilege/audit; medium complexity; compatible with later multi-user ownership. |
| Device authorization flow | Short-lived device code, then user/session tokens; central revocation | No secret typed into Package; final token stays in credential store. | Strong user/device binding depending implementation; bearer replay still applies after issuance. | Good headless UX but needs browser/login and polling; both Harnesses can use it. | Strong audit/multi-user potential; high implementation complexity for MVP. |
| Manually copied one-time proxy token | One use or very short TTL; naturally expires/revocable | Clipboard/shell-history risk; never Package. Copied folder alone has no authority. | Can bind one Package/capability/request budget; captured token may race legitimate use. | Explicit and supervised but burdens every session/operation; both Harnesses can pass it to client. | Clear audit, medium complexity, poor repeated-use UX. |

### Recommended MVP option

Recommend **one short-lived project/Package capability token**, minted only
after a supervised authenticated owner action. The token should be scoped to an
authenticated subject, tenant/project, exact Package ID/checksum, Workflow
identity, allowed capability versions, maximum operations/cost and short expiry.
The local client retrieves it outside the Package, never prints it, and sends it
only over TLS. Copying the Package therefore copies task state but not cloud
authority.

This is the best balance of least privilege, revocation, Package portability,
Codex/Claude Code suitability and a future multi-user model. It is a
recommendation only. Owner approval is required before implementation. Whether
the MVP token is a signed bearer, opaque server-side session, proof-of-possession
credential, or minted through a one-time bootstrap remains `SOURCE_UNDECIDED`.

Long-lived project tokens are not recommended because a Package-oriented tool
would make leakage/copy risk durable. Device flow is a good later UX but is too
broad for the first fake-provider contract slice. A manually copied one-time
token is safe for an acceptance bootstrap but too burdensome as the product
model. A full user login bearer token should eventually authenticate the person,
then mint the narrower Package capability rather than serve as the proxy
credential itself.

## 7. Recommended implementation controls for R3B

Subject to owner approval, the fake-provider-only R3B design should include:

- a dedicated proxy route/service/composition graph with forbidden Hosted
  imports;
- deterministic operation identity and an additive Package-scoped operation
  ledger, without fabricating `WorkflowRun` rows;
- an authentication seam with a fictional acceptance credential mechanism
  matching the approved MVP shape, never a production secret;
- strict `paper.search/v0.1` request/response schemas;
- immutable response bytes only if the approved R3B retention design calls for
  them;
- request, response, concurrency, count, timeout and zero-cost budgets;
- explicit operation status reconciliation;
- structured redacted logs and security rejection matrix;
- provider/AgentRuntime/LLM canaries proving zero forbidden execution.

These recommendations do not authorize implementation while the gate is
closed.

## 8. Owner decisions required

Every row remains `SOURCE_UNDECIDED` unless an owner later records approval.

| Decision | Required resolution |
|---|---|
| Authentication mechanism | Approve or replace the short-lived project/Package capability recommendation and its issuance flow. |
| Token lifetime and refresh | Exact TTL, refresh/mint interaction and maximum session duration. |
| Revocation | Token/session/package/project revocation model and propagation latency. |
| Local credential storage | OS credential store, ephemeral environment, agent integration and safe failure behavior. |
| Package binding | Exact Package ID/checksum/Workflow fields and behavior after package refresh. |
| Project ownership/authorization | Authenticated principal and tenant/project/package ownership enforcement. |
| Signing/replay controls | Bearer only versus request signing, nonce, proof of possession and clock-skew policy. |
| Multi-user isolation | Tenant boundary, collaborator roles, shared budgets and audit visibility. |
| First capability | Approve `paper.search/v0.1` as the only R3B/R3C first slice. |
| Provider eligibility | Fake adapter for R3B; whether OpenAlex remains the first R3C adapter after current terms review. |
| Request/result limits | Exact request bytes, query lengths, result count, timeout, attempt and response-byte caps. |
| Budget/cost | Per operation/project/package/user/time-window requests and approved monetary cost. |
| Response normalization | Exact metadata/abstract fields and whether provider-native ordering is returned. |
| Raw response retention | Default recommendation is never; approve any exception and its encryption/access limits. |
| Normalized response retention | Whether, where and for how long metadata/abstracts may persist. |
| Rejected/unsafe data | What safe hashes/categories may remain; default is no unsafe body retention. |
| Deletion/export | Schedule, user-triggered deletion, audit retention and backup behavior. |
| Progress Report link | Whether a future v0.2-compatible additive field may reference operation IDs/checksums. |
| Hosted route isolation | How teacher-aligned proxy credentials are prevented from authorizing optional Hosted routes. |

## 9. Residual risks

- A general-purpose local Harness may still be influenced by malicious provider
  text after safe delivery; instructions and client presentation reduce but do
  not eliminate this risk.
- Exactly-once provider execution cannot be guaranteed when the provider offers
  neither idempotency nor status reconciliation.
- Provider terms, rate limits, schemas and cost rules change. R3C must verify
  current official sources immediately before any supervised live call.
- Metadata, abstracts and third-party rights may differ; a provider’s dataset
  license does not automatically settle all retained field rights.
- Token theft grants its scoped authority until expiry/revocation. Short TTL,
  binding, narrow budget and optional proof of possession reduce impact.
- Server-side redaction can miss novel secrets. The first slice should retain
  the minimum normalized data and no raw body by default.
- Authentication, multi-user isolation, retention and limits are not approved;
  therefore `R3B_IMPLEMENTATION_GATE` remains closed.
