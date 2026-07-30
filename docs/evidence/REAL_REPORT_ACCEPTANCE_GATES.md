# Real Grounded Report Acceptance Gates

Date: 2026-07-30
Status: **Proposed; numeric gates are Class D ReAgent policy**

Passing code does not approve a provider, spend, real abstract processing, or a
product report.

## A. Code acceptance

- immutable v2 contracts, canonical hashes, and provider-independent port;
- a new immutable workflow/skill version; V2 hash unchanged;
- deterministic Fake LLM vertical slice remains network-free;
- malformed/refusal/timeout/citation/evidence/budget/crash tests;
- ProviderOperation settlement and zero-call replay;
- API/frontend additions preserve ownership boundaries;
- no credentials or real content in fixtures.

## B. Real provider acceptance

Blocking: exact approved model/adapter/prompt/schema identities; approved ZDR
and input rights; 100% schema-valid outputs after at most one allowed retry;
reported usage/cost/request IDs; zero unsettled operations; zero duplicate calls
on replay; total usage inside approved caps. Refusal is an explicit failed
outcome, never empty success.

## C. Product acceptance

Blocking:

- 100% approved paper/source checksum match;
- 100% known summary/evidence/claim/citation IDs;
- 100% substantive claims have valid evidence;
- zero invalid spans, unknown citations, unapproved papers, duplicate DOIs,
  unsupported claims, or unmarked inference;
- disclosure, references, provider/prompt/workflow/skill identities present;
- all artifact writes and bidirectional checksums valid;
- report/API/frontend/restart reload the same bytes;
- literature corpus checksum and provenance link correctly.

A supervised human confirms the report is readable and disclosures/citations
are visible. This is product review, not scientific correctness validation.

## Proposed warnings

- any repair call;
- retry rate above 20% of logical calls;
- runtime over 15 minutes but within the 20-minute cap;
- missing methodology/limitation in most abstracts;
- multilingual output requiring substantial human correction;
- user finds a claim misleading despite mechanical support.

Informational: per-stage latency/tokens/cost, unavailable abstract fields,
claim/category counts, evidence per claim, report length, and download/reload
timing. These are not provider-quality claims from one acceptance.

## Class D rationale

The 100% identity/grounding rules are safety invariants: a small report has no
reason to tolerate fabricated sources. Call/token/cost/runtime/retry values are
operational envelopes from `REAL_REPORT_COST_MODEL.md`, not research
thresholds. Alternatives are stricter zero-retry/zero-repair or deferral.
Tradeoffs are recovery and usability versus cost and hallucination exposure.
All require owner approval and are revisited after Fake validation, first live
acceptance, any incident, or provider/model/prompt change.

## D. Deferred production requirements

Authentication, authorization, worker queue, distributed lease, S3, retention
worker, monitoring/alerting, multi-user permissions, and regional deployment
are explicitly outside V1 supervised acceptance.

## Testing levels

1. Pure contracts: no network.
2. Fake LLM vertical slice: deterministic, normal suite.
3. Recorded synthetic provider fixtures: no real abstract/response committed.
4. Opt-in real acceptance: approved provider/model/key/ZDR/rights/budget,
   isolated DB/root, explicit live flag, exactly 3 approved papers, bounded
   calls, end-to-end API/frontend/restart and zero-call replay.

No level-4 execution is authorized in Phase 9C-0.

