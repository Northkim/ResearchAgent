# Post-D1 R6 subtractive Owner UX and information hierarchy — complete

## Status

`R6 = PASS_AT_DECLARED_LEVEL`

`VERIFIER_INDEPENDENCE = LIMITED`: the implementing Codex session also ran the
qualification. The controlled E5/E6 public paths passed; no E7 real research,
E8 protected Workspace, or E9 Owner journey was rerun.

## Baseline and scope

- Baseline before R6: `321d1955fc5e73ac7cf66fd3d793743b9dca8444`.
- Change packet commit: `bcc2d9791003679e97b58916933e953245c7fdcc`.
- Product and direct qualification commit:
  `39f4d72a67ca52d962bd0dcf552b930ae9e3b0cb`.
- Approved packet: `2026-08-20_post_d1_r6_change_packet.md`.
- Closed ledger scope: `D1-WORKFLOW-ORDINAL-01`, `D1-WRITING-ENTRY-01`,
  `D1-WRITING-UX-02`, `D1-WORKSPACE-UX-01`,
  `D1-OVERVIEW-PRIORITY-01`, `D1-OUTPUT-LABEL-01`,
  `D1-RETIRED-UX-01`, `D1-PROGRESS-HISTORY-01`,
  `D1-REVIEW-PRESENTATION-01`, `D1-OUTPUTS-LAYOUT-01`, and
  `D1-PRESENTATION-CONTINUITY-01`.
- `D1-OVERVIEW-VISUAL-01` remains `OBSERVATION_NEEDS_CONFIRMATION`: the Owner
  E9 screenshot remains valid evidence, but the bounded long-topic controlled
  reproduction did not show the overlapping/duplicated hero.
- Protected Owner D1 state was not accessed or changed.

## Exact source changes

- One shared backend Owner-label projection uses explicit published
  `writing_role` authority, keeps Initial Writing and Writing Revision distinct
  and unnumbered, and uses deterministic exact-instance ordering for repeated
  non-Writing roles. Local projection uses exact immutable workflow descriptor
  identity rather than version comparison.
- Exact installed-Capsule acknowledgement keeps unchanged Workflows current
  when a manifest adds another Workflow. The Project shows one sync notice and
  the new exact Workflow is simply not installed; same-instance pin drift still
  remains stale.
- Forward v3/v4/v5 Artifact types have centralized Owner-facing labels across
  Board, Overview, Activity, and Outputs.
- Overview separates the latest completed research outcome from remaining work;
  active Workflows remain primary and retired Workflows are preserved under
  secondary history.
- Historical Activity cards label exact Progress-report round/status rather than
  mixing it with a current Workflow action.
- Review presentation v0.2 adds bounded issue identity, category, problem,
  requested action, and status. Historical v0.1 remains immutable and readable.
- Exact v4/v3 presentation companions can be reported/backfilled idempotently
  through the existing Local artifact refresh path without rerunning science.
- Outputs use a wider content-first responsive layout; materialization copy says
  it prepares verified selected inputs; primary Overview overflow is clipped
  safely without adding explanatory copy.

## Publication, persistence, and migration

- Scientific Artifact schemas, Workflow Definitions, Capsules, checksums,
  bindings, and evidence authority: unchanged.
- Review presentation v0.2 is an optional exact Artifact-bound UI companion;
  presentation remains non-authoritative.
- `MIGRATION_REQUIRED = NO`.
- Alembic sole head remains `20260820_0039`.

## Verification matrix

| Requirement | Evidence | Level | Result |
|---|---|---|---|
| Role authority, ordinals, typed labels, acknowledgement semantics | focused backend/frontend projection tests | E1/E2 | PASS |
| Review v0.1/v0.2 validation and bounded rendering | validator, service, component tests | E1/E2 | PASS |
| Independent presentation backfill and replay | public copied Workspace test | E5 | PASS |
| Task-first Board/Overview/Activity/Outputs and downstream chain | real FastAPI/Next.js/system-Chrome controlled journey | E6 | PASS |
| Four accepted D1 contract locks | focused backend regression group | E1–E5 fixtures | PASS |

## Executed evidence

- Focused backend plus four D1 repaired-contract locks: `119 passed`.
- Broader affected backend group: `159 passed`.
- Full frontend Vitest suite: `21 files / 81 tests passed`.
- TypeScript, full ESLint, Python compileall/py_compile, and
  `git diff --check`: PASS.
- Production Next.js build: PASS with the approved process permission required
  for its local worker.
- E5 public copied Workspace:
  `test_forward_downstream_public_workspace.py`: `1 passed`.
- E6 repository-native controlled browser:
  `f1f-product-width.spec.ts`: `3 passed` (FE-M, U1, and forward Full Research)
  against real FastAPI, real Next.js, system Chrome, and marked disposable
  PostgreSQL.
- Qualification database
  `reagent_qualification_6770d36f06dc4ef2ab2c79658d3bd689` passed identity
  marker verification, was dropped, and all controlled services stopped.
- Screenshot evidence includes
  `.agent_read/tmp/fe-m-desktop-final-review/overview__1440x900.png` and
  `frontend/test-results/ep-d2-e6/screenshots/01` through `10`. Visual review
  confirms concise issue presentation, typed Outputs, completed-outcome
  priority, role-aware labels, and report-scoped Activity status.

## Fixture alignment and qualification limits

- Direct E6 fixture expectations were aligned only where objectively stale:
  forward pins now use the already-published R4 catalog, Revision expects 0.7,
  controlled Review presentation uses its exact v0.2 schema, and the isolation
  runner accepts both qualification cleanup markers that F1F deliberately
  creates. No product behavior was weakened to satisfy a test.
- A combined F1F+historical-H1 exploratory run exposed stale H1 Help assertions
  and a deeper Literature 0.8 interactive-resume exit mismatch. H1 source was
  restored byte-for-byte and was not used for the R6 claim. The final scoped R6
  E6 passed; the historical H1 qualification debt is carried into R7 for exact
  classification rather than hidden.
- The original `D1-OVERVIEW-VISUAL-01` Owner observation is not erased by the
  controlled non-reproduction and remains open for future E9/reproduction.

## New-defect audit

1. Exact scientific boundary weakened: **NO**.
2. Implicit latest/merge introduced: **NO**.
3. Cloud made authoritative for complete Local bytes: **NO**.
4. User Skill gained Capability/evaluation authority: **NO**.
5. Completed Workflow must rerun to synchronize: **NO**.
6. New manual Owner orchestration step introduced: **NO**.
7. Immutable publication changed in place: **NO**.
8. Accepted D1 repaired contract changed: **NO**.
9. Fixture changed to avoid production semantics: **NO**.
10. UI made more verbose instead of simpler: **NO**.

## Ledger result and safe next action

Eleven scoped findings are `FOUND_AND_REPAIRED_POST_D1`.
`D1-OVERVIEW-VISUAL-01` is `OBSERVATION_NEEDS_CONFIRMATION` with its original
Owner evidence preserved. No new HIGH/CORE R6 product defect was found.

Proceed automatically to R7 full-system qualification. R7 changes no product
behavior unless a separately authorized repair is required; a new HIGH/CORE
defect must stop the program under `NEW_PRODUCT_DEFECT`.
