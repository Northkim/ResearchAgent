# NIGHT-F1C Full Research Project preset and five-Workflow readiness UX

Date: 2026-08-09

Status: PASS — OWNER REVIEW READY

## Baseline and boundary

- branch/start: `main` at `f9eba63ef201916daf30cedddf004c1b187a93e6`
- F1B final commit: verified ancestor
- initial worktree: clean; extra worktrees: none
- migration: sole `20260806_0015`; F1C migration not required
- no live Provider, `.env`, credential, owner DB/Workspace, branch, worktree or push
- no pipeline, Skill/Resource shell, real scaffold core, GitHub/HF or multi-user work

## Product setup

- stable server-side presets: Literature-only, Literature + Idea, Full Research
- Registry-driven Custom selection, including safe waiting for missing upstream inputs
- Full preset resolves current Registry pins and atomically creates five ordinary
  Workflow Instances plus one revision-1 Desired Manifest
- legacy omitted setup remains Literature-only
- injected Instance failure rolls back Local Project, canonical Project,
  Instances and Manifest

## Readiness and UX

- per-Instance readiness and next action are derived, never persisted
- authority inputs: Desired/lifecycle, installation acknowledgement, frozen DB
  requirement rows, exact active bindings, compatible Artifact metadata and Progress
- states/actions cover sync, upstream wait, exact selection, conservative local
  materialization guidance, run, continue, result review and Review-to-Writing revision
- research status and `REVIEWED_CORE`/`SCAFFOLD_CORE` remain independent dimensions
- generic exact Artifact selector shows source Workflow friendly label, maturity,
  produced time and short technical identity; no automatic latest/binding
- same-type product restriction removed; ordinal Writing/Review labels preserve rounds
- CLI checks all required materialization receipts, exposes maturity/readiness/Progress,
  and prints exact commands when a stable selector is ambiguous

## Qualification

- F1C focused plus Progress/API: `58 passed`
- full backend on isolated PostgreSQL 18: `742 passed, 11 skipped`
- Full preset bootstrap/sync: exact five downloads, acknowledged Installed Lock,
  initial five-Workflow readiness, second sync `NO_CHANGE`
- scale regression: 20 Workflow Instances / 1,000 reports, fixed-query projection PASS
- F1B full scaffold chain, F1A contracts, B7, B6, B5, B4, B3, H1/H2: PASS in full suite
- frontend Vitest: `16 files, 33 tests passed`
- TypeScript: PASS; ESLint: PASS; production build: PASS
- Playwright with deterministic fake Provider: `5 passed`
- Python compileall: PASS
- Alembic heads/current/check: `20260806_0015`, no drift
- migration files changed by F1C: none
- git diff check: PASS

## Skip audit

Seven dedicated historical migration database gates (B1, B2, B4, B5, B6,
B7, F1A), three pre-existing isolated integration gates (destructive demo,
9B-1 contract, 9A-2), and one explicit live OpenAlex gate were skipped. The
dedicated F1B migration database gate was supplied and passed.

`F1C_NEW_SKIP = 0`.

## Manual/product metrics

- `CREATE_PROJECT_CHOICES = 4`
- `FULL_PRESET_WORKFLOWS_CREATED = 5`
- `TERMINAL_COMMANDS_TO_INITIAL_READY_STATE = 4` (bootstrap, cd, sync, workflow list)
- `RAW_UUID_COPY_REQUIRED = 0`
- `MANUAL_JSON_EDIT_REQUIRED = 0`
- `DEAD_ENDS = 0`

## Deferred

- F1D: Skill Registry / Version / Workflow Pin / Capsule Delivery shell
- F1E: Resource shell
- F1F: complete five-Workflow product E2E
