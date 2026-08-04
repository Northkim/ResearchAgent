# Cloud API Proxy Threat Model

Status: **R3B ACCEPTED; R3C-N2-I OPENALEX DIAGNOSTICS QUALIFIED — LIVE/PRODUCTION CLOSED**

Date: 2026-08-04

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
local Harness process -- R3B loopback HTTP / future approved HTTPS --> cloud edge
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
2. Authentication and authorization fail closed. In R3B, the server derives
   token, tenant, subject, project, exact Package ID/checksum, exact Workflow
   identity/checksum, capability, fake-adapter, operation-count, expiry and
   revocation scope from the server token record, never from client roles.
3. No arbitrary URL, host, scheme, method, header or redirect is accepted from
   the local caller. Provider and operation allowlists select fixed server-owned
   endpoints.
4. Strict versioned capability schemas reject unknown fields, type confusion,
   injection strings, invalid Unicode/control characters and out-of-range
   values before provider invocation.
5. R3B bounds the request body at 16 KiB, normalized result at 512 KiB,
   `max_results` at 20, timeout at 10 seconds, concurrency per token at 2,
   operations per token at 50, and money/real-provider/external-network use at
   zero.
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
| Provider-key leakage into a Package | Key is placed in `cloud/`, prompt, output or context and moves with the folder. | R3B has no provider key. R3C accepts only server-side `REAGENT_OPENALEX_API_KEY`; Package schema forbids secrets and generated Packages are scanned. | Production secret management/rotation remains unapproved. |
| Key leakage into logs/errors/Progress Reports | Credential-bearing URL or exception is collected. | Inject at adapter boundary; never log request URL/headers; sanitize exception chains; secret-field denylist; Progress Report validator rejects credentials/raw provider response. | Third-party observability configuration needs implementation review. |
| Bearer-token plaintext leakage | Operator/client prints it, passes it as an argument, stores it in `.env`, Package, database/artifact or permissive file. | Operator CLI writes once to a new outside-Git/Package file at mode `0600`, refuses overwrite and emits no plaintext; client reads process environment only; server stores SHA-256 digest; logs/Progress Reports/artifacts reject it; delete the file after acceptance. | A same-user local process may still read process environment; R3B is isolated and short-lived. |
| Arbitrary URL / SSRF | Caller asks proxy to fetch attacker, loopback, link-local, private, metadata or internal service. | No URL parameter; fixed adapter host/scheme/path; redirects disabled. If future DNS resolution is used, revalidate all resolved addresses and deny loopback, private, link-local, multicast, reserved and metadata ranges. | Any new adapter endpoint requires separate allowlist review. |
| Cross-project access | Caller submits another project/package ID or reads its operation. | Server derives tenant/subject/project/Package/Workflow scope from the token record; route/body identity cannot expand it; every read uses the same scope. | Production ownership and multi-user roles remain `SOURCE_UNDECIDED`. |
| Package identity spoofing | Copied/altered Package claims an allowed identity. | Validate exact token-bound Package ID/checksum and Workflow ID/version/checksum; reject all mismatch before adapter use; no client ownership claims. | Production Package/token issuance remains unapproved. |
| Stolen bearer capability | Token theft grants its R3B scope. | At least 256 random bits; SHA-256 digest-only server storage; constant-time comparison; 60-minute default/120-minute maximum; narrow exact scope/count; explicit revocation; plaintext outside Package/Git and removed after acceptance. | No proof of possession in R3B; loopback-only use limits but does not remove local-process theft risk. |
| Replay attack | Captured request is resubmitted to consume quota or obtain data. | Loopback-only R3B transport; short-lived authorization; UUIDv4 idempotency; exact replays return the same operation without a second adapter call; changed-content replay conflicts; status reads are scoped. | Detached signing/nonces/proof of possession are deferred to production security review. |
| Idempotency-key substitution | Attacker reuses another key with changed request. | Operation identity binds authorized scope, key and request checksum; conflict before call; key lookup never crosses tenant/project/package scope. | Concurrent-race behavior must be accepted in R3B. |
| Parameter/query injection | Provider-specific syntax, control characters or huge arrays alter operation. | Capability-specific schema, max lengths/counts, allowlisted enum/range fields, canonical encoding; no raw filter/header/URL; adapter uses structured parameters. | Provider query-language edge cases require adapter tests. |
| Oversized request | Memory/CPU exhaustion or log amplification. | Enforce 16 KiB before JSON expansion plus depth, UTF-8, query-length and unknown-field checks. | Production limits require separate review. |
| Oversized provider response | Memory/storage exhaustion or malicious content. | R3C enforces 512 KiB actual decoded Provider response bytes before persistence, 20 records and 10 seconds; reject without unsafe artifact. | Live server/provider behavior remains for R3C-A. |
| Provider-cost abuse | Many operations consume budget. | R3B remains zero-cost. R3C-A caps 20 operations/calls and USD 0.05, requires exact sub-cent settlement, zero retry and no prepaid authorization. | Production funding/rate policy remains unapproved. |
| Quota exhaustion / noisy neighbor | One caller exhausts the experimental service. | Token-bound count/concurrency limits and fail-closed accounting; no provider switching. | Production tenant/global allocation remains `SOURCE_UNDECIDED`. |
| Malicious provider content | Titles/abstracts include HTML, script, terminal escapes, URLs, secrets or instructions. | Validate Unicode/size; tag as untrusted; escape on presentation; no script execution; no automatic fetching; no cloud LLM; local client prints metadata only, not raw content by default. | Local Harness can still be influenced; Package instructions must reinforce data/instruction separation. |
| Prompt injection in provider data | Provider text tells Harness/cloud to disclose secrets or change task. | Cloud never promotes provider text to instructions or LLM prompts; normalized fields labelled untrusted; local Skill instructs Harness to ignore embedded instructions. | Existing general-purpose Harness behavior remains a user-environment risk. |
| Executable/script-bearing response | Browser/client executes active content. | JSON-only normalized response for first slice; `nosniff`, attachment where applicable, strict CSP/escaping in future UI; no HTML media type; never eval/import. | Frontend is out of R3A/R3B scope. |
| Secret-bearing provider response | Provider echoes credentials or returns accidental secrets. | Field allowlist, secret-like scan, redact/reject unsafe data before retention/delivery; record checksum/category only. | False positive/negative policy needs tests; raw unsafe body should not persist. |
| Path injection/local disclosure | Request or response supplies absolute/traversal path; client reads arbitrary local file. | Proxy request has no local path; local client accepts only package-relative declared configuration; storage keys are relative and traversal/symlink-safe. | Future upload features require their own path review. |
| Log injection | Newlines/control characters forge audit events. | Structured JSON logs, encoded values, control-character rejection, length caps, stable request IDs. | Operator log sink must preserve structure. |
| Structural diagnostic becomes a value side channel | Field values, unknown key names, exceptions or request/response objects leak through a diagnostic or its checksum. | Default-off server flag; closed stage/path/kind/validator enums; value-independent approved-field shape descriptor; no exception interpolation/`exc_info`; one temporary mode-`0600` log; leakage/checksum tests. | A future live diagnostic remains separately owner-gated and requires post-run leakage audit/cleanup. |
| Tenant data leakage | Caches, replay/status reads or error details reveal another tenant’s query/results/budget. | Scope every lookup/cache key by authenticated tenant/project/package; response DTO allowlist; no existence oracle; row-level repository predicates and tests. | Multi-user tenancy is `SOURCE_UNDECIDED`. |
| Retention beyond approval | Provider data or token material remains after acceptance. | R3B/R3C acceptance-lifetime retention only; no raw body/query/key/token/Auth URL/header; remove isolated database/runtime/secret material and retain sanitized evidence only. | Production retention/deletion/export remains unapproved. |
| Legacy Hosted endpoint misuse | Caller uses `/runs/.../resume` to execute research instead of the proxy. | Proxy credentials cannot authorize Hosted routes; teacher-aligned deployment can separately disable/hide Hosted paths; proxy service imports no Hosted graph. | Route-level mode separation needs later explicit implementation scope. |
| Accidental AgentRuntime/LLM invocation | Composition injects `ApplicationServices` or research Skills into proxy. | Dedicated proxy composition/service dependency; static forbidden-import tests and runtime provider canaries; database checks for no Hosted run/event/checkpoint/memory rows. | Required R3B acceptance gate. |
| Cloud crash/partial persistence | Provider may have completed but operation appears absent/incomplete. | Durable reservation before call; immutable result then settlement; conservative `RECONCILIATION_REQUIRED`; status read; no ambiguous auto retry. | Exactly-once is impossible without provider reconciliation/idempotency. |
| Operation-status probing | Attacker guesses operation IDs. | Authorization-scoped reads, deterministic IDs include auth binding but are not treated as secrets, uniform errors and rate limits. | Token compromise still exposes its authorized scope. |

## 6. Ratified R3B authentication and authorization

R3B uses one short-lived opaque bearer capability token with at least 256 bits
of cryptographically secure randomness. An operator-only CLI, not a public
endpoint, issues it. The server stores a SHA-256 digest and metadata only and
uses constant-time comparison. The CLI writes plaintext once to a new caller-
specified `0600` file outside Git and the Workflow Package, refuses overwrite,
and never prints it to ordinary stdout/logs. The client reads it only from the
`REAGENT_PROXY_TOKEN` process environment; it is never a command-line argument
or `.env` file value. The file is deleted after acceptance.

Default lifetime is 60 minutes; maximum and R3B acceptance lifetime is 120
minutes. There is no refresh. Explicit server-side revocation is required.
R3B uses loopback HTTP bound to `127.0.0.1`, permits client timestamp skew of
plus or minus five minutes, and has no detached signature, nonce or proof of
possession. Non-loopback use requires HTTPS and separate approval.

The token record binds token, tenant and subject IDs; project ID; exact Package
ID/checksum; exact Workflow ID/version/checksum; capability
`paper.search/v0.1`; the deterministic fake adapter; maximum operation count;
issue/expiry times; and revocation state. The server never trusts client-
supplied actor, role, tenant, owner or permission claims. All mismatches fail
before adapter use.

This is an experimental acceptance mechanism, not production authentication or
multi-user authorization.

## 7. Implemented R3B-I controls

The authorized fake-provider-only R3B-I implementation includes:

- a dedicated Proxy route/service/composition graph with forbidden Hosted
  imports;
- deterministic operation identity and a separate Package-scoped Proxy ledger,
  without fabricating Hosted provider/run/step rows;
- the exact digest-only token lifecycle and server-derived scope above;
- strict `paper.search/v0.1` `query`/`max_results` schemas;
- 16 KiB request, 512 KiB normalized result, 10-second timeout, two concurrent
  operations/token, 50 operations/token and zero-cost/network/real-provider
  limits;
- explicit `RECEIVED`, `RUNNING`, `SUCCEEDED`, `FAILED` and
  `RECONCILIATION_REQUIRED` handling;
- UUIDv4 scoped idempotency, HTTP 409 `IDEMPOTENCY_CONFLICT`, explicit timeout
  status reads and no ambiguous automatic retry;
- acceptance-lifetime safe retention and complete isolated-environment cleanup;
- structured redacted logs and a security rejection matrix;
- provider/AgentRuntime/LLM canaries proving zero forbidden execution.

The bearer is generated with `secrets.token_urlsafe(32)`, stored only as a
SHA-256 digest and compared with `hmac.compare_digest`, including a dummy miss
comparison. The operator CLI accepts no plaintext-token argument, writes only
to a new outside-repository/outside-Package `0600` file and redacts failures.
The client accepts the token only from `REAGENT_PROXY_TOKEN`; API bodies,
responses, paths and query parameters cannot contain it.

The Proxy request parser reads and bounds actual bytes before JSON decoding,
rejects duplicate keys, unsupported fields, invalid UTF-8/control characters,
non-UUIDv4 idempotency, stale/future timestamps and every Package/Workflow/
capability mismatch. Result size is calculated after canonical serialization
and before persistence/delivery. Oversize and timeout outcomes retain only safe
terminal metadata.

The runtime route selects only
`reagent.deterministic-fake-paper-search/v0.1`; its focused socket canary and
source/import audit show no live transport. The Proxy module imports no Hosted
Runtime/dispatcher/operation graph. PostgreSQL tests verify that Proxy calls
create only separate token/operation rows and that the operation table has no
Hosted Workflow foreign key.

R3B-A accepted the full external token-file, live server, loopback HTTP,
restart and cleanup lifecycle with the deterministic fake adapter. That
evidence is not production authentication or public-network acceptance.

## 8. Ratified R3C experimental controls

ADR 0012 resolves the live-provider decisions only for one supervised OpenAlex
metadata-search experiment. R3C-I is network/key-free implementation with a
scripted transport. R3C-A remains separately gated and, when explicitly
started, may use only:

- the sole server-side credential source `REAGENT_OPENALEX_API_KEY`;
- one fixed HTTPS origin/path with TLS verification, redirects and ambient
  proxies disabled;
- ordinary `paper.search/v0.1`, one unchanged query, one Works page and the
  fixed field allowlist;
- no more than 20 calls/operations, USD 0.05, 20 results, 512 KiB and 10
  seconds, with zero automatic retry or prepaid authorization;
- fictional public non-sensitive queries;
- acceptance-lifetime normalized metadata/checksums/usage only, without raw
  body, query-at-rest, key, credential URL, PDF or full text;
- existing durable idempotency and conservative reconciliation with no second
  call after uncertainty.

The additional OpenAlex-specific threats and mitigations are frozen in
`R3C_OPENALEX_CREDENTIAL_PRIVACY_AND_COST_POLICY.md`. Official pricing, Terms,
Privacy and schema must be rechecked immediately before R3C-A.

ADR 0013 additionally ratifies strict complete-response failure and an internal
value-free structural diagnostic. Its separate server flag is disabled by
default and cannot enable the Proxy or credential loading. Per-Work failures
and service sensitive-content rejection have distinct fixed classifications;
neither changes the public error. Diagnostics are log-only, contain no Provider
value/query/key/raw body/URL/exception, and add no SQL/API/Package/Progress
Report field. A future at-most-one-call diagnostic requires fresh owner
authorization and does not open R3C-I2 or R3D.

The following remain `SOURCE_UNDECIDED` for production:

- production user authentication and multi-user project ownership;
- production token issuance UX, storage, revocation and proof of possession;
- HTTPS/non-loopback deployment and public-network security acceptance;
- production Provider eligibility, paid/prepaid terms, rate/cost/retry policy;
- production raw/normalized data retention, deletion/export and backup policy;
- production logs, audit retention and tenant visibility;
- formal Progress Report proxy-operation fields;
- authorization separation from optional Hosted routes in a production
  deployment.

`R3C_STATE = LIVE_ACCEPTANCE_PENDING`, while
`R3C_A_LIVE_ACCEPTANCE_GATE = CLOSED` and
`R3D_PRODUCTION_PROVIDER_GATE = CLOSED`.

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
- The R3B bearer has no proof of possession; its narrow scope, short lifetime,
  revocation and loopback-only use limit but do not eliminate theft/replay risk.
- Production authentication, multi-user isolation and live-provider retention
  remain unapproved; therefore `R3D_PRODUCTION_PROVIDER_GATE` remains closed.
