# Post-D1 R3B4 — Generic Harness public lifecycle

## Status

`R3B4 = PASS`

R3 itself remains open pending R3C browser entry/checkpoint qualification and
R3D controlled end-to-end evidence.

## Ledger scope

- `D1-EXPERIMENT-CAPABILITY-01`
- `D1-EXPERIMENT-INGEST-01`
- `D1-EXPERIMENT-OPERATOR-01`
- `D1-EXPERIMENT-ENV-01`
- `D1-EXPERIMENT-DURABILITY-01`
- Experiment portions of `D1-CHECKPOINT-PRESENTATION-01` and
  `D1-APPROVAL-BRIDGE-01`

`D1-EXPERIMENT-ENTRY-01` remains assigned to R3C.

## Exact source changes

- Added the high-level Workspace Generic Harness workflow coordinator.
- Added forward immutable source authority for Experiment 0.8 / Capsule 0.11.
- Added schema-free migration `20260820_0038` and source/database equivalence.
- Advanced only the new-Project Full Research Experiment pin to 0.8/0.11.
- Reused the existing exact Research Idea requirement, one-use controlled-local
  run approval, no-egress bounded runner, `experiment-record/v5`, Progress
  upload, and Artifact presentation persistence.
- Added deterministic bounded Experiment v5 presentation projection.
- Classified execution-unit interruption as durable/resumable rather than
  `LOCAL_PROGRESS_INVALID`.

No historical migration, Definition, Capsule, Artifact schema, presentation
schema, scientific result, or protected Owner row changed.

## Publication identities

- Definition: `reproduction-experiment-local-experimental` `0.8.0`
- Contract checksum:
  `sha256:16aeb60bd42a982c3e52ee4210fe7e51b5eaf8a103504e6d0e573c38be6818b8`
- Capsule: `capsule-aaf4d527b1aa60eed6b4bdad47da9826` `0.11.0`
- Capsule checksum:
  `sha256:aaf4d527b1aa60eed6b4bdad47da982669865c1be71d95ab80ba2dc5c9232ec1`
- Output remains `experiment-record/v5`.
- Alembic sole head: `20260820_0038`.

## Qualification evidence

- Generic Harness contracts/workspace/adapter/publication/lifecycle and preset
  focused suite: 44 non-loopback tests passed.
- Exact v5 presentation projection passed the existing v0.2 server validator.
- Two copied public-Workspace loopback tests passed outside the restricted
  sandbox.
- Frontend TypeScript and source-scoped ESLint passed; the production Next.js
  build passed outside the restricted sandbox (Turbopack requires an ephemeral
  loopback worker).
- Python compileall, `git diff --check`, and Alembic sole-head verification
  passed.
- Marked disposable PostgreSQL:
  - 0038 publication/source equivalence and upgrade/downgrade/re-upgrade: 2 passed;
  - durable Owner-decision migration lock: 1 passed;
  - optional-input decision migration lock: 2 passed;
  - zero-paper consumer-precondition lock: 2 passed.
- Every disposable database was identity-verified and dropped.

The PostgreSQL files were intentionally run in separate disposable databases:
their downgrade tests require no Project rows. Combining them in one shared DB
correctly fails on immutable Project→Capsule foreign keys and is not a product
failure.

## Historical integrity

- Experiment 0.7 / Capsule 0.10 exact checksum remains unchanged.
- Review optional-evidence and Revision subset semantics remain unchanged.
- User-managed Skills remain outside Capability/scientific authority.
- No real provider or uncontrolled research was used.
- Protected D1 Owner database and Project were not accessed.

## New findings

None classified as a new product defect in this subphase. Browser and complete
controlled-chain evidence remain required before R3 can close.

## Safe next action

Commit the already-focused R3C exact-input browser entry separately, then run
R3D with a deterministic fake Harness and disposable PostgreSQL/Workspace.
