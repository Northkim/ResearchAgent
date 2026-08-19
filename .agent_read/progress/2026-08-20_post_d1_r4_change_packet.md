# Engineering change packet — Post-D1 R4 research Workflow semantics

> Completing this packet does not authorize implementation. The Owner's
> Post-D1 Consolidated Repair Program separately authorizes the bounded R4 work.

## 1. Objective

Repair the confirmed Review-scope wording boundary, make forward Literature
search strategy researcher-oriented, preserve exact uncertain screening state,
remove any implication that a user Skill is scientific authority, and provide an
explicit provenance-preserving way to consolidate multiple Literature rounds.

## 2. Owner intent

The Owner supplies a research direction/question and optional domain keywords.
The Agent proposes bounded direct, supporting, contextual, and background query
families and adapts them with Owner review. Literature remains iterative, but no
consumer may infer latest or silently merge results. Review distinguishes
authoring provenance, evidence available in its scope, and evidence it actually
verified. User Skills guide Harness behavior only.

## 3. User problem

- Literature 0.5 asks for query variants but does not require a research-strategy
  model, so D1 overfit retrieval to the exact research-question wording.
- A Project can contain multiple exact paper-library Artifacts, but each current
  downstream requirement accepts one exact Artifact and has no composition path.
- Review can accurately omit optional evidence, yet Owner-facing review language
  must not turn “unavailable in this Review scope” into “unavailable to the
  authoring Workflow” or invalid manuscript provenance.
- A D1 finalization message attributed evidence disposition to a pinned Skill,
  which risks conflating instructions with scientific authority.
- `selected-papers/v0.2` places all non-selected candidates in `exclusions`, even
  though durable `memory/owner-decisions.json` separately preserves UNCERTAIN and
  EXCLUDED decisions.

## 4. Current baseline

- Branch `main`; baseline HEAD
  `d34e852dd0c7474b8b384909d8a2e71b2e4e8446`; clean; one worktree.
- Repository Alembic sole head `20260820_0038`.
- Current forward Literature is Definition 0.5 / Capsule 0.7 and publishes
  `selected-paper-library/v1`.
- Current forward Idea is Definition 0.4 / Capsule 0.5 with an exact non-empty
  library qualification precondition.
- Current forward Review is Definition 0.4 / Capsule 0.6 and publishes
  `review-report/v3`; its contextual validator already limits issue references to
  the exact manuscript plus optional evidence actually bound to Review.
- The protected D1 Owner Project and database are read-only acceptance evidence.

## 5. Authoritative sources

- `docs/PROJECT_DEVELOPMENT_PLAN.md` and the Owner's Post-D1 R4 authorization.
- `.agent_read/progress/2026-08-20_final_d1_defect_ledger.md` rows
  `D1-REVIEW-SEMANTICS-01`, `D1-LIT-QUERY-01`, `D1-LIT-ITERATIVE-01`,
  `D1-LIT-SCHEMA-01`, and `D1-SKILL-AUTHORITY-01`.
- ADRs 0020, 0027, 0039, 0047, 0048, 0050, 0051, and 0053.
- `backend/workflow_packages/template.py` and
  `backend/workflow_packages/production_workflows.py` for published Literature
  packages.
- `backend/artifact_references/review_contract_compatibility.py` for Review scope
  and independently usable evidence.
- Artifact requirement/binding persistence and services, which allow one active
  exact binding per requirement key.

## 6. Conflicts

- A generic multi-binding interpretation conflicts with the active-binding unique
  index and R1's per-requirement replacement/readiness semantics. It is rejected.
- Changing `selected-paper-library/v1`, Literature 0.5/0.7, Review 0.4/0.6, or an
  existing migration in place conflicts with immutable publication authority.
- Treating every omitted Review source as invalid conflicts with accepted optional
  Review evidence semantics.
- Reclassifying user Skill instructions as reviewed evaluation authority conflicts
  with ADR 0047 and the global trust boundary.

## 7. Scope

- Publish forward Literature Definition 0.6 / Capsule 0.8 with explicit bounded
  query-family roles and explicit non-authority language for pinned/user Skills.
- Add one reviewed local `Literature Consolidation` Workflow that requires exactly
  `base_library` and `additional_library`, both exact
  `selected-paper-library/v1`, and publishes one new exact
  `selected-paper-library/v1` only after Owner-reviewed deduplication and selection.
- Preserve the exact two source bindings as the composition Workflow's Cloud
  lineage and Local input provenance. A later consolidation may recursively bind a
  prior consolidated library plus another exact round.
- Advance only new Full Research Projects to Literature 0.6/0.8; do not add the
  consolidation Workflow as a sixth initial Workflow.
- Add focused Review semantic regression coverage and audit the existing v0.2
  uncertain/excluded preservation boundary.
- Update governance records and the authoritative ledger only after qualification.

## 8. Non-goals

- No implicit latest, automatic merging, global multi-binding redesign, or sibling
  Workflow private reads.
- No changes to `selected-paper-library/v1`, selected-research-idea, manuscript,
  Review, Revision, or Experiment Artifact schemas.
- No automatic extra Literature round, provider expansion, global novelty claim,
  hosted execution, or Cloud Artifact-byte storage.
- No redesign of Review/Outputs presentation or other R6 UX.
- No Owner database migration or protected D1 Project mutation.

## 9. Domain semantics

- Query families are classified as DIRECT, SUPPORTING, CONTEXTUAL, or BACKGROUND;
  each query declares its purpose and evidence boundary before provider transport.
- Query adaptation may broaden or narrow within the existing three-call/fifteen-
  candidate bound and must remain Owner-reviewed.
- A Literature round remains an immutable scientific result. Consolidation is a
  separate exact scientific action, not an update to either source.
- Consolidation deduplicates only exact provider/OpenAlex/DOI identity, preserves
  source order deterministically, and requires the Owner to resolve the final
  selected/uncertain/excluded dispositions.
- Review authoring provenance is preserved even when a source is absent from Review.
  Such a source is UNAVAILABLE for independent verification in that Review scope
  and cannot be cited by Review issues.
- Skill instructions may shape process; Artifact evidence, exact Owner decisions,
  and validators determine admissible scientific output.

## 10. State transitions

- Literature 0.6: CREATED → bounded plan proposed → Owner plan decision recorded →
  provider transport → exact screening decisions → Owner finish → one immutable
  library Artifact → pending/synced terminal Progress. Authority and retry remain
  the existing exact local state/receipt path.
- Consolidation: CREATED → select exact base and additional libraries → current-plan
  materialization → present deduplication/composition plan → exact Owner screening
  decisions → Owner finish → one immutable consolidated library → pending/synced
  terminal Progress.
- Replaying finalization with identical source bindings and bytes returns the same
  content-addressed Artifact/Progress identities and creates no duplicate.
- Binding or source checksum drift invalidates setup and fails closed; it never
  silently recomputes a scientific selection.
- A consolidated Artifact may be used as `base_library` in a later instance. The
  graph is explicit and acyclic because an instance can bind only already-published
  project Artifacts.

## 11. Artifact impact

- `selected-paper-library/v1` bytes and validator remain unchanged.
- Literature 0.6 continues to publish v1.
- Consolidation also publishes v1 from validated local candidate/selection sources;
  its exact predecessor lineage is retained by the producer Workflow's two bindings,
  materialization receipts, and input provenance.
- No presentation can substitute for either source Artifact. Downstream consumers
  still bind exactly one final v1 library.

## 12. API impact

- Existing generic Workflow-instance creation, candidate listing, exact binding,
  input-setup decision, materialization, Artifact reporting, and Progress APIs are
  reused.
- No new Artifact endpoint, wildcard, auto-selection, or server merge endpoint.
- The new Workflow appears through the existing reviewed catalog and generic create
  operation.

## 13. Persistence impact

- No mutable table is required.
- One forward migration publishes immutable Literature 0.6/0.8 and Literature
  Consolidation 0.1/0.1 rows, its two exact requirements, and catalog/preset pins.
- Existing Projects and Workflow Instances receive no update. Existing Project rows
  gain no consolidation association by default.

## 14. Frontend impact

- Existing generic Workflow catalog/board/detail and exact-input selection surfaces
  should carry the new consolidation Workflow. Only a narrow label/summary addition
  is allowed if the generic registry lacks a truthful name.
- R6 owns broad layout, ordinal, output-label, and information-hierarchy work.

## 15. Security impact

- Provider access remains only through the bounded Literature proxy path.
- Consolidation performs no network call and reads only two exact materialized input
  files in its Capsule.
- No credentials, private paths, complete local repository, or transcripts enter
  Cloud. Strict validators and exact checksums remain fail closed.

## 16. Cloud/local boundary impact

- Cloud stores publications, exact predecessor bindings, Artifact metadata,
  qualification, and bounded Progress/presentation only.
- Local Workspace materializes and combines complete paper-library bytes. Cloud does
  not inspect or merge the scientific bytes.
- The Browser chooses exact Artifacts but never reads or writes Workspace files.

## 17. Compatibility and versioning

- Literature prompt/Skill/contract change: compatible forward Definition 0.6 and
  Capsule 0.8; historical 0.5/0.7 remains byte-identical.
- New Literature Consolidation: Definition 0.1 and Capsule 0.1.
- `selected-paper-library/v1`: unchanged-compatible output contract.
- Review 0.4/0.6: unchanged; focused tests lock already-accepted optional-evidence
  semantics instead of mutating publication bytes.
- Full Research remains exactly five initial Workflows and advances only its
  Literature pin for newly created Projects.

## 18. Migration impact

- Expected migration: exactly one schema-free forward publication migration,
  `20260820_0039`.
- It must pass clean upgrade, downgrade to 0038, re-upgrade, source/database exact
  equivalence, and sole-head checks on marked disposable PostgreSQL.
- Owner database remains at its current revision until the complete relevant phase
  is qualified and separately authorized for upgrade.

## 19. Files expected to change

- Production: bounded changes under `backend/workflow_packages/`,
  `backend/project_workspaces/`, one migration under
  `backend/database/migrations/versions/`, and at most one narrow frontend registry
  label file if required.
- Tests: focused Workflow-package, Artifact/publication, preset/sync, PostgreSQL, and
  optional Review semantic tests.
- Governance: this packet, one ADR, R4 report, ledger, and context.
- R4 limit: at most 20 production files and 4,000 net production lines. Split into
  R4A/R4B before writes if recovery exceeds either bound.

## 20. Rejected alternatives

- Multiple active bindings for one requirement key: rejected because it changes the
  binding/persistence/materialization model globally and risks R1.
- Implicitly union every Project library or pick latest: rejected because it removes
  Owner authority and exact lineage.
- In-place v1 schema expansion: rejected because the Artifact contract is published.
- A Cloud merge endpoint: rejected because complete Artifact bytes are Local
  authority.
- Making every downstream Workflow accept a new v2 library: rejected as unnecessary
  version proliferation when a separate exact producer can lawfully emit v1.
- Treating uncertain as selected or excluded without durable Owner disposition:
  rejected as scientific state loss.

## 21. Test design

- Query strategy: four family roles, bounded call/candidate limits, Owner plan gate,
  no global novelty claim, and explicit Skill non-authority.
- Consolidation: exact two requirements, no candidate auto-binding, exact Local
  materialization, deterministic deduplication, preserved source order, explicit
  selection, one v1, replay idempotency, recursive prior-composite case, and source
  mismatch rejection.
- Schema audit: UNCERTAIN and EXCLUDED remain distinct in durable Owner decisions and
  final selected output cannot disagree with that snapshot.
- Review: omitted authoring source projects UNAVAILABLE/not independently verifiable;
  issue use of omitted source rejects; bound same-role mismatch rejects.
- Publication: source/database exact equality, historical checksums, new-project
  five-workflow composition, historical Projects unchanged, Workspace first sync /
  second NO_CHANGE.
- Controlled browser/local E6: create additional Literature and consolidation,
  select two exact libraries, materialize, finish through deterministic Harness,
  and select the resulting exact library downstream. No real provider.
- Run all four accepted D1 regression locks.

## 22. Acceptance criteria

- Researcher-oriented query-family planning is present in the forward package.
- User Skill wording cannot claim scientific disposition authority.
- Two exact Literature rounds can be explicitly consolidated without implicit latest
  or schema mutation; downstream consumes exactly the consolidated Artifact.
- Review clearly and mechanically distinguishes provenance, scope availability, and
  evidence it may cite.
- UNCERTAIN screening survives resume and is not silently converted.
- New Full Research still creates exactly five initial Workflows.
- Migration/publication and controlled public Workspace/browser qualification pass.
- Protected D1 fingerprints remain unchanged; repository is clean after the R4
  commit(s).

## 23. Rollback conditions

- Before publication, revert only unpublished R4 source/fixtures.
- After immutable rows are published in a qualified database, rollback uses the
  tested migration downgrade only in disposable qualification; accepted user state
  is never deleted or rewritten.
- If v1 cannot truthfully retain exact composition provenance through Workflow
  lineage, stop before migration with `HISTORICAL_CONTRACT_CONFLICT` and design a
  forward Artifact schema rather than weakening provenance.

## 24. Stop conditions

- Historical Capsule/Definition/schema/migration bytes would need mutation.
- Multi-input implementation requires global active-binding or materializer changes.
- Composition would rely on latest, implicit merge, sibling private reads, or Cloud
  Artifact bytes.
- User Skill must become evaluator/Capability/scientific authority.
- Review optional-evidence or Revision subset regression locks fail.
- A second migration or more than 20 production files / 4,000 production lines is
  required without a packet amendment.
- Real provider, Owner database, protected D1 Workspace, or destructive research
  mutation becomes necessary.

## 25. Owner decisions

- Already accepted by the Post-D1 program: explicit exact composition rather than
  implicit latest/merge; forward-additive publication when required; Skill guidance
  is non-authoritative; Review evidence-scope distinctions; no speculative v1 schema
  change.
- Implementation authorization: `AUTHORIZED_BY_POST_D1_PROGRAM`, subject to this
  packet's bounds and stop conditions.
- Packet status: `READY_FOR_IMPLEMENTATION_REVIEW`.
- Remaining Owner decisions: none before bounded implementation. Any need for a new
  Artifact schema or global binding cardinality change becomes
  `OWNER_DECISION_REQUIRED`.
