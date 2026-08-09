# NIGHT-F1B interrupted checkpoint

Date: 2026-08-09

Status: IMPLEMENTATION IN PROGRESS — SAVED, NOT COMMITTED

## Baseline

- branch: `main`
- starting HEAD: `349538631bed4767880b8024afcc32e3aae7fa06`
- F1A ancestor: verified
- initial worktree: clean
- extra worktrees: none
- migration baseline: sole head `20260806_0014`
- live Provider/credential access: none

## Implemented

- deterministic migration `20260806_0015`
- Writing, Review, Reproduction & Experiment stable production Registry rows
- immutable Definition/Capsule version `0.1.0`, `SCAFFOLD_CORE`
- exact Artifact requirements and independent sync/install pins
- shared scaffold Capsule compiler, validator and generic local runner
- deterministic visibly marked manuscript/review/experiment placeholders
- content-addressed Artifact and Progress promotion with exact provenance
- generic required-input preflight, materialization receipt/checksum checks
- producer-authoritative Artifact and Progress maturity projection
- Registry/Board/Progress maturity badges and scaffold warnings
- architecture/getting-started documentation and ADR 0031
- F1B Registry, sync, Capsule, migration, full-chain, security and frontend tests

## Qualification completed

- migration base -> 0014 -> 0015 -> 0014 -> 0015: `1 passed`
- Alembic heads/current/check: sole `20260806_0015`, no drift
- targeted Artifact/maturity/N+1 + F1B chain: `32 passed`
- frontend Vitest: `16 files, 32 tests passed`
- TypeScript: PASS
- ESLint: PASS
- production build: PASS (required sandbox escalation for Turbopack worker port)
- Playwright: `5 passed` with deterministic fake Provider
- Python compileall: PASS before the final maturity batch refactor; rerun required
- git diff --check: PASS before this checkpoint

## Full backend checkpoint

The first isolated-PostgreSQL full run after implementation produced:

- `733 passed`
- `11 skipped`
- `1 failed`

The sole failure was a new Artifact maturity projection N+1 (`5`/`54` queries
against a limit of `4`). Maturity authority was changed to one bulk
Workflow-Instance/Definition-Version join. The exact PostgreSQL N+1 test and
31 related Artifact/F1B tests then passed. The complete backend suite has not
yet been rerun after that final fix.

## Resume sequence

1. Review `git diff` and rerun compileall/diff-check.
2. Start a fresh isolated PostgreSQL 18 cluster and two explicitly named F1B
   databases; upgrade the normal test DB to 0015.
3. Rerun the full backend suite with `REAGENT_TEST_DATABASE_URL` and the F1B
   migration database gate. Record all 11 skip reasons.
4. Perform PostgreSQL stop/start and readiness/current checks.
5. Rerun focused F1A/B6/B7/H2 if the full suite exposes anything.
6. Re-run frontend Vitest/typecheck/lint/build if code changes.
7. Run final immutable checksum comparison for Literature 0.5/0.6, Idea
   0.1/0.2 and new scaffold Capsules.
8. Run final status/diff/temporary-file/credential scan.
9. Update this progress record to the final F1B report, update context and the
   plan status, then create semantic commits on `main` only.
10. Verify clean main and do not push or start F1C.

## Interruption cleanup

- Playwright completed successfully before termination was applied.
- backend and frontend server processes stopped.
- isolated PostgreSQL stopped.
- `/private/tmp/reagent-night-f1b-pg.0mDmBC` removed.
- no temporary Workspace or test Artifact bytes remain in the repository.
- no commit and no push occurred.
