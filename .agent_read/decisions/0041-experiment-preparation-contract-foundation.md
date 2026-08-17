# 0041: Provider-neutral Experiment preparation contract foundation

- Status: Accepted
- Date: 2026-08-17

## Context

The default ReAgent Owner is a research-methodology expert who must not need
Python, Git, manifests, dependency files, checksums, or ResourceReference
knowledge. Historical Real Experiment 0.4 proves bounded execution of an exact
owner-staged package but does not prepare an implementation for that Owner.

## Decision

Keep Reproduction & Experiment as one top-level Workflow and preserve the
existing bounded runner. Future preparation paths—ReAgent-prepared, local
project, and historical exact external package—must converge on one validated
Experiment Package identified by local content checksums and a provider-neutral
prepared-package receipt. Git is optional supporting provenance and never the
executed-byte authority.

Methodology is a checksum-bound local contract. Scientific requirements are
frozen, implementation decisions may not change scientific meaning, and only
material unresolved methodology is returned to the Owner. Design approval
authorizes implementation preparation only; a separate one-use exact-plan
approval will authorize execution. Drift invalidates the relevant approval.

Reserve, without publication, Experiment 0.5 / Capsule 0.8 /
`experiment-record/v3` and the forward Writing/Review/Revision identities
ratified by the Owner. The v3 record is provider-neutral and separates process
outcome, evaluation validity, scientific evidence status, and limitations. Its
bounded presentation contract is exact-Artifact-bound and excludes source,
paths, credentials, repositories, diffs, logs, and package bytes.

## Consequences

EP-B may implement the constrained ReAgent-prepared path without a second
runner. EP-C may adapt a copied local project, including non-Git and dirty Git,
to the same package boundary. EP-D remains required for published downstream
consumers. EP-A itself publishes nothing and changes no runtime or persistence.

## Alternatives considered

Requiring GitHub for generated packages was rejected because it makes
programming/Git expertise a default prerequisite. A sixth Workflow and a
second runner were rejected because preparation is a stage of the existing
Experiment Workflow. Treating optional Git HEAD as executed-byte identity was
rejected because dirty and non-Git projects require exact content identity.
