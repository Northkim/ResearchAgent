# Owner Manual F1F Test Defect Repair — Literature Interrupted Finalization Recovery

Date: 2026-08-11

Status: PASS — OWNER MAY RESUME THE EXISTING LITERATURE ROUND

## Classification

- `OWNER_TEST_DEFECT_ID = LITERATURE_INTERRUPTED_FINALIZATION_RECOVERY`
- `OWNER_TEST_SEVERITY = P0_BLOCKING_E2E`
- `OWNER_TEST_DEFECT_INVESTIGATION = PASS`
- `OWNER_TEST_DEFECT_REPAIR = PASS`
- `MIGRATION_REQUIRED = NO`

This is a narrow F1F continuity integration repair. It adds no Workflow,
research capability, pipeline engine, persistence model, Capsule version, or
Artifact, Skill, Resource or Progress contract.

## Existing state and root cause

`SEARCH_COMPLETED` with both confirmation booleans false is a valid resumable
round: plan and normalized query results are checksum-bound, but candidate
review and explicit finalization are not durably proven. The Capsule already
supports `--resume`; it preserves valid files, restores `last_completed_state`,
skips existing normalized results, and fails closed on identity/checksum drift.

The generic Workspace runner did not inspect this state and launched the
Capsule without `--resume`, so the Capsule's partial-work guard rejected the
retry. `workflow list` only read finalized Progress reports and dependencies,
so no report meant `Ready / Run`. The one-round timeout raises `LocalRoundError`
rather than `RoundInterrupted`, leaving no interruption marker. `finish` is not
a durable event by itself: both confirmations and output checksums are written
only after final outputs/context/report draft succeed, so a timeout before that
transition must require confirmation again.

## Repair

The generic Workspace launcher now:

- invokes the immutable Capsule validator before interpreting continuity;
- combines Cloud readiness with the verified local round-control state;
- displays `Interrupted`, `In Progress`, or `Finalization Pending` and
  `Next: Resume` for valid unfinished Literature work;
- automatically appends the Capsule's existing `--resume` to the unchanged
  product command;
- after a nonzero attached Harness exit, records only the last valid state,
  bounded stage, and `HARNESS_SESSION_STOPPED` when resumable work exists;
- never invents screening consent, explicit finish, outputs, Progress, or
  completion.

No Capsule byte or version changed. The 20-minute Capsule timeout remains
bounded but is demonstrably tight for leisurely three-checkpoint owner testing;
it was not increased because duration alone cannot provide continuity and
changing the published Capsule would require a separately versioned artifact.

## Cross-session qualification

The real controlled product route used a Full Research Project, downloaded
generic client, bootstrap, five-Capsule sync, and the exact Workspace command.
Session A confirmed the plan, made two deterministic fake-Provider calls,
screened candidates, received `finish`, then deterministically stopped before
writing final outputs. The generic launcher recorded an interruption around
`SEARCH_COMPLETED`; workflow list reported Resume.

Session B was a fresh PTY/Harness process with no chat history. It read the
same local query plan, normalized results and context, repeated uncommitted
screening/finalization confirmation, made zero Provider calls, and completed
the existing round. The two query-result hashes remained identical. It
produced the validated content-addressed `selected-paper-library/v1`, finalized
and uploaded Progress, received Cloud acknowledgement, and the result was
materialized into downstream Idea Discovery.

Tampered query-result checksum, Capsule identity and immutable-package paths
remain fail closed. Previous relative Workspace dot/absolute/relative/space/
Unicode, controlled DEMO/no-key and all five Capsule launcher regressions pass.

## Tests

- targeted Literature + Workspace continuity: `53 passed`;
- focused Workspace/B7 regression: `29 passed`;
- full backend, isolated PostgreSQL at 0017: `783 passed, 14 existing skips`;
- frontend Vitest: `17 files / 34 tests passed`;
- frontend ESLint and production build: passed;
- real controlled cross-session Playwright: `1 passed`;
- compileall, Alembic sole head and `git diff --check`: passed;
- `F1F_NEW_SKIP = 0`; `OWNER_DEFECT_NEW_SKIP = 0`.

The explicitly named temporary database was deleted after qualification.
Controlled backend/frontend were stopped. No owner Workspace, Project or
database, live OpenAlex, GitHub/Hugging Face, credential, or research bytes
were read or changed.

## Owner recovery

Restart `make controlled-start`, download the current Local Workspace tool, and
replace only the existing Workspace-root `reagent_local.py`. In the existing
Workspace run:

```bash
python reagent_local.py workflow list .
python reagent_local.py run . \
  --workflow literature-search-local-experimental
```

The list should report Resume and the run should reuse the existing search.
No Capsule sync, re-bootstrap, Project recreation, database change, JSON edit,
or Provider re-query is required.
