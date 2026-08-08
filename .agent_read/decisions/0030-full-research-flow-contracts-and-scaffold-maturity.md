# 0030: Full Research Flow contracts and scaffold maturity

- Status: Accepted
- Date: 2026-08-07

## Context

Literature Search and Idea Discovery already prove one real typed Artifact
handoff. Later product phases need stable contracts for selecting one research
idea and for composing Writing, Review, and Experiment without prematurely
claiming those research cores exist. A placeholder flow must remain visibly
and mechanically distinct from reviewed scientific capability.

## Decision

Publish Idea Discovery Definition/Capsule 0.2.0 as a new immutable reviewed
version. It may complete only after the user explicitly selects exactly one
validated candidate and local finalization publishes a content-addressed
`selected-research-idea/v1` through the existing Progress-to-Artifact path.
Idea 0.1.0 and every Literature Capsule remain unchanged; existing instances
never upgrade automatically.

Make `core_capability_maturity` canonical on every immutable Workflow
Definition Version with exactly `REVIEWED_CORE` or `SCAFFOLD_CORE`. Lifecycle,
review status, and maturity remain separate. Artifact schema maturity must
match the producer Version; an immutable reviewed finalizer, not a client
claim, supplies the selected-idea maturity.

Freeze code-level JSON contracts for `manuscript-draft/v1`,
`review-report/v1`, and `experiment-record/v1`, plus the future exact
dependency map. These contracts do not create production Workflow records.
Writing revisions bind a specific review and prior manuscript. Scaffold
experiment records must use `PLACEHOLDER_NOT_EXECUTED` with null results.

All handoffs retain same-Project, explicit Artifact-ID-and-checksum selection,
verified copy materialization, immutable content-addressed outputs and no
automatic latest resolution.

## Consequences

The complete research-flow boundary can be tested before downstream research
cores exist, without confusing Product/Registry availability with a schema
contract. Future F1B scaffold versions must declare `SCAFFOLD_CORE`, and any
replacement by a reviewed core requires new immutable Definition/Capsule
versions. Cloud preserves metadata/provenance but not local Artifact bytes.

The production Registry after F1A still contains only Literature Search and
Idea Discovery. No Writing, Review, Experiment, preset, UI card, Prompt, Skill
Registry, Resource Registry, or external resolver is authorized by this ADR.

## Alternatives considered

- Adding future Workflow Registry rows now was rejected because it would make
  unavailable research cores appear production-ready.
- Encoding maturity only in UI labels or arbitrary Artifact payloads was
  rejected because either can drift from immutable producer provenance.
- Editing Idea Discovery 0.1.0 in place was rejected because it would break
  checksum-bound Capsule identity and existing Project reproducibility.
- A mutable manuscript file loop or automatic latest review was rejected in
  favor of explicit immutable Draft A -> Review A -> Draft B references.
- Multi-file bundles were deferred; current B6 production handoff remains one
  self-contained JSON file per canonical Artifact.
