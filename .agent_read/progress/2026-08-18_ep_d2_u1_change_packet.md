# EP-D2-U1 engineering change packet

## 1. Objective

Add bounded, deterministic Owner-facing presentation companions for exact
`selected-paper-library/v1` and `selected-research-idea/v1` Artifacts, including
automatic Local reporting, idempotent backfill through `artifact refresh`, and
typed Outputs/input-selection rendering.

## 2. Owner intent

Close only `UPSTREAM_PRESENTATION_GAP`. Cloud coordinates and stores bounded UI
metadata; exact Artifact bytes and scientific authority remain Local. The explicit
EP-D2-U1 prompt authorizes implementation after this packet.

## 3. User problem

Owners currently see Artifact identity and completion metadata but cannot see which
papers or research direction they are selecting without opening Local JSON.

## 4. Current baseline

`main` at `9c58c372e59960b5686802178cd8fbbf86119f8d`, clean, one worktree,
Alembic sole head `20260818_0032`. EP-D1 is accepted; EP-D2 is stopped.

## 5. Authoritative sources

- Owner EP-D2-U1 authorization and accepted ODR-009/010/011.
- Immutable Literature 0.4/Capsule 0.6 and Idea 0.2/Capsule 0.3 publications.
- Local Artifact builders/validators in `backend/workflow_packages/production_workflows.py`.
- Artifact presentation persistence/service in `backend/artifact_references/`.
- Standalone public client in `backend/project_workspaces/workspace_cli.py`.
- Current Outputs and exact-selection components under `frontend/components/`.

## 6. Conflicts

No blocking authority conflict. Planning asks for candidate/exclusion counts, scope,
methodology, constraints, reproducibility, and claim boundaries only where exact
fields exist. The immutable Artifacts do not carry several of these fields, so they
are explicitly omitted. This is compatible with the Owner's A/B/NOT_SUPPORTED rule.

## 7. Scope

- Two exact presentation schemas and validators.
- Static Artifact-type/schema/validator registry preserving Experiment v4.
- Deterministic Local projection from verified final Artifact bytes.
- Best-effort future reporting and idempotent backfill via `artifact refresh`.
- Typed Outputs, exact-selection, and minimal completed Workflow preview reuse.
- Focused E1-E6 and historical regression evidence.

## 8. Non-goals

No scientific contract/runtime change, Full Research preset, downstream previews,
Experiment change, D1, Path B, Terminal redesign, full Artifact upload, new table,
or browser Workspace access.

## 9. Domain semantics

Presentation is a non-authoritative immutable projection. Paper order is preserved.
Only exact fields or conservative counts/labels are projected. Absence never blocks
binding or materialization.

## 10. State transitions

- Verified Artifact + no presentation + Local report -> exact immutable presentation.
- Same exact report replay -> same stored presentation and success.
- Different report for same Artifact -> immutable conflict.
- Invalid/drifted local bytes -> no report, fail closed for explicit refresh.
- Future finalization report transport failure -> Artifact remains valid; preview is
  absent and retryable through `artifact refresh`.
- Browser selection -> exact Artifact binding only; presentation state never changes
  binding identity.

## 11. Artifact impact

Artifact schemas/checksums/bytes are unchanged. Add companion schemas
`reagent.artifact-presentation.selected-paper-library/v0.1` and
`reagent.artifact-presentation.selected-research-idea/v0.1`.

## 12. API impact

Reuse `PUT /projects/{project_id}/artifacts/{artifact_id}/presentation`. Dispatch is
by exact Artifact type plus presentation schema. Unknown pairs fail closed.

## 13. Persistence impact

Reuse the four existing presentation columns on `local_artifact_references`. No ORM
or database schema change and no migration.

## 14. Frontend impact

Add bounded presentation renderers to Outputs, exact candidate cards, and completed
upstream Workflow output area. Missing preview presents one Local refresh command.

## 15. Security impact

Strict 65,536-byte maximum; bounded counts/text/authors; no abstracts, raw candidates,
HTML/code, credentials, URLs, paths, logs, provider payloads, NaN/Infinity, or arbitrary
nested data.

## 16. Cloud/local boundary impact

Projection generation and Artifact verification are Local. Cloud receives only the
exact-bound bounded companion. Browser reads Cloud metadata only.

## 17. Compatibility and versioning

Existing Experiment v4 behavior is unchanged-compatible. Literature/Idea companions
are new optional v0.1 contracts. Historical Artifact consumers remain unchanged.

## 18. Migration impact

Zero migrations; sole head remains `20260818_0032`.

## 19. Files expected to change

Production maximum nine: one new upstream presentation module; Artifact contracts
and service; Workspace CLI; frontend API type; one shared renderer; Outputs,
input-selection, and Workflow Detail components. Tests maximum six. Governance
maximum two.

## 20. Rejected alternatives

Full Artifact upload, browser Local reads, Progress prose parsing, dynamic plugin
registry, per-type endpoints/tables, scientific schema mutation, and Capsule edits.

## 21. Test design

E1 validators/unsafe negatives and registry pairing; E2 deterministic projection,
future report/backfill/idempotency/drift; E3 service/API and selection; E4 existing
PostgreSQL roundtrip; E5 disposable Workspace without research rerun; E6 real
Playwright/Chrome. Historical Experiment presentation and Artifact binding regressions.

## 22. Acceptance criteria

Both typed previews are useful and bounded; DOI/stable identity and limitations are
visible; absence remains truthful; exact selection remains explicit; automatic and
backfill reporting are idempotent; no scientific authority or bytes move to Cloud;
no migration; screenshots and clean commit exist.

## 23. Rollback conditions

Before commit, revert only unpublished EP-D2-U1 source if schema pairing, privacy,
historical checksum, or browser evidence fails. Never delete existing Artifact or
presentation state.

## 24. Stop conditions

Stop for insufficient Artifact content, historical Capsule drift, schema identity
conflict, new persistence need, browser/Workspace bridge, implicit selection, scope
over 17 files/2,400 lines, or unavailable release-blocking browser evidence.

## 25. Owner decisions

Packet status: `READY_FOR_IMPLEMENTATION_REVIEW`.

Packet approval: supplied by explicit EP-D2-U1 authorization.

Implementation authorization: `AUTHORIZED_EP_D2_U1_ONLY`.

Remaining blockers: none before bounded implementation.

## Verification record

- Verification date/baseline: 2026-08-18; U1 began at
  `9c58c372e59960b5686802178cd8fbbf86119f8d` and completed after the isolated
  foundation correction `0e97bf039a68c589247fa543de7493cde9e60309`.
- Verifier independence: `LIMITED` (the same Codex session implemented the change).
- Implementation scope: two upstream presentation contracts, a fixed registry,
  Local projection/report/backfill, and bounded frontend reuse only.
- E1/E2/E3: PASS on 159 focused backend tests and 62 frontend component tests.
  Fixtures are synthetic/controlled; the public `artifact refresh` parser path is
  exercised with a fake loopback transport and proves idempotent no-rerun backfill.
- Build: TypeScript, ESLint, and production Next.js build PASS. The first build was
  sandbox-blocked because Turbopack could not bind a helper port; the approved
  escalated rerun passed.
- E4: marked disposable PostgreSQL upgraded cleanly to `20260818_0032`; Alembic
  check passed; six current presentation carrier tests passed and the database was
  identity-verified and dropped. One historical GEN-D migration test has a stale
  hard-coded expectation for head `20260817_0030` and failed at current accepted
  head `20260818_0032`; no migration was added or changed here.
- E5: the supported `python reagent_local.py artifact refresh .` path passes in a
  disposable synthetic Workspace without Harness/research rerun. Long-lived Owner
  Workspace evidence was not run and is not claimed.
- Browser launch: PASS with repository Playwright 1.61.1 and system Chrome channel
  `chrome`.
- F2 fixture alignment: PASS. The controlled fixture now verifies one exact output
  declared by the latest Progress report and three valid Workflow Artifacts; no
  production aggregation behavior changed. All other U1 working-set bytes remained
  unchanged before the governance closeout.
- Focused F2 rechecks: backend U1 tests 17/17, frontend U1/board tests 23/23, and
  historical Experiment presentation validator tests 7/7 PASS.
- E6: PASS 2/2 using repository Playwright, system Chrome, real controlled FastAPI,
  real Next.js, and marked disposable PostgreSQL. Typed Literature/Idea Outputs,
  DOI/stable identity, limitations, exact-selection previews, preview absence,
  three-candidate no-auto-bind behavior, secondary Technical Details, and the
  foundation-sensitive Project-creation journey all passed.
- Screenshot evidence:
  `frontend/test-results/ep-d2-u1-e6/screenshots/01-upstream-outputs-typed-previews.png`,
  `02-literature-exact-selection-multiple-candidates.png`,
  `03-writing-literature-idea-selection-previews.png`, and
  `04-idea-exact-selection-for-experiment.png`.
- Cleanup: the successful runner stopped FastAPI/Next.js and dropped
  `reagent_qualification_17fe12f3845f4de699184877bfad8a86`; zero disposable
  databases, runtime roots, or controlled listeners remained. Owner DB was not
  accessed.
- Architecture drift: none found in the implementation. Artifact bytes, binding,
  presentation authority, Capsule bytes, Full Research pins, D1, and Alembic remain
  unchanged.
- Verification outcome: `PASS_EP_D2_U1_READY_TO_RETRY_EP_D2` with verifier
  independence `LIMITED`.
- Safe next action: retry EP-D2 from the clean committed U1 baseline; do not begin it
  automatically and do not resume D1.
