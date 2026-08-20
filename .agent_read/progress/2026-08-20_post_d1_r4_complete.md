# Post-D1 R4 research Workflow semantics — complete

## Status

`R4 = PASS_AT_DECLARED_LEVEL`

R4 closes the scientific-semantics phase only. R5 Project/Skill lifecycle and
navigation remains next; R6 presentation/labels remains deferred until R1–R5
semantics are stable.

`VERIFIER_INDEPENDENCE = LIMITED`: the same Codex session implemented and
verified this phase.

## Baseline and scope

- Baseline before R4: `d34e852dd0c7474b8b384909d8a2e71b2e4e8446`.
- R4A query-strategy commit: `a0f6d0e67065a4ae049c8119b75adfaa89334dea`.
- R4B publication/composition/qualification commit:
  `c9938d386a4a14f80e26ec073beecc483a827c0b`.
- Approved packet: `2026-08-20_post_d1_r4_change_packet.md`.
- Ledger scope: `D1-REVIEW-SEMANTICS-01`, `D1-LIT-QUERY-01`,
  `D1-LIT-ITERATIVE-01`, `D1-LIT-SCHEMA-01`, and
  `D1-SKILL-AUTHORITY-01`.
- Protected Owner D1 database, Project, Workspace, Artifacts, bindings, and
  Progress were not accessed or changed.

## Exact source changes

- Forward Literature Search is Definition 0.6 / Capsule 0.8. Its immutable
  instructions require bounded DIRECT, SUPPORTING, CONTEXTUAL, and BACKGROUND
  query families, Owner-reviewed adaptation, no global novelty inference, and
  explicit Skill non-authority.
- Literature Consolidation 0.1 / Capsule 0.1 uses two distinct exact required
  roles: `base_library` and `additional_library`. It performs no network call,
  does not infer latest, reads only materialized exact inputs, preserves source
  order, deduplicates stable identities deterministically, records exact Owner
  dispositions, and emits one content-addressed `selected-paper-library/v1`.
- New Full Research Projects retain five initial Workflows and advance only the
  Literature pin to 0.6/0.8. Consolidation is catalog-available but not initial.
- Review 0.4/0.6 and the four accepted D1 repairs were not changed. R4 confirms
  that omitted authoring provenance is unavailable to Review and cannot be cited
  as independently verified evidence.
- `selected-paper-library/v1` is unchanged. The existing exact Owner-decision
  snapshot preserves `UNCERTAIN` separately from `EXCLUDED`.

## Publication and migration

- One schema-free additive migration: `20260820_0039`.
- New Literature contract checksum:
  `sha256:d1f2cee4cd570826276977854e2ab178e925e0f10b3331f9fc5fac1bd9038afc`.
- New Literature Capsule ID/checksum:
  `capsule-5d6056c7c5e6a9d8df6bbdab161c2fb0` /
  `sha256:5d6056c7c5e6a9d8df6bbdab161c2fb055bfcf9dcd76ff8cbefcefcb06b71325`.
- Consolidation contract checksum:
  `sha256:e5a9c0b39b0334142df047ea88fffcdff80f7fc0cd82667413db6ba6c58898f1`.
- Consolidation Capsule ID/checksum:
  `capsule-8b7d8665c2ede6b050995c4e196c9a2f` /
  `sha256:8b7d8665c2ede6b050995c4e196c9a2fb29c0d2b83807a58008454dcfb514a9e`.
- Alembic sole head: `20260820_0039`.
- Upgrade, downgrade to 0038, re-upgrade, `alembic check`, source/database
  equivalence, and Foundation idempotency passed on marked disposable
  PostgreSQL. Each migration-roundtrip test used its own database because those
  tests intentionally downgrade and use fixed fixture identities.
- No historical migration or immutable publication file changed.

## Verification matrix

| Requirement | Evidence | Level | Fixture | Result |
|---|---|---|---|---|
| Forward query families and Skill non-authority | `test_r4_research_semantics.py` | E1 CONTRACT | synthetic package build | PASS |
| Review provenance/scope/verified-evidence separation | R4 semantics plus D1 Review lock | E1–E3 | production validator fixtures | PASS |
| Two exact sources, deterministic dedupe, Owner disposition, replay negatives | `test_literature_consolidation.py` | E1–E2 | synthetic exact bytes | PASS |
| Public sync/materialize/run and downstream exact selection | `test_r4_literature_consolidation_workspace.py` | E5 FAKE_HARNESS | disposable Workspace | PASS |
| Publication/migration/source equivalence | `test_literature_strategy_and_consolidation_postgresql.py` | E4 MIGRATION | marked disposable PostgreSQL | PASS |
| Browser catalog, two-role no-auto-bind, Local run, downstream binding | `r4-literature-consolidation.spec.ts` | E6 CONTROLLED_BROWSER + E5 FAKE_HARNESS | real controlled API/UI/DB, disposable Workspace | PASS |

## Executed evidence

- Backend/local/service/D1-lock group: `165 passed`.
- Historical immutable publication group: `37 passed`.
- Frontend Vitest: `20 files / 76 tests passed`.
- TypeScript and full ESLint: PASS.
- Production Next.js build: PASS. The sandboxed attempt was unable to bind a
  Turbopack worker port; the identical build passed with the required process
  permission, and controlled E6 also built the production frontend.
- Focused PostgreSQL: R4 publication `2 passed`; owner-decision historical
  roundtrip `1 passed`; input-setup historical roundtrip `2 passed`; all
  disposable databases were identity-verified and dropped.
- Controlled browser/system Chrome: `1 passed`; database
  `reagent_qualification_59d1eba31c9645fd92e89eeaf0bdf340` was dropped and
  controlled processes stopped.
- Python compileall and `git diff --check`: PASS.
- Screenshots:
  `.agent_read/tmp/post-d1-r4-literature/exact-candidate-choices.png`,
  `exact-two-source-confirmed.png`, and
  `composite-selected-downstream.png`.

## Verification limits

- Highest achieved level is E6 for the controlled product path.
- The Harness is deterministic/fake; this does not claim E7 Real Codex.
- No E8 protected long-lived Workspace or E9 Owner research run was performed.
- No external provider was called and no uncontrolled research was executed.
- The long generic input page is an existing R6 subtractive-UX concern; it did
  not compromise exact candidate identity or explicit selection in R4.

## Historical and architecture review

- Historical Literature 0.5/0.7, Review, Writing, Revision, Experiment, and all
  prior migrations remain byte-identical.
- The four D1 regression locks pass: Real Writing provenance/recovery, Review
  optional evidence, Revision subset support, and Revision approval resume.
- No implicit latest/merge, browser Workspace access, hosted research execution,
  second Artifact store, second Agent runtime, or User-Skill authority was added.
- Cloud stores exact metadata/lineage; complete paper-library bytes are combined
  only in the Local Workspace.

## Ledger result

- `D1-LIT-QUERY-01`: `FOUND_AND_REPAIRED_POST_D1`.
- `D1-LIT-ITERATIVE-01`: `FOUND_AND_REPAIRED_POST_D1`.
- `D1-SKILL-AUTHORITY-01`: `FOUND_AND_REPAIRED_POST_D1` for forward wording;
  the historical D1 observation remains recorded.
- `D1-REVIEW-SEMANTICS-01`: `FOUND_AND_REPAIRED_DURING_D1`, with R4 audit and
  regression coverage confirming the accepted Review optional-evidence repair.
- `D1-LIT-SCHEMA-01`: `EXPECTED_BEHAVIOR`; no schema change is justified because
  exact durable decision state preserves the semantic distinction.

## New findings and safe next action

No new product defect was found. The first controlled browser attempt exposed an
incomplete readiness registry count; it was fixed within R4. Two later failures
were qualification-fixture ordering/projection mismatches and were corrected
without weakening product behavior.

Proceed to R5 Project/Skill lifecycle and stable navigation only. Do not start R6
presentation work or touch the protected Owner D1 state.
