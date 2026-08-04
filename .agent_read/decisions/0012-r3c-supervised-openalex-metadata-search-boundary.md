# ADR 0012: R3C Supervised OpenAlex Metadata-Search Boundary, Credential, Budget, Privacy, and Retention Decisions

- **Status:** Accepted
- **Date:** 2026-08-04
- **Scope:** Supervised experimental R3C only
- **Governing decisions:** ADR 0009, ADR 0010, and ADR 0011
- **Official-source qualification:** `PASS_WITH_CURRENT_SOURCE_WARNINGS`

## Context

R3B accepted a separate local-Harness Cloud API Proxy using a deterministic
fake adapter. R3C may replace that fake transport with one tightly bounded live
metadata operation, but must not revive Hosted research execution. Current
official OpenAlex sources were retrieved from approved documentation domains,
fingerprinted and compared with the existing Hosted adapter. No Provider API or
key was used.

The current official keyed Works-search contract supports the proposed slice.
Official pages differ on whether tiny unauthenticated/demo usage remains
available. That wording does not affect this decision because R3C requires an
owner-provided key and prohibits anonymous use. Pricing, Terms, Privacy and API
schema are mutable and must be rechecked immediately before R3C-A.

The current developer Overview labels the complete dataset CC0, while the
older 2024 Terms retain reserved-rights and unauthorized-redistribution
language for the Database/Data and warn about third-party publication rights.
This decision authorizes only temporary normalized acceptance metadata, not
public redistribution, and does not claim to resolve that legal wording.

## Decision

### 1. Phase classification

R3C is experimental and non-production. It is split into:

- **R3C-I:** implementation plus mocked/scripted-transport and isolated-SQL
  qualification; no API key, live Provider call or Internet access.
- **R3C-A:** separately authorized supervised live OpenAlex acceptance from an
  exact clean R3C-I baseline, with an owner-provided key and tightly capped
  calls.

This decision does not implement or execute either phase.

### 2. Provider and capability

The only approved live Provider is **OpenAlex**. The only capability remains
`paper.search/v0.1`. The Provider operation is one single-page OpenAlex Works
metadata search. The external Package/Harness request remains provider-neutral;
OpenAlex parameters, identity and error details stay behind the server adapter.

### 3. Operation restrictions and mapping

The adapter maps the locally supplied, outer-trimmed `query` directly to the
current ordinary OpenAlex `search` parameter without generating, tokenizing,
quoting, translating, expanding or otherwise rewriting it. `max_results` maps
to `per_page`, range 1–20, for exactly one page.

The fixed top-level `select` list is:

```text
id,doi,display_name,authorships,abstract_inverted_index,publication_year,primary_location,language
```

These fields are sufficient for the current provider-neutral `PaperRecord`:
provider identity, DOI, title, authors, abstract when available, publication
year, venue and language. `source_url` is constructed only from a validated
OpenAlex Work ID. The adapter follows no Provider-returned URL.

The slice does not accept arbitrary filters, sort, cursor/page, pagination,
semantic or exact search, text/aboutness classification, autocomplete,
grouping, content/PDF/full-text download, other entity endpoints, arbitrary
Provider URLs, custom headers or methods. Provider default sequence may be
preserved as transport provenance but is not a ReAgent relevance judgment.

### 4. Credential source

The repository already has one safe authoritative variable:

```text
REAGENT_OPENALEX_API_KEY
```

R3C reuses that as the sole active OpenAlex credential source. The key remains
server-side. During R3C-A plaintext may exist only in the supervised server
process environment or one owner-controlled secret file outside Git, the
Workflow Package and runtime evidence. It is prohibited from PostgreSQL,
artifact storage, Package files, committed `.env`, command arguments, API
responses, Progress Reports, logs and tracked acceptance evidence.

The Provider currently accepts `api_key` through its documented request
mechanism. Every URL, exception and transport/log path must therefore redact
both the key and the full credential-bearing URL.

### 5. Outbound network boundary

Only the fixed official origin required by the current OpenAlex API contract is
allowed:

```text
https://api.openalex.org
```

The transport uses HTTPS with certificate verification, a fixed host and fixed
Works path, redirects disabled, no user-controlled URL/host/method/header, no
private/loopback/link-local destination and no inherited ambient proxy
configuration. DNS, connect, read, write and pool timeouts are bounded. Every
newly admitted live operation causes at most one Provider HTTP request.

### 6. Live acceptance limits and budget

R3C-A ceilings are:

- 20 newly admitted live Provider operations;
- 20 total Provider HTTP calls;
- USD 0.05 total reported acceptance spend;
- no prepaid spending authorization;
- 20 results per call;
- 512 KiB Provider response bytes;
- 10 seconds per Provider operation;
- zero automatic Provider retries;
- zero full-text/PDF calls.

Current official pricing states Works search costs `$0.001` per call, so the
maximum expected 20-call total is `$0.02`. R3C-I reserves and settles cost using
an exact decimal or equivalent precision; the Hosted whole-cent usage field is
not sufficient. R3C-A must recheck pricing and require owner confirmation that
prepaid spending is unavailable/disabled before the first call. A missing,
invalid or contradictory `meta.cost_usd`/usage-header contract, changed price,
exhausted local call/cost budget, missing key or wrong capability fails closed.
No separate `/rate-limit` preflight is approved because it would consume an
extra Provider call.

### 7. Idempotency, retry and reconciliation

R3B Proxy idempotency remains authoritative. Exact replay returns the existing
ProxyOperation and causes no second OpenAlex call or cost. Changed canonical
content under the same scoped idempotency key remains
`IDEMPOTENCY_CONFLICT` before Provider use.

There is no automatic Provider retry, even though official OpenAlex guidance
recommends backoff for transient failures. A timeout or uncertain outcome uses
the existing explicit status path and `RECONCILIATION_REQUIRED`; the system
does not guess failure or issue a replacement call. No worker, queue, lease,
fallback Provider or retry engine is authorized.

### 8. Provider data and retention

Provider data is untrusted. The adapter may normalize only the fixed fields
above into the existing provider-neutral paper-search model. It must not
execute HTML/script, follow file/content URLs, read local paths, send content to
an LLM, judge relevance, rank for research quality or synthesize findings.

R3C-A retention lasts only for its isolated acceptance environment. It may
retain safe normalized paper metadata, request/response identities and
checksums, adapter identity/version, safe Provider identifiers, operation
status, timestamps/latency and exact safe usage/cost evidence. It must not
persist the raw Provider response body, API key, credential-bearing URL,
credential material, PDF/full text or unsafe executable content. Query text is
not retained beyond the minimum transient call path; durable idempotency uses
its canonical checksum.

After R3C-A, the isolated database, runtime material, key file/environment and
temporary evidence are removed; only sanitized tracked acceptance evidence
remains. Production retention remains unapproved.

### 9. Query privacy

R3C-A uses only fictional, public, non-sensitive acceptance queries. It does
not send unpublished research ideas, private documents, confidential titles or
abstracts, personal data, real dissertation questions or real R1B outputs.

The Provider may receive the query and technical/key-linked metadata under its
current Privacy Policy. A future real-user product must present explicit
third-party disclosure before transmission.

### 10. Error normalization

The Proxy uses safe stable categories at minimum:

- `PROVIDER_AUTHENTICATION_FAILED`
- `PROVIDER_AUTHORIZATION_FAILED`
- `PROVIDER_RATE_LIMITED`
- `PROVIDER_BUDGET_EXHAUSTED`
- `PROVIDER_TIMEOUT`
- `PROVIDER_UNAVAILABLE`
- `PROVIDER_INVALID_RESPONSE`
- `PROVIDER_RESPONSE_TOO_LARGE`
- `PROVIDER_CONTRACT_CHANGED`
- `PROVIDER_RECONCILIATION_REQUIRED`

No error exposes a key, full credentialed URL, raw Provider body, unsafe HTML
or secret-bearing traceback. Provider failure creates no Hosted WorkflowRun and
triggers no LLM or research continuation.

### 11. Production boundary

R3C does not approve public exposure, production bearer authentication,
multi-user authorization, HTTPS termination architecture, proof of possession,
production secret management, paid/prepaid use, production retention,
automated Provider failover or multiple live Providers.

```text
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

## Consequences

- R3C-I may implement only a disabled-by-default OpenAlex adapter and
  composition path behind the already separate `cloud_api_proxy` domain.
- R3C-I tests use a scripted/mock transport, fictional responses and no key or
  Internet. It ends at `R3C_STATE = LIVE_ACCEPTANCE_PENDING`.
- R3C-A remains a distinct owner-controlled live acceptance with a clean
  baseline, live key and isolated environment.
- Hosted `ProviderOperation`, WorkflowRun, Skills, AgentRuntime and LLM paths
  remain prohibited.
- `paper.search/v0.1`, Progress Reports and local Package state remain
  provider-neutral and unchanged.
- Official access/pricing/privacy wording must be rechecked before live use.

## Alternatives considered

- Reusing the Hosted OpenAlex path unchanged was rejected because it rewrites
  queries, adds filters/cursor, performs an extra preflight, retries and couples
  Provider use to Hosted research state.
- Anonymous access was rejected because official wording is inconsistent and
  the accepted supervised path requires an attributable owner key.
- `/rate-limit` preflight was rejected for this slice because it violates the
  one-Provider-request operation boundary; exact local reservations and
  response cost evidence govern instead.
- Arbitrary OpenAlex filters, pagination, semantic search, content/PDF retrieval
  and multiple Providers were rejected as capability expansion.
- Production/public deployment remains a future owner and security decision.
