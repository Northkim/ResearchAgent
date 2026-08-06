# Project Workspace and Workflow Capsule Design V0.1

> **Design-only contract.** This document is not an implemented runtime, API,
> migration, or Package contract. Owner approval of an implementation phase is
> still required.

## 1. Boundary and terminology

The teacher-aligned boundary is unchanged: cloud records Projects, desired
configuration, bounded progress, and scoped API capabilities; the local
Workspace is authoritative for concrete research state; Codex is the local
Harness; cloud does not execute, rank, synthesize, or resume research.

The following terms are authoritative:

| Term | Definition | Not equivalent to |
|---|---|---|
| Project | Cloud-owned logical research effort and authorization boundary. | Hosted `WorkflowRun` |
| Project Workspace | One long-lived logical local root associated with one Project. Copies share a logical identity but are not automatically synchronized. | One immutable Package |
| Workflow Definition | Stable catalog identity describing a Workflow type such as Literature Search. | A particular installation or run |
| Workflow Instance | Project-owned configured occurrence of a Workflow Definition. Rounds and Progress chains belong here. | Workflow Definition |
| Workflow Capsule | A versioned, independently verifiable module installed for one Workflow Instance. | The entire Workspace |
| Capsule Definition | Immutable manifest and immutable files for one Capsule version. | Mutable execution output |
| Capsule Execution State | Only the mutable roots declared by the Capsule Definition. | Capsule Definition checksum input |
| Round | One append-only execution increment of one Workflow Instance. | Hosted StepRun |
| Artifact Reference | Typed, checksum-bound metadata for immutable Workflow output. | Hosted `Artifact` provenance or uploaded bytes |
| Skill Definition | Versioned capability contract and provenance for a reusable Skill. | An automatically trusted script |
| Skill Pin | Exact Skill identity, version, and checksum required by a Capsule or Project. | Floating dependency |
| External Resource Binding | Revision-pinned metadata for content resolved by local tools. | Cloud-held credentials or storage |
| Desired Project Manifest | Revisioned cloud authority for requested Workflow Instances, Capsule/Skill pins, Artifact requirements, Resource bindings, and compatibility. | Proof of local installation |
| Installed Workspace Lock | Local verified installation and resolution state. | Cloud desired state |
| Sync Plan | Content-addressed, base-revision-bound difference from an Installed Lock to a Desired Manifest. | An instruction to delete local data |
| Installation Acknowledgement | Idempotent local report that a planned installation was verified and committed. | Proof of current device availability forever |
| Package | Only the accepted V0.1 complete Literature Search download format. New modular content is called a Capsule. | Workspace or Capsule in new APIs |

## 2. Identity contract

All strings are UTF-8 and serialized canonically as described in the design
schemas. UUID-like identities use 32 lowercase hexadecimal characters without
hyphens to remain compatible with current `project-...` identifiers.

| Identity | Format | Creator and scope | Stability/reuse | Representations |
|---|---|---|---|---|
| `project_id` | `project-[0-9a-f]{32}` | Cloud; globally unique | Stable; never reused | API/SQL/local metadata/Progress |
| `workspace_id` | `workspace-[0-9a-f]{32}` | Cloud once per Project; globally unique | Stable; never reused; copies share it | API/SQL/project metadata/lock; never a device ID |
| `workflow_definition_id` | `[a-z][a-z0-9.-]{1,127}` | Reviewed platform catalog; global | Stable name; never reassigned | Catalog SQL/API/Capsule/Progress |
| `workflow_instance_id` | `wfi-[0-9a-f]{32}` | Cloud in one Project; globally unique | Stable after creation; never reused | Manifest/SQL/API/Capsule path/Progress |
| `capsule_id` | `capsule-[0-9a-f]{32}` | Reviewed Capsule publisher; global family ID | Stable family; versions side by side | Catalog/manifest/lock/reference |
| `capsule_version` | SemVer without build metadata | Reviewed publisher | Immutable version; never republished | Catalog/manifest/path/lock |
| `capsule_definition_checksum` | `sha256:` plus 64 lowercase hex | Capsule compiler | Immutable; content-addressed | Manifest/archive/lock/ack |
| `round_id` | `round-[0-9a-f]{32}` | Local Capsule before a new round; instance-scoped ownership, globally unique value | Immutable; never reused | Local state/new Progress metadata/artifacts |
| `artifact_id` | `artifact-[0-9a-f]{32}` | Local producing Capsule | Immutable identity; never rebound to new bytes | Index/Progress/cloud metadata |
| `artifact_schema_version` | `reagent.artifact.<name>/v<major>.<minor>` | Platform schema publisher | Stable; compatibility is explicit | Artifact reference/requirements |
| `skill_id` | `[a-z][a-z0-9._-]{1,127}` | Platform initially; global | Stable; never reassigned | Catalog/pins/Capsule |
| `skill_version` | SemVer without build metadata | Reviewed publisher | Immutable; no floating execution | Catalog/pins/lock |
| `resource_binding_id` | `resource-[0-9a-f]{32}` | Cloud in one Project; globally unique | Stable; retirement only | Manifest/API/resource index |
| `manifest_revision` | positive signed 64-bit integer | Cloud transaction, monotonic per Project | Never reused or decremented | SQL/ETag/API/cache/lock/plan |
| `installation_id` | `install-[0-9a-f]{32}` | Local sync client; globally unique idempotency identity | One sync transaction; never reused | staging/plan/receipt/ack |

The API and SQL always carry identities as explicit fields; paths never become
identities. Local files repeat the Project, Workspace, and Workflow Instance
binding so cross-project substitution is detectable. New Progress Reports add
instance/round mappings only in a future backward-compatible contract version.
Legacy v0.2 report bytes remain unchanged; compatibility projections derive
the mapping externally.

## 3. Logical cloud data model

These entities are additive. Because the repository already has Hosted
`workflow_definitions` and `artifacts`, the proposed physical local-product
tables use a `local_` prefix. The logical API names remain Workflow Definition
and Artifact Reference. Every table uses PostgreSQL `timestamptz`, UTC values,
database-generated `created_at`, and application/database-updated `updated_at`
where noted. No hard deletion API is exposed.

### 3.1 Project and catalog

| Logical entity / physical table | Columns and constraints | Mutability, indexes, legacy mapping |
|---|---|---|
| `projects` / `projects` | `project_id text PK`; `workspace_id text NOT NULL UNIQUE`; `name varchar(200) NOT NULL`; `research_topic varchar(4000) NOT NULL`; `status enum(ACTIVE,ARCHIVED) NOT NULL`; `current_manifest_revision bigint NOT NULL DEFAULT 0 CHECK >=0`; `legacy_local_project_id text NULL UNIQUE`; timestamps | IDs immutable. Name/topic/status/revision mutable by explicit APIs. Index `(status,updated_at desc)`. Existing `local_projects` are copied once with their IDs and preserved in place. |
| `workflow_definitions` / `local_workflow_definitions` | `workflow_definition_id text PK`; `display_name varchar(120)`; `description varchar(2000)`; `lifecycle enum(AVAILABLE,PLANNED,RETIRED)`; `allows_multiple_instances bool`; timestamps | ID immutable; descriptive/lifecycle fields curated. Index lifecycle. Does not reuse Hosted table. |
| `workflow_definition_versions` / `local_workflow_definition_versions` | composite PK `(workflow_definition_id,version)`; FK definition; `contract_checksum char(71) UNIQUE`; `input_schema_id/output_schema_id varchar(200)`; `compatibility jsonb`; `review_status enum(DRAFT,REVIEWED,RETIRED)`; `published_at`; timestamps | Version/checksum/contracts immutable after REVIEWED; retirement metadata mutable. Index `(workflow_definition_id,review_status)`. |
| `workflow_capsule_versions` / `local_workflow_capsule_versions` | composite PK `(capsule_id,capsule_version)`; FK `(workflow_definition_id,workflow_version)`; `definition_checksum char(71) UNIQUE`; `archive_size_bytes bigint CHECK 0..536870912`; `archive_media_type varchar(100)`; `mutable_roots jsonb`; `capability_requirements jsonb`; `compatibility jsonb`; `review_status enum(DRAFT,REVIEWED,RETIRED)`; `legacy_package_compatible bool`; timestamps | Reviewed row immutable except retirement. Index workflow version and review status. Legacy LS Package gets a deterministic compatibility row without rewriting it. |

### 3.2 Project desired configuration

| Logical entity / physical table | Columns and constraints | Mutability, indexes, legacy mapping |
|---|---|---|
| `project_workflow_instances` / same | `workflow_instance_id text PK`; `project_id FK`; `workflow_definition_id/version FK`; `capsule_id/version FK`; `desired_state enum(ACTIVE,RETIRED)`; `display_name varchar(160)`; `created_manifest_revision bigint`; `retired_manifest_revision bigint NULL`; `legacy_package_id text NULL`; timestamps; UNIQUE `(project_id,workflow_instance_id)` | Identity and original pins immutable. Upgrades create a later manifest entry/version, not an in-place Capsule. UI enforces one ACTIVE/type initially; domain does not. Index `(project_id,desired_state)` and `(project_id,workflow_definition_id)`. |
| `project_desired_manifests` / same | composite PK `(project_id,manifest_revision)`; `workspace_id`; `base_revision bigint NULL`; `schema_version`; `canonical_checksum char(71) UNIQUE`; `manifest_json jsonb`; `created_by_subject_id text`; `idempotency_key uuid`; timestamps; UNIQUE `(project_id,idempotency_key)` | Append-only immutable revisions. `projects.current_manifest_revision` points to latest committed revision. Index project/revision desc. |
| `project_manifest_entries` / same | `entry_id text PK`; FK project+revision; `entry_kind enum(WORKFLOW_INSTANCE,SKILL_PIN,ARTIFACT_REQUIREMENT,RESOURCE_BINDING,COMPATIBILITY)`; typed FK columns nullable according to kind; `desired_action enum(ENSURE_PRESENT,RETIRE)`; `entry_checksum char(71)`; UNIQUE `(project_id,manifest_revision,entry_kind,entry_id)` | Immutable denormalized index over immutable manifest JSON; check constraints enforce kind-specific fields. Index instance/skill/resource. |

### 3.3 Progress and Artifacts

| Logical entity / physical table | Columns and constraints | Mutability, indexes, legacy mapping |
|---|---|---|
| `project_workflow_progress_projections` / `local_workflow_progress_projections` | composite PK `(project_id,workflow_instance_id)`; FKs; `latest_round_number int CHECK >=0`; `latest_round_id text NULL`; `status enum(NOT_STARTED,READY,RUNNING,UPLOAD_PENDING,COMPLETED,FAILED,BLOCKED,UNKNOWN_LOCAL_STATE)`; `latest_cloud_known_state jsonb`; `sync_uncertainty enum(CURRENT_AS_REPORTED,LOCAL_STATE_UNKNOWN,INSTALL_ACK_PENDING,MANIFEST_UPDATE_AVAILABLE)`; `last_report_id text NULL`; checksums; `projection_revision bigint`; timestamps | Mutable derived projection only. Unique `(project_id,workflow_instance_id,last_report_id)` when report present; index project/status. Legacy reports map to deterministic legacy instance IDs outside report bytes. Existing projection remains unchanged. |
| `local_artifact_references` / same | `artifact_id text PK`; `project_id`; `workflow_instance_id`; `round_id`; `artifact_type varchar(160)`; `artifact_schema_version`; `media_type`; `state enum(DECLARED,LOCAL_AVAILABLE,EXTERNAL_AVAILABLE,METADATA_ONLY,MISSING,STALE,INCOMPATIBLE,RETIRED)`; `relative_path varchar(1024) NULL`; `content_checksum char(71) NULL`; `size_bytes bigint NULL`; `resource_binding_id NULL`; `cloud_metadata_available bool`; `produced_at`; `retired_at`; timestamps | Producer/round/type immutable. Availability/location/status may change with new verified observations; byte identity cannot change—new bytes require new `artifact_id`. Index project, producer, type/state, checksum. Metadata only; no general byte column. |
| `workflow_artifact_requirements` / same | composite PK `(workflow_definition_id,workflow_version,requirement_key)`; `artifact_type`; `schema_constraint`; `cardinality_min/max`; `required bool`; `materialization_mode enum(REFERENCE_ONLY,VERIFIED_COPY)`; timestamps | Reviewed version requirement immutable. Index artifact type/schema. |

### 3.4 Skills and Resources

| Logical entity / physical table | Columns and constraints | Mutability, indexes, legacy mapping |
|---|---|---|
| `built_in_skill_definitions` / `local_builtin_skill_definitions` | `skill_id text PK`; `display_name`; `description`; `owner_subject`; `visibility enum(PLATFORM_BUILT_IN)`; `execution_scope enum(BUILT_IN_REVIEWED_ONLY)`; timestamps | Curated metadata; retirement through versions. |
| `skill_versions` / `local_skill_versions` | composite PK `(skill_id,skill_version)`; `content_checksum`; input/output schemas; `required_tools jsonb`; `capabilities jsonb`; `permissions jsonb`; `side_effect_class enum(READ_ONLY,LOCAL_DECLARED_WRITE,EXTERNAL_READ,EXTERNAL_WRITE)`; `source_uri`; `license`; `trust_tier enum(BUILT_IN_REVIEWED,PRIVATE_DISABLED,IMPORTED_QUARANTINED)`; `review_status enum(PENDING,REVIEWED,REJECTED,QUARANTINED,RETIRED)`; timestamps | Executable only when both built-in and REVIEWED. Reviewed content immutable. Unique checksum. |
| `workflow_skill_requirements` / same | PK `(workflow_definition_id,workflow_version,requirement_key)`; `skill_id`; `version_constraint`; `required bool`; `permission_ceiling jsonb`; timestamps | Immutable per reviewed Workflow version. |
| `project_skill_pins` / same | `pin_id text PK`; `project_id`; `workflow_instance_id NULL`; `skill_id/version FK`; `skill_checksum`; `manifest_revision`; `desired_state enum(ACTIVE,RETIRED)`; UNIQUE `(project_id,manifest_revision,pin_id)` | Append-only by manifest revision; exact pin, never floating. |
| `external_resource_bindings` / same | `resource_binding_id text PK`; `project_id`; `provider enum(GIT,GITHUB,HUGGING_FACE,LOCAL_DIRECTORY,EXTERNAL_STORE)`; `resource_type`; `locator`; `immutable_revision`; `expected_checksum NULL`; `workspace_relative_path`; `access_mode enum(READ_ONLY,OWNER_CONFIRMED_WRITE)`; `sync_policy enum(MANUAL,VERIFY_ONLY,PULL_ON_EXPLICIT_SYNC)`; `availability enum(UNRESOLVED,AVAILABLE,UNAVAILABLE,GATED,PRIVATE,STALE,RETIRED)`; patterns/license warnings jsonb; `manifest_revision`; `retired_at`; timestamps | Credentials prohibited. Identity immutable; availability is locally reported metadata and does not assert bytes. Index project/provider/availability. Retirement only. |

### 3.5 Installation observations

| Logical entity / physical table | Columns and constraints | Mutability, indexes, legacy mapping |
|---|---|---|
| `workspace_installation_acknowledgements` / same | `installation_id text PK`; `project_id`; `workspace_id`; `manifest_revision`; `installed_lock_checksum`; `plan_checksum`; `status enum(INSTALLED,ACK_PENDING,ACKNOWLEDGED,FAILED_SAFE)`; `installed_capsules jsonb`; `installed_at`; `acknowledged_at NULL`; `idempotency_key uuid UNIQUE`; timestamps; UNIQUE `(workspace_id,manifest_revision,installed_lock_checksum)` | Installation evidence append-only except ACK_PENDING→ACKNOWLEDGED. It is a report from a logical Workspace, not first-class device state. Index project/revision/status. |

No new entity has a foreign key to Hosted `WorkflowRun`, `StepRun`, Hosted
`Artifact`, AgentRuntime, or Hosted `ProviderOperation`.

## 4. Proposed additive migration sequence

This is a design sequence, not migration files:

1. **Catalog and identity foundation:** create canonical `projects`, local
   Workflow Definition/version, Capsule version, and Workflow Instance tables;
   copy legacy project metadata while preserving `local_projects`; install the
   deterministic legacy mapping function and verify downgrade/re-upgrade.
2. **Desired configuration:** add immutable manifests, entries, Skill metadata,
   pins, Artifact requirements, and Resource bindings; seed reviewed Literature
   Search catalog rows.
3. **Per-instance continuity:** add local Artifact references and per-instance
   progress projections; project legacy reports/projections without rewriting
   bytes.
4. **Sync acknowledgement:** add installation acknowledgements only after local
   sync semantics and idempotency tests are accepted.

Each revision has one head, additive downgrade, no dropped legacy column/table,
and a rollback gate proving current V0.1 APIs and downloaded Packages still
operate.

## 5. Legacy compatibility

- `local_projects` remains readable and unchanged. A canonical Project row
  records `legacy_local_project_id`; dual-read compatibility prefers canonical
  state after migration and never dual-writes without an accepted transition.
- A deterministic UUIDv5-like derivation over the fixed namespace plus
  `project_id`, current `package_id`, and Workflow identity yields a stable
  `workflow_instance_id` and `capsule_id` for compatibility metadata. The
  resulting prefixed values are stored so the derivation need not be repeated.
- Existing `selected_workflow=LITERATURE_SEARCH`, current Package fields, local
  session scope versions, report bytes, report checksums, and projection rows
  are not changed.
- Current legacy Package identities remain opaque values accepted by the
  existing Package identifier contract (for example the deterministic
  `literature-search-project-…-v0.5` form); they are not coerced into the new
  `capsule_id` format. The compatibility mapping stores both identities.
- Existing `python reagent_local.py run .` behavior continues in downloaded
  Packages. New scopes receive new version identifiers; old scopes are not
  reinterpreted as Workspace scopes.
- A legacy Package may be adopted by a local reference outside cloud-derived
  identity files or explicitly moved as one intact directory after owner
  confirmation and checksum validation. No silent rewrite, move, or manifest
  augmentation is permitted.
- Complete V0.x support is required. Deprecation requires owner approval, a
  successful import/export path, two released compatibility cycles, explicit
  warning, and no loss of runnable state or historical evidence.

## 6. Local Workspace layout

```text
<workspace>/
├── AGENT.md
├── project.json
├── reagent_local.py
├── .reagent/
│   ├── desired-manifest.json
│   ├── installed-lock.json
│   ├── artifact-index.json
│   ├── resource-index.json
│   ├── capsule-registry.json
│   ├── context/project-summary.md
│   ├── sync/current.json
│   ├── sync/staging/<installation_id>/
│   ├── receipts/installations/<installation_id>.json
│   ├── acknowledgements/<installation_id>.json
│   ├── local/legacy-locations/<workflow_instance_id>.json
│   └── runtime/
├── capsules/<workflow_definition_id>/<workflow_instance_id>/<capsule_version>/
│   ├── capsule.json
│   ├── AGENT.md
│   ├── workflow/
│   ├── skills/
│   └── <declared mutable roots>/
├── artifacts/materialized/<artifact_id>/
└── resources/<resource_binding_id>/
```

| Class | Paths | Rule |
|---|---|---|
| Immutable | `project.json` identity fields; Capsule definition files; installed materialized Artifact bytes; installation receipts | Content-bound; never overwritten; new identity/version required. |
| Cloud-derived | desired-manifest cache, reviewed Capsule archives/references, Resource desired bindings | Replaced only by validated sync with revision/checksum binding. |
| Locally mutable | project cognitive summary; Capsule-declared execution roots; availability portions of indexes | Must be declared; atomic writes; excluded from definition checksums. |
| Append-only | installation receipts, acknowledgements, per-Capsule round/report histories | New named entry; never rewrite accepted history. |
| Ephemeral | staging, sync transaction pointer, process runtime | Protected, recoverable, removable only by validated ownership; never identity evidence. |
| Secret-prohibited | every Workspace and Capsule path above | API keys, database URLs, bearer tokens, credential URLs, and private auth material are forbidden. Runtime tokens stay in memory or OS-protected temporary files outside the Workspace. |

OS logs and process PID files should live outside the Workspace under the
existing protected local runtime root. A Workspace is never hashed as one
immutable folder. Checksums independently bind immutable project metadata,
manifest revisions, Capsule Definitions, installed locks, Artifacts, and
receipts. Checksums exclude their own checksum field to avoid circularity.

## 7. Capsule contract

A new Capsule Definition manifest identifies its schema, Project-neutral
Workflow Definition/version, Capsule identity/version/checksum, immutable file
manifest, exact Skill pins, typed Artifact inputs/outputs, required capability
names and ceilings, declared mutable roots, launcher protocol, supported
Workspace schema range, and platform compatibility. Unknown fields fail.

| Manifest field | Type / bound | Ownership and rule |
|---|---|---|
| `schema_version` | constant `reagent.workflow-capsule/v0.1` | Reviewed runtime contract when promoted; design-only now. |
| `workflow_definition_id`, `workflow_definition_version` | canonical ID + SemVer | Project-neutral catalog binding; immutable. |
| `capsule_id`, `capsule_version` | canonical ID + SemVer | Exact side-by-side publication identity; immutable and never republished. |
| `capsule_definition_checksum` | SHA-256 | Canonical manifest with this field omitted plus ordered immutable-file records. |
| `immutable_files` | ≤2,000 records: relative path, checksum, size, media/executable policy | Paths normalized; no link/device/undeclared file; total archive ≤512 MiB. |
| `mutable_roots` | ≤32 unique relative directory records with purpose and size/file limits | The only Capsule write locations; cannot contain/overlap immutable files or escape the Capsule. |
| `skill_pins` | ≤100 exact identity/version/checksum/trust records | Only built-in reviewed execution initially; no floating versions. |
| `artifact_inputs` | ≤100 typed requirements | Exact/range/converter compatibility plus required/optional and materialization mode. |
| `artifact_outputs` | ≤100 typed declarations | Type/schema/media/path pattern; producer creates new immutable Artifact identities. |
| `required_capabilities` | ≤50 reviewed names with count/cost/side-effect ceilings | Declarative ceiling; session must be equal or narrower; no token included. |
| `compatibility` | Workspace schema range, minimum CLI, OS/architecture/tool constraints | Unknown/incompatible fails before execution. |
| `launcher` | reviewed protocol identifier and relative executable/module path | Data, never arbitrary cloud shell syntax; exact path is immutable. |
| `secret_policy` | constant `PROHIBITED` | Applies to definition, mutable roots, reports, logs, and receipts. |

The immutable manifest and every immutable file are verified independently.
Mutable roots may contain round state, outputs, context, report drafts, and
receipts only as declared. A launcher resolves identity from its Capsule and
Workspace metadata; it cannot infer another instance or write another Capsule.
Required capabilities remain exact and short-lived. Capsule validation never
requires executing Capsule code.

New Capsules are copied into a new versioned Workspace destination. External
reference mode is limited to unchanged legacy Packages and records only a local
machine path plus verified legacy checksums. No symlink is an installation or
Artifact-sharing mechanism.

## 8. Ownership rules

- Cloud owns Project identity and desired configuration.
- Reviewed platform publication owns Workflow, Capsule, and built-in Skill
  immutable definitions.
- Local sync owns Installed Lock and installation receipts.
- A local Capsule owns its declared mutable state and produced Artifact bytes.
- Progress upload reports bounded local assertions; cloud projection owns only
  cloud-known state.
- External tools own Resource bytes and local credentials; ReAgent owns only
  the binding and verification metadata.
