# 0050: Explicit optional-input setup decision

- Status: Accepted
- Date: 2026-08-20

## Context

During D1, Review moved from required-input selection to Local preparation as
soon as its required manuscript was bound. Optional Research Idea evidence was
still unresolved, but the selection surface collapsed and later
materialization correctly made the active pass read-only. The Owner therefore
could not add useful optional evidence without recreating the pass.

Required-input completeness alone cannot prove that an Owner has deliberately
finished choosing optional evidence. Browser-local state also cannot be the
authority because the accepted exact bindings live in Cloud and must remain
stable across sessions.

## Decision

Before a Workflow with unresolved optional Artifact requirements may enter
materialization, ReAgent requires one durable Project/Workflow-scoped input
setup decision. The decision records the exact active binding-set checksum and
the exact sorted optional requirement keys deliberately omitted by the Owner.
It is idempotent and contains no Artifact bytes or presentation data.

The decision is current only while its exact binding set and unresolved
optional keys still match the Workflow. Any accepted binding change invalidates
the prior decision by identity, without rewriting its historical row. Required
input bindings remain exact and mandatory. The decision does not create a
binding, select an Artifact, infer latest, or turn presentation into evidence.

Owner-facing input setup stays open until the decision is current. The UI
renders accepted server bindings, not optimistic radio state, and offers an
explicit concise continuation action when optional evidence is intentionally
omitted.

## Consequences

Optional evidence can no longer disappear merely because required inputs are
complete. A later binding change requires a new exact setup decision before
materialization. Historical and already-progressed Workflows retain their
existing lifecycle projection; the gate applies to pre-materialization setup.

This adds one forward persistence table and one small API surface. It does not
change Workflow Definitions, Capsules, Artifact schemas, scientific validators,
or the read-only rule after materialization.

## Alternatives considered

Treating all optional requirements as implicitly omitted was rejected because
it reproduces the D1 evidence-loss path. Keeping the decision only in browser
state was rejected because it is not durable or authoritative. Allowing
optional bindings to mutate after materialization was rejected because that
would invalidate exact input provenance. Requiring a synthetic binding or a
placeholder Artifact was rejected because omission is a decision, not
scientific evidence.
