# 0032: Full Research preset and derived readiness

- Status: Accepted
- Date: 2026-08-09

## Context

Five production Workflow types now exist, but users need one understandable
Project setup and consistent guidance without introducing a linear execution
engine or exposing Manifest and Artifact identities as the primary UX.

## Decision

Define stable server-side setup keys `literature-only`,
`literature-and-idea`, `full-research`, and `custom`. Project creation resolves
Registry authority and creates all selected ordinary Workflow Instances plus
revision-1 Desired Manifest in the existing transaction. Presets are not
persisted entities.

Derive per-Instance readiness and next action from Desired state, installation
acknowledgement, immutable version requirements, compatible Artifact metadata,
exact active bindings, and Progress. Do not persist readiness and do not claim
that Cloud knows local materialization. Multiple same-definition Instances use
friendly ordinal labels; Review recommends a new, explicitly bound Writing
round.

## Consequences

Legacy omitted setup remains Literature-only, Full setup is all-or-nothing,
Custom remains Registry-validated, and existing Projects are unchanged.
Readiness is distinct from research status and core maturity. No pipeline
table, automatic binding, latest selection, browser-local write, or automatic
execution is introduced.

## Alternatives considered

- Frontend mutation chaining was rejected because it leaves partial Projects.
- Pipeline persistence was rejected because the approved flow is non-linear.
- Client-derived dependency logic was rejected as a second business authority.
- Cloud materialization receipts were rejected because local bytes remain local
  truth.
