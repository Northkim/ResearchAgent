# Real Judge Calibration Cost Model

Cost-model version: `reagent-real-judge-cost/v1-proposed`
Price access date: 2026-07-29
Currency: USD
Current authorized budget: **USD 0.00**

No amount in this document authorizes spending.

## Proposed hard envelope

| Limit | Proposed value |
|---|---:|
| request candidates | 15: 12 private real + 3 synthetic |
| pointwise logical calls | 30: A and B for every candidate |
| pairwise logical calls | 6: three pairs in both orders |
| total logical calls | 36 |
| retry attempts per logical call | at most 1 transient retry |
| global retry-attempt budget | 6 |
| maximum physical attempts | 42 |
| pointwise input reservation | 2,000 tokens/call |
| pointwise output reservation | 256 tokens/call |
| pairwise input reservation | 2,500 tokens/call |
| pairwise output reservation | 128 tokens/call |
| aggregate logical input | 75,000 tokens |
| aggregate logical output | 8,448 tokens |
| retry reserve | 15,000 input + 1,536 output tokens |
| hard aggregate input | 90,000 tokens |
| hard aggregate output | 9,984 tokens |
| runtime | 15 minutes wall clock |
| failure budget | at most 2 failed logical calls; any unresolved required call fails calibration |
| proposed monetary reservation | **USD 0.75 maximum** after owner approval |

These are **Proposed Class D ReAgent policy**. Rationale: 36 calls cover two
pointwise prompts and one mirrored pair per topic; six bounded retries absorb
transient failures without making SDK defaults an unbounded cost multiplier.
Alternatives: no retries (more brittle) or one retry for every call (84 maximum
attempts and much larger uncertainty). Tradeoff: a noisy provider may stop the
experiment early. Owner approval is required. Revisit if the renderer/token
counter exceeds reservations, price/model changes, or a preflight shows that
256 output tokens cannot satisfy the schema.

## Transparent upper bounds

### Proposed primary: Anthropic `claude-sonnet-5`

Conservative standard price after 2026-08-31:

- input: 0.090M × USD 3/M = USD 0.2700;
- output: 0.009984M × USD 15/M = USD 0.14976;
- token upper bound: **USD 0.41976**.

Current introductory price through 2026-08-31:

- input: 0.090M × USD 2/M = USD 0.1800;
- output: 0.009984M × USD 10/M = USD 0.09984;
- token upper bound: **USD 0.27984**.

Use the conservative standard price for reservation because execution timing is
unknown. The proposed USD 0.75 hard cap leaves USD 0.33024 for tokenizer,
schema-instruction, price-rounding, and estimation uncertainty. No prompt
caching, Batch discount, tool charge, or region discount is assumed. If
`inference_geo: "us"` applies, Anthropic currently documents a 1.1× multiplier;
the USD 0.75 cap still applies.

### OpenAI fallback: `gpt-5.6-terra`

At the current USD 2.50/M input and USD 15/M output:

- input: 0.090M × USD 2.50/M = USD 0.2250;
- output: 0.009984M × USD 15/M = USD 0.14976;
- token upper bound: **USD 0.37476**.

This estimate does not make Terra approved. Cached-input discounts are excluded,
and no long-context surcharge applies at the proposed size.

### Local gpt-oss-20b

Hosted-token price is not applicable. Cost is **unknown**, not zero: GPU access,
electricity, setup, storage, engineering, and runtime must be priced separately
before a local calibration can be approved.

## Provider constraints versus project policy

Provider-imposed: available model, tokenizer, schema subset, organization rate
limit, request-size/context/output ceilings, price, region/ZDR eligibility, and
provider retry/error behavior.

Evidence-informed project defaults: two pointwise prompts, mirrored pair order,
bounded output, usage recording, and fail-closed operation settlement.

Owner policy: sample/call/token/runtime/retry/failure/monetary caps. No provider
limit overrides a smaller ReAgent cap.

## Reservation and settlement

The existing `ProviderOperationService` remains the required boundary:

1. estimate tokens using the chosen provider's official/token-count endpoint or
   a conservative local estimator;
2. reserve the full logical call before sending;
3. disable SDK automatic retries or count every attempt under one operation;
4. record request ID, actual identity, tokens, latency, attempt, and cost;
5. settle success/failure exactly once;
6. reject aggregation if any required operation is unsettled;
7. replay from immutable artifacts without a new reservation or call.

## Fail-closed rules

- Missing current price: no reservation and no call.
- Token estimate above any per-call/aggregate cap: no call.
- Reservation would exceed USD 0.75 or the smaller owner-approved budget: no
  call.
- Wrong/unavailable model ID: settle failure and stop.
- Structured output/refusal/truncation: at most one policy-permitted retry; then
  fail the required call.
- Missing usage or provider request ID: settlement is incomplete; stop.
- More than six retries, two failed logical calls, 42 attempts, or 15 minutes:
  stop remaining calls.
- Provider SDK performs an uncounted retry: treat as a budget-integrity failure.

## Official price evidence

| Source | Organization | URL | Class | Accessed | Supported claim | Limitation |
|---|---|---|---|---|---|---|
| Pricing | Anthropic | https://platform.claude.com/docs/en/about-claude/pricing | A | 2026-07-29 | Sonnet 5 introductory/standard prices, tokenizer note, region multiplier | recheck immediately before execution |
| GPT-5.6 Terra model | OpenAI | https://developers.openai.com/api/docs/models/gpt-5.6-terra | A | 2026-07-29 | Terra token prices and context surcharge boundary | account discounts/credits not assumed |
| Introducing gpt-oss | OpenAI | https://openai.com/index/introducing-gpt-oss/ | A | 2026-07-29 | downloadable weights and hardware claims | does not price local ownership |

