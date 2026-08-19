# Post-D1 R1 exact-input and Local-safety repair

Status: **PASS — R1 COMPLETE; R2 NEXT**

Date: 2026-08-20

Authority: R1 of
`.agent_read/progress/2026-08-20_post_d1_repair_program.md`, ADRs 0049–0052,
and the accepted R1 change packet.

## Closed ledger roots

R1 qualified and closed these ten shared roots while retaining their D1
occurrence evidence:

- `D1-INPUT-RECONCILE-01`
- `D1-INPUT-RUNNABLE-01`
- `D1-INPUT-RECEIPT-01`
- `D1-INPUT-REFRESH-01`
- `D1-FRONTEND-KEY-01`
- `D1-WRITING-BINDING-01`
- `D1-REVIEW-INPUT-LIFECYCLE-01`
- `D1-UPSTREAM-ZERO-PAPER-01`
- `D1-PACKAGE-OS-METADATA-01`
- `D1-PACKAGE-PRIVATE-PATH-01`

The broader one-command Owner orchestration root remains assigned to R2.

## Result

R1A makes the last network-observed exact Cloud plan authoritative for Local
readiness. Safe A→B replacement is atomic only for a uniquely proven prior
ReAgent-managed target; unchanged exact siblings are verified and re-receipted
under the new whole-plan identity; ambiguous files fail closed. High-level
materialization reconciles the current Artifact Index automatically, and stale
bytes/receipts cannot yield `RUNNABLE`.

R1B1 keeps optional evidence visible until the Owner records an exact durable
continue-without-optional decision. R1B2 preserves a valid zero-paper Literature
Artifact but publishes forward Idea 0.3 / Capsule 0.4 with one shared exact
content-precondition evaluator for candidates, bind, readiness, and Local
materialization. Browser candidate identity is exact Artifact identity.

R1C implements ADR 0052 in the Workspace coordinator without changing immutable
Capsule validators. Bounded managed `.DS_Store` is handled before package
comparison; unknown files and real secrets still fail closed; private paths are
reported as private-path metadata rather than credentials.

## Publication and migration

R1 added migrations 0035 and 0036 only:

- `20260820_0035`: exact optional-input decisions;
- `20260820_0036`: forward Idea 0.3 / Capsule 0.4 and bounded exact paper-count
  qualification.

Both are forward-additive. Historical publications and migrations remain
byte-identical. Independent marked PostgreSQL databases passed upgrade,
downgrade/re-upgrade, Alembic drift, source/publication, and SQL round-trip
qualification. The direct migration test was corrected to migrate before
creating rows that truthfully reference the new publication; no FK or downgrade
semantics were weakened. The Owner database remains at 0034.

## Consolidated qualification evidence

| Evidence | Result |
|---|---|
| R1 exact-input/platform + four D1 repaired-contract locks | **115 passed** |
| Frontend full component suite | **20 files / 72 tests passed** |
| Focused real FastAPI/Next.js/system-Chrome R1 browser tests | **2 passed** |
| TypeScript | **PASS** |
| ESLint | **PASS** |
| Production Next.js build | **PASS** |
| Python compileall | **PASS** |
| `git diff --check` | **PASS** |
| Alembic sole head | **`20260820_0036`** |

The browser fixture was updated to the exact forward Idea 0.3/0.4 pin and now
reports the bounded selected-paper qualification derived by the controlled Local
fixture. Multiple eligible candidates preserve exactly one previously accepted
binding; the UI does not auto-change it.

The unrelated full EP-D2 browser scenario exposed the already-owned R6 role
projection root more precisely: downstream Detail still hard-codes Revision
recognition to version 0.6 and therefore routes forward 0.7/0.9 through generic
Writing UI. This is merged into `D1-WORKFLOW-ORDINAL-01` / R6 and was not patched
in R1.

## Integrity and prevention gate

- Protected Owner D1 Project and Owner database: **untouched**.
- No real provider or scientific research: **run**.
- Presentation/evidence and User Skill/Capability boundaries: **unchanged**.
- No auto-latest, implicit merge, or Cloud authority over Local bytes: **added**.
- Four D1 repair locks: **PASS**.
- Disposable databases and controlled services: **identity-cleaned/stopped**.
- New-defect prevention questions: **all NO for R1**; the R6-owned routing debt
  is explicitly deferred, not hidden.

Safe next action: begin R2 pre-write recovery and shared Owner-decision/Harness
lifecycle change packet. Do not alter the protected D1 Project.
