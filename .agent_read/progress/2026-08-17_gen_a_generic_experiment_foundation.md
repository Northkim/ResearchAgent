# GEN-A generic Experiment contract foundation

- Date: 2026-08-17
- Status: `PASS_GEN_A_READY_FOR_REVIEW`
- Evidence level: E2 automated contract/component evidence
- Verifier independence: `LIMITED`
- D1: `PAUSED`

## Plan alignment and scope

GEN-A implements only unpublished contract foundations for generic local
computational experiments. ReAgent Core owns lifecycle identity, approval,
Resource readiness, package/runtime compatibility, normalized status,
provenance, and finalization. Codex and exact reviewed Experiment Capabilities
own domain-specific methodology-to-implementation and evaluation semantics.

No Experiment 0.6 or Capsule 0.9 publication, migration, coordinator, execution
admission, runner, frontend, API, persistence, Path B implementation, network
behavior, dependency installation, scientific execution, or D1 state change was
made. ADR 0043 remains the accepted architecture authority; no new ADR was
needed.

## Contract foundation

- `reagent.experiment-research-objective-ref/v0.1` binds exact Artifact type,
  ID, checksum, and a bounded summary. The current forward production boundary
  accepts only `selected-research-idea/v1`.
- `reagent.experiment-methodology/v0.2` is domain-neutral and binds questions,
  materials, protocol, observations, evaluation criteria, reproducibility,
  Resource/compute constraints, network policy, assumptions, claim boundaries,
  unresolved material decisions, and an optional domain-methodology reference.
- `reagent.experiment-design-approval/v0.2` is checksum-bound, authorizes only
  preparation, rejects unresolved material decisions, and fails on methodology,
  evaluation, objective, or claim drift.
- `reagent.experiment-capability/v0.1` binds exact Skill, Capsule, optional
  implementation entrypoint, supported operations, and optional Capability-owned
  specification/evaluation/presentation schemas. Core has no closed scientific
  family enum and no mutable discovery registry.
- Capability assessment and `reagent.experiment-capability-selection/v0.1`
  preserve `SUPPORTED`, `UNSUPPORTED`, and `NEEDS_OWNER_DECISION`. Zero support
  fails explicitly; one supported Capability may auto-select; materially
  different alternatives require Owner confirmation; only explicitly
  fallback-equivalent alternatives use deterministic ordering.
- `reagent.experiment-implementation-specification-ref/v0.1` stores Capability,
  methodology, schema, validation-receipt, and specification checksums plus a
  bounded non-executable summary. Core never parses the scientific spec.
- `reagent.experiment-preparation-requirement/v0.1` is separate from execution
  runtime contracts. Runtime requirement/candidate/compatibility v0.1 contracts
  are language-neutral. Absolute launcher paths exist only in the local-private
  candidate; portable compatibility evidence contains checksums, not the path.
- Existing Workflow ResourceRequirement, ResourceReference, exact binding, and
  local verified-index semantics are referenced by a bounded Experiment bridge.
  No duplicate Resource taxonomy or readiness authority was created.
- Experiment package, prepared receipt, and validated package v0.2 accept zero,
  one, or multiple dependency declarations and a generic launch contract. They
  preserve traversal/link/special-file/case-collision rejection, exact lineage,
  independent validation, and Path A/future Path B convergence.
- `reagent.experiment-capability-evaluation/v0.1` carries exact output and plan
  lineage plus a Capability-owned result checksum and conservative validity.
  Core distinguishes process outcome, evaluation validity, scientific evidence
  status, and limitations.
- Safe presentation v0.2 primitives support bounded prose, scalars, tables,
  series, and checksum-bound figure/output references while rejecting HTML,
  code fences, local paths, credentials, logs, non-finite numbers, and excessive
  shapes/content.
- The unpublished `experiment-record/v4` foundation references only generic
  contracts and exact checksums. It imports no sklearn code and requires no ML,
  numeric metric, CV, robustness, dataset, or Python field.

## Resource boundary note

The existing Resource system is sufficient for the GEN-A requirement/reference
and readiness seam. It retains its current reviewed kinds and providers. GEN-A
does not introduce a production local-file provider; a future Capability that
needs a Resource outside the current taxonomy must use a separately reviewed
forward Resource extension rather than bypassing or duplicating this authority.

## Verification

- New focused GEN-A tests plus frozen 0.4/0.5/v2/v3 contract and publication
  tests: `83 passed`.
- A stale historical validated-package fixture was updated only to supply the
  already-required immutable 0.5 implementation-specification checksum; no
  production or Capsule byte changed.
- Python compile checks for all four new production modules: PASS.
- Alembic sole head: `20260817_0027`; no migration was added or run against an
  Owner database.
- Experiment 0.5 definition contract checksum remains
  `sha256:23b6e3cae5746c8589927d2380595df61d01c6fb3f487cf47e09753f3ef8b600`.
- Capsule 0.8 remains
  `capsule-5e02c832357355b6036b7e21cfbae306` with checksum
  `sha256:5e02c832357355b6036b7e21cfbae3061306b16268d04ee75c764c56c759bd98`.
- Non-ML genericity fixture: PASS using textual/categorical evidence and a
  non-sklearn runtime family.
- Diff whitespace and scope gates: PASS.

No real Experiment, scientific dependency, package, Project, Workspace,
Resource, Artifact, database state, network action, or D1 continuation occurred.
GEN-B, GEN-C, and GEN-D remain unauthorized and unstarted.
