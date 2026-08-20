# 0054: Explicit Literature composition

- Status: Accepted
- Date: 2026-08-20

## Context

Research may require several Literature rounds, while every downstream ReAgent
input must remain one explicitly selected immutable Artifact. The current
binding model intentionally permits one active exact Artifact per requirement;
changing it to accept an unordered collection would weaken R1 readiness and
materialization semantics. Implicit latest selection or Project-wide merging
would also remove Owner authority and obscure provenance.

The forward Literature package additionally needed to turn a research direction
and optional domain keywords into bounded direct, supporting, contextual, and
background query families. Historical Literature publications and
`selected-paper-library/v1` are immutable.

## Decision

Publish Literature Search Definition 0.6 / Capsule 0.8 with an Owner-reviewed,
bounded query-family strategy. Skills may guide the Harness, but exact provider
records, Owner decisions, and validators remain scientific authority.

Publish a separate Literature Consolidation Definition 0.1 / Capsule 0.1. It
requires exactly two explicitly selected `selected-paper-library/v1` Artifacts,
materializes them locally, deterministically removes only exact provider/DOI/
OpenAlex duplicates, obtains exact Owner dispositions, and publishes one new
`selected-paper-library/v1`. The two source bindings and Local provenance remain
exact. A consolidated result may be used as one exact source in a later
consolidation.

New Full Research Projects advance their initial Literature pin to 0.6/0.8 but
still contain exactly five initial Workflows. Literature Consolidation is an
available reviewed Workflow and is never inserted automatically.

Keep `selected-paper-library/v1` unchanged. The existing durable Owner-decision
snapshot preserves `UNCERTAIN` versus `EXCLUDED`; the v1 transport's shared
withheld container does not erase that authoritative decision state.

## Consequences

- Iterative evidence composition is explicit and content-addressed; no consumer
  needs multi-binding, latest selection, or Cloud access to full Artifact bytes.
- Source order is deterministic (base then additional) and the combined set
  remains bounded to fifteen candidates.
- Existing Projects and historical Literature/Capsule bytes remain unchanged.
- Migration `20260820_0039` is schema-free and publishes only new immutable rows.
- The generic exact-input UI can present both source requirements without a new
  frontend architecture.
- Composition requires an additional intentional Workflow rather than silently
  changing an existing downstream binding.

## Alternatives considered

- Multiple active Artifacts under one requirement: rejected because it changes
  exact binding and materialization cardinality globally.
- Implicit latest or automatic union: rejected because it removes Owner choice
  and exact causal lineage.
- Cloud-side merge: rejected because complete Artifact bytes remain Local.
- A new paper-library schema: rejected because existing v1 plus exact Workflow
  lineage and durable Owner decisions preserve the required semantics.
