# Phase 9B-2C-1: Multilingual Search and Safe Diagnostics

Status: **PASS**
Date: 2026-07-29
Baseline: `686687b (HEAD -> main, origin/main, origin/HEAD) docs`

## Scope and ADR authority

ADR 0005 is **Accepted with limited scope**. The accepted scope is explicit,
immutable multilingual query variants; separate operation provenance;
deterministic exact merge; no fuzzy automatic merge; safe future rejection
diagnostics; retention of blank human-review packets; and the silver-not-gold
terminology boundary.

No automated judge, judge provider/model, LLM call/key/budget, relevance label,
confidence threshold, audit threshold, machine translation, or unrestricted
query expansion was implemented or accepted. No additional ADR was required.

## Implemented contracts

`backend/research/contracts/multilingual.py` adds:

- `reagent-query-variant/v1`;
- `reagent-multilingual-search-plan/v1`;
- `reagent-search-diagnostic/v1`;
- `reagent-field-rejection-diagnostic/v1`;
- typed variant, diagnostic-code, and diagnostic-cause enums.

Contracts are frozen dataclasses, expose tuples and frozen mappings, serialize to
canonical JSON, and compute or verify stable SHA-256 values. Plans reject
duplicate variant IDs, duplicate exact provider queries, invalid budgets, and
unsupported schemas. The execution service rejects any unapproved variant.

The additive versioned plan
`evaluation/topics/openalex_chinese_multilingual_v1.json` contains four manual,
owner-approved variants:

1. `zh-original-v1`;
2. `zh-manual-synonym-v1`;
3. `en-manual-pivot-v1`;
4. `zh-en-bilingual-v1`.

Every source expression and its exact quoted-AND OpenAlex query were checked
against the existing adapter compiler. No LLM or machine translation generated
the variants. Plan checksum:
`sha256:9b04cc0d10bd1952b13f1423e6ac3470670afe4f78a8ed6890cf1a70d440e85f`.

## Execution and persistence

`MultilingualCandidatePoolGenerator` is evaluation-only orchestration. It:

- validates the plan and approval flags;
- executes variants in immutable definition order;
- creates one ProviderOperation per variant;
- settles every started operation success/failure;
- enforces injected reservation, per-variant, total request, runtime, and
  zero-cost budgets;
- records partial/all-variant failure without inventing a fallback query;
- publishes immutable relative-key artifacts through
  `ArtifactContentStorage`;
- verifies completed artifacts and settled operations on replay, making no
  duplicate provider call.

Artifacts:

- `multilingual_search_plan.json`;
- `query_variant_execution.json`;
- `multilingual_search_statistics.json`;
- `deterministic_merge_report.json`;
- `coverage_diagnostics.json`;
- `merged_candidates.json`;
- topic and evaluation manifests.

Raw HTTP response bodies are not retained. Full `PaperRecord` content is not
duplicated in per-variant evidence. Candidate metadata retains first-seen/all
matched variants, exact-query checksums, operation IDs, source query language,
provider/adapter identity, retrieval timestamp, raw metadata hash, and original
normalized PaperRecord checksum. Review export includes this query provenance.

## Deterministic merge

Automatic identity order is:

1. exact normalized DOI;
2. exact OpenAlex Work ID;
3. normalized title plus year as advisory only;
4. fuzzy automatic merge prohibited.

Conflicting DOI/OpenAlex identities remain separate with `IDENTITY_CONFLICT`.
Preprint/conference/journal manifestations remain separate without exact
identity. Citation count and provider rank do not participate. Candidate ordering
uses normalized paper identity. Exact merges, conflicts, advisory clusters, and
candidate-cap exclusions are explicit; the merge report asserts no silent loss.

## Diagnostics and historical boundary

Typed diagnostics cover zero/low/no-normalized results; missing abstract, DOI,
authors, year, venue, and language; field length, controls, invalid Unicode;
language mismatch/distribution; duplicate concentration; advisory clusters;
partial failures; request-budget excess; identity conflicts; and explicit
candidate-limit truncation.

Future rejected provider fields record:

- field name;
- normalized measured character length;
- configured character limit;
- safe Work ID when available;
- SHA-256 of the rejected value;
- normalized, control-free, secret-redacted preview capped at 80 characters;
- actual preview length;
- adapter version `1.0.0`;
- validator version `openalex-field-validator/v2`.

Validation limits were not weakened. Full rejected content is not stored.

The Phase 9B-2B-1 Chinese rejection remains historically
`details_available: false`: its artifact did not record field, measured length,
or configured limit. The new live run observed a future record under the new
schema; this does not retroactively alter or backfill the historical artifact.

## Network-free verification

Commands:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m pytest -q backend/research/tests

conda run --no-capture-output -n reagent-dev \
  python -m pytest -q backend

conda run --no-capture-output -n reagent-dev \
  python -m compileall -q backend
```

Results before documentation finalization:

- focused research: `90 passed`, exit 0;
- full backend: `173 passed, 18 skipped`, exit 0;
- compileall: exit 0.

All default tests are network-free. PostgreSQL tests were not separately run
because no persistence port, SQL adapter, ORM, migration, or SQL-backed path
changed. Frontend tests were not required because no frontend or API DTO changed.

## Live Chinese acceptance

Official OpenAlex authentication/pricing, `/rate-limit`, Works, and search
documentation was rechecked on 2026-07-29. The first isolated run
`openalex-chinese-multilingual-v1` failed locally before receiving any OpenAlex
response; four operations settled `PROVIDER_UNAVAILABLE`. It is retained as
ignored failure evidence.

The network-authorized isolated run
`openalex-chinese-multilingual-v1-live` completed:

| Variant | Provider count | Received | Normalized | Rejected |
|---|---:|---:|---:|---:|
| `zh-original-v1` | 1 | 1 | 0 | 1 |
| `zh-manual-synonym-v1` | 0 | 0 | 0 | 0 |
| `en-manual-pivot-v1` | 56,822 | 20 | 20 | 0 |
| `zh-en-bilingual-v1` | 0 | 0 | 0 | 0 |

Objective merged evidence:

- eight requests: four free-credit preflights and four Works searches;
- four ProviderOperations `SUCCEEDED/SETTLED`, zero unsettled;
- 20 normalized merged candidates;
- zero exact cross-variant duplicates;
- zero title/year advisory clusters;
- zero identity conflicts;
- zero candidate-cap exclusions;
- declared language distribution: 20 English;
- one future safe field rejection:
  `abstract_inverted_index.token`, normalized length 324, configured limit 200,
  with an 80-character safe preview and SHA-256;
- no raw response, full rejected value, label, judgment, or relevance metric;
- replay returned `resumed` with the recorded request count and made no network
  call.

These figures measure retrieval, normalization, and coverage only. They do not
show relevance or scientific-quality improvement.

## Retention and cleanup

Retained ignored roots:

- `runtime_data/evaluations/openalex/openalex-chinese-multilingual-v1/`;
- `runtime_data/evaluations/openalex/openalex-chinese-multilingual-v1-live/`.

No database was created or modified. Evidence is not automatically deleted.
Optional owner-directed cleanup:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  clean openalex-chinese-multilingual-v1 \
  --confirm openalex-chinese-multilingual-v1

conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  clean openalex-chinese-multilingual-v1-live \
  --confirm openalex-chinese-multilingual-v1-live
```

## Compatibility and limitations

- Single-query `SearchPlan` remains the default.
- Composition still defaults to `FakePaperSearchProvider`.
- `guided-literature-review@2.0.0` and hash
  `af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`
  are untouched.
- No Secondary provider, SourceContent provider, full text, judge, or relevance
  label was added.
- OpenAlex non-English coverage remains uncertain.
- Variants are manually selected and have no independent query-quality
  validation.
- No machine translation exists.
- Metadata language and rights can be incomplete.
- Execution is synchronous.
- Retention/orphan cleanup remains operator-owned.
- Docker remains outside this acceptance and was not run.

## Next recommendation

Proceed only to an **automated-relevance-judge substrate using a Fake Judge**:
immutable request/result contracts, fake deterministic adapter, aggregation
input boundary, and audit-queue scaffolding. Do not add a real LLM provider until
the fake substrate, aggregation, and audit queue are verified and the deferred
provider/model/cost decisions are explicitly approved.
