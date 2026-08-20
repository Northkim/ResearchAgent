# Progress upload CONFLICT reconciliation (2026-08-21)

Status: **ROOT CAUSE CONFIRMED; repaired; owner recovery pending**

## 1. Exact CONFLICT meaning

The real KNN/Wine NORMAL upload failed with `stage = PROGRESS_REPORT_UPLOAD`,
`code = CONFLICT`. The server history for the Literature instance contains an
ACCEPTED stale IN_PROGRESS round-1 checkpoint report
(`prv2-109c0785…`, uploaded 2026-08-20T15:35 by the old checkpoint coordinator
via `reagent-workspace-progress-recovery/0.1.0` from
`.reagent/checkpoints/literature/progress/`). The real terminal COMPLETED
report (`prv2-15baa453…`) was therefore classified `BRANCHED_HISTORY`
("another accepted report already occupies this execution round") and rejected,
which the router maps to HTTP 409 `CONFLICT`
(`backend/api/routers/local_sessions.py` ->
`backend/progress_reports/service.py::upload` ->
`backend/progress_reports/chain.py::ProgressReportChainValidator`).

This is a genuine lifecycle defect: a stale non-terminal checkpoint permanently
occupied round 1 and blocked the round's terminal outcome.

## 2. Cloud state for the exact report

Read-only API inspection of the running backend confirmed:

- `prv2-15baa453…` exists in Cloud history as REJECTED
  (`validation_status REJECTED`, `chain_state BRANCHED_HISTORY`,
  `accepted_for_projection false`) with the exact local identity
  (project, workflow instance, package, workflow, round 1, checksums).
- Cloud's accepted history for the round is the stale IN_PROGRESS checkpoint.
- The Cloud projection currently reports IN_PROGRESS /
  SEARCH_PLAN_DECISION_REQUIRED (driven by the stale checkpoint), while the
  local completed report is authoritative for `workflow list` "Completed"
  (local-status-derived display, not Cloud acceptance).

CLOUD_REPORT_MATCH = DIFFERENT_REPORT (exact report is present only as a
REJECTED row; the accepted round occupant is a different stale checkpoint).

## 3. Repairs

- `backend/progress_reports/chain.py`: a terminal COMPLETED report supersedes a
  stale same-round IN_PROGRESS checkpoint of the exact same scope when the
  checkpoint has no accepted successor; a second COMPLETED report remains
  BRANCHED_HISTORY. Supersession emits a warning and keeps `VALID_CHAIN`.
- `backend/progress_reports/projection.py`: the round projection prefers the
  terminal COMPLETED report.
- `backend/progress_reports/service.py`: only ACCEPTED exact rows replay
  idempotently; a previously-REJECTED exact report is re-validated on retry so a
  later change of blocking conditions can admit it.
- `backend/project_workspaces/workspace_cli.py`: `_accepted_cloud_progress`
  keeps each round's terminal representative; `_recover_progress_backlog`
  re-uploads a local terminal report that supersedes a stale checkpoint and
  verifies the round representative after upload; the capsule upload path raises
  `PROGRESS_UPLOAD_CONFLICT` with accurate partial-success guidance instead of
  `INTERNAL_FAILURE`.

## 4. Regression tests

Chain supersession (stale checkpoint, competing COMPLETED still branches,
successor blocks supersession); service supersession + projection + idempotent
replay + previously-rejected re-validation; client round-representative
accepted history; stale-checkpoint recovery stores the exact workspace receipt;
incompatible COMPLETED conflict fails closed with PROGRESS_HISTORY_CONFLICT;
accurate error-message wording; capsule upload conflict mapping.

Focused: 95 passed (progress_reports + Literature + sync). Full backend:
1152 passed, 80 skipped, 1 deselected, 18 environment-only PostgreSQL setup
errors (REAGENT_TEST_DATABASE_URL absent; unrelated). Loopback e2e owner gate
passes.

## 5. Owner recovery

Deploy this commit and restart the backend, then rerun the SAME command:
`python reagent_local.py run . --workflow literature-search-local-experimental`.
It will NOT open Codex and will NOT rerun Provider/search; it re-uploads the
local terminal report, Cloud accepts it via supersession, the exact workspace
receipt is persisted, and the command reports PROGRESS_SYNCHRONIZED. The local
outputs, selections, OpenAlex results, report, and Artifact remain the source
of truth; KNN_RESEARCH_RERUN_REQUIRED = NO.
