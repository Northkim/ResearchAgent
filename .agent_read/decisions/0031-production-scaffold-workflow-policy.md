# 0031: Production scaffold Workflow policy

- Status: Accepted
- Date: 2026-08-09

## Context

The five-Workflow product skeleton must exercise real Registry, local state,
dependency, Artifact and Progress boundaries before Writing, Review or
Experiment has an owner-reviewed research core. Product availability must not
be mistaken for scientific capability.

## Decision

Publish Writing, Review, and Reproduction & Experiment Definition/Capsule
0.1.0 as `AVAILABLE`, creatable production Workflows with canonical
`SCAFFOLD_CORE` maturity. Their flow, persistence and provenance are real, but
all human and canonical outputs are deterministically marked placeholders.
Writing cannot create substantive manuscript content, Review returns only
`INSUFFICIENT_EVIDENCE`, and Experiment supports only an unexecuted
`IDEA_EXPERIMENT` skeleton with null actual results.

Use the existing generic Workspace CLI, B4 sync/Installed Lock, B6 exact
binding/materialization and B5 Progress path. Writing revision rounds use a
new Writing Instance and explicit Draft A/Review A inputs; no latest selection
or mutable Artifact replacement is introduced. Maturity is derived from the
immutable producer Workflow Version in API, Progress and frontend projections.

Any reviewed research core requires a new immutable Definition/Capsule
version. Version 0.1.0 checksums and behavior cannot be changed in place.

## Consequences

The production Registry contains five Workflow types while clearly separating
two reviewed cores from three scaffold cores. Full-flow composition, security,
restart and provenance can be qualified without fabricated scientific output.
The Full Research Flow preset, complete setup UX, Skill platform, Resource
platform, paper reproduction and real experiment execution remain deferred.

## Alternatives considered

- Keeping the Workflows contract-only would not exercise the product body.
- Frontend-only cards were rejected because they would not prove state,
  installation, execution, Artifact or Progress boundaries.
- Letting a model draft plausible scientific content was rejected because a
  scaffold must never resemble evidence or a research conclusion.
- Updating one Writing Instance binding in place was not required; a new
  Instance preserves immutable round provenance without expanding B6 schema.
