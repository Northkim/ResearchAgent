# Literature lifecycle closure: supersession model, completion semantics, auto-continuation, readability (2026-08-21)

Status: **VERIFIED with repairs; real KNN recovery and downstream materialization
acceptance pending**

## 1. Same-round progress model

The authoritative model is **Model B**: multiple accepted observations may exist
for one execution round, with one canonical terminal representative. Evidence:
the `uploaded_progress_reports` table has no unique constraint on
(workflow_instance, execution_round) — only exact report identity is unique;
`build_projection` sorts by (round, completed_at, …) and takes the last; the
chain validator's original one-accepted-per-round check was the defect.
`42cd857`'s terminal-supersedes-stale-IN_PROGRESS direction is confirmed.

Consumers audited and aligned:

- `ProgressReportChainValidator` — terminal COMPLETED supersedes stale
  same-round IN_PROGRESS checkpoint with no accepted successor; a competing
  COMPLETED still branches.
- `ProgressReportService` — accepted exact rows replay idempotently;
  previously-REJECTED exact rows are re-validated under the exact supersession
  contract (same project/package/checksum/round), never converted arbitrarily;
  audit rows are immutable and both the rejection and acceptance remain in
  history.
- `projection.py` — prefers the terminal COMPLETED representative (timestamp +
  status tiebreak).
- `aggregation.py` (Cloud UI / history API) — `_report_activity_key` now prefers
  COMPLETED on timestamp ties; `instance_progress` picks the terminal
  representative while retaining both rows in history (`report_count` reflects
  observations).
- `workspace_cli._accepted_cloud_progress` — round-representative dedupe;
  `_recover_progress_backlog` re-uploads a local terminal that supersedes a
  stale checkpoint and verifies the round representative before persisting the
  exact workspace receipt.
- Artifact references / upload-only session authorization — per-report scoped,
  no round→one-row assumption.

## 2. Completion-state semantics

`workflow list` now uses the existing `PROGRESS_UPLOAD_PENDING` / `CONTINUE`
readiness for Literature when a local terminal report is not Cloud-acknowledged
(previously it advertised "Completed · Review Result" from local status alone).
The next command is the existing recovery command
(`python reagent_local.py run . --workflow literature-search-local-experimental`).
After recovery, readiness = ACKNOWLEDGED → `COMPLETED` / `REVIEW_RESULT`.

## 3. Upload-only recovery + CLI self-update

Recovery sequence proven from source:

1. Deploy/restart the backend with the fix.
2. `python reagent_local.py sync .` — `sync_workspace` → `_refresh_workspace_cli_copy`
   atomically replaces the root CLI from `/local-client/reagent_local.py` when
   the served bytes differ (fail-closed). `run` does NOT self-update.
3. `python reagent_local.py run . --workflow literature-search-local-experimental`
   — pre-run `_recover_progress_backlog` (0 Codex, 0 Provider) re-uploads the
   local terminal report, Cloud accepts it via supersession, the exact workspace
   receipt is persisted, and `_finalize_literature_upload_state` writes the
   Capsule receipt and moves round-control to UPLOADED; the command returns
   PROGRESS_SYNCHRONIZED.

## 4. Automatic post-search continuation

The historical `9db9d9e` instruction ("wait for the launcher to change it to
SEARCH_COMPLETED or FAILED") and the fake required the Owner to type
`continue`; real Codex interpreted "wait" as waiting for input. The root CLI now
appends an AUTOMATIC CONTINUATION directive: after PLAN_CONFIRMED the same
session must actively re-read `memory/round-control.json` until
SEARCH_COMPLETED/FAILED, automatically present candidate screening on
SEARCH_COMPLETED, and surface FAILED, with no Owner keystroke. The PTY driver no
longer feeds `continue`; the owner-gate e2e feeds only proceed+finish and
asserts the candidate checkpoint appears automatically.

## 5. Candidate-screening readability

The instruction now requires a concise default summary (retrieved/unique/
recommended/needs-review/excluded counts, top recommended evidence with
one-line reasons, needs-attention items, coverage gap) and default-hides
OpenAlex W IDs, checksums, provider IDs, source_query_ids, internal IDs, and the
full excluded table, expanding them only on request. Exact dispositions and
candidate-set checksum binding are unchanged (presentation only).

## 6. Tests

Chain supersession/branch/successor; service supersession + re-validation +
idempotent replay; aggregation terminal-representative tiebreak; client
round-representative + recovery + fail-closed; workflow-list pending-vs-completed;
`_finalize_literature_upload_state` capsule/Cloud convergence; outer CLI
PROGRESS_UPLOAD_CONFLICT renderer (no "No state was declared successful");
provider-failure surfaced without input; PTY owner gate (proceed+finish only,
auto candidate presentation, concise summary). Focused: 73 passed + e2e 3
passed. Full backend: 1158 passed, 80 skipped, 1 deselected, 18
environment-only PostgreSQL setup errors.
