# Per-paper Structured Summary Contract

Status: **Proposed `PerPaperSummary/v1`**
Date: 2026-07-30

One structured result is bound to one known paper and SourceContent checksum:

- `summary_id`, `paper_id`, `citation_label`;
- `research_objective`;
- `methodology: {status: EXPLICIT|UNAVAILABLE, text, evidence_unit_ids}`;
- `key_findings[]`;
- `stated_limitations: {status: EXPLICIT|UNAVAILABLE, items[]}`;
- `contribution`;
- `topic_relevance` (descriptive linkage, not a screening label);
- `uncertainties[]` and `missing_information_flags[]`;
- `abstract_only_disclosure`;
- all referenced `evidence_unit_ids`;
- input/request/output checksums;
- prompt ID/version/hash, provider/model/snapshot/adapter identity;
- provider request ID, `generated_at`, `schema_version`.

## Semantic rules

- Every populated substantive field cites at least one EvidenceUnit from that
  paper; the summary cannot cite another paper.
- Methodology or limitations absent from the abstract are `UNAVAILABLE`, not
  guessed from title, venue, discipline, or model knowledge.
- A model interpretation uses an explicit `SYSTEM_INFERENCE` marker and
  uncertainty text. It never becomes a source-stated finding.
- Findings use source-qualified wording (“the abstract reports…”).
- No scientific-correctness, causal-validity, novelty, venue-quality,
  citation-impact, paper-quality, trust, or full-paper claim is allowed.
- Empty/unknown values are explicit; fabricated filler fails validation.
- A citation label must be present in `GroundedReportInput`.

## Validation

Mechanical validation checks schema, IDs, evidence existence, label membership,
 span/hash location, missing-information consistency, prohibited phrases,
checksums, and exact provider/prompt identities. Semantic ambiguity is retained
as uncertainty or fails to human review; it is not silently repaired.

The summary is a model-produced abstract synopsis, not expert interpretation or
a relevance judgment. It remains private until the final publication gate.

