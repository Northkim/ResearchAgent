# Real Grounded Report LLM Provider Matrix

Date/access date: 2026-07-30
Status: **Proposed; no provider or spend approved**

Dynamic facts below are Class A official-provider evidence. Report quality has
not been measured on ReAgent and is never inferred from a vendor benchmark.

## Decision matrix

| Contract | Anthropic | OpenAI | Local/open-weight |
|---|---|---|---|
| Proposed model | Claude Sonnet 5 | GPT-5.6 Terra | gpt-oss-20b |
| Exact ID | `claude-sonnet-5` | `gpt-5.6-terra` | weight release `gpt-oss-20b`; runtime identity must also be pinned |
| Pinning | canonical dateless ID is a fixed snapshot; serving infrastructure may change | model page says snapshots lock behavior, but currently lists no distinct dated slug | weights/hash and serving stack are owner-controlled |
| Structure | constrained JSON output; standard JSON Schema with documented limits | strict Structured Outputs; documented JSON Schema subset | model supports structured outputs, but guarantee depends on chosen runtime |
| Context/output | 1M / 128k | 1.05M / 128k | 128k; output limit runtime-dependent |
| Multilingual | vendor positions current Claude as multilingual; ReAgent validation absent | latest models officially support multilingual input/output; ReAgent validation absent | mostly-English training data is an explicit limitation |
| Tools/functions | tool use available, but V1 report calls require none | function/tool calling available, but V1 report calls require none | runtime-dependent; prohibited in V1 |
| Determinism | Sonnet 5 rejects non-default temperature/top-p/top-k; no seed contract | reasoning/sampling controls exist; no cross-request determinism guarantee | seed and decoding may be exposed, but hardware/runtime can change results |
| Usage/identity | input/output usage and `request-id`; official SDK typed errors | token usage and response/request IDs; official SDKs | operator must implement and verify both |
| Timeout/cancel | caller/SDK timeout and streaming are available; cancellation settlement still needs adapter design | caller timeout/stream cancellation are available; cancellation settlement still needs adapter design | operator-owned |
| Retry | official SDK retries transient connection/429/5xx twice by default; ReAgent must override to its smaller budget | retry behavior is SDK/version dependent; ReAgent must own bounded retries | operator-owned |
| Account/rate limits | API key and organization/account limits; exact limits are account-dependent | API key and tier-dependent limits; Terra page lists tier schedules | local capacity-dependent |
| Current price | introductory $2/M input, $10/M output through 2026-08-31; standard $3/$15 thereafter | $2.50/M input, $15/M output; >272k inputs use higher rates | weights free under Apache 2.0 plus usage policy; compute/operations not free |
| Retention/training | ZDR only for approved organizations; structured-output schemas can be cached up to 24h and must contain no sensitive data | API data is not used for training by default; default abuse logs up to 30 days; ZDR requires approval | local policy; no hosted disclosure if truly local |
| Region | provider/account configuration must be verified; not assumed | provider/account configuration must be verified; not assumed | deployment-selected |
| Deprecation | each ID has its own lifecycle; pinned weights do not freeze serving infrastructure | deprecation page and current model catalog govern lifecycle | operator controls model retirement and dependency compatibility |
| SDK/testability | mature official SDKs; injectable adapter and recorded synthetic fixtures | mature official SDKs; injectable adapter and recorded synthetic fixtures | integration burden is materially larger |
| Commercial use | governed by current commercial terms; input rights remain owner responsibility | services agreement assigns output to customer where law permits and makes customer responsible for input rights/accuracy | Apache 2.0 allows broad commercial use subject to usage policy; runtime licenses also apply |

## Report-generation criteria

All three can theoretically emit the required structures. None is proven to
preserve ReAgent citation labels, distinguish source statements from inference,
or synthesize 3–5 abstracts faithfully. Those properties require Fake tests and
bounded live acceptance.

### Proposed primary

Use **Anthropic `claude-sonnet-5`** for the first bounded report acceptance,
only after owner approval. This Class D recommendation favors its explicit
canonical fixed-ID contract, constrained output, long output capacity, and
eligible ZDR path. It is not a claim of superior report quality.

### Fallback

`gpt-5.6-terra` is the proposed fallback/comparison option, but it must not run
automatically. Switching requires a revised owner-approved model identity,
retention configuration, cost reservation, and separate acceptance record.
`gpt-oss-20b` is suitable for adapter development and privacy-sensitive future
experiments, not the initial multilingual V1 acceptance.

## Unresolved dynamic facts

- owner account access, rate/spend limits, region, ZDR eligibility, and key;
- exact endpoint feature compatibility under ZDR;
- real latency, tokenization, refusal behavior, and citation-label stability;
- Terra's distinct dated-snapshot availability;
- SDK versions and default retries at implementation time;
- permission and rights to transmit each approved abstract.

Any changed model ID, price, retention rule, schema feature, or deprecation
notice triggers re-review before execution.

## Class A source register

| Source | Organization | Publication/update | Supported claim | Limitation |
|---|---|---:|---|---|
| [Claude model IDs and versioning](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions) | Anthropic | accessed 2026-07-30 | 4.6+ canonical IDs are pinned; infrastructure may change | not a quality guarantee |
| [Claude Sonnet 5](https://platform.claude.com/docs/en/about-claude/models/whats-new-sonnet-5) | Anthropic | accessed 2026-07-30 | ID, 1M/128k, sampling restrictions, tokenizer, price period, ZDR eligibility | account configuration remains unknown |
| [Claude structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) | Anthropic | accessed 2026-07-30 | constrained JSON, schema limitations, schema cache | schema compliance is not semantic truth |
| [Claude API errors](https://platform.claude.com/docs/en/api/errors) | Anthropic | accessed 2026-07-30 | request IDs, typed errors, default SDK retries | ReAgent must still bound retries |
| [Anthropic ZDR scope](https://privacy.claude.com/en/articles/8956058-i-have-a-zero-data-retention-agreement-with-anthropic-what-products-does-it-apply-to) | Anthropic | 2026-06-09 | ZDR is agreement- and product-specific | exceptions may apply |
| [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra) | OpenAI | accessed 2026-07-30 | ID, context/output, structure, pricing, tier-dependent limits | no ReAgent quality evidence |
| [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) | OpenAI | accessed 2026-07-30 | strict schema and supported subset | refusals and semantic errors remain possible |
| [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data) | OpenAI | accessed 2026-07-30 | no-training table, 30-day default monitoring, approved ZDR behavior | account eligibility unknown |
| [OpenAI Services Agreement](https://openai.com/policies/services-agreement/) | OpenAI | effective 2026-01-01, accessed 2026-07-30 | API commercial terms, content responsibilities | engineering summary, not legal advice |
| [gpt-oss model card](https://openai.com/index/gpt-oss-model-card/) | OpenAI | 2025-08-05 | Apache 2.0, structure, model limitations | serving contract is not included |
| [Introducing gpt-oss](https://openai.com/index/introducing-gpt-oss/) | OpenAI | 2025-08-05 | 20b memory/context and mostly-English training | benchmark claims do not establish ReAgent quality |
