# Phase 9B-2B-1: OpenAlex Three-topic Candidate-pool Pilot

- **Date:** 2026-07-28
- **Phase verdict:** PASS_WITH_WARNINGS
- **Evaluation workflow state:** WAITING_FOR_HUMAN_REVIEW
- **Evaluation ID:** `openalex-three-topic-pilot-v1`
- **Topic set:** `reagent-openalex-engineering-evaluation@1.0.0`
- **Database:** none; evaluation-only append-only ProviderOperation journal
- **Private ignored root:**
  `runtime_data/evaluations/openalex/openalex-three-topic-pilot-v1/`

## 1. Git and authorization gate

Gate passed before any live execution:

- clean baseline: `e51f185` (`Phase 9B-2A` implementation);
- `.env` ignored by `.gitignore:39` and untracked;
- `runtime_data/` ignored by `.gitignore:53`;
- no tracked credential or live candidate output;
- owner authorized exactly three topics, one page/topic, max 20 candidates/topic,
  max three attempts/topic, metadata + <=500-character abstract preview,
  zero out-of-pocket cost and 30/14-day retention.

The local `origin/main` reference observed at gate time still displayed
`3d1e90a`; no fetch/pull/push or commit rewrite was performed. The clean local
`HEAD` itself contained the reviewed Phase 9B-2A files.

## 2. Official contract recheck

Accessed 2026-07-28:

- [Authentication & Pricing](https://developers.openalex.org/api-reference/authentication)
- [Check rate limit status](https://developers.openalex.org/api-reference/rate-limits/check-rate-limit-status)
- [List works](https://developers.openalex.org/api-reference/works/list-works)
- [Error Handling](https://developers.openalex.org/api-reference/errors)

Current facts remain compatible with the adapter:

- `api_key` query authentication and explicit `/rate-limit` endpoint;
- free key daily allowance and endpoint-cost reporting;
- full-text Works search currently reports `$0.001` per programmatic search;
- `GET /works`, one-page `meta + results`, `per_page <= 100`;
- `meta.cost_usd`, rate-limit headers, 429 on exhaustion and bounded
  exponential-backoff guidance.

No material contract drift blocked execution. `/rate-limit` response bodies can
contain the API key, so raw bodies remain prohibited.

## 3. Selected topics

The frozen selection rationale is in
`.agent_read/progress/openalex_three_topic_pilot_selection.md`.

| Topic ID | Role in pilot | Risk |
|---|---|---|
| `cs-machine-unlearning` | narrow technical CS/privacy query | verification terminology; preprint/published ambiguity |
| `social-algorithmic-management` | interdisciplinary terminology-ambiguous query | management/labor/IS scope collision |
| `nonenglish-chinese-digital-humanities` | non-English/Unicode coverage-risk query | missing abstracts, bilingual metadata, field-length/security limits |

The remaining nine topics were not called.

## 4. Live candidate-pool evidence

Exact live invocation used explicit `--live`, three `--topic` values and
`--include-abstract-preview`. It produced three per-topic immutable manifests,
one top-level manifest and a checksum-chained mode-`0600` operation journal.

| Topic | Provider count | Received | Normalized | Rejected | Abstract | DOI | Authors | Year | Venue | DOI/ID/title-year duplicates | Requests / retries | Latency | Provider credit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|---:|
| `cs-machine-unlearning` | 101 | 20 | 20 | 0 | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 | 0 / 0 / 0 | 2 / 0 | 2021 ms | `$0.001` |
| `social-algorithmic-management` | 137 | 20 | 20 | 0 | 20/20 | 19/20 | 20/20 | 20/20 | 19/20 | 0 / 0 / 0 | 2 / 0 | 1424 ms | `$0.001` |
| `nonenglish-chinese-digital-humanities` | 1 | 1 | 0 | 1 | n/a | n/a | n/a | n/a | n/a | 0 / 0 / 0 | 2 / 0 | 1431 ms | `$0.001` |

The Chinese topic's only record was rejected because one provider text field
exceeded the adapter's safe length limit. The security/schema boundary was not
weakened, the query was not changed, and no replacement record was fabricated.
This empty normalized pool is the phase warning and objective coverage evidence;
it is not a relevance conclusion.

Totals:

- three live topic operations;
- six provider requests: three `/rate-limit` + three `/works`;
- zero retries;
- 4876 ms summed provider latency;
- 40 normalized candidates;
- provider-reported search credit `$0.003`;
- ReAgent `estimated_cost_minor_units=0`, zero owner out-of-pocket use.

## 5. ProviderOperation and replay

- operations: 3;
- status: 3 `SUCCEEDED`;
- settlement: 3 `SETTLED`;
- RESERVED/RUNNING/UNSETTLED after completion: 0;
- each operation: 2 requests, 0 retries, 0 monetary minor units;
- diagnostic metadata keys: empty;
- raw URLs, authorization and API key: absent;
- second identical `generate` command returned `status=resumed`;
- candidate count/request count remained 40/6;
- no provider call, reservation, artifact or operation was duplicated.

## 6. Immutable candidate and packet evidence

Candidate-pool checksums:

- `cs-machine-unlearning`:
  `sha256:decd0eba62353b77cbf217a0e572d2dafd92838b8bcefbbd7152b3007f03a874`
- `social-algorithmic-management`:
  `sha256:98c62f77f65e69981b8ab746d25f091a9f19adfdcd3d94e21021f02d5672d6be`
- `nonenglish-chinese-digital-humanities`:
  `sha256:ac61e5df79b1ed576f9f5a6c29c21c67bdcc28d17917016fac8727098a06f006`

Shared candidate identity checksum:
`sha256:88aa7cf53861ce168d83153c26576642a500399401c1444328f614e71e1858e5`.

Review packet manifest checksum:
`sha256:ca071d209204be8689b2416f086bd4e6c16d52c5332f3e42bd51e7a7d28da4bc`.

| Private relative packet | SHA-256 |
|---|---|
| `reviews/reviewer_A/review.json` | `sha256:bd9550cd4fde81d22d170907c3b31626c74dfb98a5dfc33b177293375d6ba9f7` |
| `reviews/reviewer_A/review.csv` | `sha256:84ac46cf5984dff28a76496124b33dfee6a3bdc23db7f48cd10c5c801a67ee47` |
| `reviews/reviewer_B/review.json` | `sha256:d1d90e00eb30dc6bc30ee5c4283c3ecf779f3807f5e020012e160bae9b1852d5` |
| `reviews/reviewer_B/review.csv` | `sha256:918acb46afbec1467cfc393a65a57fcff193a73251a35198ecc6c440594acee6` |
| `reviews/adjudication_template.json` | `sha256:f152824e722d68cd8794150795ad4454624439f0b8a3941f0d8a612c5ccf29bd` |

Integrity verifier confirmed:

- every packet candidate exists in the immutable manifests;
- candidate IDs and identity hashes match;
- reviewer_A/reviewer_B contain the same 40-candidate set;
- JSON/CSV candidate identity rows are equivalent;
- no duplicate candidate row;
- pseudonymous reviewer assignment is the only prefilled reviewer field;
- relevance, confidence, exclusion, duplicate, ambiguity, metadata-error, note
  and timestamp values are empty;
- maximum abstract preview length is 500 normalized characters;
- adjudication labels, adjudicator, source hashes and timestamps are empty;
- all packet file checksums match the manifest.

## 7. Minimal implementation corrections

Live preparation exposed two harness gaps, fixed without changing core Runtime or
OpenAlex adapter ownership:

- `CandidatePoolGenerator` now records the topic's 20-candidate discovery intent
  in `ResearchQuery.max_results` while preserving the adapter's separate
  selected-paper `limit=5` contract.
- CLI adds reviewer-specific export and one `packets` command that creates two
  pseudonymous JSON/CSV packets, a blank adjudication template, retention
  metadata and an immutable checksum manifest.

No migration, database, API, frontend, dependency, Agent Runtime, Workflow
Engine, Skill, Semantic Scholar, Crossref, real LLM or full-text code changed.

## 8. Test evidence

Newly executed:

- first focused run: exit 1, `6 failed, 18 passed`; the attempted change passed
  20 as the provider's `limit`, but that parameter is the frozen selected-paper
  cap (3–5), not discovery page size. The implementation was corrected to keep
  `limit=5` while using the topic's 20-candidate `ResearchQuery.max_results`;
  no adapter limit was weakened;
- focused evaluation tests:
  `conda run --no-capture-output -n reagent-dev python -m pytest -q backend/research/tests/test_evaluation_*.py`
  → `24 passed in 0.21s`, exit 0;
- full network-free backend:
  `conda run --no-capture-output -n reagent-dev python -m pytest -q backend`
  → `163 passed, 18 skipped in 1.03s`, exit 0;
- compile:
  `conda run --no-capture-output -n reagent-dev python -m compileall -q backend`
  → exit 0.

PostgreSQL tests were not required: this evaluation harness deliberately uses
the approved isolated journal and no database was created. Frontend source/API
DTOs did not change; frontend tests were not run.

## 9. Retention and human boundary

- root size at generation: 448 KiB / 27 files;
- abstract-preview expiry:
  `2026-08-11T04:37:24.600031+00:00` or adjudication, whichever is earlier;
- normalized pools/journal expiry:
  `2026-08-27T04:37:24.600031+00:00`;
- raw provider response retained: no;
- human judgments imported: no;
- metrics/adjudication/provider-quality report generated: no;
- database created: no.

Final redacted leakage audit:

- OpenAlex API key configured: yes, value never printed;
- credential in tracked files: no;
- credential in 27 pilot files: no;
- tracked `runtime_data/` files: 0;
- raw provider response body: no;
- full abstract committed: no;
- three `search_execution.json` files contain the literal requested-field name
  `abstract_inverted_index`; this is SearchPlan metadata, not a retained response
  value or raw body;
- `.env` and the exact pilot root both resolve to Git ignore rules.

The owner-facing procedure is
`docs/evidence/OPENALEX_THREE_TOPIC_PILOT_REVIEW_GUIDE.md`.

Optional cleanup after owner review and evidence preservation:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  clean openalex-three-topic-pilot-v1 \
  --confirm openalex-three-topic-pilot-v1
```

Do not execute before both reviews/adjudication or owner cancellation.

## 10. Next allowed milestone

Only after two independent human-completed files are returned:

**Phase 9B-2B-2 — judgment import, human adjudication and metric report.**

Codex must not fill labels, infer missing judgments, adjudicate, calculate final
retrieval metrics, promote OpenAlex, or begin Semantic Scholar/Crossref/real-LLM
work before that boundary.
