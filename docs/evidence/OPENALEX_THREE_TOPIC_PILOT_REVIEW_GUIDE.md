# OpenAlex Three-topic Pilot Blind-review Guide

## Scope and current state

Evaluation ID: `openalex-three-topic-pilot-v1`

Current state: `WAITING_FOR_HUMAN_REVIEW`

This packet contains 40 normalized OpenAlex discovery candidates from three
bounded queries. One non-English topic produced an empty normalized pool after
its single returned record failed the adapter's safe field-length validation.
This is technical pilot evidence, not a relevance or provider-quality result.

Codex generated no relevance labels and performed no adjudication. Two humans
must review independently before Phase 9B-2B-2 may import judgments or calculate
retrieval metrics.

## Private packet locations

These files live under ignored private storage and must not be committed:

- reviewer_A JSON:
  `runtime_data/evaluations/openalex/openalex-three-topic-pilot-v1/reviews/reviewer_A/review.json`
- reviewer_A CSV:
  `runtime_data/evaluations/openalex/openalex-three-topic-pilot-v1/reviews/reviewer_A/review.csv`
- reviewer_B JSON:
  `runtime_data/evaluations/openalex/openalex-three-topic-pilot-v1/reviews/reviewer_B/review.json`
- reviewer_B CSV:
  `runtime_data/evaluations/openalex/openalex-three-topic-pilot-v1/reviews/reviewer_B/review.csv`
- blank adjudication template:
  `runtime_data/evaluations/openalex/openalex-three-topic-pilot-v1/reviews/adjudication_template.json`
- packet/checksum manifest:
  `runtime_data/evaluations/openalex/openalex-three-topic-pilot-v1/reviews/review_packet_manifest.json`

JSON and CSV are equivalent alternatives. Each reviewer should complete and
return exactly one authoritative format to avoid duplicate imports.

## Independent review procedure

1. Assign reviewer_A and reviewer_B to two different humans.
2. Do not allow either reviewer to inspect the other reviewer's file, notes, or
   labels before both files are frozen and returned.
3. Review only the permitted title, authors, year, venue, DOI, OpenAlex ID and
   abstract preview. The preview is at most 500 normalized characters and may
   be insufficient.
4. Do not use citation count as a quality or relevance signal.
5. Do not perform external provider lookups during this pilot.
6. Do not edit topic, rank, candidate ID, identity hash, title, authors, year,
   venue, DOI, OpenAlex ID, abstract availability, or preview.
7. Complete only the judgment fields. `reviewer_id` is already assigned.
8. Return the completed files privately; do not attach them to Git issues or
   commit them.

Rank remains visible because the approved protocol evaluates the current product
ordering. It must not be treated as an automated recommendation or label.

## Relevance labels

- `HIGHLY_RELEVANT`: directly answers the topic/research question and fits the
  intended scope.
- `RELEVANT`: clearly useful and within scope, but not a central/direct answer.
- `PARTIALLY_RELEVANT`: contains a material relevant component mixed with
  broader, adjacent, or uncertain scope.
- `NOT_RELEVANT`: outside the defined topic or exclusion boundary.
- `CANNOT_JUDGE`: permitted metadata/preview is insufficient. Do not convert
  missing evidence into `NOT_RELEVANT`.

Confidence uses the existing 1–5 human scale. A short note should explain only
material ambiguity; do not paste full abstracts or copyrighted source text.

## Duplicate, identity and metadata fields

- `duplicate_cluster`: use the same short human-created cluster token for
  candidates believed to represent the same work/manifestation family.
- `identity_ambiguity`: mark true when DOI/OpenAlex/title/year/authors do not
  establish a safe identity decision.
- `metadata_error_flags`: use concise approved flags such as
  `TITLE_MISMATCH`, `AUTHOR_MISSING`, `YEAR_CONFLICT`, `VENUE_MISSING`,
  `DOI_SUSPECT`, or `ABSTRACT_INSUFFICIENT`.
- `exclusion_reason`: explain a `NOT_RELEVANT` decision or a scope exclusion.
- `reviewer_note`: maximum concise reasoning; no copied full abstract.
- `judged_at`: timezone-aware ISO 8601 timestamp.

Do not merge fuzzy title matches automatically. Preprint, conference, and
journal manifestations remain separate unless exact identity is established.

## Return and adjudication

The owner should receive one completed JSON or CSV file from each reviewer,
verify that file checksums can be recorded, and nominate a third independent
human adjudicator. Phase 9B-2B-2 will:

1. import and validate both files against the immutable candidate identities;
2. reject changed metadata, duplicate rows, invalid labels, or unknown IDs;
3. expose disagreements to the human adjudicator;
4. import the human-completed adjudication template;
5. only then calculate metrics and generate an evidence report.

Neither Codex nor ranking logic may fill missing labels or adjudicate.

## Retention and protection

- abstract previews expire no later than `2026-08-11T04:37:24.600031+00:00`,
  or immediately after adjudication if earlier;
- normalized candidate pools and ProviderOperation journal expire no later than
  `2026-08-27T04:37:24.600031+00:00`;
- keep files private with local filesystem access controls;
- do not email unencrypted packets or place them in public/shared repositories;
- preserve aggregate checksums and an owner-approved no-abstract report before
  eventual deletion;
- cleanup must remain explicit and scoped to this exact evaluation ID.

No provider-quality conclusion should be made before two independent files and
human adjudication are complete.
