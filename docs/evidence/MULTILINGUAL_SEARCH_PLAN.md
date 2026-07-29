# Multilingual SearchPlan Contract

Contract status: Proposed; no multilingual search execution is authorized  
Expansion version: `multilingual-search-expansion/v1`

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

Immutable schema: `query-variant/v1`

- `variant_id`
- `source_query`
- `query_language`
- `variant_language`
- `variant_type`: `ORIGINAL`, `MANUAL_SYNONYM`, `MANUAL_TRANSLATION`,
  `QUOTED_TERM`, `BOOLEAN_EXPANSION`, `ENGLISH_PIVOT`, or
  `BILINGUAL_MIXED`
- `generated_by` (human identity or deterministic compiler identity)
- `generation_method_version`
- `exact_provider_query`
- `checksum`
- `owner_approved`
- optional `translation_source_checksum` and `review_note`

The source expression and exact provider query are distinct. The adapter freezes
the exact provider query after provider-specific compilation so quoting,
Boolean operators, escaping, and term joining are replayable.

## MultilingualSearchPlan

Immutable schema: `multilingual-search-plan/v1`

- `original_research_query`
- `original_language`
- ordered `query_variants`
- optional `language_filter`
- `merge_policy_version`
- `deduplication_policy_version`
- `per_variant_request_limit`
- `total_request_limit`
- `expansion_version`
- `provenance`
- `coverage_warning_policy_version`
- `planned_at`, provider/adapter identity, and canonical fingerprint

Every executable variant must be owner-approved and unique by checksum. Search
requests are separate and bounded; a failed variant cannot be silently replaced
or combined with another request.

## Proposed V1 execution policy

All values are **Class D ReAgent project-policy proposals**:

- maximum four approved variants per topic;
- one provider request page per variant;
- maximum 20 provider records per variant;
- maximum four provider requests per topic;
- deterministic merge after all attempted variants;
- candidate-pool cap and truncation reason recorded separately;
- no automatic fuzzy deduplication;
- no automatic LLM expansion or machine translation.

These limits require owner approval and current OpenAlex budget revalidation.

## Existing Chinese topic

The frozen topic `nonenglish-chinese-digital-humanities` currently contains:

- original query: `中国 数字人文 文本分析`;
- research question: `哪些研究使用文本分析方法开展中国语境下的数字人文研究？`;
- keywords: `数字人文`, `文本分析`, `中国`;
- 2015–2026 range; Chinese/bilingual preference.

Proposed variants for human review—not executable or hard-coded by this phase:

| Type | Proposed source expression | Rationale |
|---|---|---|
| ORIGINAL | `中国 数字人文 文本分析` | preserves the frozen topic query |
| MANUAL_SYNONYM | `中国 数字人文 计算文本分析` | tests a manually reviewed Chinese methodological synonym |
| MANUAL_TRANSLATION / ENGLISH_PIVOT | `Chinese digital humanities text analysis` | tests English-indexed metadata without replacing Chinese intent |
| BILINGUAL_MIXED | `("数字人文" OR "digital humanities") ("文本分析" OR "text analysis") 中国` | tests bilingual metadata with explicit term provenance |

The exact OpenAlex query for each must be produced and reviewed against the
current adapter compiler before implementation. The owner may revise or reject
any phrase. No claim about Chinese recall follows from these proposals.

## Per-variant provenance

Each returned record carries:

- provider request/operation ID;
- variant ID and checksum;
- exact provider query checksum;
- first-seen variant;
- ordered all-matched variant IDs;
- provider result position within each variant, stored only as provenance and
  hidden from relevance judging/audit;
- provider/adapter versions and retrieval time;
- normalization/rejection outcome and safe diagnostic reference.

## Deterministic merge and deduplication

1. Normalize records independently within each variant.
2. Merge exact normalized DOI matches, after rejecting impossible DOI conflicts.
3. Merge exact OpenAlex ID matches.
4. Create a title/year advisory cluster only; it requires human resolution and
   never performs an automatic fuzzy merge.
5. Preserve the first-seen record by variant order, then record every matching
   variant and field conflict.
6. Sort the merged candidate set by the existing deterministic candidate policy;
   do not use the number of matching variants, provider citation count, or
   provider rank as a quality score.

If DOI and OpenAlex ID imply incompatible clusters, retain separate candidates,
emit `BILINGUAL_METADATA_CONFLICT`, and require review.

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
- `REJECTED_RECORDS`
- `MISSING_ABSTRACT`
- `FIELD_LENGTH_VIOLATION`
- `UNICODE_OR_CONTROL_CHARACTER_REJECTION`
- `LANGUAGE_MISMATCH`
- `PROVIDER_LANGUAGE_FIELD_MISSING`
- `DUPLICATE_CONCENTRATION`
- `ONLY_ENGLISH_RESULTS_FOR_NON_ENGLISH_QUERY`
- `ONLY_ORIGINAL_LANGUAGE_RESULTS`
- `BILINGUAL_METADATA_CONFLICT`

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
