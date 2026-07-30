# Real Grounded Report Cost Model

Date: 2026-07-30
Status: **Proposed Class D policy; current authorized spend USD 0.00**

## Operation plan

| Operation kind | Maximum logical calls | Idempotency input |
|---|---:|---|
| `llm.paper_summary_evidence` | 5 | run + paper + source/input + model/prompt/schema checksums |
| `llm.cross_paper_claims` | 1 | all validated summary/evidence checksums |
| `llm.report_markdown` | 1 | validated claims/citations + disclosure checksum |
| `llm.mechanical_repair` | 1 | failed output hash + sanitized diagnostics |
| **Total** | **8** | — |

Each call reserves ProviderBudget before transport, starts with request
fingerprint, records exact identity/request ID, and settles reported usage,
latency, retries, cost, currency, and outcome. Failure settles when outcome and
usage are known; ambiguous transport remains unsettled and blocks publication.

## Proposed hard envelope

- 3–5 papers; 8 logical calls;
- 11 maximum physical attempts (3 global retries, including one repair);
- 90,000 total input tokens and 32,000 total output tokens across attempts;
- 20 minutes wall-clock runtime;
- one retry per transient operation, three retries globally;
- one mechanical repair call;
- hard monetary cap **USD 1.25**.

Rationale: the envelope tolerates long schema/prompts and one bounded failure
while remaining a low-cost supervised acceptance. Evidence is current provider
pricing plus staged-recovery patterns. Alternatives are 3 papers/6 calls,
USD 0 deferral, or a larger $2 cap. The tradeoff is auditability and recovery
versus latency/cost. Every value requires owner approval and is revisited after
Fake measurements, provider token counting, or any price/model change.

## Transparent upper bound

Using post-introductory Claude Sonnet 5 standard rates of $3/M input and $15/M
output:

`90,000 × $3/1M + 32,000 × $15/1M = $0.27 + $0.48 = $0.75`.

At the current introductory $2/$10 rates through 2026-08-31 the same envelope
is $0.50. GPT-5.6 Terra at $2.50/$15 is $0.705. The proposed $1.25 hard cap
covers tokenizer-estimation error and account/region price variation; it does
not authorize caching, batch, tools, web search, or a comparison model.

Prices exclude taxes and may change. Long-context surcharges are not expected
below 272k per request but remain a contract check. Before each live run the
system must obtain an owner-approved price manifest, tokenize with the exact
model where supported, and fail closed if price or usage is missing.

## Reservation/replay

Reservations use worst-case remaining tokens/cost, not average estimates.
Retries consume the same global envelope. A completed operation is replayed
from immutable artifacts and never re-billed. Missing usage, currency mismatch,
model drift, reservation overflow, or uncertain settlement blocks the next
stage and publication.

No API key, non-zero budget, or call is approved by this document.

