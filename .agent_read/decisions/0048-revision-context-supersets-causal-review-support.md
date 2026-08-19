# 0048: Revision context may be a strict superset of causal Review support

- Status: Accepted
- Date: 2026-08-19

## Context

Review supporting evidence is explicitly optional. A valid Review may audit a
manuscript with Literature while recording its Research Idea evidence as unavailable
and not independently verifiable. The parent manuscript must still retain that exact
Research Idea provenance, and Writing Revision must inherit the parent manuscript's
context. Immutable Writing Revision 0.6 / Capsule 0.8 incorrectly required those two
sets to be equal.

## Decision

Writing Revision validation distinguishes inherited parent-manuscript context from
causal Review support. The causal Review source manuscript must exactly match the
Revision prior manuscript. Every Artifact actually bound and used by Review must be
present in Revision under the same role, Artifact ID, and checksum. Revision may also
contain exact parent-manuscript sources that Review omitted; those sources remain
context and provenance, not Review-verified evidence. Review issues may cite only the
manuscript and actual Review support.

The incompatible Capsule startup semantics are published additively as Writing
Revision 0.7 / Capsule 0.9. Historical 0.6 / 0.8 remains immutable. The output schema
remains `manuscript-draft/v5` and its contextual Cloud validator applies the same
strict subset and identity rules.

## Consequences

Limited-scope Reviews remain genuinely valid causal inputs to Revision without
dropping manuscript provenance or binding unavailable evidence into Review. Same-role
identity conflicts, missing required lineage, and issue evidence outside the Review
scope still fail closed. Existing 0.6 instances remain historical; a blocked instance
must be retired and recreated through the supported exact Review action to receive
the new Capsule.

## Alternatives considered

Mutating Capsule 0.8 or migration 0032 was rejected as an immutable-publication
violation. Binding omitted evidence into Review was rejected because it would falsify
Review scope. Dropping inherited manuscript sources was rejected because it would
break exact provenance. A global relaxation of Artifact binding was rejected because
only the causal Review support/context relationship is changing.
