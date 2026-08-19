# 0053: Publish forward upstream Owner decision durability

- Status: Accepted
- Date: 2026-08-20

## Context

The real D1 journey proved that a resumed Literature session could preserve files
while losing an Owner screening disposition. Accepted Literature 0.4 / Capsule
0.6 and Idea 0.3 / Capsule 0.4 do not declare exact pre-finalization Owner
decisions as durable package state. Their immutable bytes cannot be changed.

## Decision

Publish forward Literature Definition 0.5 / Capsule 0.7 and Idea Definition 0.4
/ Capsule 0.5. Each declares mutable `memory/owner-decisions.json` state bound to
the exact candidate-set checksum. Literature preserves every candidate's
`SELECTED`, `UNCERTAIN`, or `EXCLUDED` disposition. Idea preserves the exact
selected idea identity. Validators reject candidate drift and final outputs that
disagree with the durable decision.

New Projects use these forward pins. Historical Workflow Instances remain pinned
to their existing immutable publications. The selected-paper-library/v1 and
selected-research-idea/v1 Artifact contracts do not change.

## Consequences

A new Harness session can restore exact upstream Owner decisions from Workspace
state before inference instead of reconstructing them from conversation. Migration
`20260820_0037` publishes only the new immutable rows and Idea requirement; it adds
no mutable research schema and does not update existing Projects. The protected
Owner D1 database is not upgraded by this repair program phase.

## Alternatives considered

- Editing the accepted Capsules was rejected because published package bytes are
  immutable.
- Treating chat history or final output labels as the decision authority was
  rejected because session state is disposable and loses uncertainty semantics.
- Changing the scientific Artifact schemas was rejected because exact local
  Workflow memory is sufficient and downstream scientific contracts are unchanged.
