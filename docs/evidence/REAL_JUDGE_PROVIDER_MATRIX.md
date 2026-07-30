# Real Judge Provider Matrix

Evidence snapshot and access date: 2026-07-29
Phase: 9B-2C-3A
Status: Proposed; no provider, model, key, call, or spend is authorized

This matrix is a Class A contract review, not a model-quality evaluation.
None of the candidates has been measured on ReAgent's topical-relevance task.
All account-dependent facts must be verified again immediately before a
calibration is approved.

## Current candidates

| Contract property | OpenAI GPT-5.6 Terra | Anthropic Claude Sonnet 5 | Local OpenAI gpt-oss-20b |
|---|---|---|---|
| Provider / exact identity | OpenAI / `gpt-5.6-terra` | Anthropic / `claude-sonnet-5` | OpenAI weights / `gpt-oss-20b`, plus an owner-pinned weight revision |
| Snapshot or pin | The model page describes snapshots but currently lists only the same undated ID. A stronger dated pin was not found; treat this as unresolved. | Anthropic documents every 4.6+ canonical model ID, including this dateless ID, as a fixed snapshot. Serving infrastructure may still change. | ReAgent must pin weight commit, tokenizer, prompt renderer, serving image, driver/runtime, and decoding configuration. |
| Availability | Current API model; free tier is not supported and account tier controls rate limits. | Current Claude API model and listed active. | Downloadable weights; local hardware and serving stack are owner responsibilities. |
| Structured output | Structured Outputs is supported and constrains output to a supplied JSON Schema. Refusals remain a separate response path. | `output_config.format` uses constrained sampling and promises schema-valid JSON within documented refusal, token-limit, enum-casing, and schema-complexity exceptions. | The model supports Structured Outputs, but the actual guarantee comes from the pinned serving stack. |
| JSON Schema | Provider-supported subset; the exact ReAgent schema requires a no-spend compatibility preflight or approved first calibration attempt. | Standard JSON Schema with documented limitations. SDKs may remove unsupported features and move constraints into descriptions, so the canonical request schema must be checked rather than silently transformed. | Serving-version dependent; schema compilation, refusal, and malformed-output behavior are not defined by the weights alone. |
| Multilingual evidence | OpenAI describes current models as multilingual. This is not evidence of Chinese topical-relevance accuracy. | Anthropic describes all current Claude models as multilingual. This is not ReAgent calibration evidence. | OpenAI documents mostly-English, text-only training. This makes it a poor first multilingual calibration candidate. |
| Context / maximum output | 1,050,000 / 128,000 tokens. | 1,000,000 / 128,000 tokens. | 128,000-token context; output cap depends on serving policy. |
| Sampling / determinism | Reasoning controls exist. The inspected current official contract did not establish a supported seed or a temperature guarantee for Terra structured output. | Sonnet 5 does not accept `temperature`, `top_p`, or `top_k`; no seed is documented. Pin the ID and effort, then measure repeatability rather than claiming deterministic sampling. | Local decoding parameters and a seed can be fixed, but kernels, drivers, quantization, batching, and hardware can still change outputs. |
| Usage reporting | Responses returns token usage, including input/output and relevant cached/reasoning details. | Messages returns input/output usage; token counting is available. | Must be implemented and validated by the local adapter; compute cost needs separate measurement. |
| Provider request identity | `x-request-id`; a client request ID is also supported by the platform. | Every response includes `request-id`; official Python/TypeScript SDKs expose it. | ReAgent operation ID only unless the serving stack supplies a distinct request ID. |
| Timeout / cancellation | Client/HTTP timeout and cancellation are adapter concerns; current SDK contract must be pinned before implementation. | Official Python SDK supports configurable timeouts; default is ten minutes. ReAgent must override it with the calibration limit. | Serving-stack dependent. |
| Retry semantics | Provider errors must be normalized and SDK automatic retries disabled or bounded by ReAgent's operation budget. Exact SDK defaults remain version-dependent. | Official SDKs retry connection errors, 408, 409, 429, and 5xx twice by default. ReAgent must override to the approved one-retry and global retry budget. | Operator-defined. |
| Current price | USD 2.50/M input, USD 0.25/M cached input, USD 15/M output. Long-context surcharges do not apply to this small contract. | Introductory USD 2/M input and USD 10/M output through 2026-08-31; standard USD 3/M and USD 15/M begins 2026-09-01. The newer tokenizer may produce about 30% more tokens for the same text. | No token license price. Hardware, electricity, engineering, and opportunity costs are unknown rather than zero. |
| Rate limits | Published tiers exist, but the owner's project tier is decisive. | Organization usage tier and headers are decisive. | Operator-defined capacity. |
| Default data handling | API data is not used for training by default. Default abuse-monitoring logs may contain content for up to 30 days. Responses application state has endpoint/configuration exceptions. Qualifying ZDR exists. | Prompts/outputs are not retained by default under the current first-party contract except documented features/models. Contractual ZDR prevents at-rest prompt/response storage after the response; enablement is per organization. Schema grammars may be cached for 24 hours and must contain no sensitive content. | Can remain local, but logs, swap, crash dumps, backups, telemetry, and shared-host access become ReAgent's responsibility. |
| ZDR suitability | Eligible Responses/Chat endpoints can use ZDR when the organization is approved; `store` is then forced false. Eligibility is not known for the owner. | Messages and structured output are eligible for qualified ZDR. ZDR must be requested and confirmed per organization. | No hosted processor; “local” is not equivalent to an audited retention configuration. |
| Region controls | Regional storage/processing depends on region, endpoint, and approved controls. | First-party `inference_geo` and workspace storage geography are independent; a US inference option carries a 1.1x price multiplier for current models. | Physical host location is operator-controlled. |
| Deprecation / drift | Exact Terra retirement horizon was not found. Model output can vary even under a stable name; revalidation is required. | Canonical ID has its own lifecycle. Anthropic documents active/deprecated/retired states and notices affected customers; fixed weights do not freeze routers, classifiers, or sampling infrastructure. | Weights remain if retained, but serving dependencies and hardware can drift. |
| Official SDK / testability | Official Python and JavaScript SDKs; existing ReAgent fake/port contracts support adapter tests. | Official typed multi-language SDKs; clear request IDs, typed errors, retries, and timeouts. | Multiple mature runtimes, but a materially larger reproducibility and security test surface. |
| API key / commercial terms | Hosted API key and paid account required. Owner must confirm rights to process previews under applicable service terms. | Hosted API key and commercial organization required. Owner must confirm terms and ZDR arrangement. | Apache 2.0 weights permit commercial use subject to applicable usage policy and third-party serving dependencies. |
| Calibration-specific unresolved facts | exact immutable snapshot, owner ZDR eligibility, region, current SDK behavior, actual schema/refusal rate, latency, Chinese behavior | owner access/ZDR, actual schema/refusal rate, latency, Chinese behavior, effect of unavailable sampling controls | hardware availability, exact weight/runtime pins, schema guarantees, usage accuracy, latency, multilingual quality, total compute cost |

## Proposed recommendation

**Proposed Class D choice:** use one primary hosted Judge,
`claude-sonnet-5`, for the bounded calibration only. Do not use a comparison
model in the first execution.

Rationale:

- its canonical ID has the clearest current fixed-snapshot contract;
- it supports schema-constrained output and a direct request ID/usage boundary;
- it is officially multilingual, although that claim must be tested rather than
  trusted;
- its conservative post-introductory price still fits the proposed sub-USD 1
  envelope;
- one provider isolates adapter and prompt evidence and avoids doubling the
  privacy, cost, and interpretation surface.

This does not assert that Sonnet 5 is more accurate than Terra. It selects the
cleaner current reproducibility contract for a small experiment.

Fallback: use `gpt-5.6-terra` only if the owner prefers OpenAI and accepts the
weaker current pinning evidence, or if Anthropic ZDR/access cannot be obtained
but an approved OpenAI ZDR project can. A local `gpt-oss-20b` run is a separate
engineering experiment, not a silent fallback for the multilingual calibration.

Tradeoff: Sonnet 5 exposes no seed or adjustable sampling parameters. ReAgent
therefore measures A/B repeat stability and records the fixed model ID and
effort setting. The recommendation must be revisited if the ID, structured
output, price, ZDR eligibility, region contract, or deprecation status changes,
or if a preflight reveals schema incompatibility.

Owner approval is required for provider, exact model ID, organization, key,
ZDR state, inference region, abstract-preview processing, and non-zero budget.

## Official evidence register

| Source title | Organization | URL | Class | Published/updated | Accessed | Supported claim | Limitation |
|---|---|---|---|---|---|---|---|
| GPT-5.6 Terra model | OpenAI | https://developers.openai.com/api/docs/models/gpt-5.6-terra | A | live contract | 2026-07-29 | identity, context/output, price, features, rate tiers, snapshot table | table exposes no distinct dated Terra pin; account state is not public |
| Structured model outputs | OpenAI | https://developers.openai.com/api/docs/guides/structured-outputs | A | live contract | 2026-07-29 | JSON Schema adherence, refusals, official SDK helpers | supported subset and model behavior need contract tests |
| Data controls in the OpenAI platform | OpenAI | https://developers.openai.com/api/docs/guides/your-data | A | live contract | 2026-07-29 | no-training default, 30-day abuse logs, Responses state, ZDR, region controls | account eligibility and endpoint configuration remain unknown |
| Error codes | OpenAI | https://developers.openai.com/api/docs/guides/error-codes | A | live contract | 2026-07-29 | normalized errors and request-ID guidance | SDK defaults are version-sensitive |
| Services Agreement and Service Terms | OpenAI | https://openai.com/policies/services-agreement/ and https://openai.com/policies/service-terms/ | A | current agreement; Service Terms updated 2026-06-12 | 2026-07-29 | commercial API relationship and customer obligations | owner/counsel must assess preview-processing rights; this matrix is not legal advice |
| Models overview | Anthropic | https://platform.claude.com/docs/en/about-claude/models/overview | A | live contract | 2026-07-29 | Sonnet 5 ID, multilingual declaration, context/output, active model, price summary | no ReAgent-specific quality evidence |
| Model IDs and versioning | Anthropic | https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions | A | live contract | 2026-07-29 | 4.6+ canonical IDs are pinned; infrastructure may still change | a pinned ID does not guarantee byte-identical output |
| Structured outputs | Anthropic | https://platform.claude.com/docs/en/build-with-claude/structured-outputs | A | live contract | 2026-07-29 | constrained JSON, schema limitations, cache, refusal/token-limit exceptions | exact ReAgent schema has not been tested |
| Pricing | Anthropic | https://platform.claude.com/docs/en/about-claude/pricing | A | live contract | 2026-07-29 | USD prices, introductory deadline, tokenizer note, region multiplier | price may change before execution |
| Claude API errors | Anthropic | https://platform.claude.com/docs/en/api/errors | A | live contract | 2026-07-29 | request IDs, error shape, SDK retry behavior | ReAgent must override SDK retry defaults |
| Python SDK | Anthropic | https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python | A | live contract | 2026-07-29 | typed SDK, configurable retry/timeout, request ID | implementation must later pin an exact SDK release |
| API and data retention | Anthropic | https://platform.claude.com/docs/en/manage-claude/api-and-data-retention | A | live contract | 2026-07-29 | ZDR scope, prompt/response handling, schema cache, exceptions | contract/account representative is authoritative |
| Data residency | Anthropic | https://platform.claude.com/docs/en/manage-claude/data-residency | A | live contract | 2026-07-29 | inference and workspace geography controls | availability and price are account/region dependent |
| Model deprecations | Anthropic | https://platform.claude.com/docs/en/about-claude/model-deprecations | A | live contract | 2026-07-29 | lifecycle definitions and notifications | partner platforms have different schedules |
| Commercial Terms of Service | Anthropic | https://www.anthropic.com/legal/commercial-terms | A | effective 2025-06-17 | 2026-07-29 | commercial API relationship, customer content/output and fees | owner/counsel must assess preview-processing rights; this matrix is not legal advice |
| Introducing gpt-oss | OpenAI | https://openai.com/index/introducing-gpt-oss/ | A | 2025-08-05 | 2026-07-29 | Apache 2.0, 16 GB claim, 128K, mostly-English data, Structured Outputs | serving stack determines runtime guarantees and cost |
