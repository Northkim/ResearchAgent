# Post-D1 R2 completion report

Status: **R2 COMPLETE — R3 NEXT**

Date: 2026-08-20

## Scope and ledger routing

R2 implemented the shared Local Owner-checkpoint, managed Harness, terminal
Progress recovery, and high-level continuation roots for forward Writing, Review,
and Writing Revision. It also published forward Literature and Idea packages whose
pre-finalization Owner decisions are exact durable Workspace state.

Closed for the implemented forward paths:

- `D1-LOCAL-ORCHESTRATION-01`
- `D1-HARNESS-TERMINATION-01`
- `D1-PROGRESS-SYNC-01`
- `D1-RESUME-DECISION-01`

Partially repaired but intentionally still open through R3:

- `D1-CHECKPOINT-PRESENTATION-01`
- `D1-APPROVAL-BRIDGE-01`

The remaining evidence for those two roots is the Generic Experiment methodology
and run/result decision lifecycle. R2 does not pre-empt the authorized R3
architecture.

## Exact source changes

Commit `f8754bb` adds a supported high-level Local `run` continuation that composes
Workspace sync, exact Artifact materialization/reconciliation, pending terminal
Progress recovery, current-phase evaluation, managed Codex phase execution, exact
natural Owner decisions, finalization, and upload. Writing, Review, and Revision
reuse their installed immutable runner-owned decision writers. `Approve`,
`Revise`, `Explain`, and `Abort` are human actions; exact checksums remain internal.
Normal completion returns control to the launcher and bounded cancellation avoids a
raw traceback.

Commit `68cc605` adds Literature 0.5 / Capsule 0.7 and Idea 0.4 / Capsule 0.5.
Their exact `memory/owner-decisions.json` snapshots bind dispositions/selections to
the candidate-set checksum and reject drift. New presets pin these versions;
historical instances and Artifact schemas are unchanged.

## Migration

`20260820_0037` is a schema-free forward publication migration. It inserts only the
two Definition versions, two Capsule versions, and the exact forward Idea input
requirement. Upgrade, Alembic drift check, downgrade to 0036, and re-upgrade passed
on marked disposable PostgreSQL databases. Source Foundation ensure is exact and
idempotent. The protected Owner database remains at its pre-program revision and
was not accessed.

## Qualification evidence

- Forward package decision durability: 2 focused tests passed.
- R2 coordinator, checkpoint, pending Progress, preset, sync, API, content
  precondition, and all four D1 repair locks: 109 passed; the macOS spawn-path lock
  test passed separately with explicit repository `PYTHONPATH`.
- Directly affected preset/catalog/API suites: 63 and 49-test focused passes during
  development.
- PostgreSQL publication/idempotency/reversibility: passed in isolated marked
  databases; adjacent 0035 and 0036 migration contracts each passed in their own
  disposable database. All qualification databases were dropped.
- Python compileall, `git diff --check`, Alembic drift check, and sole-head
  verification passed.

The combined execution of independent downgrade tests in one shared disposable
database was rejected by expected foreign-key/test-ID isolation. Running each
migration contract in its intended isolated database passed and changed no product
semantics.

## Historical and boundary evidence

The four D1 repaired contracts remain passing: Real Writing provenance/upload-only
recovery, Review optional evidence, Revision support-subset semantics, and existing
Revision Plan approval as a resume checkpoint. No implicit latest binding, Cloud
scientific-byte authority, User Skill capability authority, or science rerun for
sync was introduced.

## Commits and status

- R2 packet: `bd8eeef`
- R2A/R2B: `f8754bb`
- R2C: `68cc605`
- Repository was clean after each implementation commit.
- Alembic sole head: `20260820_0037`.
- Safe next phase: R3 Generic Experiment architecture packet and bounded
  implementation only.
