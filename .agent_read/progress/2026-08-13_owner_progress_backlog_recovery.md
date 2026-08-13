# Owner Progress backlog execution-round recovery

Date: 2026-08-13

The owner completed Idea Discovery locally through execution round 6 and
published the immutable selected-research-idea/v1 bytes, but Cloud had zero
Progress reports and no local receipts. The observed Capsule error was
`execution round must increment the latest round`.

Investigation rejected the proposed filesystem/hash ordering root cause. The
Idea runner's `_reports` function and standard Progress validation already sort
by `(execution_round, report_id)`. Instead, the real Harness followed AGENT.md
and finalized round 6 before exiting; the immutable Idea runner then called
`finalize` a second time against the same round. That duplicate finalization
failed before `_upload`, and the generic Workspace launcher had neither pending
backlog calculation nor upload-only recovery for Idea/scaffold Capsules.

The generic Workspace client now:

- validates each content-addressed v0.2 report, exact Package/Workflow identity,
  contiguous predecessor/context chain, and current output integrity;
- reads accepted Cloud Progress for the exact Workflow Instance;
- proves Cloud rounds are the exact local prefix;
- uploads only `Cloud latest + 1` onward, strictly by execution round;
- opens a fresh checksum-scoped UPLOAD_ONLY session for each report;
- re-reads Cloud acknowledgement before atomically storing a checksummed
  Workspace-level receipt;
- reconciles a Cloud-accepted report when receipt persistence was interrupted;
- returns `PROGRESS_SYNCHRONIZED` without starting the Harness when the local
  latest report is COMPLETED;
- reports `Progress Upload Pending / Continue` until exact acknowledgement is
  locally evidenced.

Gaps, same-round branches, foreign Workflow Instance history, Cloud/local
divergence and receipt conflicts fail closed. Literature's existing state
machine/resume adapter and immutable Capsule bytes are unchanged. The selected
Idea Artifact is byte-identical before and after recovery.

Qualification:

- focused owner route and backlog: 6 passed;
- broad Workspace/Workflow/Progress/Artifact/owner-runtime set: 313 passed;
- full backend on generated `reagent_qualification_<uuid>` PostgreSQL: 810
  passed, 14 existing skips; exact database dropped;
- controlled Playwright: 4 passed;
- frontend: 17 files / 34 tests, TypeScript, ESLint and production build passed;
- compileall, diff check, sole Alembic head and Alembic schema check passed.

No migration is required; sole head remains `20260811_0018`. No owner Project,
Workspace, research Artifact, owner database row, Provider, or credentials were
read or modified. Owner recovery requires a backend restart and replacement of
only the Workspace-root downloaded `reagent_local.py`; no sync, re-bootstrap,
Project recreation, Literature rerun or Idea rerun is required. The same
printed Idea command performs upload-only recovery.
