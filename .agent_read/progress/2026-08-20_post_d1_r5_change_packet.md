# R5 change packet: Project / Skill lifecycle and stable navigation

## 1. Objective

Close the seven R5 ledger findings with one bounded lifecycle/navigation change:
make Project entry stable, make Owner-managed Skill provenance and safe deletion
discoverable, and add explicit transactional Cloud-only Project deletion while
leaving every Local Workspace byte untouched.

## 2. Owner intent

The Owner authorized R5 in the Post-D1 Consolidated Repair Program. Cloud owns
Cloud Project state; the user owns Local Workspace files. User-managed Skills
remain mutable reusable Agent instructions and never become reviewed Skills,
ExperimentCapabilities, or scientific authority.

## 3. User problem

Project-scoped Skills can trap navigation, empty states provide no escape, and
the library hides existing detail/delete capabilities. Project portfolio actions
can enter Help instead of Overview. Project Help duplicates the global Local
Guide. Cloud Projects have no explicit deletion lifecycle, leaving mistakes and
test Projects permanently visible.

## 4. Current baseline

- Branch: `main`
- HEAD: `67da8f1e7478d38a72d3be942e32be24f926fbb3`
- Worktree: clean; one worktree
- Alembic sole head: `20260820_0039`
- Published Workflow Definition/Capsule and Artifact contracts: unchanged by R5
- Owner D1 Project/database: protected; neither is a qualification fixture
- Existing Skill service/API already implements get and safe delete; frontend
  does not expose them.
- Project creation spans `local_projects`, canonical `projects`, manifests,
  Workflow Instances, exact inputs, Progress, Workspace acknowledgements, and
  optional hosted-compatibility rows. No Project deletion operation exists.

## 5. Authoritative sources

- Post-D1 repair authorization and R0 map
- `.agent_read/progress/2026-08-20_final_d1_defect_ledger.md`
- ADR 0047, separate Owner-managed Agent Skills
- Owner Project-deletion intent recorded during D1
- `docs/PROJECT_DEVELOPMENT_PLAN.md`
- `docs/engineering/SOURCE_OF_TRUTH_POLICY.md`
- ODR-009, ODR-010, ODR-011, ODR-013, ODR-014
- Current persistence mappings and FKs in `backend/database/orm/models.py`
- Current Skill service/API in `backend/user_skills.py` and
  `backend/api/routers/project_workspaces.py`

## 6. Conflicts

There is no immutable-publication conflict. The persistence graph does not have
uniform `ON DELETE CASCADE`; relying on a single parent-row delete would fail or
leave legacy project-scoped rows. R5 therefore needs one centralized deletion
operation with an explicit dependency order. This is not ad hoc API deletion:
the ownership graph is encoded once at the persistence transaction boundary and
qualified against PostgreSQL.

Project-scoped immutable Progress content objects and generated Capsule delivery
files are outside the relational record lifecycle and are not directly
addressable after relational deletion. R5 does not broaden the immutable content
storage port into a general destructive filesystem API. Any future physical
retention/erasure policy is a separate storage-governance decision.

## 7. Scope

Ledger IDs:

- `D1-SKILL-NAV-01`
- `D1-SKILL-EMPTY-01`
- `D1-SKILL-DETAIL-01`
- `D1-SKILL-LIFECYCLE-01`
- `D1-PROJECT-NAV-01`
- `D1-LOCAL-GUIDANCE-IA-01`
- `D1-PROJECT-LIFECYCLE-01`

Implement a small Skill detail route, safe delete UI, unscoped global Skills
navigation, actionable project-scoped empty state, stable Project Overview entry,
concise contextual Help, Cloud Project delete API/service/UI, and deleted-Project
Workspace error handling.

## 8. Non-goals

- No archive/restore lifecycle, recycle bin, batch deletion, Skill marketplace,
  Skill version history, ratings, Capability promotion, or Local cleanup.
- No deletion or mutation of Workflow/Capsule/Artifact contracts.
- No physical access to or cleanup of a user's Local Workspace.
- No Owner database migration or protected D1 Project action.
- No R6 visual/label redesign beyond the directly owned navigation surfaces.

## 9. Domain semantics

- A User Skill record is global reusable metadata. Project deletion removes only
  its association, never the Skill.
- Skill deletion succeeds only at usage count zero; attached deletion returns the
  existing `USER_SKILL_IN_USE` conflict.
- Project deletion is an explicit destructive Owner action against one exact
  Project ID. It removes all relational Project-owned Cloud state atomically.
- Local Workspace content is never an input or target of Cloud deletion.
- A Local Workspace whose exact Project no longer exists is orphaned. It cannot
  recreate/rebind the Project and receives `PROJECT_NOT_FOUND` before sync writes.

## 10. State transitions

| Before | Event / authority | After | Idempotency / retry | Durable evidence |
|---|---|---|---|---|
| Skill unattached | Owner deletes exact Skill | Skill absent | Repeat returns not found | Skill row absent |
| Skill attached | Owner deletes exact Skill | No change; conflict | Safe retry after detach | Associations and Skill unchanged |
| Project exists | Owner confirms delete | All Project-owned relational rows absent; global records remain | Repeat returns not found | Transaction commit |
| Project delete transaction fails | Persistence error | Entire Project remains visible | Safe retry | Transaction rollback |
| Workspace references deleted Project | High-level Local cloud preflight | `PROJECT_NOT_FOUND`; no Local mutation | Safe repeat | Unchanged local tree |

The destructive action is not idempotent as a success response: a second delete
fails closed with Project not found rather than implying that another identity
was deleted.

## 11. Artifact impact

No Artifact bytes, schemas, checksums, or scientific contents change. Project
deletion removes Project-scoped Artifact metadata/presentation/qualification rows
with the Project transaction. Global publication rows remain untouched.

## 12. API impact

- Add `DELETE /projects/{project_id}` returning no content on success.
- Preserve existing User Skill list/create/get/delete and attach/detach endpoints.
- Extend User Skill detail response with bounded Project usage names/IDs only.
- Project-not-found responses retain the stable `PROJECT_NOT_FOUND` code.

## 13. Persistence impact

No migration expected. Add a Unit-of-Work Project deletion operation implemented
for SQLAlchemy and the test in-memory adapter. SQL deletion follows current FK
ownership in child-to-parent order, including legacy hosted compatibility rows,
Progress projections/reports, exact bindings/references, resources, manifests,
Workspace acknowledgements, Project-Skill links, canonical Project, and local
Project bridge row. Global definitions, publications, capabilities, and Skills
are excluded.

## 14. Frontend impact

- Force the global Skills destination to unscoped `/skills`.
- Add compact Skill detail/provenance/usage and secondary Delete action.
- Give project-scoped empty Skills a direct global-library/Add path.
- Project card title/body target Overview; task action remains a separate CTA.
- Add a secondary Project delete confirmation on Overview.
- Shorten Project Help to contextual setup/next-step guidance and point to the
  generic Local Guide for reference.

## 15. Security impact

Deletion is loopback single-owner only under ODR-013. Confirmation names the
exact Project and states that Local files are untouched. No local paths or
credentials are uploaded or displayed. Skill source checksums/revisions remain
under Technical details. Unknown Project identity fails closed.

## 16. Cloud/local boundary impact

Cloud deletion cannot enumerate, read, write, or delete Local Workspace paths.
The future Local command preflight reads the exact Cloud Project identity before
opening its normal Workspace write section and stops cleanly if deleted.

## 17. Compatibility and versioning

API additions are compatible. Existing read/create paths remain unchanged.
Historical Projects remain readable until explicitly deleted. No Workflow,
Capsule, Artifact, Progress, or presentation publication changes.

## 18. Migration impact

`MIGRATION_REQUIRED = NO`. Existing schema can express the lifecycle. A migration
becomes necessary only if PostgreSQL qualification proves that current ownership
cannot be deleted transactionally without changing historical constraints; that
is an R5 stop condition, not permission to add a migration silently.

## 19. Files expected to change

Bounded production areas:

- persistence Unit of Work port plus SQL/in-memory adapters;
- Project Workspace application service and local Project router;
- User Skill detail projection/router;
- Local Workspace HTTP preflight/error copy;
- frontend API client, App shell, Skills list/detail, Project list/detail, Help,
  and Local Guide;
- directly related backend/frontend/E2E tests;
- R5 governance records.

Limits: at most 20 production files and 4,000 net production lines. Expansion
requires packet amendment and explicit review.

## 20. Rejected alternatives

- Database-wide implicit cascade migration: rejected; unnecessary and broad.
- Route-level scattered `DELETE` statements: rejected; no single ownership or
  transaction contract.
- Soft-delete/archival state: rejected; Owner authorized basic deletion.
- Delete attached Skill with cascade: rejected; shared Skill lifecycle must be
  explicit.
- Remote Local Workspace cleanup: prohibited.
- Treat old Workspace as a new Project: prohibited identity substitution.

## 21. Test design

- E1/E2: Skill detail, attached delete conflict, unattached delete, navigation,
  empty state, Help/Guide separation, Project confirmation.
- E3: in-memory API deletion removes all project-scoped collections and preserves
  global Skills/publications/other Project; injected failure rolls back.
- E4: marked disposable PostgreSQL Project graph inventory before/after delete;
  global records and second Project preserved; no migration.
- E5: copied disposable Workspace tree fingerprint unchanged when deleted Project
  sync preflight returns `PROJECT_NOT_FOUND`.
- E6: real FastAPI/Next.js/system Chrome journey for Skill lifecycle, stable
  navigation, delete confirmation, and post-delete portfolio.
- Regression locks: all four D1 bounded repair tests and Skill/Capability boundary.

## 22. Acceptance criteria

- All seven R5 ledger reproductions pass.
- Skill detail is useful but secondary; safe deletion semantics are unchanged.
- One Skill remains usable by another Project after detach/delete of a Project.
- Project relational state is removed in one PostgreSQL transaction.
- Local Workspace bytes are unchanged and receive a clear orphan error.
- Project row/title opens Overview; global Skills clears Project scope.
- Help and Local Guide have distinct bounded purposes.
- No migration, publication, scientific Artifact, or protected D1 change.

## 23. Rollback conditions

Before release, revert the R5 commit if deletion can partially commit, touches a
global record, writes Local files, or causes existing non-deleted Projects to
fail. Do not restore a deleted accepted Owner Project from repository logic; R5
qualification uses disposable Projects only.

## 24. Stop conditions

- `HISTORICAL_CONTRACT_CONFLICT` if immutable publication data is a delete target.
- `REPAIR_SCOPE_EXPANSION` if a migration or >20 production files are required.
- `NEW_PRODUCT_DEFECT` if PostgreSQL cannot roll back the full Project graph.
- `OWNER_DECISION_REQUIRED` if physical immutable Cloud content retention must be
  defined to complete the Owner's intended record-deletion semantics.
- Stop if any implementation reads/writes a Local Workspace from Cloud.

## 25. Owner decisions

All required decisions are already explicit in the Consolidated Repair Program
and D1 Product intent. Packet status: `READY_FOR_IMPLEMENTATION_REVIEW`.
Implementation authorization: `AUTHORIZED_BY_POST_D1_PROGRAM`.
