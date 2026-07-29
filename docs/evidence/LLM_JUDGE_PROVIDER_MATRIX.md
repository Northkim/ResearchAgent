# LLM Judge Provider Matrix

Evidence snapshot: 2026-07-29  
Status: Proposed; no provider/model selected or called

Dynamic facts below use official **Class A** sources only. Performance as a
ReAgent relevance judge is unmeasured; marketing or general benchmark claims are
not treated as validation.

## Decision matrix

| Criterion | OpenAI GPT-5.6 Terra | Anthropic Claude Sonnet 5 | Local OpenAI gpt-oss-20b |
|---|---|---|---|
| Candidate identity | `gpt-5.6-terra` | `claude-sonnet-5` | weights pinned by repository/model revision |
| Availability | GA in OpenAI API as of 2026-07-09 | active and available on Claude API | downloadable open weights; self-hosted |
| Structured output | Structured Outputs supported; implementation must use the provider's schema-constrained mode and handle refusal/incomplete response | `output_config.format` constrains output to supported JSON Schema; schema-valid output is guaranteed within documented limitations | model supports structured outputs, but enforcement and guarantees depend on the selected serving stack |
| Schema support | JSON Schema subset; exact ReAgent schema must be compatibility-tested | standard JSON Schema with documented limitations and grammar complexity/compile limits | vLLM can constrain output to JSON Schema; compatibility is serving-version dependent |
| Pinning / drift | official docs recommend pinned model versions; current model page lists `gpt-5.6-terra` but exposes no distinct dated snapshot in the inspected snapshot table—exact stronger pin is unresolved | IDs from 4.6 onward, including `claude-sonnet-5`, are documented pinned snapshots; serving infrastructure can still change | pin model-weight commit, tokenizer, serving image, GPU/runtime, and decoding config; operator owns all drift |
| Multilingual | latest OpenAI models are officially described as multilingual | current Claude models are officially multilingual; docs publish language-varying results | trained on a mostly English text-only dataset; unsuitable as the uncalibrated multilingual default |
| Context / output | 1.05M context; 128K max output | 1M context; 128K max output | up to 128K context; output cap is serving policy |
| Deterministic controls | reasoning effort is supported; exact temperature/seed support for this model/request mode is not established by the inspected official docs | non-default `temperature`, `top_p`, and `top_k` are rejected; no seed is documented | decoding parameters/seed may be controlled locally, but hardware/kernel determinism is not guaranteed |
| Usage | Responses exposes input/output/total and reasoning/cache detail | Messages returns input/output usage; token counting is available | serving stack must supply trustworthy usage; local compute cost is separately metered |
| Price | $2.50/M input, $0.25/M cached input, $15/M output; long-context surcharge applies only far above this workload | introductory $2/M input and $10/M output through 2026-08-31, then $3/$15; tokenizer change can alter equivalent-request cost | no per-token license fee; hardware, electricity, engineering, and hosting are real unpriced costs |
| Latency | no official per-request guarantee found; measure under approved account/tier | no official per-request guarantee found; measure; adaptive thinking affects latency | hardware-dependent; benchmark locally |
| Rate limits | tier/account dependent; model page publishes tier tables but execution must preflight the owner's current project | organization/tier dependent; read current headers/console limits and do not hard-code a public value | operator-defined concurrency, memory, and queue limits |
| Retry / errors | normalize HTTP/provider errors; log provider request ID; adapter must own a bounded retry policy because SDK defaults are version-sensitive | official SDKs retry transient connection/rate-limit/5xx failures twice by default with exponential backoff and honor `retry-after`; ReAgent must override to its one-retry policy | operator owns queueing, timeout, retry, and overload behavior |
| Request ID | log `x-request-id`; client may send `X-Client-Request-Id` | error responses include `request_id`; SDK raw response exposes headers | create a local operation/request ID; no external support ID |
| Retention / training | API inputs/outputs not used for training by default; default abuse-monitoring logs up to 30 days; Responses has endpoint/configuration-specific application-state retention; qualifying ZDR exists | API inputs/outputs normally deleted within 30 days; ZDR may be contracted; structured-output prompt/response processing is ZDR-eligible but schema can be cached up to 24 hours | input/output can remain local; ReAgent/operator retention, backups, swap, telemetry, and host security become the whole policy |
| Commercial terms | API use is governed by the OpenAI Services Agreement and Service Terms; key required; input rights and preview-retention rights remain the customer's responsibility | API use is governed by Anthropic Commercial Terms; customer owns output as between the parties, must evaluate it, and pays published fees/credits; key required | Apache 2.0 permits commercial use, subject to the gpt-oss usage policy |
| SDK / testability | official client SDKs; existing ReAgent `LLMProvider` and fake support network-free adapter tests | official multi-language SDKs and typed errors; adapter can be contract-tested against fixtures/fake transport | mature open serving options, but larger test matrix across weights/runtime/hardware |
| Deprecation | outputs can vary across snapshots; OpenAI recommends pinned versions and evals; exact GPT-5.6 snapshot/deprecation horizon unresolved | at least 60 days' retirement notice for public models; Sonnet 5 listed active and not retiring before 2027-06-30 | weights remain available if ReAgent preserves the approved revision; ecosystem dependencies can deprecate |

## Provider-specific assessment

### OpenAI

Strengths: schema-capable current model family, existing ReAgent `LLMProvider`
shape, multilingual claim, detailed usage/request identity, and a balanced
Terra tier. Risks: hosted retention/configuration, variable outputs, no
ReAgent-specific validation, account-dependent rate limits, and the unresolved
stronger-than-model-ID snapshot for GPT-5.6 Terra.

### Anthropic

Strengths: schema-constrained JSON, a documented pinned Sonnet 5 ID, clear model
lifecycle, multilingual documentation, request IDs, usage, and explicit SDK
retry behavior. Risks: non-default sampling controls are unavailable, hosted
retention/account terms apply, equivalent tokenization can change cost, and no
ReAgent-specific validation exists.

### Local/open-weight

`gpt-oss-20b` is feasible for a privacy-sensitive development comparison:
Apache 2.0, approximately 16 GB memory for the supplied quantization, 128K
context, and structured-output capability. It is not the initial multilingual
recommendation because OpenAI documents its training set as mostly English.
Schema guarantees, latency, usage metering, request IDs, retries, security, and
retention depend on the chosen local serving stack. Local is not automatically
free or reproducible.

## Conditional recommendation

**Recommendation:** after ADR approval, calibrate `gpt-5.6-terra` as the primary
hosted candidate using the two-prompt contract and a small owner-reviewed,
non-production fixture set; compare a bounded subset against
`claude-sonnet-5`. Select neither model if prompt agreement, audit agreement,
usage completeness, retention configuration, or cost reservation fails.

Why Terra rather than Luna: Terra is the provider's balanced intelligence/cost
tier, while the judge has a high consequence for metric validity and only 40
candidates. Luna remains the cost-sensitive alternative. This recommendation is
**Class D ReAgent policy**, not evidence that Terra is more accurate for paper
relevance.

Implementation remains blocked by owner approval of provider, exact model ID,
API-key availability, retention, and a non-zero budget. If an immutable OpenAI
snapshot cannot be established at implementation time, Anthropic Sonnet 5 has a
clearer official pinning contract and should be preferred for the reproducibility
pilot, subject to cost and retention approval.

## Unresolved dynamic facts

- exact OpenAI GPT-5.6 Terra snapshot/deprecation horizon;
- account-specific OpenAI/Anthropic rate limits and regional availability;
- actual latency and structured-output failure/refusal rates on ReAgent prompts;
- actual tokenization and total pilot cost;
- whether the owner's accounts qualify for ZDR and which endpoint settings apply;
- exact SDK versions and their default retry/timeout behavior;
- commercial/legal acceptability for retaining abstract previews;
- local hardware availability and measured Chinese judgment quality.

These require revalidation immediately before implementation. No rate limit,
latency, retention exception, or price is hard-coded by this contract.

## Official evidence register

| Source title | Organization | URL | Class | Publication/update date | Access date | Supported claim | Limitation |
|---|---|---|---|---|---|---|---|
| Models / Compare models | OpenAI | https://developers.openai.com/api/docs/models and https://developers.openai.com/api/docs/models/compare | A | live docs | 2026-07-29 | model IDs, multilingual support, context, output, price, structured-output support | dynamic catalog; no task-specific judge validation |
| GPT-5.6 Terra model page | OpenAI | https://developers.openai.com/api/docs/models/gpt-5.6-terra | A | live docs | 2026-07-29 | Terra identity/features/rate-limit tiers/snapshots section | inspected table did not expose a distinct dated snapshot |
| GPT-5.6 release | OpenAI | https://openai.com/index/gpt-5-6/ | A | 2026-07-09 | 2026-07-29 | GA date, tier roles, prices | product benchmarks are not ReAgent evidence |
| Structured model outputs | OpenAI | https://developers.openai.com/api/docs/guides/structured-outputs | A | live docs | 2026-07-29 | JSON-Schema-constrained output, explicit refusals, official SDK helpers | supported schema subset/model behavior must be fixture-tested |
| Model guidance | OpenAI | https://developers.openai.com/api/docs/guides/latest-model | A | live docs | 2026-07-29 | Terra balance recommendation, reasoning controls, Responses guidance | general guidance; behavior must be evaluated |
| API backward compatibility / request IDs | OpenAI | https://platform.openai.com/docs/api-reference/backward-compatibility | A | live docs | 2026-07-29 | pin versions, expect output variability, log request IDs | no fixed retirement promise for Terra found |
| Data controls in the OpenAI platform | OpenAI | https://platform.openai.com/docs/models/default-usage-policies-by-endpoint | A | live docs | 2026-07-29 | default training, abuse logs, Responses state, ZDR behavior | eligibility/configuration varies by account and endpoint |
| Services Agreement / Service Terms | OpenAI | https://openai.com/policies/services-agreement/ and https://openai.com/policies/service-terms/ | A | current agreement; Service Terms updated 2026-06-12 | 2026-07-29 | API commercial contract, customer obligations and output-use limitations | legal interpretation and input rights require owner/counsel review |
| Models overview | Anthropic | https://platform.claude.com/docs/en/about-claude/models/overview | A | live docs | 2026-07-29 | Sonnet 5 ID, context/output, multilingual capability | provider benchmark claims are not independent |
| What's new in Claude Sonnet 5 | Anthropic | https://platform.claude.com/docs/en/about-claude/models/whats-new-sonnet-5 | A | 2026-06-30 | 2026-07-29 | price, context, sampling-parameter restriction, ZDR eligibility | introductory price expires 2026-08-31 |
| Structured outputs | Anthropic | https://platform.claude.com/docs/en/build-with-claude/structured-outputs | A | live docs | 2026-07-29 | JSON Schema constraint, limitations, schema cache retention | complex schemas can fail compilation; feature matrix changes |
| Model IDs and versioning | Anthropic | https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions | A | live docs | 2026-07-29 | 4.6+ dateless IDs are pinned; serving infrastructure can change | fixed weights do not imply identical outputs |
| Claude API errors | Anthropic | https://platform.claude.com/docs/en/api/errors | A | live docs | 2026-07-29 | error/request-ID shape and SDK retry defaults | ReAgent must override defaults to its budget |
| Model deprecations | Anthropic | https://platform.claude.com/docs/en/about-claude/model-deprecations | A | live docs | 2026-07-29 | status, retirement dates, 60-day notice | partner platforms may differ |
| Organization data retention | Anthropic | https://privacy.anthropic.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data | A | updated 2026-07 | 2026-07-29 | standard 30-day deletion and exceptions | contract/account exceptions apply |
| Commercial Terms of Service | Anthropic | https://www.anthropic.com/legal/commercial-terms | A | effective 2025-06-17 | 2026-07-29 | API-key commercial use, customer content/output, human-review responsibility, fees | legal interpretation and input rights require owner/counsel review |
| Introducing gpt-oss | OpenAI | https://openai.com/index/introducing-gpt-oss/ | A | 2025-08-05 | 2026-07-29 | Apache 2.0, 16 GB claim, 128K, mostly-English training, structured output | operator/serving stack determines production properties |
| gpt-oss repository/model card | OpenAI | https://github.com/openai/gpt-oss | A/C, official source and implementation | live repository | 2026-07-29 | license, serving options, structured-output capability | repository can change; pin a revision |
| Structured Outputs | vLLM | https://docs.vllm.ai/en/v0.15.0/features/structured_outputs/ | C, official project docs | v0.15.0 | 2026-07-29 | local JSON-Schema constrained decoding option | not an OpenAI-hosted guarantee; version-specific |
