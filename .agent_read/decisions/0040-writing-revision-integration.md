# 0040: Review-to-Writing revision integration

- Status: Accepted
- Date: 2026-08-15

## Context

W1 publishes evidence-bound `manuscript-draft/v2`; R1 publishes a typed
`review-report/v2` whose issues are intended for deterministic downstream
consumption. W2 must close one revision loop without treating reviewer requests
as evidence, claiming that Writing resolved Review issues, reading sibling
private files, or mutating either accepted Artifact contract.

## Decision

Publish reviewed Writing Definition 0.4.0 and Capsule 0.6.0 with immutable
`manuscript-draft/v3`. Require one exact v2 prior manuscript, its exact causal v2
Review, and the exact Idea/Literature plus optional Experiment evidence already
carried by the Draft. The Review must identify the same prior Draft by Artifact
ID and checksum. No auto-latest or implicit evidence acquisition is permitted.

Codex performs two bounded passes. First it accounts for every causal Review
issue exactly once and proposes a checksum-bound Revision Plan. After exact Owner
approval it revises only within that plan, rechecks the W1 claim/citation truth
contract, records ADDRESSED, PARTIALLY_ADDRESSED, or NOT_ADDRESSED for each issue,
and waits for exact final Owner review. Partial and unaddressed dispositions
retain a limitation. Remaining blocking issue IDs remain explicit even when the
revision Workflow completes.

The v3 Artifact binds prior Draft, causal Review, exact supporting evidence,
approved plan, issue accounting, remaining blockers, revised evidence-bound
manuscript, Capsule identity, and final Owner review. Progress and Cloud Artifact
projection reuse the existing adopt-or-finalize public Workspace path.

## Consequences

Review-to-Writing is a reliable structured revision contract rather than a
free-text handoff. W2 completion means one approved revision pass completed; it
does not mean Review issues are scientifically resolved. Historical Writing
Capsules, manuscript-draft/v1/v2, review-report/v1/v2, and all E1/R1 evidence
remain immutable.

## Alternatives considered

Mutating v2, auto-selecting latest Review, letting the Owner override a causal
mismatch, treating all issues as resolved, or acquiring evidence during revision
were rejected. Multi-round revision, response-to-reviewer, new Literature or
Experiment work, hosted revision, and frontend implementation remain deferred.
