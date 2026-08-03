# Real Grounded Report LLM Provider Matrix

Original decision date: 2026-07-30
Official-contract revalidation: 2026-08-03
Status: **Proposed; no provider, key, abstract transmission, or spend approved**

Dynamic facts below are current official-provider evidence accessed on
2026-08-03. Report quality has not been measured on ReAgent and is never
inferred from a vendor benchmark.

## Complete contract comparison

| Contract | Anthropic | OpenAI | Local/open-weight |
|---|---|---|---|
| Provider / exact model | Anthropic first-party Claude API / `claude-sonnet-5` | OpenAI API / `gpt-5.6-terra` | OpenAI weights `gpt-oss-20b`; serving runtime is a separate identity |
| Snapshot/pinning | For Claude 4.6 and later, the canonical dateless ID is itself one fixed snapshot; weights/configuration remain fixed for that ID, while surrounding serving infrastructure may change | The model page currently lists only `gpt-5.6-terra` as both model ID and current snapshot; no stronger dated slug is documented | Pin weight files and hashes, tokenizer/Harmony format, runtime/version, quantization, decoding configuration, hardware, and container image |
| Structured output | GA constrained JSON through `output_config.format` | Strict Structured Outputs on Responses and Chat Completions | Model supports Structured Outputs, but enforcement and response normalization depend on the selected runtime |
| JSON Schema subset | Supports core object/array/string/number/integer/boolean/null constructs and documented constraints; unsupported/over-complex schemas fail before generation; schema compliance does not prove semantic grounding | Supports a documented subset rather than arbitrary JSON Schema; all fields must be required, object schemas must use `additionalProperties: false`, and refusals/incomplete outputs remain separate cases | Runtime/operator must publish and test its supported subset; model capability alone is not a constrained-decoder guarantee |
| Context / maximum output | 1,000,000 / 128,000 tokens | 1,050,000 context, 922,000 maximum input, 128,000 maximum output | 131,072 native context; usable output and memory limits are runtime-dependent |
| Authentication | `x-api-key` plus pinned `anthropic-version`; workload identity is a future alternative | Bearer API key; project/org selection and key scope are account configuration | No hosted credential if truly local; any remote runtime has its own secret and trust boundary |
| Request identity | Unique `request-id` response header; errors also contain `request_id` | Response object ID and `x-request-id`; callers may supply `X-Client-Request-Id` under the documented constraints | Must be generated, persisted, and proven unique by the operator/runtime |
| Usage reporting | Messages usage reports input/output token families; ReAgent must normalize every billed category actually returned | Response usage reports input/output/total and relevant cached/reasoning details | Runtime token counters must be validated against the exact tokenizer and billing/compute method |
| Timeout/cancellation | Client/transport timeouts and streaming exist; cancelling a local request does not prove remote cancellation or zero billing | Client timeouts/stream closure exist; cancellation and billing reconciliation remain application responsibilities | Entirely operator-owned |
| Retry guidance | Official SDKs retry connection errors, 429, and 5xx twice by default; direct API returns `retry-after`; ReAgent must disable hidden retries and use its smaller global budget | SDK defaults are version-dependent; documented transient classes include 408/409/429 and 5xx; ReAgent must own and account for retries | Entirely operator-owned |
| Standard price | Introductory $2/M input and $10/M output through 2026-08-31; $3/$15 thereafter; new tokenizer can increase token count for the same text | Standard short-context $2/M input, $0.20/M cached input, $2.50/M cache writes, $12/M output; requests over 272k use $4/$18 for the full request | Weights are free under Apache 2.0; compute, storage, electricity, runtime engineering, and any third-party hosting are not free |
| Rate limits | Organization/workspace and usage-tier dependent; Sonnet 5 has a separate model bucket; exact effective limits must be read from the account | Usage-tier/project dependent; exact effective limits and spend controls are account facts | Hardware/runtime-capacity dependent |
| Account requirements | Commercial organization/workspace, billing/access, scoped key or approved workload identity; ZDR requires separate organization enablement | API organization/project, billing/access, scoped key; ZDR/data residency require eligibility and configuration | Rights to download/use weights plus approved infrastructure and operations owner |
| Standard retention / training | Standard commercial API inputs/outputs are deleted within 30 days, subject to longer feature, safety, legal, or contractual cases; inputs/outputs are not used for training without express permission | API data is not used for training unless explicitly opted in; abuse-monitoring logs default to up to 30 days and Responses application state is retained at least 30 days when stored/default behavior applies | Local policy if truly local; third-party hosting changes the processor and retention contract |
| ZDR/equivalent | Organization-specific ZDR: eligible Messages prompts/responses are not stored at rest after response; Structured Outputs is qualified because the content-free JSON schema may be cached up to 24 hours; flagged/legal exceptions remain | Prior-approved org/project ZDR excludes customer content from abuse logs and forces `store=false`; feature/model eligibility, prompt-cache application state, Eyes Off/Safety Retention, and endpoint limitations still apply | Achievable only if all model/runtime/logging/telemetry/storage stays on approved local infrastructure |
| Region controls | `inference_geo` and account/contract availability are dynamic; exact region and processing arrangement must be confirmed | Project data residency/regional processing is eligibility- and endpoint-specific; eligible regional endpoints can carry a 10% pricing uplift | Operator-selected, including any runtime telemetry/subprocessor |
| Deprecation | Each canonical model ID has its own retirement schedule; new releases use new IDs | Current catalog and deprecation page govern lifecycle; the Terra page currently exposes no distinct dated pin | Operator controls retirement, but runtime/CUDA/library compatibility can still drift |
| SDK / HTTP support | First-party REST Messages API and official Python SDK; direct HTTP fits the existing injected protocol | First-party REST Responses/Chat Completions and official SDKs | OpenAI reference implementations plus third-party runtimes; no single hosted contract |
| Commercial-use implications | Current Commercial Terms and Usage Policy apply; customer remains responsible for input rights and use | Current Services Agreement/Usage Policies apply; customer remains responsible for inputs, use, and validating outputs | Apache 2.0 permits broad commercial use subject to the gpt-oss usage policy; runtime and dependency licenses also apply |
| ReAgent uncertainty | Account key, workspace, ZDR, region, rate/spend tier, taxes, latency, refusal behavior, token count, and report quality | Account key, project, ZDR, region, rate/spend tier, stronger pin, latency, and report quality | Exact weights/hashes, runtime, hardware, constrained decoder, capacity, logging, security, operational cost, and ReAgent quality |

## Proposed primary

Use **Anthropic first-party Claude API / `claude-sonnet-5`** for this one
bounded acceptance, only after explicit owner approval. The recommendation is
Class D and rests on the existing inactive Anthropic adapter substrate, a
canonical fixed-snapshot ID, first-party constrained output, request/usage
identity, and a documented ZDR route. It is not a claim that Claude produces a
more correct report.

OpenAI `gpt-5.6-terra` and local `gpt-oss-20b` are evidence alternatives only.
They are not fallbacks or comparison providers for this acceptance. Changing
provider/model requires a revised owner decision, transport/retention review,
cost reservation, and separate acceptance record.

## Revalidation result

The 2026-08-03 recheck found no Anthropic contract drift that changes the
proposed primary or the USD 1.00 envelope. It did find one stale comparison
fact: current OpenAI standard short-context Terra pricing is $2/M input and
$12/M output, replacing the package's earlier $2.50/$15 entry. No OpenAI cost
is used to reserve this Anthropic-only acceptance.

Any changed model ID, price, retention rule, schema feature, region support, or
deprecation notice blocks execution until this register is revalidated again.

## Official source register

All sources accessed 2026-08-03 unless a publication date is stated.

### Anthropic

- [Claude Sonnet 5](https://platform.claude.com/docs/en/about-claude/models/whats-new-sonnet-5): ID, context/output, tokenizer, sampling constraints, price period, availability, and ZDR eligibility.
- [Model IDs and versioning](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions): canonical fixed-snapshot behavior and serving-infrastructure caveat.
- [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs): request shape, constrained JSON, supported/unsupported schema constructs, refusals, and schema caching.
- [Claude API errors](https://platform.claude.com/docs/en/api/errors): error taxonomy, request ID, `retry-after`, and SDK retry defaults.
- [Authentication](https://platform.claude.com/docs/en/manage-claude/authentication): `x-api-key`, `ANTHROPIC_API_KEY`, expiration, workspaces, and workload identity.
- [Rate limits](https://platform.claude.com/docs/en/api/rate-limits): account tiers, separate Sonnet 5 bucket, spend/rate controls, and headers.
- [API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention): organization-specific ZDR, feature eligibility, 24-hour schema cache, and safety/legal exceptions.
- [Commercial API retention](https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data): standard 30-day deletion rule, exceptions, and no-training statement.
- [Python SDK](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python): package, async support, timeouts, raw-response access, logging, and errors.

### OpenAI

- [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra): exact ID/snapshot, context/input/output, endpoints, and supported features.
- [Model guidance](https://developers.openai.com/api/docs/guides/latest-model): current GPT-5.6 family roles and canonical aliases.
- [API pricing](https://developers.openai.com/api/docs/pricing): current standard/long-context/cached/cache-write prices and regional uplift.
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs): strict-schema request contract and supported subset.
- [Data controls](https://developers.openai.com/api/docs/guides/your-data): no-training default, abuse logs, application-state retention, ZDR, prompt caching, and region controls.
- [API overview](https://developers.openai.com/api/docs/overview): authentication and request-ID guidance.
- [Deprecations](https://developers.openai.com/api/docs/deprecations): lifecycle authority.
- [Services Agreement](https://openai.com/policies/services-agreement/): commercial content responsibilities; this package gives no legal conclusion.

### Local/open-weight

- [gpt-oss model card](https://openai.com/index/gpt-oss-model-card/) (published 2025-08-05): open-weight, Apache 2.0, structured output, and operator safety responsibility.
- [Introducing gpt-oss](https://openai.com/index/introducing-gpt-oss/) (published 2025-08-05): 20b footprint, 128k context, mostly-English text-only training, and runtime positioning.
- [OpenAI gpt-oss repository](https://github.com/openai/gpt-oss): reference runtimes, Harmony format, and operator-owned serving limitations.
