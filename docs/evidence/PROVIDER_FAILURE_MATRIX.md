# ReAgent Paper Provider Failure Matrix

日期：2026-07-27；状态：**Proposed Class D policy informed by current Class A contracts**。  
数值不是 provider 标准：request timeout 15 s、初次调用后最多 2 retries、
exponential full-jitter backoff（base 1 s、cap 20 s），优先遵守合法
`Retry-After`/provider reset header。每次 live attempt 都必须受
`ProviderOperationService` reserve/start/settle 控制；idempotent replay 不得重复预留。

现有 `ProviderFailureCategory` 无法逐项命名 permission/DNS/pagination/identity
等情形时，先使用最接近的现有 category，并在 `diagnostic.code` 保存下表
`RESEARCH_*` code；是否扩充 enum 留给实现审查，不能悄悄改变 persistence semantics。

| Condition | Normalized category/code | Retry | Fallback / partial retention | User-visible / internal/event | Settlement | Terminal policy |
|---|---|---|---|---|---|---|
| invalid query | `INVALID_QUERY/RESEARCH_INVALID_QUERY` | no | none | “检索条件无效”；sanitized validation path；event only code/hash | failed, zero actual cost unless provider charged | fail before/at discovery |
| authentication failure (401) | `AUTHENTICATION/RESEARCH_AUTH_FAILED` | no | no silent provider switch | “Provider 认证失败”；never key/body; provider/status only | failed, record actual usage if known | primary fail; enrichment pause/degrade only per identity |
| permission failure (403) | closest `AUTHENTICATION/RESEARCH_PERMISSION_DENIED` | no | none | permission message; endpoint/provider, no response body | failed | fail called role |
| missing API key | `AUTHENTICATION/RESEARCH_KEY_MISSING` | no | anonymous only if explicitly configured/officially allowed | “配置缺少所需凭据”；env variable name allowed, value forbidden | no invocation; reservation released/failed per existing service | OpenAlex live discovery fail |
| rate limit (429) | `RATE_LIMITED/RESEARCH_RATE_LIMIT` | yes, max 2; honor Retry-After | retain completed pages | bounded retry message; status/reset header allowlist | every attempt auditable, final failed or success settled | final primary fail; optional enrichment can degrade if unambiguous |
| provider timeout | `TIMEOUT/RESEARCH_PROVIDER_TIMEOUT` | yes, max 2 | completed immutable pages kept diagnostic-only | timeout/provider/elapsed; no payload | failed attempt; no guessed usage | same as rate limit |
| DNS/network failure | closest `UNAVAILABLE/RESEARCH_NETWORK_FAILURE` | yes, max 2 | completed pages retained | sanitized exception class; no host secrets/query | failed | primary fail; optional layer conditional degrade |
| malformed JSON | `MALFORMED_RESPONSE/RESEARCH_MALFORMED_JSON` | once only if transient truncation plausible | raw body **not** exposed; retain hash/length | generic malformed response; parser offset internally bounded | failed | fail closed; never publish partial parsed record |
| partial response / omitted items | `MALFORMED_RESPONSE/RESEARCH_PARTIAL_RESPONSE` or warning | retry missing page/item once | retain valid records with `complete=false` | counts/IDs only | operation success-with-warning only if provider contract permits; else failed | discovery cannot claim complete; pause/fail if minimum/method requires |
| missing required mapped fields | `SCHEMA_VIOLATION/RESEARCH_REQUIRED_FIELD_MISSING` | no | reject record; keep aggregate counts | field name, provider ID hash | call may settle success; adapter emits rejected-record diagnostic | continue if enough valid candidates, else fail |
| 5xx | `UNAVAILABLE/RESEARCH_PROVIDER_5XX` | yes, max 2 | completed pages retained | status only; no body | failed attempt | final primary fail; optional conditional degrade |
| pagination failure | closest `MALFORMED_RESPONSE/RESEARCH_PAGINATION_FAILURE` | retry page once | retain earlier pages as incomplete | page/cursor hash, counts | failed page operation | fail/pause; never silently truncate |
| duplicate page | `SCHEMA_VIOLATION/RESEARCH_DUPLICATE_PAGE` | no after one detection | dedup bytes/IDs but mark incomplete | page hashes and cursor hashes | settle transport, workflow failure diagnostic | fail closed (loop/contract risk) |
| cursor invalidation | `UNAVAILABLE/RESEARCH_CURSOR_INVALIDATED` | restart only if total request cap allows and policy approved | old attempt preserved separately | cursor hash only | old operation failed; restarted operation new idempotency key | supervised pause by default |
| quota exhausted / credit limit | `BUDGET_EXCEEDED` or `RATE_LIMITED/RESEARCH_QUOTA_EXHAUSTED` | no within run | none | budget/remaining sanitized | no further reservation; current settles actual | fail primary; do not spend beyond cap |
| provider contract drift | `SCHEMA_VIOLATION/RESEARCH_CONTRACT_DRIFT` | no | preserve response hash/known fields only for diagnosis | expected/observed contract version, unknown-field counts | failed | fail closed; adapter update required |
| ambiguous paper identity | closest `SCHEMA_VIOLATION/RESEARCH_IDENTITY_AMBIGUOUS` | no transport retry | Crossref/S2 verification if budget allows; keep candidates separate | conflict fields/IDs, no abstract | successful calls settled | pause before approval/manual unresolved |
| DOI mismatch | `SCHEMA_VIOLATION/RESEARCH_DOI_MISMATCH` | no | agency-aware Crossref lookup once | asserted DOIs + provider provenance | calls settle; merge step fails/pause | fail/pause; never auto-overwrite |
| source not found (404) | `CONTENT_UNAVAILABLE/RESEARCH_NOT_FOUND` | no unless eventual consistency documented | next configured verifier/fallback | paper/provider ID; no query/body | failed lookup or successful “not found” per adapter contract | discovery item may be unresolved; selected ambiguous item pauses |
| provider disagreement | `SCHEMA_VIOLATION/RESEARCH_PROVIDER_DISAGREEMENT` | no | preserve all assertions | per-field conflict map | successful calls settled | continue only for non-identity advisory fields; identity conflict pauses |
| cancellation/deadline | `CANCELLED` / `TIMEOUT` | no automatic | immutable completed work retained | operation IDs and elapsed | cancelled/failed settled | workflow cancelled/failed |
| checksum/raw storage corruption | `STORAGE_ERROR/RESEARCH_RESPONSE_CORRUPT` | no provider retry until storage diagnosed | none | hash mismatch only | provider operation already settled; artifact op fails | fail closed |

## Role-specific degradation

### Primary OpenAlex discovery

After bounded retries, authentication/permission/quota/network/5xx/contract/pagination
failure blocks the workflow. ReAgent must not silently switch the primary search
engine because that changes the recorded methodology and ranking distribution.
A user may explicitly approve a new SearchPlan/run.

### Semantic Scholar verification/enrichment

- Core identity unambiguous (exact DOI/external ID and title sanity check):
  verification unavailable may continue as `unverified_due_to_provider`, with a
  visible warning and no S2-derived fields.
- Core identity ambiguous or S2 reports a conflicting DOI: pause/fail before the
  exact paper-set approval.
- Citation count, venue or abstract disagreement alone is advisory; preserve both
  assertions and selected display-source provenance.

### Crossref DOI fallback

- Only invoke for a DOI-bearing unresolved/conflicting record and verify the
  registration agency.
- Not found/non-Crossref DOI may continue as unresolved if identity is otherwise
  strong; never describe Crossref absence as invalid DOI.
- DOI mismatch or conflicting manifestation pauses/fails; abstract absence is not
  blocking.

## Diagnostics and event policy

Allowed event payload:

```json
{
  "provider": "openalex",
  "adapter_version": "…",
  "operation_id": "…",
  "failure_code": "RESEARCH_RATE_LIMIT",
  "http_status": 429,
  "retryable": true,
  "attempt": 2,
  "request_fingerprint": "sha256:…",
  "page_number": 2,
  "cursor_hash": "sha256:…"
}
```

Forbidden: API keys, authorization headers, email in query string, raw query URL,
abstract/title/author payloads, provider response bodies, absolute paths, stack
traces in public API/UI. Internal diagnostic text is length-bounded and sanitized.

## Official-contract notes

- OpenAlex current docs expose rate/credit headers and recommend bounded
  backoff on 429; current key/credit values must be read from official docs/config
  at implementation time.
- Semantic Scholar’s exact effective rate can depend on anonymous shared pool or
  issued key; do not encode ARS’s historical fixed limits.
- Crossref current official limits distinguish single/list and public/polite pool;
  `mailto` and caching are recommended. Values are recorded in the evidence
  register and must be rechecked before implementation.

