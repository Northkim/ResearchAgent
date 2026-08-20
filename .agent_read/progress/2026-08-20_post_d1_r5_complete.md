# Post-D1 R5 Project / Skill lifecycle and navigation — complete

## Status

`R5 = PASS_AT_DECLARED_LEVEL`

`VERIFIER_INDEPENDENCE = LIMITED`: the same Codex session implemented and
verified R5. R6 presentation/labels remains the next phase; R7 full-system
qualification has not yet run.

## Baseline and scope

- Baseline before R5: `67da8f1e7478d38a72d3be942e32be24f926fbb3`.
- Change packet commit: `7971f4392703b8fb7fc3fc67a1ab5aaab5743f8b`.
- Product and direct qualification commit:
  `758eb6f9c38a0adbcfcf675d735a515cfd2b9079`.
- Approved packet: `2026-08-20_post_d1_r5_change_packet.md`.
- Ledger scope: `D1-SKILL-NAV-01`, `D1-SKILL-EMPTY-01`,
  `D1-SKILL-DETAIL-01`, `D1-SKILL-LIFECYCLE-01`, `D1-PROJECT-NAV-01`,
  `D1-LOCAL-GUIDANCE-IA-01`, and `D1-PROJECT-LIFECYCLE-01`.
- `D1-SKILL-SUBTRACTIVE-01` was audited visually; no distinct remaining defect
  was reproduced.
- Protected Owner D1 database, Project, Workspace, Artifacts, bindings, and
  Progress were not accessed or changed.

## Exact source changes

- Global Skills navigation now enters exact unscoped `/skills`, and a scoped
  empty state offers one direct library/Add action.
- A compact Skill detail shows purpose, Project usage, and source; exact revision
  and checksum plus safe deletion remain secondary.
- Attached User Skills cannot be deleted. After explicit detach, deletion removes
  only that global exact record; Project deletion never deletes a shared Skill.
- Project title/body is the stable Overview entry while task actions and Help are
  distinct explicit destinations.
- Project Help is shortened to exact setup/continuation; Local Guide is generic
  reference.
- `DELETE /projects/{project_id}` performs one Unit-of-Work transaction over all
  Project-owned relational state in current FK-safe order.
- A deleted Project's Local Workspace fails `PROJECT_NOT_FOUND` before the Local
  write lock. No Local byte is removed, rewritten, or rebound.

## Persistence and migration

- `MIGRATION_REQUIRED = NO`.
- Alembic sole head remains `20260820_0039`.
- Marked disposable PostgreSQL qualification verified rollback, exact deletion,
  zero remaining rows in every table carrying the deleted `project_id`, survival
  of a second Project and global shared Skill, and no pending schema operations.
- Qualification database `reagent_qualification_bc03b0a277964a07b57177e909828e02`
  was identity-verified and dropped.

## Verification matrix

| Requirement | Evidence | Level | Fixture | Result |
|---|---|---|---|---|
| Stable Skills/Project navigation and bounded empty/detail views | frontend component tests + `skill-m1.spec.ts` | E2 / E6 | component mocks + real controlled API/browser | PASS |
| Attached conflict, detach, safe exact delete, shared usage | Skill service/API tests + E6 | E3 / E4 / E6 | in-memory + disposable PostgreSQL + controlled browser | PASS |
| Atomic Project graph delete and rollback | `test_project_lifecycle.py`, `test_project_deletion_postgresql.py` | E3 / E4 | in-memory and marked PostgreSQL | PASS |
| Global Skill/publication/other Project preservation | deletion service/PostgreSQL tests | E3 / E4 | independent second-Project graph | PASS |
| Deleted-Project Workspace remains byte-identical | `test_workspace_cli.py` + E6 copied Workspace | E5 / E6 | disposable public Workspace | PASS |
| Help/Guide information boundary | component tests + build/E6 visual review | E2 / E6 | component + controlled browser | PASS |
| Four repaired-D1 locks | focused backend group | E1–E5 by existing fixtures | production validators/public Workspace fixtures | PASS |

## Executed evidence

- R5 backend plus four D1 locks: `94 passed, 1 skipped` (the skip is an existing
  opt-in/environment-qualified path, not an R5 requirement).
- R5 frontend components: `5 files / 19 tests passed`.
- TypeScript and source-scoped ESLint: PASS.
- Python compileall and `git diff --check`: PASS.
- Production Next.js build: PASS. The sandboxed attempt could not bind a
  Turbopack worker port; the identical build passed with required process
  permission.
- Marked PostgreSQL R5 suite: `4 passed`; database dropped.
- Controlled FastAPI/Next.js/system Chrome E6: `1 passed`; database
  `reagent_qualification_142c76b04b32492f87c51c9fd9001595` was dropped and
  controlled processes stopped.
- Screenshots are under `.agent_read/tmp/skill-m1-e6/01` through `08` and cover
  the empty library, Add form, library, detail, Project Ready/detached states,
  delete confirmation, and deleted portfolio.

## Verification limits

- Highest achieved level is E6 for the controlled Owner-facing path.
- No E7 Real Codex, E8 protected long-lived Workspace, or E9 new Owner journey
  was performed; those levels are not required for R5's bounded lifecycle claim.
- The E5 orphan case uses a copied disposable Workspace, not the protected D1
  Workspace.
- Project deletion removes all Project-addressable relational Cloud state. R5
  does not claim physical erasure of immutable content-store objects without a
  separate storage-retention contract.

## Risk and architecture review

- Negative cases cover attached Skill deletion, repeat Project deletion, injected
  transaction rollback, deleted-Project sync, and preservation of an unrelated
  manually created Local Skill.
- No implicit Artifact selection, Cloud Workspace access, hosted execution,
  second Skill truth, User-Skill capability authority, or scientific contract
  change was introduced.
- No Workflow, Capsule, Artifact schema, migration, or historical publication
  changed.
- The four D1 repaired contracts remain passing.
- A broader backend regression run encountered two objectively stale R4 catalog
  expectations in `backend/project_workspaces/tests/test_api.py` (old Literature
  0.7 pin and missing Literature Consolidation). They are outside R5 and were not
  changed or used to weaken this claim; R4's direct qualification remains PASS.

## Ledger result and safe next action

The seven scoped findings are `FOUND_AND_REPAIRED_POST_D1`.
`D1-SKILL-SUBTRACTIVE-01` is now `EXPECTED_BEHAVIOR` for the bounded R5 surface.
No new R5 product defect was found.

Proceed to R6 subtractive Owner UX, labels, and information hierarchy only. Do
not touch the protected Owner D1 state and do not begin R7 until R6 is committed.
