# Post-D1 R3B2 — deterministic Generic Harness pre-execution lifecycle

## Status

`PASS_R3B2_GENERIC_HARNESS_PRE_EXECUTION`

This checkpoint remains pre-publication. Experiment 0.8 / Capsule 0.11 and the
Full Research pin are not yet published or advanced.

## Implementation

- Generic package admission now requires the exact R3A validation receipt to
  match the frozen methodology/specification, implementation tree, and
  entrypoint checksum.
- Added deterministic lifecycle composition from exact objective, methodology,
  natural design approval, implementation specification, validation receipt,
  discovered existing runtime, promoted package, and execution plan.
- Durable contract snapshots are write-once-or-exact-match.
- Re-entry independently rebuilds and validates a candidate before reusing the
  managed promoted package. Drift fails closed; exact replay leaves no candidate
  debris and does not execute science.
- Added strict mapping reconstruction for the durable methodology, approval,
  implementation specification, and validation documents.

## Evidence

- Generic Harness adapter/lifecycle: 3 passed.
- The lifecycle test proves exact idempotent plan/package reconstruction and
  round-trip durable contract identity.
- No Provider call, package execution, dependency installation, Cloud mutation,
  or Owner D1 access occurred.

## Safe next action

R3B3 may add the forward public Capsule/runtime and schema-free publication
migration, then qualify source/database identity before advancing the preset.
