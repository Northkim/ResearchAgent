# 0051: Forward Idea content precondition

- Status: Accepted
- Date: 2026-08-20

## Context

Literature may validly finalize a `selected-paper-library/v1` with zero selected
papers and an insufficient-evidence disposition. Historical Idea Discovery
accepted that Artifact by exact type/schema, but its Local runtime separately
required at least one selected paper. Cloud could therefore bind and
materialize an input that Local later rejected.

The producer Artifact must remain valid, and Cloud cannot inspect or become
authority for its complete Local bytes. The historical reviewed Idea
Definition/Capsule is immutable, so the consumer precondition cannot be added
in place.

## Decision

Publish forward Idea Definition 0.3 / Capsule 0.4 with one exact reviewed
content precondition: its `paper_library` must have a bounded qualification for
the same Artifact ID/checksum reporting at least one selected paper.

The Local Workspace derives that qualification deterministically from the
validated exact `selected-paper-library/v1` bytes and reports only the Artifact
identity/checksum, selected count, qualification checksum, and timestamp.
Qualification is immutable per Artifact and is neither presentation nor
scientific evidence. Complete Artifact bytes remain Local authority.

One shared evaluator applies the precondition to server candidate listing,
exact binding, Progress readiness, and materialization. Missing, stale, or
zero-paper qualification fails closed for forward Idea. Historical Idea 0.2 /
Capsule 0.3 retains its published type/schema-only behavior.

## Consequences

A valid zero-paper Literature result remains visible and selectable by consumers
whose contracts allow it, but cannot enter the forward Idea path. A one-paper
result is eligible only after its exact Local-derived qualification is reported.
Fresh Full Research Projects use the new explicit pins; existing Projects and
Workflow Instances are not upgraded.

This adds bounded Cloud metadata, one requirement field, and a forward
migration/publication. It does not add a generic predicate language, inspect
Artifact bytes in Cloud, permit auto-latest, or weaken exact identity.

## Alternatives considered

Invalidating all zero-paper Literature Artifacts was rejected because
insufficient evidence is a truthful producer outcome. Repeating the check only
inside the Local Idea runtime was rejected because it preserves the Cloud/Local
readiness split. Treating presentation as the qualification was rejected
because presentation is optional UI metadata. Editing Idea 0.2/Capsule 0.3 was
rejected as an immutable-publication violation.
