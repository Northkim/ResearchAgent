# Owner interactive scaffold Progress finalization and recovery repair

Date: 2026-08-14

The owner-confirmed duplicate-finalization and list/run predicate-drift defects
are repaired at the future Capsule runtime and generic Workspace-client
boundaries. New Writing/Review Capsule 0.4.0 and Experiment Capsule 0.5.0 use a
public deterministic `finalize-scaffold` command. The runner snapshots the
Progress chain, then strictly adopts exactly one Agent-finalized next terminal
report or performs the prior runner-owned finalization once. Adopted paths do
not publish, rewrite context or finalize again.

One structured local readiness evaluator now drives both `workflow list` and
`run`. It distinguishes no local completion, exact recovery, exact known
legacy scaffold drift, acknowledgement and invalid state. Historical Writing
0.3/Review 0.3/Experiment 0.4 drift is accepted only when the immutable report,
chain, output bytes, deterministic scaffold payload, exact materialization
receipts/provenance and canonical terminal context prove the historical
post-report `completed_rounds=N+1` transformation. Recovery uploads the exact
missing report, confirms Cloud projection and persists acknowledgement without
Harness launch, Artifact mutation, context normalization or a new round.

Seed-only migration `20260813_0021` publishes the three new Capsule records;
Definitions, schemas and Research Artifact Provenance 0.1.0 / Scaffold Core
Safety 0.1.0 pins are unchanged. Historical Writing 0.2/0.3, Review 0.2/0.3 and
Experiment 0.3/0.4 renderers remain immutable; shared historical runner SHA-256
remains `280a3cfaa2e8c4a1599a10e9e2052e270d992d8e1943d28e6b33270c707d8332`.

Qualification used synthetic/disposable state only. Fake Harnesses actually
invoked the bundled finalizer. Writing 0.4, Review 0.4 and Experiment 0.5 each
produced one Cloud-visible round; the Workspace Writing->Review->Writing chain
preserved immutable prior outputs and exact bindings. Real Codex 0.146.0 fully
completed all three Capsules and runner adoption, rather than stopping at
INPUT_REVIEW. Synthetic historical Writing 0.3 and Experiment 0.4 states
recovered with zero Harness calls and zero local mutations; list/run
equivalence, context A-H, tamper/security, Idea backlog and idempotency
regressions passed.

Full backend on a marker-guarded disposable PostgreSQL database passed `857
passed, 14 existing skips`; Alembic upgraded from empty to sole head 0021 and
reported no schema changes, then the database was dropped. Frontend Vitest
passed `17 files / 34 tests`, TypeScript, ESLint and production build passed;
controlled Playwright passed 4; owner-runtime scripts passed 43; focused
security/history suites passed 41 and lifecycle suites passed 45. No owner
Project/Workspace/database, live OpenAlex, Provider key or research Artifact
was accessed. Nothing was pushed.

Owner continuation: upgrade 0021, restart owner runtime, replace only the
Workspace-root client, sync/list, run the exact pending Writing and Experiment
commands for upload-only recovery, verify Completed, retire the unexecuted
Review 0.3 Instance, add Review 0.4 and continue the scaffold UX loop. Do not
rerun Writing/Experiment or implement real cores.
