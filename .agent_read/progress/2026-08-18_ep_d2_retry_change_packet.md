# Engineering change packet

## 1. Identity and status

- Change ID / title: EP-D2 RETRY — Full Research product width, downstream UX, and preset advancement
- Author / date / baseline: Codex / 2026-08-18 / `e4b85c1c8ba327d24600e6009f7d1051df9bcaae` on `main`, clean, one worktree, Alembic `20260818_0032`
- Packet status: `APPROVED_OWNER_PACKET`
- Implementation authorization: `AUTHORIZED_BY_CURRENT_OWNER_REQUEST`

## 2. Intent and baseline

- Objective, Owner intent, and user problem: expose the already-published v5 Experiment → Initial Writing → Review → Writing Revision chain as a task-first Full Research product, with bounded optional Cloud previews and exact Review-to-Revision creation.
- Current behavior and supported public path: publication and Local Workspace contracts are qualified, upstream Literature/Idea previews are qualified, but the Full Research source pins remain historical, downstream Artifacts have no typed presentation, and forward Writing/Review/Revision pages use the generic Workflow view.
- Authoritative sources and published identities:
  - Literature Search `0.4.0`, Capsule `capsule-e9e6a2e0aa46146818fb6123e03877f3@0.6.0`.
  - Idea Discovery `0.2.0`, Capsule `capsule-3976596c49e3df30e08774233055bcce@0.3.0`.
  - Experiment `0.7.0`, Capsule `capsule-cd7ff18e9857b6d20fbe9ba2ccab7ba6@0.10.0`, `experiment-record/v5`.
  - Initial Writing `0.5.0`, Capsule `capsule-2abb078c2c2112b284f9a7dae8ea2854@0.7.0`, `manuscript-draft/v4`.
  - Review `0.4.0`, Capsule `capsule-133692a783abb9a5061ebd315159a90e@0.6.0`, `review-report/v3`.
  - Writing Revision `0.6.0`, Capsule `capsule-ff1975990022b65f0bfd83514820dd3b@0.8.0`, `manuscript-draft/v5`.

### Pre-write product-width recovery

| Role | Current version | Current Owner-facing presentation | Current checkpoint / next action | Needed EP-D2 change |
|---|---|---|---|---|
| Literature Search | 0.4.0 | Qualified typed paper-library preview | Existing Progress projection | Preserve unchanged |
| Idea Discovery | 0.2.0 | Qualified typed idea preview | Existing Progress projection | Preserve unchanged |
| Experiment | 0.7.0 | v5 can carry the existing bounded Experiment projection; v0.6 detail routing is version-narrow | Generic fallback for 0.7 | Admit exact v5/schema pair and reuse GEN-D detail/renderer |
| Initial Writing | 0.5.0 | Generic Artifact shell only | Generic Progress action and command | Bounded manuscript preview and task-first detail |
| Review | 0.4.0 | Generic Artifact shell only | Generic Progress action and command | Bounded review preview, task-first detail, exact Revision action |
| Writing Revision | 0.6.0 | Generic Artifact shell only | Generic Progress action and command | Bounded revised-manuscript preview and task-first detail |

## 3. Decisions and scope

- Conflicts and authority levels: no source conflict. Presets are source-resolved rather than persisted (ADR 0032), so advancement requires no migration. Published role metadata already distinguishes `INITIAL` from `REVISION`; immutable publication rows remain unchanged.
- Assumptions / unknowns: the optional presentation carrier remains sufficient; short manuscript summaries and section lists are deterministic bounded projections of validated local Artifact fields, not a second scientific authority.
- Owner decisions required or already accepted: GEN-D, EP-D0, EP-D1, F1, and U1 are accepted; the current request explicitly authorizes EP-D2 implementation.
- In scope: exact five-pin fresh Full Research preset; bounded manuscript/review presentations; local report/backfill; v5 Experiment presentation routing; task-first downstream detail; exact idempotent Review-to-Revision metadata action; typed Outputs/selection reuse; controlled E1–E6 qualification.
- Non-goals: scientific contract changes, Capsule changes, migrations, Full Artifact Cloud storage, Path B, Terminal redesign, hosted execution, real D1, real research.
- Deferred findings: generic Workflow foundation HTTP error observability and unrelated stale test debt.

## 4. Contract behavior

- Domain semantics: presentation remains optional UI metadata. Writing/Review/Revision continue to consume exact verified Artifact bytes. Review creates a new immutable Revision instance with exact parent Draft and causal Review bindings.
- State transitions, authority, idempotency, failure, and retry: a finalized review can request one deterministic equivalent Revision; exact replay returns the same instance; differing input identity produces a distinct explicit request. Presentation replay is exact/idempotent, while report failure leaves the Artifact valid and retryable.
- Artifact impact: none to Artifact schemas or checksums. New presentation schemas are bounded companions only.
- API impact: one bounded Project-scoped Review-to-Revision command accepting exact parent/review Artifact IDs; existing presentation endpoint is extended through the exact validator registry.
- Persistence impact: existing Workflow Instance, binding, manifest, and presentation repositories only; no schema migration.

## 5. Product and safety boundaries

- Frontend impact: typed bounded previews, one task-first downstream detail hierarchy, exact Revision action after review evidence, and Owner-facing role labels.
- Security/privacy impact: strict presentation bounds reject code/HTML, credentials, private paths, logs, and oversized or arbitrary nested content; complete manuscript/review/revision bytes stay Local.
- Cloud/local boundary impact: Cloud coordinates exact metadata and bounded previews; Local Workspace validates Artifacts and generates previews; browser never reads or writes Workspace files.

## 6. Compatibility and delivery

- Compatibility/versioning classification: additive presentation schemas and fresh-Project preset advancement; no existing Project or Workflow Instance upgrade.
- Migration impact: `0`; Alembic remains `20260818_0032`.
- Historical immutable versions affected: none; historical publications, Capsules, migrations, Custom compositions, and Project manifests remain byte-identical.
- Rollback conditions: stop before writes if a migration, scientific contract mutation, auto-selection, or more than the authorized scope becomes necessary.

## 7. Implementation budget

- Expected files/directories: `backend/artifact_references/`, `backend/project_workspaces/`, `backend/api/`, `frontend/components/`, `frontend/api/`, focused tests, and this/context progress governance.
- New/modified/deleted file limits: production backend/frontend `<=11`; tests/fixtures `<=7`; governance `<=2`; total `<=20`; migrations `0`.
- Net line or size limits: `<=3200` changed/added lines.
- Scope-expansion approval rule: stop as `EP_D2_SCOPE_EXPANSION` before exceeding a limit or introducing new persistence/scientific architecture.

## 8. Alternatives and verification

- Rejected alternatives: latest/highest-version preset resolution; Revision as a sixth initial row; presentation as binding/evidence; storing full research content; a second presentation table; browser Workspace access; rewriting immutable publications.
- Verification design and required evidence levels: E1 validators/privacy; E2 projection/reporting/components; E3 preset and idempotent causal Revision; E4 disposable PostgreSQL; E5 public Workspace and injected Harness; E6 repository-native controlled browser. E7 is inherited from EP-D1 and is not rerun.
- Acceptance criteria: exact five forward initial Workflows; Revision absent then exactly one; useful bounded typed previews; task-first pages; presentation absence non-blocking; exact sync/lock; historical preservation; clean committed repository.
- Stop conditions: `EP_D2_PRODUCT_WIDTH_SEMANTIC_GAP`, `EP_D2_PRESET_PERSISTENCE_GAP`, migration need, historical checksum drift, or scope expansion.

## 9. Authorization gate

- Packet approval: accepted by the explicit EP-D2 RETRY owner packet.
- Explicit implementation authorization: `YES`, limited to the current owner request.
- Remaining blockers at pre-write recovery: none.

## 10. Qualification outcome

- E1–E5 and build evidence passed: focused backend `53 passed`, focused frontend
  `34 passed`, forward preset/public Workspace `12 passed`, disposable PostgreSQL
  publication/project creation `4 passed`, TypeScript, ESLint, compileall, and the
  production Next.js build.
- F1 made the shared Progress projection use exact published `writing_role` metadata,
  so Initial Writing and Writing Revision remain distinct on the Board, Overview, and
  Activity without version inference. F2 kept the backend exact Artifact-list contract
  unchanged: the frontend-only `all` sentinel now omits `artifact_type`, while typed
  filters serialize exactly. The U1 fixture now reaches production `SELECT_INPUT`
  through current installation, missing required bindings, compatible candidates, and
  no superseding durable Writing Progress checkpoint.
- Focused F2 evidence added `30 passed` frontend tests and `49 passed` backend/API/
  foundation tests. TypeScript, source-scoped ESLint, Python compileall, Alembic head
  `20260818_0032`, and the production Next.js build passed.
- Repository-native E6 used real controlled FastAPI, real Next.js, marked disposable
  PostgreSQL, and system Chrome. Final qualification passed `3/3`: FE-M task-first,
  U1 bounded Outputs/true Writing input selection, and the full forward Full Research
  Owner journey. Thirteen bounded screenshots were captured. Controlled services were
  stopped, the runtime root removed, and the disposable database dropped.
- Verifier independence is `LIMITED`; this same Codex session implemented and verified
  the change. E7 remains inherited from EP-D1 and was not rerun. No Owner D1 or real
  scientific research evidence is claimed.
- Phase status: `PASS_EP_D2_READY_FOR_D1_OWNER_JOURNEY`.
- Safe next action: Owner begins the real D1 journey when ready; do not start it
  automatically.
