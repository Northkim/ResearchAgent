# 0039: Real Review structured evidence audit

- Status: Accepted
- Date: 2026-08-15

## Context

Historical Review Scaffold proved lifecycle mechanics but produced only a
`review-report/v1` scaffold. R1 needs one substantive Codex-performed Review
whose output can be consumed deterministically by W2. The authority must remain
the exact `manuscript-draft/v2` plus explicitly bound evidence Artifacts; Review
cannot read sibling Workflow private files or turn free-form reviewer prose into
an implicit revision contract.

## Decision

Publish reviewed Review Definition 0.3.0 and Capsule 0.5.0, preserving historical
Review 0.2/0.4 and `review-report/v1`. Require one exact `manuscript-draft/v2` and
permit exact supporting Idea, Literature, and Experiment v2 bindings only when
they match manuscript lineage. Produce immutable `review-report/v2`.

Codex performs two bounded passes: exact Review Scope, then claim/evidence,
method/result, citation, and reproducibility audit. The local runner records an
exact checksum-bound Scope approval between the passes and exact checksum-bound
Owner review before publication. Evidence availability is AVAILABLE,
UNAVAILABLE, or SCOPE_LIMITED. Structured issues use bounded categories,
MAJOR/MINOR revision priority, exact section/claim targets, exact evidence
references, recommended action, and a blocking flag. Overall assessment is only
NO_BLOCKING_ISSUES, REVISION_REQUIRED, or INSUFFICIENT_EVIDENCE.

Validators fail closed on source lineage, evidence membership, issue targets,
assessment consistency, provenance, prohibited publication-decision semantics,
Capsule paths, and exactly-once finalization. They do not claim to judge
scientific correctness. Progress and Cloud Artifact projection reuse the
existing adopt-or-finalize path.

## Consequences

W2 receives a stable typed revision contract rather than free-form reviewer
comments. Missing or scope-limited evidence remains explicit, and a clean bounded
assessment is not publication acceptance. R1 deliberately excludes issue
resolution, response-to-reviewer, novelty/venue judgment, scoring, retrieval,
hosted Review, and frontend implementation.

## Alternatives considered

Mutating `review-report/v1` or historical Review publications was rejected for
immutability. A free-form review document was rejected because Writing could not
consume it reliably. A large peer-review ontology, numeric score, acceptance
prediction, hosted reviewer, and automatic external evidence retrieval were
rejected as outside the narrow evidence-audit boundary.
