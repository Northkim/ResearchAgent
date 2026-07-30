# Real Report Prompt-freeze Proposal

Date: 2026-07-30
Status: **Proposed; contract records only, no production prompt**

Hashes are SHA-256 over the exact canonical record strings shown below. The
future implementation must either use these records or publish a new version
and owner-reviewed hash; it must not edit a version in place.

| Prompt | Purpose / I/O | Canonical record | SHA-256 |
|---|---|---|---|
| `grounded-paper-summary/v1` | one approved paper slice → `PerPaperSummary/v1` | `grounded-paper-summary/v1\|paper-slice\|PerPaperSummary/v1\|abstract-only,no-fabrication,missing-unavailable` | `e22da29506c33875107aa2a526466447aefd947f19a64885c6b629c34747bcb3` |
| `grounded-evidence-extraction/v1` | same slice → `EvidenceUnit/v2` | `grounded-evidence-extraction/v1\|paper-slice\|EvidenceUnit/v2\|exact-locator,short-span,bidirectional-links` | `c78bc2cbe6ecc57b3dd7b480a6f71c4a2685f9bf27df1703876c2296278843b4` |
| `grounded-cross-paper-synthesis/v1` | validated summaries/evidence → `GroundedClaim/v2` | `grounded-cross-paper-synthesis/v1\|validated-summaries-and-evidence\|GroundedClaim/v2\|known-evidence-only,inference-marked` | `2ffc6262481d6e7dec357aa8c1faae7010043078c212e8afc63b4951f7041cc3` |
| `grounded-report-markdown/v1` | validated claims/citations → `ResearchReport/v2` | `grounded-report-markdown/v1\|validated-claims-and-citations\|ResearchReport/v2\|known-labels-only,required-disclosures` | `79fbeed6d303aa4a97032063f5f7708c09781e5b5a7e06fb2efd558e6ce0fc46` |
| `grounded-report-mechanical-repair/v1` | invalid output + normalized diagnostics → same schema | `grounded-report-mechanical-repair/v1\|invalid-output-and-diagnostics\|same-target-schema\|no-new-claims,no-new-citations` | `fc0f031941c4ef9607739874e91ff8c4a60431b537b72cc9b098fdd930eb15a7` |

## Common contract

Every prompt declares purpose, input/output schema versions, allowed source
fields, prohibited fields, source-only boundary, missing-information behavior,
citation allow list, inference rules, output language, and disclosure.

Allowed source data is enclosed in typed JSON data blocks after the system
instructions. Abstracts/titles/venue strings are untrusted data and cannot
override instructions. Prohibited input includes rank, citation count, Judge or
human labels, model knowledge, unapproved paper data, keys, paths, and other
users' data.

The model may emit only supplied paper/evidence/claim/citation identifiers.
Unknown identifiers fail validation. Short spans must be exact substrings;
missing content is `UNAVAILABLE`; source statements and system inference are
separate. The prompts prohibit method-quality, novelty, truth, and
systematic-review claims.

## Language

Proposed Class D default is an English report while preserving original paper
titles and citation labels. A non-English report language must be frozen in
`GroundedReportInput`; translation is model-generated and marked as such.
Alternatives are owner-selected language or source-language report. This choice
affects usefulness and fidelity and therefore blocks live acceptance until
approved; revisit after multilingual Fake and live acceptance.

## Combined-call V1

The first implementation may execute paper-summary and evidence-extraction
schemas in one structured operation per paper. Both prompt records/hashes,
output schemas, and validation results remain visible. It may not merge the
artifacts or omit either contract.

## Mechanical repair

At most one repair call is proposed. It receives only the invalid model output,
the same allow lists, and sanitized mechanical diagnostics. It cannot add a
claim, paper, citation, evidence span, or source fact. Semantic grounding
failures are not repairable by rewriting and require failure/human review.

Known risks include instruction injection in source text, schema-valid but
unsupported content, prompt sensitivity, citation drift, translation drift,
and provider refusal. Delimiters and schemas reduce but do not remove them.

