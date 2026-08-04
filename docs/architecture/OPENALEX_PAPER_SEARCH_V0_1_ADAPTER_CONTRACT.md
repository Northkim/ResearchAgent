# OpenAlex `paper.search/v0.1` Adapter Contract

Status: **APPROVED FOR R3C-I IMPLEMENTATION; LIVE ACCEPTANCE PENDING**
Date: 2026-08-04
Governing ADR: 0012

## 1. Responsibility boundary

This adapter is a transport-and-normalization component behind the separate
teacher-aligned Cloud API Proxy:

```text
local Harness supplies one query
  -> Proxy authenticates and authorizes exact Package/Workflow scope
  -> Proxy admits one immutable operation under count/cost policy
  -> fixed OpenAlex adapter performs one Works request
  -> adapter returns untrusted normalized paper metadata and safe provenance
  -> local Harness interprets results and writes local state
```

The adapter does not choose or rewrite the question, generate terms, decide
relevance, rerank results, fetch content, invoke a Workflow/Skill/LLM, write a
Package, or create/upload a Progress Report.

## 2. Contract identity

- Proxy contract: `reagent.cloud-api-proxy/v0.1`
- Capability: `paper.search/v0.1`
- Live adapter ID: `reagent.openalex-paper-search/v0.1`
- Provider: `OpenAlex`
- Provider operation: one `GET /works` ordinary metadata search
- Feature profile: experimental, loopback-managed, disabled by default

The client never submits a Provider URL, Provider endpoint, adapter choice,
credential, HTTP method/header or Provider-specific parameter. The server
derives the adapter from the authenticated token record and capability
registry.

R3C-I must use a separate explicit feature flag named
`REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED`, false by default. Enabling it
without SQL Proxy persistence, an exact OpenAlex adapter registration and the
required credential configuration fails closed. The existing fake-adapter flag
and adapter remain independent.

## 3. Provider-neutral request

The external request remains the existing immutable
`CloudProxyRequestEnvelope`. Its only capability parameters are:

```json
{
  "query": "outer-trimmed UTF-8 text, 1-500 characters",
  "max_results": 10
}
```

`max_results` is an integer from 1 through 20. Unknown fields fail before
admission. R3C reuses the short-lived, digest-only, loopback capability-token
profile accepted in R3B, but an OpenAlex token binds the exact live adapter and
has a maximum of 20 admitted operations. It does not contain the Provider key.

The canonical request checksum and operation ID rules do not change:

```text
canonical semantic request -> request_content_checksum
request checksum + UUIDv4 key + stable server-derived authorization scope
  -> proxyop-v1 operation_id
Provider outcome -> provider_data_checksum -> response_content_checksum
delivery envelope with response_checksum omitted -> response_checksum
```

The Provider key, credential-bearing URL, token plaintext/digest, server time,
operation ID and idempotency key are not request content. Provider-specific
parameters do not enter the local contract.

## 4. Exact OpenAlex request mapping

The adapter constructs only this fixed request:

```text
method: GET
origin: https://api.openalex.org
path: /works
query parameters:
  search=<exact outer-trimmed local query>
  per_page=<max_results, 1..20>
  select=id,doi,display_name,authorships,abstract_inverted_index,publication_year,primary_location,language
  api_key=<server-side REAGENT_OPENALEX_API_KEY>
```

The adapter uses structured parameter encoding. It does not alter the query or
add `filter`, `sort`, `page`, `cursor`, `group_by`, `sample`, semantic/exact
search, content flags or arbitrary parameters. It issues no `/rate-limit`
preflight and performs no automatic pagination or retry.

## 5. Transport policy

- HTTPS only; certificate verification mandatory.
- Fixed host and path; no user-controlled URL or DNS target.
- Redirects disabled. A redirect is a contract change/failure and is not
  followed, even when it points to another OpenAlex host.
- Ambient HTTP proxy configuration is disabled (`trust_env=False` or equivalent).
- DNS/connect/read/write/pool and complete-operation deadlines are bounded by a
  maximum of 10 seconds.
- Maximum received Provider response body is 512 KiB, enforced on actual bytes
  before full retention or normalization. Compression cannot bypass the
  decoded-byte cap.
- Exactly one Provider HTTP request is permitted per newly admitted operation.
- No retry, provider failover, secondary endpoint or background execution.
- URLs and transport exceptions are sanitized before logging; the query string
  is never logged because it contains both user data and the Provider key.

## 6. Response validation and normalization

The accepted top-level response is one JSON object containing an object `meta`
and array `results`. The adapter bounds depth, arrays, strings, Unicode and
record count before constructing the provider-neutral result. More than
`max_results` results, malformed JSON, invalid root/meta/results, unsupported
encoding, unsafe controls or oversized content fails closed without raw-body
retention.

Each accepted Work maps as follows:

| `PaperRecord` field | OpenAlex source/rule |
|---|---|
| `paper_id` | deterministic internal ID from normalized DOI, otherwise validated namespaced Work ID |
| `provider_id` | validated `W` plus digits from `id` |
| `title` | `display_name`, normalized and length/control validated |
| `authors` | bounded `authorships[].author` names plus validated OpenAlex author ID and optional ORCID string |
| `abstract` | deterministic reconstruction of bounded `abstract_inverted_index`; optional/untrusted |
| `publication_year` | optional valid integer year |
| `publication_venue` | optional `primary_location.source.display_name` |
| `doi` | optional normalized DOI |
| `language` | optional bounded ISO-style string from `language` |
| `source_provider` | fixed live adapter identity |
| `source_url` | constructed `https://openalex.org/{validated Work ID}`; never followed |
| `retrieved_at` | server receipt timestamp |
| `raw_metadata_hash` | canonical checksum of the approved selected Work mapping, not a retained raw body |
| `metadata_limitations` | explicit missingness and discovery-only/unverified status |

The capability result remains:

```text
paper-search-result/v0.1
  source_classification = LIVE_OPENALEX_SCHOLARLY_METADATA
  untrusted_provider_data = true
  papers = [PaperRecord, ...]
```

Provider result order may be preserved, but neither the adapter nor Proxy adds
a relevance label, score, ranking explanation, summary or research conclusion.
OpenAlex data can contain malicious or instruction-like text; it remains data.

## 7. Usage, cost and budget evidence

The adapter parses and bounds these safe current fields when supplied:

- response `meta.cost_usd` as an exact non-negative decimal string;
- `X-RateLimit-Limit`;
- `X-RateLimit-Remaining`;
- `X-RateLimit-Credits-Used`;
- `X-RateLimit-Reset`;
- a safe opaque request ID only if the current Provider supplies one and its
  value passes a strict length/character allowlist.

Raw headers are not retained. Cost is never rounded down into the existing
whole-cent Hosted usage field. The Proxy records exact USD evidence or an
equivalent integer precision sufficient for `$0.001` calls, plus local admitted
call/cost totals.

R3C-I freezes a pre-admission reservation of `$0.001` from the current official
search price. R3C-A rechecks that price before first use. Missing/invalid cost,
a different price, contradictory headers/meta, more than one call, more than 20
total calls or a projected/settled total above `$0.05` fails closed and stops
further live admission. The owner must confirm no prepaid spending is enabled;
the Proxy does not make an extra Provider call to inspect account balance.

## 8. Errors and uncertain outcomes

| Condition | Proxy category | Retry behavior |
|---|---|---|
| missing/invalid key or Provider authentication failure | `PROVIDER_AUTHENTICATION_FAILED` | none |
| Provider permission failure | `PROVIDER_AUTHORIZATION_FAILED` | none |
| official rate/daily limit response | `PROVIDER_RATE_LIMITED` | none |
| local call/cost limit or changed price | `PROVIDER_BUDGET_EXHAUSTED` or `PROVIDER_CONTRACT_CHANGED` | none |
| operation deadline/transport timeout | `PROVIDER_TIMEOUT` or `PROVIDER_RECONCILIATION_REQUIRED` when outcome is uncertain | status read only |
| DNS/TLS/5xx/unavailable | `PROVIDER_UNAVAILABLE` | none |
| malformed JSON/schema/usage evidence | `PROVIDER_INVALID_RESPONSE` or `PROVIDER_CONTRACT_CHANGED` | none |
| more than 512 KiB | `PROVIDER_RESPONSE_TOO_LARGE` | none |

Raw Provider error bodies, HTML, credentialed URLs and exception chains are not
returned or persisted. A failure can settle only the Proxy operation. It does
not create Hosted rows, run a fallback, generate a report or alter local state.

If the server cannot prove whether the one Provider request completed, the
operation becomes `RECONCILIATION_REQUIRED`. Because OpenAlex has no approved
request-idempotency/status operation in this slice, the server never repeats
the call automatically. Exact client POST replay returns the existing uncertain
operation; recovery uses explicit status.

## 9. Persistence and provenance

The separate Proxy operation ledger remains authoritative. R3C-I may add only
the safe fields required for live adapter identity, exact decimal usage/cost,
Provider-call count and normalized result checksums. It must not add a Hosted
WorkflowRun/step/provider-operation foreign key.

Acceptance-lifetime durable state may contain normalized paper metadata,
request/result/response checksums, adapter/version, safe Provider IDs,
status/timestamps/latency and exact usage/cost. It excludes the raw body, key,
credential URL/header, PDF/full text and unsafe payload. The query is used
transiently for the call; the durable identity is its canonical request
checksum.

The local Package can record the returned Proxy operation ID as ordinary local
provenance. The server does not add it to a Progress Report or mutate Package
files.

## 10. Qualification and gates

R3C-I uses only scripted/mock HTTP transport, fictional Provider responses and
isolated PostgreSQL. Network and credential canaries must prove zero Internet
and zero key use. R3C-I may end only at:

```text
R3C_STATE = LIVE_ACCEPTANCE_PENDING
```

R3C-A alone may use the owner key and fixed live origin after a fresh official-
source/pricing/privacy recheck. Public deployment and production security stay
closed.
