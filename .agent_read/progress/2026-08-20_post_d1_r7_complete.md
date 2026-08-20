# Post-D1 R7 full-system qualification — complete

Date: 2026-08-20

Status: **PASS_AT_DECLARED_LEVEL**

`VERIFIER_INDEPENDENCE = LIMITED`: the same Codex session implemented the
bounded timezone repair and completed qualification. No E7 real research, E8
protected Workspace recovery, or E9 Owner journey was rerun.

## Baseline and bounded unblock

- R7 entry HEAD: `a6d44432c78ba9e2950bc468f283f9f6704cdfe3`.
- R6 product commit: `39f4d72a67ca52d962bd0dcf552b930ae9e3b0cb`.
- Bounded repair commit: `86abbc196fe388d1c7f6cd1030d8afbc7bba89dc`.
- R7 qualification/fixture commit:
  `c255ce5d330445d47a6f96f448056cde61d0ba00`.
- Alembic sole head: `20260820_0039`.
- Owner database and protected D1 Project: not accessed.

`R7-INPUT-SETUP-DECISION-TIMEZONE-01` is closed by canonical aware-UTC
serialization before an input-setup decision timestamp participates in
identity, checksum, comparison, validation, or response projection. The same
instant now has the same bytes across offsets and PostgreSQL reloads, while a
different instant still fails integrity. Supported historical records already
used the UTC `Z` representation; no compatibility fallback, row rewrite,
migration, or publication change was required. Full bounded evidence is in
`2026-08-20_r7_input_setup_decision_timezone_repair.md`.

## Full-system verification matrix

| Requirement | Evidence | Level | Result |
|---|---|---:|---|
| Same-instant decision integrity and tamper negatives | focused decision service suite | E1 | PASS |
| HTTP create, PostgreSQL reload, current decision, materialization | marker-verified product-width PostgreSQL route | E4 | PASS |
| Exact A→B inputs, unchanged sibling, no stale runnable state | artifact/reference and public Workspace suites | E1–E5 | PASS |
| Zero-paper producer plus forward Idea precondition | current/historical API, publication, Workspace routes | E1–E5 | PASS |
| Optional Review evidence and exact setup decision | downstream product-width and PostgreSQL routes | E1–E5 | PASS |
| Natural approvals, clean Harness completion, pending sync/replay | public Workflow/Workspace suites | E1–E5 | PASS |
| Generic Experiment, durable units, exact v5 admission | generic public Workspace plus R3D browser | E1–E6 | PASS |
| v4 → v3 → v5 and four D1 locks | focused lifecycle plus F1F browser | E1–E6 | PASS |
| Skill lifecycle and Cloud-only Project deletion | API/PostgreSQL/public Workspace/Skill browser | E1–E6 | PASS |
| Platform metadata/private-path/real-secret boundaries | package and public runtime matrices | E1–E5 | PASS |
| Real controlled Owner surfaces | cumulative repository Playwright and B0 | E6 | PASS |

## Executed automated evidence

- Focused bounded repair: artifact-reference service `15 passed`; PostgreSQL
  product-width route `1 passed`; decision migration cycle `1 passed`.
- Broad non-database backend qualification: `1124 passed, 5 skipped` in the
  sandboxed run; the exact nine loopback/process/no-egress cases were rerun with
  the approved local elevation and all `9 passed`. Combined qualified evidence:
  `1133 passed, 5 skipped`.
- Every current PostgreSQL test module ran in its own freshly created,
  marker-verified disposable database. Actual current modules passed, including
  artifact-reference `7 passed`, forward downstream v5 `6 passed`, and
  materializable Experiment evidence `3 passed`. Legacy opt-in modules that
  require their old dedicated environment-variable names remained explicit
  skips; their current migration contracts were covered by the isolated current
  harness.
- Full frontend Vitest suite: `21 files / 82 tests passed`.
- TypeScript, full ESLint, Python compile/compileall, `git diff --check`, and
  production Next.js build: PASS. The build and nine exact backend cases used
  only the approved local process/loopback elevation.
- Alembic upgrade, downgrade/re-upgrade routes, `alembic check`, and sole-head
  verification passed on disposable PostgreSQL. Sole head remains
  `20260820_0039`; no migration or immutable publication changed during the
  timezone repair or R7.

## E5 public Workspace evidence

The public copied-Workspace routes passed for exact input reconciliation,
automatic Artifact Index refresh, current plan/receipt readiness, optional
evidence decisions, natural downstream checkpoints, terminal Progress replay,
Generic Experiment execution-unit resume and v5 admission, presentation
backfill, managed Skills, deleted-Project orphan safety, and the four repaired-
D1 lifecycle locks. Complete research bytes remained Local; Cloud received only
the existing bounded contracts.

## E6 repository-native browser evidence

The controlled real FastAPI/Next.js/system-Chrome matrix passed cumulatively:

- `local-v0-1.spec.ts`
- `h1-product-journey.spec.ts`
- `f1f-product-width.spec.ts`
- `r3d-generic-harness.spec.ts`
- `r4-literature-consolidation.spec.ts`
- `skill-m1.spec.ts`

The first combined pass completed eight of nine scenarios; the sole H1 case was
then rerun from its first failed gate after aligning stale qualification wording
to accepted R5/R6 contracts and passed, including the exact disposable-database
isolation audit. This is cumulative `9/9` scenario evidence, not a substitution
with mocked components.

The independent B0 controlled-browser gate also passed all seven checks:
repository Playwright, system Chrome test-body entry, backend and frontend
loopback readiness, exact disposable dataset identity, three screenshot
viewports, and teardown. Verified PNG evidence before intentional temporary-root
cleanup:

- `1440×900`: 167,567 bytes;
- `1280×800`: 112,823 bytes;
- `390×844`: 74,321 bytes.

B0 additionally proved `WORKSPACE_BROWSER_MUTATION=NONE`.

Persistent bounded evidence from the scenario matrix remains under
`.agent_read/tmp/r3d-generic-harness/`,
`.agent_read/tmp/post-d1-r4-literature/`,
`.agent_read/tmp/skill-m1-e6/`, and the R6 responsive review directories.

## Qualification-only alignment

R7 changed no additional product behavior after the bounded timezone repair.
Qualification fixtures were aligned only to already-published/current
authority: current 0039 migration head, current Literature/Idea/Experiment
recommendations, exact manifest revisions, natural decision records, current
role-aware Board structure, Project Help wording, newly installed Workflow sync
target, and `Selected` rather than the ambiguous `Ready` Cloud-binding label.

The isolated runner's H1 database marker was updated from the obsolete fixture
name to the exact Project name the H1 test creates. F1F's distinct historical
isolation marker remains checked separately. No assertion was weakened to avoid
production semantics.

## Cleanup and safety

- Every database created by the isolated harness passed the disposable marker
  check before use and before deletion.
- Final PostgreSQL catalog audit:
  `QUALIFICATION_DATABASE_LEFTOVERS=0`.
- All controlled FastAPI, Next.js, and Chrome processes and dynamic ports were
  stopped by their exact harnesses.
- One inactive 583 MB qualification-copy/runtime directory left by an earlier
  interrupted run was identity-audited (recorded PIDs and port were absent) and
  removed. It contained only disposable copied frontend/runtime state and is not
  recoverable or needed.
- No Owner database, protected D1 row, research Artifact, binding, Progress
  report, or Local Workspace was accessed or changed.

## Historical integrity and new-defect audit

All four D1 regression locks pass: Real Writing recovery, optional Review
evidence, Review-support subset Revision context, and Revision-plan approval
resume. Historical immutable publication checks remain exact.

1. Exact scientific boundary weakened: **NO**.
2. Implicit latest/merge introduced: **NO**.
3. Cloud made authoritative for complete Local bytes: **NO**.
4. User Skill gained Capability/evaluation authority: **NO**.
5. Completed Workflow reruns merely to synchronize: **NO**.
6. New manual Owner orchestration step introduced: **NO**.
7. Immutable publication changed in place: **NO**.
8. Accepted D1 repaired contract changed: **NO**.
9. Fixture changed to avoid production semantics: **NO**.
10. UI made more verbose instead of simpler: **NO**.

No additional HIGH/CORE product defect was exposed after the bounded timezone
repair. R7 full-system qualification passes at E6 with the stated limited
verifier independence.
