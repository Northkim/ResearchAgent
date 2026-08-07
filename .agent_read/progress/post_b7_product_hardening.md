# NIGHT-H1 Product Hardening and UX Validation

Date: 2026-08-07

Status: **PASS — CONTROLLED USER TESTING READY**

## Baseline and scope

H1 started on clean `main` at B7 final commit
`79a00e143b362668959fc36327ea8580f87fcb70`; that commit remained an
ancestor and the repository had one worktree. Alembic had one head,
`20260806_0013`. Production records and source contracts for Literature Search
0.4.0 / Capsule 0.6.0, Idea Discovery 0.1.0 / Capsule 0.1.0, and
`selected-paper-library/v1` were verified from migration, Registry/compiler,
API, and tests. No credentials, `.env`, owner database, live Provider, or
external research network was used.

H1 adds no Workflow and no database migration. It preserves Cloud/Local,
Installed Lock, explicit Artifact binding/materialization, immutable Capsule,
and no-auto-latest boundaries.

## Audited journeys

The audit followed the actual current routes and commands:

1. `/projects/new` → Project Overview → `/projects/{id}/help`;
2. `workspace-bootstrap.json` download → `reagent_local.py bootstrap` →
   `sync`;
3. Literature Search preflight, interactive deterministic fixture, explicit
   finish, production Artifact, Progress, and browser reload;
4. `/projects/{id}/workflows` → Add Idea Discovery → incremental sync;
5. explicit Artifact choice → `artifact refresh` → `artifact materialize`;
6. Idea preflight → local run → outputs/Progress;
7. a fresh process with no chat history → `workflow list` → continuation;
8. acknowledgement retry, Manifest conflict, Artifact drift, target conflict,
   interrupted run, PostgreSQL restart, and browser reload recovery;
9. legacy standalone Package and retained Hosted deterministic-run regression.

For each stage the audit inspected visible copy, required input, primary action,
UUID exposure, terminal transition, error recovery, and whether the next action
was discoverable. Browser/API behavior was exercised in real Chrome through the
repository Playwright suite; CLI and filesystem steps executed the real copied
Workspace tool against an isolated real backend/PostgreSQL. The in-app Browser
runtime was unavailable, so it was not used as a substitute control plane.

## Findings

### P0 — 3 found, 3 fixed, 0 open

1. `backend/progress_reports/service.py`: an explicit Literature Search 0.6.0
   finish persisted accepted Progress but its immutable local-session adapter
   omitted the redundant Artifact declarations. Cloud now derives only from the
   exact reviewed producer Capsule contract and immutable completed Progress;
   exact retry also repairs the previously missing canonical row.
2. `frontend/api/client.ts`: the Idea selector sent unsupported
   `state=AVAILABLE`, producing a 422 and an empty dead end. The selector now
   requests the production type and leaves lifecycle/eligibility validation to
   the existing binding service.
3. `backend/project_workspaces/workspace_cli.py`: valid Idea outputs require an
   exact source Artifact ID, but normal materialization exposes bytes rather
   than receipt internals. After full preflight, the runner atomically creates
   only the empty source-provenance envelope. Users never edit receipt/output
   JSON to begin the Workflow; differing existing output fails closed.

### P1 — 5 found, 5 fixed, 0 owner-independent open

1. Overview/Help now expose the Project-specific Workspace setup download and
   a copyable bootstrap command instead of requiring API knowledge.
2. `workflow list` and unique stable `--workflow` selectors remove UUID copying
   from the normal journey; multiple same-type instances remain exact and
   ambiguity fails closed.
3. Overview and Workflow cards use a minimal derived next-action model for
   sync, input selection, materialization, run, continuation, and review.
4. Critical CLI errors now preserve their code while explaining what happened,
   why it matters, and the next safe recovery action.
5. Project Help, root README, Local Guide, bootstrap guide, and Idea Discovery
   guide now form one 0-to-continuation onboarding path, including the legacy
   0.3.0/0.5.0 adoption boundary.

### P2 — 6 found, 4 fixed, 2 deliberately retained

- Fixed: Manifest/checksum/Capsule identity moved to secondary diagnostics;
  Artifact choices lead with producer/date/summary and show a single choice as
  recommended without auto-binding; sync/materialization human output uses
  product language; copy controls, mutation focus, form error association, and
  responsive command overflow were hardened.
- Retained: Cloud cannot truthfully know whether a local materialization receipt
  exists, so Web conservatively says to prepare the bound input while local
  `workflow list` gives byte-verified readiness. The legacy standalone Package
  route remains secondary rather than a primary Workspace CTA, but remains
  addressable, tested, and linked from detailed help.

### P3 — 0

No purely aesthetic finding was promoted into H1 scope.

## Next-action model

`frontend/lib/workflow-next-action.ts` derives Web guidance from active/retired
state, installation acknowledgement, exact dependency edge, and Workflow
Progress. `workspace_cli.workflow_list` derives local readiness from the
Installed Lock, exact Capsule metadata, self-identifying Progress, materialized
receipt, and current target checksum. Neither is persisted as new truth.

Typical Idea sequence is `SYNC` → `SELECT_INPUT` → `MATERIALIZE` → `RUN`
→ `CONTINUE` → `REVIEW_RESULT`. Cloud never claims local bytes were
verified; the CLI never guesses Cloud selection.

## CLI and error recovery

The additive commands/selectors are:

```text
python reagent_local.py workflow list <workspace> [--json]
python reagent_local.py artifact materialize <workspace> --workflow <stable-key>
python reagent_local.py run <workspace> --workflow <stable-key>
```

Stable selection works only for one active matching local instance. Existing
`--workflow-instance` forms and existing JSON result documents are unchanged.
Human output summarizes added/retained Workflows and Cloud confirmation rather
than leading with pins/checksums.

Recovery was verified as follows:

- `ACK_PENDING`: installed state remains valid; exact sync retry acknowledges
  without another download.
- Manifest conflict: frontend refreshes current state and requires another
  explicit action.
- source/input drift: materialization/run fail closed with restoration or
  re-selection guidance; Cloud metadata is not rewritten.
- target conflict: existing bytes are not overwritten.
- interrupted/closed Harness: local memory, outputs, and Progress remain the
  continuation authority; `workflow list` exposes `CONTINUE`.
- PostgreSQL/browser restart: persisted projections and both Workflow histories
  reload; Alembic remains at the sole head with no drift.

## Deterministic real-code E2E

`frontend/tests/e2e/h1-product-journey.spec.ts` ran this 23-step controlled
journey using real frontend/backend/API/CLI/filesystem code:

1. create Project in browser; 2. open Overview; 3. download setup file;
4. bootstrap Workspace; 5. sync Literature Search; 6. run preflight;
7. run the official deterministic literature fixture; 8. review deterministic
selection checkpoints; 9. explicit finish; 10. create
`selected-paper-library/v1`; 11. upload Progress; 12. verify Web Progress;
13. add Idea Discovery in UI; 14. verify Manifest mutation; 15. sync only the
Idea Capsule and verify the Literature Capsule tree hash is unchanged;
16. explicitly choose the specific Artifact; 17. persist binding; 18. refresh
the Artifact Index; 19. materialize and verify input; 20. run Idea preflight;
21. execute representative session one and upload Progress; 22. close and run
a fresh process/session two from local memory; 23. verify both Workflows and
both Idea stages in Board/Progress.

Fixture boundary: literature retrieval and representative Idea conversation
content use committed deterministic no-network test Harnesses. Project,
Manifest, Capsule download/install/Lock/ack, Progress, Artifact promotion,
Index, binding, receipt, materialization, files, browser responses, and
continuation are real. There is no direct DB insertion, fake Lock, fake receipt,
or fake frontend response.

Manual ordinary-user diagnostics for the same path:

- `USER_VISIBLE_STEPS_COUNT = 23`
- `TERMINAL_COMMANDS_REQUIRED = 8`
- `RAW_UUID_COPY_REQUIRED = 0`
- `MANUAL_FILE_EDIT_REQUIRED = 0`
- `DEAD_ENDS_FOUND = 3 initially / 0 unresolved`

`LIVE_PROVIDER_PRODUCT_E2E = NOT_AUTHORIZED`; this is not an H1 failure.

## Qualification

- targeted H1/B7/B6 Progress/Artifact/CLI tests: `66 passed`;
- full backend with the isolated PostgreSQL URL: `683 passed, 10 skipped`;
- post-physical-restart B7/Artifact/Progress/sync/Manifest PostgreSQL set:
  `12 passed`;
- frontend Vitest: `15 files / 29 tests passed`;
- full Playwright: `5 passed` (current H1, standalone interactive/auto Package,
  and retained Hosted deterministic paths);
- TypeScript, ESLint, production Next.js build, and Python compileall: passed;
- Alembic heads/current/check after PostgreSQL restart: sole
  `20260806_0013`, no new operations;
- `git diff --check`: passed.

The 10 skips are pre-existing explicit gates: six historical dedicated
migration database suites and four destructive/live integration environments.
No H1 test skipped and no skip was added. The first non-DB full-backend command
correctly exposed 18 mandatory PostgreSQL setup errors; the authoritative rerun
with the isolated URL executed them and passed. The first production build was
sandbox-blocked by Turbopack's internal worker port; the controlled rerun passed.

The existing 20-Workflow/1,000-Progress and 1,000-Artifact scale tests remain
green. Board state uses one aggregated Project Progress response and React
Query-shared Catalog/Artifact reads; H1 adds no per-card Progress/dependency
request.

## Deferred findings and owner decisions

No P0 or owner-independent P1 remains. No owner decision is required for the
accepted H1 journey. Public deployment, multi-user auth, operator telemetry,
backup/restore, and broader controlled-user feedback remain unqualified.
Writing, Review, Experiment, Skills/Resources, external resolvers, Cloud
Artifact bytes, cross-device restore, background sync, and browser local
execution remain outside H1.

Evidence supports **Deployment / Controlled User Testing Hardening** as the
next owner decision before another production Workflow: the architecture and
core journey now work, while deployment/security/operator and real-user
feedback boundaries remain the largest readiness gap.
