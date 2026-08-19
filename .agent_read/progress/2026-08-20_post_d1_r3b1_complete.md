# Post-D1 R3B1 — truthful Generic Harness lifecycle adapter

## Status

`PASS_R3B1_GENERIC_HARNESS_ADAPTER`

This bounded checkpoint does not yet publish Experiment 0.8 / Capsule 0.11 or
advance the Full Research preset. It establishes the exact adapter required by
the approved R3 change packet before the public Local lifecycle is wired.

## Root cause addressed

The immutable v4/v5 Experiment lifecycle uses an `ExperimentCapability`
structural carrier, while the historical implementation descriptor accepts only
reviewed/reference/test classifications and the historical coordinator describes
every selected implementation as reviewed. Reusing either unchanged for the
Generic path would falsely classify the Agent Harness as a reviewed Capability.

## Implementation

- Added a forward-only `GENERIC_AGENT_HARNESS` lifecycle descriptor with explicit
  `reviewed_capability=false` and `user_skill_authority=false`.
- Added a bounded hybrid resolver and coordinator subclass. Exact reviewed support
  remains preferred; the Generic Harness is selected only when no reviewed
  Capability exactly supports the frozen methodology.
- Added a system adapter that validates exact Harness implementation
  specifications, prepares a checksummed local-project package, declares runtime
  requirements without installing dependencies, accepts only contract-validated
  exact evaluation evidence, and projects it into the existing v4/v5 carrier.
- The adapter uses the existing coordinator and bounded runner interfaces. It does
  not introduce another execution engine and does not use User Skills as
  implementation or evaluation authority.

## Evidence

- Generic Harness adapter/contracts/workspace: 10 passed.
- Historical Generic coordinator/publication/v5: 28 passed, 1 opt-in real-Codex
  case skipped.
- Python compileall and `git diff --check`: passed.

The test lifecycle reaches a validated local-project package, exact run approval,
bounded execution evidence, exact evaluation, Owner result review, v4 lifecycle,
and `experiment-record/v5`, while preserving the truthful Generic Harness
classification.

## Historical integrity

No historical 0.7/0.10 source module, Workflow/Capsule, Artifact schema,
migration, preset, API, frontend, or Owner D1 data changed.

## Safe next action

R3B2 may publish the forward 0.8/0.11 package and wire its deterministic public
runtime around this adapter. Publication must stop if exact source/database
equivalence or v5 provenance fails.
