# Real Grounded Report Live Cost Model

Date/access date: 2026-07-30  
Status: **Proposed Class D limits; authorized spend remains USD 0.00**

## Call and token plan

| Stage | Logical calls | Proposed aggregate reservation |
|---|---:|---:|
| three paper summary/evidence calls | 3 | 30k input / 6k output |
| cross-paper synthesis | 1 | 12k input / 4k output |
| report composition | 1 | 10k input / 6k output |
| optional mechanical repair | ≤1 | 8k input / 4k output |
| **maximum** | **6** | **60k input / 20k output** |

The aggregate token caps include all retries. Five normal calls plus one repair
are six logical operations; at most two bounded transient retry attempts yield
eight total attempts. Cached-input discounts are assumed to be zero because
they are not guaranteed or needed for the bound.

## Official price calculation

Anthropic's current Sonnet 5 introductory price through 2026-08-31 is USD
$2/M input and $10/M output:

`60,000 × 2/1,000,000 + 20,000 × 10/1,000,000 = $0.12 + $0.20 = $0.32`.

At the documented post-introductory $3/$15 rates:

`60,000 × 3/1,000,000 + 20,000 × 15/1,000,000 = $0.18 + $0.30 = $0.48`.

Tax, billing currency, tokenization, account-specific terms, and price changes
remain uncertain. The same source text may tokenize differently under Sonnet 5.
The preflight must re-record current official price immediately before a live
run.

Source: [Anthropic, “What's new in Claude Sonnet 5”](https://platform.claude.com/docs/en/about-claude/models/whats-new-sonnet-5),
accessed 2026-07-30. It supports model price and tokenizer-change claims, not
actual ReAgent usage.

## Proposed monetary controls

- owner-facing hard cap: **USD 1.00**;
- initial total reservation: **USD 0.75**;
- per-operation reservation cap: **USD 0.30**;
- aggregate token caps: 60k input / 20k output;
- six logical operations, eight total attempts;
- no batch, cache-write, tool, fallback, comparison, or long-context surcharge;
- all reservations and actual usage use USD.

These values are Proposed Class D policy. Rationale: the hard cap is more than
twice the standard-price token envelope while remaining below the broader V3
architecture cap. Alternatives are USD 0/defer, a $0.60 cap after exact token
counting, or a larger cap. The tradeoff is estimation headroom versus financial
exposure. Owner approval is mandatory; revisit on any model/price/tokenizer/
payload/retry change or if preflight reservation exceeds $0.75.

## Fail-closed behavior

Do not start when price is missing, currency differs, token estimation is
unavailable, reservation exceeds the approved amount, or the account spend
limit is unknown. Abort before the next call if projected aggregate use exceeds
any cap. Missing provider usage or ambiguous transport settlement leaves the
operation unsettled, blocks publication, and requires reconciliation; do not
estimate actual usage into a successful settlement.

Retries consume the same caps. Completed replay uses immutable results and
incurs zero calls. This document does not authorize a reservation or spend.

