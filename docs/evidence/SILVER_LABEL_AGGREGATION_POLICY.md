# Silver-label Aggregation Policy

Policy ID: `reagent-silver-aggregation/v1`  
Status: Proposed; owner approval required  
Evidence class: all thresholds and routing rules are **Class D ReAgent project
policy**

## Immutable conceptual schemas

All schemas are canonical-JSON serializable, reject unknown fields, use UTC
timestamps, and are immutable after creation. IDs are opaque and checksums are
SHA-256 over canonical content excluding the object's own checksum.

### AutomatedJudgmentRequest

Schema: `automated-judgment-request/v1`

Required fields:

- `evaluation_id`, `topic_id`, `candidate_id`
- `topic_description`, optional `research_question`
- `inclusion_rubric`, `exclusion_rubric`
- `title`, optional `abstract_preview`, optional `publication_year`, optional
  `venue`
- `content_scope` (`TITLE_ONLY` or `TITLE_AND_ABSTRACT_PREVIEW`)
- `candidate_metadata_checksum`
- `rubric_version`, `prompt_version`, `schema_version`
- original/translation language and separate text checksums when applicable

Prohibited fields: OpenAlex/provider rank, deterministic rank score, citation
count, another judge's result, existing reviewer label, or adjudicated label.

### AutomatedJudgment

Schema: `automated-judgment/v1`

Required fields:

- `judgment_id`, `candidate_id`, `run_index`
- `judge_provider`, `judge_model`, `model_version_or_snapshot`,
  `adapter_version`
- `rubric_version`, `prompt_version`, `prompt_hash`
- `label`: `HIGHLY_RELEVANT`, `RELEVANT`, `PARTIALLY_RELEVANT`,
  `NOT_RELEVANT`, or `CANNOT_JUDGE`
- `confidence` in `[0,1]`
- `supporting_spans`: bounded preview excerpts with start/end offsets and source
  checksum
- `concise_reason`, `uncertainties`, `insufficient_information`
- `input_checksum`, `output_checksum`
- `token_usage` with input/output/total and completeness state
- optional `estimated_cost` with currency and price-snapshot identity
- `latency_ms`, optional `provider_request_id`, `created_at`, `schema_version`

`CANNOT_JUDGE` requires `insufficient_information=true`. Other labels require it
to be false. Missing provider usage is preserved as missing; it is never
converted to zero.

### JudgmentConsensus

Schema: `judgment-consensus/v1`

Required fields:

- `candidate_id`, ordered `source_judgment_ids`
- `label_distribution`
- `mean_confidence`, `median_confidence`
- `agreement_state`
- `evidence_present_state`
- `pairwise_consistency_state`
- `metadata_warning_state`
- `disposition`: `AUTO_ACCEPTED`, `AUTO_REJECTED`, or
  `NEEDS_HUMAN_REVIEW`
- `proposed_silver_label` when available
- `disposition_reason`
- `aggregation_policy_version`, `created_at`, `checksum`

### HumanAuditRequest

Schema: `human-audit-request/v1`

Required fields:

- `candidate_id`, optional `silver_label_proposal`
- `audit_reason`, one or more of:
  `LABEL_DISAGREEMENT`, `LOW_CONFIDENCE`, `CANNOT_JUDGE`,
  `MISSING_SUPPORTING_EVIDENCE`, `PAIRWISE_CONFLICT`, `NON_ENGLISH`,
  `RANDOM_CONSENSUS_AUDIT`, `METADATA_WARNING`
- `source_judgment_ids`
- `candidate_metadata_checksum`
- `human_audit_type` (`REQUIRED_EXCEPTION`, `RANDOM_CONSENSUS`, or
  `TOPIC_MINIMUM`)
- optional `random_sample_seed_version`
- `status` (`PENDING`, `IN_REVIEW`, `COMPLETED`, or `WITHDRAWN`)
- `created_at`, `schema_version`, `checksum`

### HumanAuditResult

Schema: `human-audit-result/v1`

Required fields:

- `candidate_id`, `human_reviewer_id`
- `final_audit_label` using the five relevance labels
- `agrees_with_silver_label` (`true`, `false`, or `null` where no proposal
  existed)
- `reason`, `audit_confidence`, `reviewed_at`
- `source_request_checksum`, `schema_version`, `checksum`

A human-audit result is an audited silver correction, not an expert-gold label.

## Required runs

Automated disposition requires completed pointwise A and B judgments with the
approved provider/model identity. A selected pairwise check must also be complete
in both candidate orders. Provider operations must be settled and usage present.

## Proposed disposition rules

### AUTO_ACCEPTED

All conditions must hold:

- A and B have the exact same label, and it is `HIGHLY_RELEVANT` or
  `RELEVANT`;
- each confidence is at least 0.80;
- at least one valid abstract-preview supporting span is present when preview
  information is available;
- no pairwise contradiction;
- no blocking metadata warning;
- no non-English/translation uncertainty under the initial policy.

The agreed label is the proposed raw silver label.

### AUTO_REJECTED

All conditions must hold:

- A and B both label `NOT_RELEVANT`;
- each confidence is at least 0.80;
- reason is present and a valid span is present where preview information is
  available;
- no pairwise contradiction;
- no blocking metadata warning;
- no non-English/translation uncertainty under the initial policy.

The raw silver label is `NOT_RELEVANT`.

### NEEDS_HUMAN_REVIEW

Route to audit for any:

- label disagreement;
- `PARTIALLY_RELEVANT`;
- `CANNOT_JUDGE`;
- confidence below 0.80;
- missing or invalid supporting evidence;
- pairwise conflict or one-order-only pairwise result;
- non-English or machine-translated uncertainty;
- blocking metadata warning;
- missing required run, usage, identity, or settled operation.

No majority vote manufactures a label from incomplete evidence.

## Pairwise consistency

The pairwise stage uses a deterministic selection of neighboring candidates from
the frozen candidate order, while hiding rank and citation data from the judge.
Each selected pair is submitted in both orders. A preference reversal, an
incompatible tie, or a comparison that contradicts a large pointwise category
gap produces `PAIRWISE_CONFLICT`. Pairwise output never directly assigns the
five-class label.

## Random and per-topic audit

- Sample 10% of high-confidence consensus items.
- Compute a stable sample key as
  `SHA256(evaluation_id || aggregation_policy_version || candidate_id ||
  "consensus-audit/v1")`; sort ascending and select the required count.
- Each topic with at least one consensus candidate contributes at least one
  randomly audited candidate.
- Each topic with candidates must have at least one completed audit, selecting a
  required exception first and a consensus item otherwise.
- A zero-candidate topic remains a coverage limitation; no audit candidate is
  fabricated.
- Pause for owner action if more than 20 of the current 40 candidates require
  audit.

These are proposed Class D rules, not measured sampling adequacy.

## Silver metrics

Report two immutable metric families:

1. **Raw silver metrics** use automated proposed labels only. Items with
   `NEEDS_HUMAN_REVIEW` and no proposal are unavailable, never coerced to
   non-relevant.
2. **Human-audited silver metrics** replace a raw proposal with the completed
   audit label where available and include required-review items only when a
   human audit supplies a label.

Names:

- Silver Precision@5
- Silver Precision@10
- Silver nDCG@10
- Silver Relevant-paper Yield
- Automated Judgment Agreement
- Human-audit Agreement
- Human Override Rate
- NEEDS_HUMAN_REVIEW Rate
- CANNOT_JUDGE Rate
- Non-English Uncertainty Rate

Every metric artifact records metric-family (`RAW_SILVER` or
`AUDITED_SILVER`), available/unavailable state, denominator, missing-label count,
rubric/prompt/model/policy versions, and whether any values were human-overridden.
Existing untouched reviewer packets and nonexistent expert-gold labels are
reported separately.

The existing relevance gain mapping may be reused only when explicitly labeled
Class D and versioned for silver metrics. No passing threshold is approved.

## Audit effects and reporting

- Human agreement leaves the audited-silver label unchanged and increments audit
  agreement.
- Human disagreement overrides only audited-silver metrics; raw-silver metrics
  remain reproducible.
- `Human-audit Agreement = exact agreements / audits with a silver proposal`.
- `Human Override Rate = disagreements / audits with a silver proposal`.
- Audit results never back-write automated judgment artifacts.
- Reports must state coverage, unavailable values, zero-candidate topics, model
  identity, and that no expert gold labels exist.

## Approval boundary

This document does not approve 0.80 confidence, 10% sampling, pair selection,
gain mapping, or any non-zero provider spend. All require owner approval through
ADR 0005.

