# EvidenceUnit and GroundedClaim Contract

Status: **Proposed additive v2 contracts**
Date: 2026-07-30

Existing v1 contracts are preserved. The real-report workflow uses explicit v2
schemas rather than weakening historical artifacts.

## EvidenceUnit/v2

Required fields:

- `evidence_id`, `paper_id`, `source_content_id`, content checksum;
- `source_field` (`ABSTRACT` only in V1);
- bounded source locator (normalized character offsets);
- short private source span and/or normalized paraphrased evidence statement;
- span checksum, supported claim IDs, evidence type, content scope;
- extraction prompt ID/version/hash and `schema_version`.

The span must occur exactly in the supplied normalized abstract and offsets must
round-trip. Provider text is untrusted data, never instructions.

**Proposed Class D excerpt policy:** private spans are at most 200 Unicode
characters and 25 words; the user-visible report shows paraphrased evidence
statements and citations, not verbatim spans. Alternatives are no stored span
or a shorter visible excerpt. This protects copyright and reduces
substitutiveness but makes manual inspection one click deeper. Owner approval
is required; revisit after rights review and usability testing.

No full abstract is reproduced in a report, log, committed fixture, or
diagnostic. Hashes/locators preserve verification.

## GroundedClaim/v2

Required fields:

- `claim_id`, `claim_text`;
- category: `SOURCE_SUMMARY`, `CROSS_SOURCE_THEME`, `AGREEMENT`,
  `DISAGREEMENT`, `LIMITATION`, `RESEARCH_GAP`, or `SYSTEM_INFERENCE`;
- supporting EvidenceUnit IDs and supporting paper IDs;
- structured confidence, `inference_flag`, limitations;
- generation prompt ID/version/hash;
- provider/model/snapshot/adapter identity and `schema_version`.

## Cardinality and wording rules

- `SOURCE_SUMMARY` maps to exactly one paper.
- `CROSS_SOURCE_THEME` and `AGREEMENT` map to at least two distinct papers.
- `DISAGREEMENT` has evidence and paper IDs for both positions.
- `LIMITATION` states whether it is source-stated or system-inferred.
- `RESEARCH_GAP` is an explicit, tentative inference unless a source states it.
- `SYSTEM_INFERENCE` is never worded as an established fact.
- Evidence/claim links are bidirectional and checksummed.
- A substantive claim without valid evidence is removed before composition or
  causes publication failure; it is never published with a warning alone.

Confidence reflects support strength within the supplied abstracts, not truth,
method quality, or statistical certainty. No automatic numeric threshold turns
an unsupported claim into a supported one.

