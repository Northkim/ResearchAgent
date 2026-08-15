# 0038: Real Writing evidence-bound initial draft

- Status: Accepted
- Date: 2026-08-15

## Context

Writing Scaffold proved transport and lifecycle mechanics but could not honestly
produce substantive manuscripts. W1 needs one Codex-performed initial-draft path
whose claims remain bounded to exact selected Idea, selected Literature, and an
optional valid Real Experiment Output. Historical `manuscript-draft/v1` and
Writing Definition 0.2 / Capsule 0.4 are published and immutable.

## Decision

Publish reviewed Writing Definition 0.3.0 and Capsule 0.5.0. Require exact
`selected-research-idea/v1` and `selected-paper-library/v1`; permit one optional
exact `experiment-record/v2`; produce `manuscript-draft/v2`.

Codex performs two bounded passes: Writing Brief/Evidence Map/Outline, then
substantive drafting and claim/citation checking. The local runner records exact
checksum-bound Outline approval between the passes and exact checksum-bound
Owner draft review before publication. Evidence status is exactly `SUPPORTED`,
`PLANNED`, or `UNAVAILABLE`. Literature citations may reference only members of
the bound selected library and preserve metadata/abstract scope. Observed result
claims require a bound successful, valid `experiment-record/v2`.

The descriptor is authority for exact materialized inputs and exact mutable
working files. Validators remain deterministic and fail closed on provenance,
membership, status, path, and lifecycle violations; they do not claim to judge
scientific quality or prose quality. Progress uses the existing exactly-once
adopt-or-finalize and Cloud Artifact promotion path.

## Consequences

Real Review can consume one exact evidence-traceable draft without reading
Writing private files. No-Experiment drafting remains useful but cannot invent
observed Results. The first slice deliberately excludes revision intelligence,
retrieval, a citation manager, hosted Writing, and frontend implementation.
Agent subprocesses disable Python bytecode emission so self-validation cannot
introduce undeclared Capsule files.

## Alternatives considered

Mutating `manuscript-draft/v1` or historical Writing publications was rejected
for immutability. Hosted deterministic prose generation was rejected because
Codex is the qualified research Harness. A claim graph, reference manager, and
general document platform were rejected as unnecessary for the narrow slice.
