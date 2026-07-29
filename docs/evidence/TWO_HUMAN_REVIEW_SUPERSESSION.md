# Two-human Review Supersession

Status: Proposed for owner approval  
Phase: 9B-2C-0

## Statement

The Phase 9B-2A two-human blind-review protocol is a higher-rigor method
deferred due to current project scope and reviewer availability. It is not
incorrect and is not erased.

For the current prototype only, ReAgent proposes to supersede full two-human
blind review of every candidate with:

> Automated silver-label relevance evaluation with targeted human audit.

## Why the prototype changes course

Full independent review requires two reviewers for all 40 reviewable candidates,
plus disagreement adjudication, training/calibration, and availability across
topics. The current project has no completed reviewer labels and no established
domain-expert panel. Requiring that process before any retrieval diagnostic is
disproportionate to a bounded architecture prototype.

The silver workflow reduces routine review by automating two versioned
pointwise assessments, routing all uncertainty/conflicts to a person, and
auditing a deterministic sample of consensus. It produces reproducible
engineering evidence sooner while keeping its epistemic status explicit.

## Rigor lost

- no two independent human judgments for every candidate;
- no expert qualification guarantee;
- no blind human-human agreement measure for the full pool;
- no formal adjudication into gold labels;
- model errors can be correlated and systematically biased;
- non-expert audit cannot validate nuanced domain inclusion criteria.

Accordingly, silver metrics cannot be reported as ground truth or a systematic-
review evaluation.

## Controls added

- immutable rubric, two prompt versions, input/output checksums, and exact
  provider/model/adapter identity;
- no rank, citation count, other label, or judge answer in pointwise input;
- required audit of disagreement, low confidence, `CANNOT_JUDGE`, missing
  evidence, pairwise conflict, non-English uncertainty, and metadata warnings;
- deterministic sample of high-confidence consensus and per-topic minimum;
- separate raw-silver and audited-silver metrics;
- audit agreement, override, uncertainty, and coverage reporting;
- fail-closed budgets, usage settlement, retention, and model-drift controls.

These controls improve auditability; they do not restore expert-gold rigor.

## Existing packets

The blank `reviewer_A` and `reviewer_B` packets are retained untouched as
provenance of the original protocol and as reusable inputs if expert-gold
evaluation is later funded. They are not imported, labeled, rewritten, deleted,
or treated as completed human review.

They remain under the existing private/ignored evaluation retention boundary
until owner-approved evaluation cleanup. This document does not authorize that
cleanup.

## When expert gold remains required

- publishable retrieval benchmark or claimed scientific comparison;
- systematic/scoping review inclusion decisions;
- production promotion whose risk warrants formal relevance validation;
- calibration of silver thresholds across topics/languages;
- material audit disagreement or systematic judge failure;
- claims about multilingual recall or domain-expert relevance;
- any statement using “gold,” “ground truth,” or equivalent rigor.

## Owner decision

The owner must choose whether expert-gold evaluation is **deferred** or
**cancelled**. Recommendation: defer it and retain packets until evaluation
cleanup or a funded expert-review milestone. This blocks implementation of the
silver workflow until ADR 0005 is approved, but it does not change current
candidate evidence.

