# Post-D1 R3B3 — Generic Harness forward package compiler

## Status

`PASS_R3B3_FORWARD_PACKAGE_COMPILER`

The forward package is source-buildable but not yet published in database rows or
selected by the Full Research preset. This keeps the product gate closed until
the root launcher and Cloud approval path are qualified together.

## Implementation

- Added immutable source authority for Experiment 0.8 / Capsule 0.11 with the
  unchanged `experiment-record/v5` scientific output.
- The Workflow contract records exact-reviewed-first selection, the truthful
  `GENERIC_AGENT_HARNESS` fallback, no User Skill/scientific authority, the
  Workspace-managed execution namespace, and local-first execution-unit
  durability.
- Added Capsule-owned helpers for exact input/methodology parsing, implementation
  specification loading, independent validation receipt creation, bounded
  evaluation/evidence loading, v5 publication, and terminal Progress creation.
- Mutable implementation/runtime/output state remains outside Capsule package
  comparison under `.reagent/experiments/<workflow-instance-id>/`.
- The package compiler keeps the existing reviewed sklearn Capability as an exact
  fast path while making the Generic fallback separately classified.

## Evidence

- Forward publication/helper tests: 6 passed.
- A built package passes bundled pristine validation and archive validation.
- Historical Experiment 0.7 contract and Capsule checksums remain byte-exact.
- Helper tests prove methodology/specification/evaluation checksum validation
  without running scientific work.

## Migration / preset

No migration exists yet and no preset pin changed. Alembic remains 0037. The
protected Owner database and D1 Project remain untouched.

## Safe next action

R3B4 must wire the root Workspace launcher, natural methodology/run/result
decisions, controlled run-approval transport, execution resume, Artifact/Progress
upload, then add the schema-free publication migration and advance only new Full
Research Projects after qualification.
