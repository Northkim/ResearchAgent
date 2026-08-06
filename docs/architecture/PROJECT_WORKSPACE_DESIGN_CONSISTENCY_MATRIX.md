# Project Workspace Design Consistency Matrix

> **ARCH-D1 audit.** Every “proposed” item is design-only. Current runtime
> contracts stay unchanged.

## 1. Cross-layer matrix

| Entity / field | Proposed SQL | Python domain | API | Local JSON schema | CLI | Frontend | Progress / identity mapping |
|---|---|---|---|---|---|---|---|
| Project / `project_id` | `projects.project_id`; compatibility FK/key to unchanged `local_projects` | `Project` | `/projects/{project_id}` | workspace, manifest, lock, Artifact/Resource/ack | resolved from `project.json` | every Project route | existing value preserved in reports |
| Workspace / `workspace_id` | `projects.workspace_id` UNIQUE | `ProjectWorkspaceIdentity` | project, manifest, sync | workspace/manifest/lock/plan/ack | root identity; not device ID | sync status only | not proof of current local availability |
| Workflow Definition / ID+version | physical `local_workflow_definitions` and versions | `WorkflowDefinition`, `WorkflowDefinitionVersion` | `/workflow-definitions` | Capsule/manifest refs | workflow list/run | registry-driven cards/help | definition labels per instance |
| Workflow Instance / `workflow_instance_id` | `project_workflow_instances` | `ProjectWorkflowInstance` | Project instance routes | manifest/Capsule/lock/Artifact | list/run target | board/detail | owner of rounds and projection chain |
| Capsule / ID+version+definition checksum | `local_workflow_capsule_versions` and instance pins | `WorkflowCapsuleVersion`, `CapsuleReference` | catalog, instance, manifest, sync plan | Capsule reference/manifest/lock/plan/ack | sync validates; run selects exact version | technical details/status | never a Progress chain identity |
| Round / `round_id` | future report mapping/projection, not Hosted StepRun | `WorkflowRoundIdentity` | instance progress only | Artifact ref; future Progress schema | Capsule run | RoundHistory | integer sequence + stable new ID; legacy external mapping |
| Desired Manifest / revision/checksum | immutable manifest+entry rows; Project current pointer | `DesiredProjectManifest` | manifest GET/change | desired manifest | update check/sync | cloud desired revision | no local-success claim |
| Installed Lock / revision/checksum | not cloud authority; checksum referenced by ack | `InstalledWorkspaceLock` local model | sync request/ack only | installed lock | status/sync/run | last ack qualified as local report | not a report or desired state |
| Sync Plan / installation/checksums | optional bounded audit plus ack table | `WorkspaceSyncPlan` | sync-plan | sync plan | dry-run/sync/recovery | update/error state | no research Progress effect |
| Installation Ack | `workspace_installation_acknowledgements` | `CapsuleInstallationAcknowledgement` | sync-ack | installation ack | ack/retry | installed observation | sync uncertainty only |
| Artifact / identity, schema, checksum | `local_artifact_references` | `LocalArtifactReference` | metadata GET | Artifact reference/manifest/lock | artifact status/materialize | list component initially embedded in Progress | report may reference metadata; bytes remain local |
| Artifact requirement | `workflow_artifact_requirements` + manifest entries | `WorkflowArtifactRequirement` | catalog/manifest/instance | desired manifest | sync dependency check | dependency list | blocking edge, not forced order |
| Skill / pin | `local_builtin_skill_definitions`, versions, requirements, pins | `SkillDefinition`, `SkillVersion`, `SkillPin` | catalog detail/manifest only; standalone endpoints deferred | manifest/lock | sync verify/run pin | built-in choice in wizard; no catalog tab | exact metadata only |
| Resource binding | `external_resource_bindings` | `ExternalResourceBinding` | manifest reference; standalone endpoints deferred | Resource binding/manifest/lock | resource status/local resolver | hidden until implemented; dependencies may label unavailable | bounded reference only |
| Project progress projection | `local_workflow_progress_projections` | `WorkflowInstanceProgressProjection` | Project + instance progress | no local authority schema | status view | graph/list | derived only from accepted reports/acks |
| Legacy Package | unchanged `local_projects.current_package_*` | current Package models unchanged plus compatibility mapping | current Package APIs retained | existing Package manifest unchanged | legacy `run .` unchanged | compatibility links during V0.x | deterministic instance mapping outside bytes |
| Capability scope | existing scope rows untouched; future versioned scope | new exact Workspace/instance/sync scopes | auth middleware per route | never persisted in Workspace | memory/protected OS temp only | never shown | new scope does not reinterpret old report/token |
| Retirement | instance desired state/revision; no delete FK cascade | `retire()` transition | retire endpoint | manifest desired state | sync records retired desired state | retired section | histories/Artifacts remain visible/auditable |

## 2. Ownership and checksum audit

| Field | Owner | Checksum inclusion | Conflict avoided |
|---|---|---|---|
| Project/Workspace identities | Cloud | project metadata checksum; immutable | Local copy cannot mint or substitute identity. |
| Desired Manifest content | Cloud revision transaction | canonical manifest excluding `manifest_checksum` | No circular self-hash; local availability excluded. |
| Capsule Definition | Reviewed publisher/compiler | immutable files + manifest excluding definition checksum | Mutable roots excluded and separately declared. |
| Installed Lock | Local sync after verification | complete lock excluding `lock_checksum` | Does not alter Desired Manifest. |
| Artifact bytes | Local producer/materializer | exact bytes | Metadata/status changes cannot rebind bytes. |
| Progress original bytes | Existing ingestion contract | unchanged existing original/normalized checksums | Legacy mapping is external; no rewrite. |
| Resource availability | Local resolver observation | binding metadata checksum excludes mutable observation where implemented | Cloud desired binding cannot claim current bytes. |
| Installation Ack | Local sync | plan+manifest+lock+installed identities; ack envelope has no self-checksum | Replay binds existing install, not a fresh install. |

## 3. Current-to-target naming conflicts and resolutions

1. Current Hosted `workflow_definitions` already means executable Hosted graph
   definitions. **Resolution:** logical target term remains Workflow Definition,
   but additive physical table is `local_workflow_definitions`; no old row is
   reinterpreted.
2. Current Hosted `artifacts` bind `WorkflowRun`/`StepRun` provenance.
   **Resolution:** `local_artifact_references` is a separate metadata registry
   without Hosted foreign keys.
3. Current `local_projects` flattens one Workflow and Package.
   **Resolution:** preserve it for V0.x, add canonical `projects` plus instances,
   and use a deterministic compatibility adapter; no immediate column takeover.
4. Current `project_progress_projections` key is Package/Workflow-version
   scoped. **Resolution:** add `local_workflow_progress_projections`; keep old
   projection authoritative for current clients until accepted parity.
5. “Package” currently means a complete runnable folder. **Resolution:** keep
   that definition for legacy evidence; use Capsule and Workspace exclusively in
   new names/routes/docs.

## 4. Design invariants checked

- Terminology and schema versions are identical across documents and JSON
  schemas.
- Every active designed route maps to a domain entity. Skills/Resources are not
  advertised as active standalone routes.
- No frontend-visible future tab is initially enabled.
- No checksum includes its own field or the whole mutable Workspace.
- Desired configuration, installed observation, and actual local state have
  different owners and representations.
- Every removal is retirement; no designed path deletes local results or
  historical reports.
- Multiple Workflow Instances are representable at every domain/API/progress
  layer; only the initial UI/service policy limits active instances/type.
- New capability scopes are versioned; old scopes are unchanged.
- Legacy Literature Search Package/report checksum semantics remain unchanged.

## 5. Noncritical implementation-time resolutions

No critical design contradiction remains. These details require explicit
resolution during the relevant implementation phase and cannot be silently
chosen in code:

1. the exact canonical JSON implementation/library and Unicode normalization
   policy must be selected before schema promotion;
2. the compatibility ID derivation namespace constant must be owner-reviewed
   and frozen before the first migration;
3. whether canonical `projects` is populated by one-time copy plus adapter or a
   transitional database view needs migration rehearsal; historical rows remain
   untouched either way;
4. Capsule archive transport/signature policy is deferred to sync phase; SHA-256
   plus authenticated transport is the current minimum design;
5. a future Progress Report schema version must decide whether `round_id` is in
   the signed report or only an ingestion envelope; legacy bytes remain intact;
6. new Workspace bootstrap distribution/update mechanics are deferred to Phase
   3 and cannot change legacy Package launchers; and
7. local-only Resource path mappings need a separate design schema before the
   Resource resolver phase because absolute paths must not enter cloud-derived
   files.

These are bounded owner/implementation choices, not contradictions in identity,
ownership, safety, or legacy compatibility.

`DESIGN_CONSISTENCY_AUDIT = PASS`.
