# Post-D1 R1A exact-input Local repair

Status: **PASS — R1A COMMITTED CONTRACT READY**

Date: 2026-08-20

Authority: the R1 section of
`.agent_read/progress/2026-08-20_post_d1_repair_program.md` and the narrowed
packet `.agent_read/progress/2026-08-20_post_d1_r1_change_packet.md`.

## Scope and closed ledger IDs

R1A changes only Local exact materialization/readiness behavior:

- `D1-INPUT-RECONCILE-01`
- `D1-INPUT-RUNNABLE-01`
- `D1-INPUT-RECEIPT-01`
- `D1-INPUT-REFRESH-01`

R1B browser/optional-evidence/zero-paper work and R1C package classification
remain deferred to separate clean commits. No frontend, API, database,
migration, Workflow, Capsule, Artifact schema, scientific output, or Owner D1
row changed.

## Root correction

`backend/project_workspaces/workspace_cli.py` now persists the current exact
Cloud materialization plan under ReAgent-owned Local control metadata. Readiness
requires every current plan entry, exact binding receipt, and target checksum/
size to agree. A stale prior receipt cannot independently make a Workflow
runnable.

Normal materialization reconciles the Artifact Index automatically and rechecks
the Cloud plan after publication. A concurrent Cloud change persists the newer
plan and returns a concurrency failure.

For A → B replacement, one valid old receipt and verified Artifact Index entry
must prove the path is the prior managed A. B is staged and validated before an
atomic replacement. A durable managed intent makes interruption between target
publication and receipt publication recoverable. The old receipt is preserved
in managed history. An exact but unowned pre-existing target still fails closed.

An unchanged sibling's exact receipt is reissued under the new aggregate plan
after full identity/byte verification, retaining its original materialization
time. Whole-plan completion identity remains authoritative.

## Verification evidence

| Evidence | Result |
|---|---|
| Focused Artifact handoff, public command, replacement, interruption, ambiguity, sibling, concurrency tests | **21 passed** |
| Local Workspace, Progress recovery, and all four D1 repaired-contract locks | **113 passed** |
| Combined Artifact service/API plus Local regression matrix | **130 passed** |
| Copied public Workspace CLI against a real loopback FastAPI server | **1 passed** |
| Forward downstream contract/publication/public Workspace historical regressions | **15 passed** |
| Targeted marked disposable PostgreSQL exact binding/project isolation/page query cases | **3 passed** |
| Python compileall for changed Python | **PASS** |
| `git diff --check` | **PASS** |
| Protected D1 Project read-only R0 fingerprint comparison | **MATCH**; Project, 8 Workflows, 6 Artifacts, Manifest, Bootstrap, and Project-Skill projections byte-identical; Progress differs only in volatile `cloud_observed_at` |

The broader PostgreSQL file has one pre-existing stale migration-head assertion
for 0030 while immutable authority is 0034; it was not changed in R1A. The
targeted R1A database cases passed and their marked database was dropped.

## Historical and safety result

- D1 Writing Real-provenance terminal recovery: preserved.
- Review optional-evidence publication: preserved.
- Revision causal-support subset semantics: preserved.
- Existing Revision Plan approval resume: preserved.
- no latest/highest/implicit binding selection added.
- ambiguous/user-owned targets remain untouched.
- scientific Artifact bytes remain Local authority.
- Alembic remains the unchanged sole head `20260819_0034`.
- protected D1 Project was not used as a fixture or mutated.

## New-defect prevention gate

All ten phase questions are **NO**. R1A adds no implicit merge/latest behavior,
Cloud byte authority, Skill capability authority, scientific rerun, manual Owner
step, immutable publication edit, regression-lock change, fixture weakening, or
additional primary UI prose.

Safe next action: begin R1B from a clean R1A commit and resolve its additive
zero-paper consumer authority gate before production writes.
