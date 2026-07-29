# Multilingual SearchPlan Contract

Contract status: Implemented under ADR 0005 limited acceptance
Expansion version: `manual-query-expansion/1.0.0`
Implementation date: 2026-07-29

## Phase 9B-2C-1 implementation record

The additive implementation is in:

- `backend/research/contracts/multilingual.py`;
- `backend/research/evaluation/multilingual.py`;
- `evaluation/topics/openalex_chinese_multilingual_v1.json`;
- evaluation CLI command `generate-multilingual`.

The existing single-query path remains the default. Multilingual execution
requires an explicit immutable plan and explicit `--live`; it is not embedded in
the OpenAlex transport or the frozen workflow.

## Boundary

Multilingual search is an additive search-planning capability, separate from the
automated judge. V1 accepts only explicit, versioned, owner-approved variants.
It does not authorize unrestricted LLM query generation, translation, or live
OpenAlex calls.

The inspected current `SearchPlan` freezes one exact provider query, year,
language/document policies, criteria, candidate/page/sort limits, provider and
adapter versions, and a fingerprint. `OpenAlexPaperSearchProvider` executes one
bounded page (maximum 20 candidates) and compiles the current term-level query.
There is no query-variant collection, per-variant operation provenance, or
multilingual merge policy. V1 extends that plan rather than changing the meaning
of one current execution.

## QueryVariant

Immutable schema: `reagent-query-variant/v1`

- `variant_id`
- `source_query`
- `source_language`
- `variant_language`
- `variant_type`: `ORIGINAL`, `MANUAL_SYNONYM`, `MANUAL_TRANSLATION`,
  `QUOTED_TERM`, `BOOLEAN_EXPANSION`, `ENGLISH_PIVOT`, or
  `BILINGUAL_MIXED`
- `generated_by` (human identity or deterministic compiler identity)
- `generation_method` and `generation_version`
- `exact_provider_query`
- `checksum`
- `owner_approved`
- `created_at` and `schema_version`

The source expression and exact provider query are distinct. The adapter freezes
the exact provider query after provider-specific compilation so quoting,
Boolean operators, escaping, and term joining are replayable.

## MultilingualSearchPlan

Immutable schema: `reagent-multilingual-search-plan/v1`

- `plan_id` and original `ResearchQuery`
- `original_language`
- ordered `query_variants`
- optional `language_filter`
- `merge_policy_version`
- `deduplication_policy_version`
- `per_variant_request_limit`
- `total_request_limit`
- `expansion_version`
- `candidate_limit`
- immutable `coverage_warning_policy`
- `plan_checksum` and `schema_version`

Every executable variant must be owner-approved and unique by checksum. Search
requests are separate and bounded; a failed variant cannot be silently replaced
or combined with another request.

## Accepted V1 execution policy

All limits are **Class D ReAgent project policy accepted only for this bounded
multilingual implementation**:

- maximum four approved variants per topic;
- one provider request page per variant;
- maximum 20 provider records per variant;
- maximum eight HTTP requests total: one free-credit preflight plus one Works
  request per variant, with retries disabled for the supervised acceptance;
- deterministic merge after all attempted variants;
- candidate-pool cap and truncation reason recorded separately;
- no automatic fuzzy deduplication;
- no automatic LLM expansion or machine translation.

The monetary cap is USD 0.00 out-of-pocket. Provider free-credit availability is
checked before each Works call.

## Existing Chinese topic

The frozen topic `nonenglish-chinese-digital-humanities` currently contains:

- original query: `中国 数字人文 文本分析`;
- research question: `哪些研究使用文本分析方法开展中国语境下的数字人文研究？`;
- keywords: `数字人文`, `文本分析`, `中国`;
- 2015–2026 range; Chinese/bilingual preference.

The owner-approved immutable V1 variants are:

| Type | Proposed source expression | Rationale |
|---|---|---|
| ORIGINAL | `中国 数字人文 文本分析` | preserves the frozen topic query |
| MANUAL_SYNONYM | `中国 数字人文 计算文本分析` | tests a manually reviewed Chinese methodological synonym |
| ENGLISH_PIVOT | `Chinese digital humanities text analysis China` | manually reviewed English-indexed pivot without machine translation |
| BILINGUAL_MIXED | `中国 数字人文 Chinese digital humanities 文本分析 text analysis` | manually reviewed bilingual conjunction |

The configuration records the adapter-compiled quoted `AND` expression and a
stable checksum for each variant. The current compiler treats whitespace tokens
as conjunctions; it does not pass raw Boolean syntax through. Changing any text,
order, method, version, approval, or timestamp creates a new checksum and plan
version. No claim about Chinese recall follows from manual selection.

## Per-variant provenance

Each returned record carries:

- provider request/operation ID;
- variant ID and checksum;
- exact provider query checksum;
- first-seen variant;
- ordered all-matched variant IDs;
- no provider rank or citation count is used in merge or candidate ordering;
- provider/adapter versions and retrieval time;
- normalization/rejection outcome and safe diagnostic reference.

## Deterministic merge and deduplication

1. Normalize records independently within each variant.
2. Merge exact normalized DOI matches, after rejecting impossible DOI conflicts.
3. Merge exact OpenAlex ID matches.
4. Create a title/year advisory cluster only; it requires human resolution and
   never performs an automatic fuzzy merge.
5. Preserve the first-seen record under immutable variant order, then record
   every matching variant and field conflict.
6. Sort the merged candidate set deterministically by normalized paper identity;
   do not use the number of matching variants, provider citation count, or
   provider rank as a quality score.

If DOI and OpenAlex ID imply incompatible clusters, retain separate candidates
and emit `IDENTITY_CONFLICT`. Candidate-cap exclusions are recorded explicitly;
no paper disappears silently.

## Diagnostics contract

Per variant and in total, record:

- requests planned/attempted/succeeded/failed;
- provider records received;
- normalized records;
- rejected records by normalized reason;
- exact DOI and exact OpenAlex-ID duplicates;
- advisory title/year clusters;
- missing-abstract count;
- provider language-field missingness;
- language distribution;
- first-seen and all-matched counts;
- candidate-pool cap/truncation;
- coverage warnings.

Normalized warnings/reasons:

- `ZERO_RESULTS`
- `LOW_RESULT_COUNT`
- `NO_NORMALIZED_RESULTS`
- `MISSING_ABSTRACT`
- `FIELD_LENGTH_REJECTED`
- `CONTROL_CHARACTER_REJECTED`
- `INVALID_UNICODE`
- `LANGUAGE_MISMATCH`
- `LANGUAGE_FIELD_MISSING`
- `DUPLICATE_CONCENTRATION`
- `ONLY_ENGLISH_RESULTS`
- `ONLY_ORIGINAL_LANGUAGE_RESULTS`
- `IDENTITY_CONFLICT`
- `PARTIAL_VARIANT_FAILURE`
- `TOTAL_REQUEST_BUDGET_EXCEEDED`
- `CANDIDATE_LIMIT_TRUNCATED`

Thresholds for “low” and “duplicate concentration” are Class D policies and must
be approved/versioned rather than embedded as provider facts.

## Safe rejection diagnostic

The field-length gate must remain. A rejected-record diagnostic records:

- normalized rejected field name;
- measured length and unit;
- configured limit and boundary version;
- record index and provider-operation ID;
- short, safely truncated diagnostic fragment or one-way content hash;
- no full rejected field, response body, URL with credentials, or abstract in
  logs.

The diagnostic is evidence about local normalization, not permission to retain
the rejected content.

## Coverage semantics

`complete=true` means all approved bounded variants were attempted according to
plan. It never means exhaustive multilingual literature coverage. A zero-result
or zero-normalized-candidate variant remains visible. An English pivot improves
query diversity but does not prove language coverage.

## Implementation separation

The later multilingual milestone should add `QueryVariant` and
`MultilingualSearchPlan` planning/merge contracts around the existing
`PaperSearchProvider`, preserving per-variant `ProviderOperation` supervision.
It must not depend on, call, or expose automated relevance judgments.
