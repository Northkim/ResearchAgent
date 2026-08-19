# Post-D1 R3D — Controlled Generic Harness closure

## Status

`R3 = PASS`

Product/qualification commit: `b3ca13d`

The consolidated repair program remains open at R4. This report closes only the
Generic Experiment phase.

## Ledger findings closed

- `D1-CHECKPOINT-PRESENTATION-01`
- `D1-APPROVAL-BRIDGE-01`
- `D1-EXPERIMENT-DURABILITY-01`
- `D1-EXPERIMENT-ENTRY-01`
- `D1-EXPERIMENT-CAPABILITY-01`
- `D1-EXPERIMENT-INGEST-01`
- `D1-EXPERIMENT-OPERATOR-01`
- `D1-EXPERIMENT-ENV-01`

The original D1 occurrences remain in the authoritative ledger with status
`FOUND_AND_REPAIRED_POST_D1`.

## Exact closure changes

- Extended the existing exact one-use controlled-local Run Approval contract to
  forward Experiment 0.8 without creating a second approval system.
- Canonicalized relative public Workspace paths before constructing the managed
  `.reagent/experiments/<workflow-instance-id>/` namespace.
- Finalized terminal Generic Harness Progress with the exact dynamic
  `experiment-record/v5` declaration inside immutable report metadata. Removed
  the temporary unsafe uploader bypass that attempted to infer an undeclared
  output after report finalization.
- Allowed only the exact declared `memory/progress/report-draft.json` runtime
  path; undeclared sibling files remain rejected.
- Made completed Experiment evidence override a still-observable historical run
  approval on the Owner detail page. The terminal page has no active Local run
  command and renders the bounded scientific status and limitation.
- Added one real-application controlled driver and one repository-native browser
  test covering exact Idea binding, natural methodology decision, browser run
  approval, controlled interruption/resume, exact v5 admission, presentation,
  terminal replay, and exact Writing consumption.

## Publication and migration impact

R3D added no migration and changed no publication bytes. It qualifies the
already-forward-additive Experiment 0.8 / Capsule 0.11 publication from R3B4.
Historical Experiment 0.7 / Capsule 0.10 remains unchanged. Alembic sole head is
`20260820_0038`.

## Qualification evidence

- Repository-native real FastAPI/Next.js/system-Chrome journey: **1 passed**.
- Generic Harness, exact approval, v5, and four repaired-D1 lock suite:
  **100 passed** in the restricted run, plus the one required real-loopback case
  **passed** separately.
- Full Workspace CLI regression file: **19 passed**.
- Experiment detail/component suite: **25 passed**.
- Marked disposable PostgreSQL publication, downgrade/re-upgrade, exact approval
  persistence, and preset gate: **16 passed**.
- TypeScript: passed.
- Source-scoped ESLint: passed.
- Python compileall: passed.
- Production Next.js build: passed.
- `git diff --check`: passed.
- Alembic sole head: `20260820_0038`.

All qualification databases were identity-verified and dropped. No real external
provider or uncontrolled research was used.

## Controlled journey invariants

- Exactly one accepted Research Idea was bound; no presentation substituted for
  the binding.
- No matching reviewed Capability was required. The record truthfully identifies
  the system Generic Harness and does not claim `REVIEWED` authority.
- No dependency was installed, upgraded, or downloaded.
- One completed execution unit retained its exact checksum and attempt count
  across interruption; only the pending unit ran on resume.
- Exactly one `experiment-record/v5` and one terminal Progress report were
  accepted; replay created no duplicate.
- The bounded v0.2 presentation was generated from exact local Artifact bytes and
  remained non-authoritative.
- Initial Writing materialized Literature, Idea, and the exact Generic Harness v5
  as three exact inputs.

## Screenshot evidence

- `.agent_read/tmp/r3d-generic-harness/01-exact-run-approval.png`
- `.agent_read/tmp/r3d-generic-harness/02-run-approved.png`
- `.agent_read/tmp/r3d-generic-harness/03-completed-generic-experiment.png`
- `.agent_read/tmp/r3d-generic-harness/04-v5-output.png`

The screenshots use controlled fixture data. Visual inspection confirmed the
System-path trust wording, evidence-before-run approval, terminal result priority,
and hidden technical details. Existing R6 presentation debt (Outputs density and
raw enum typography) remains assigned to R6 and was not expanded into R3.

## Direct stale-test adjustment

`test_controlled_local_run_approval_postgresql.py` historically left its shared
qualification database at migration 0030 after testing the approval table. It now
restores `head` in `finally`, so the following project-creation test runs against
the repository's actual publication state. No product behavior or migration byte
was changed.

## Historical and protected-state integrity

- All four repaired-D1 contract locks passed.
- Review optional evidence and Revision subset semantics are unchanged.
- User-managed Skills retain no Capability or evaluation authority.
- Presentation remains optional UI metadata.
- The protected Owner database and D1 Project were not accessed or mutated.

## New-defect prevention gate

1. Exact scientific boundary weakened: **NO**.
2. Implicit latest/merge introduced: **NO**.
3. Cloud made authoritative for complete Local bytes: **NO**.
4. User Skill gained Capability/evaluation authority: **NO**.
5. Completed Workflow must rerun science to synchronize: **NO**.
6. New manual Owner orchestration step introduced: **NO**.
7. Immutable publication changed in place: **NO**.
8. Repaired D1 contract altered: **NO**.
9. Fixture changed to avoid production semantics: **NO**.
10. UI made more verbose: **NO**; terminal stale-run content was removed.

## Safe next action

Begin R4 source-of-truth recovery and a bounded scientific-semantics change
packet. Do not begin R5 or R6 work while R4 is active.
