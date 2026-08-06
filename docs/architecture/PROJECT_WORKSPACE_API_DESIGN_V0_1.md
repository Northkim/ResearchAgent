# Project Workspace API and Local CLI Design V0.1

> **Design only.** Routes and commands below are proposed versioned contracts;
> ARCH-D1 does not expose or change an API.

## 1. Common API envelope and security

Active design endpoints use JSON with explicit schema identifiers. Local V0.1
requires literal loopback and a short-lived local-owner bearer issued outside
the Workspace. Production authentication remains unresolved and these routes
do not authorize public deployment. Authorization is checked before existence
lookup and binds subject, Project, Workspace where applicable, capability, and
request checksum. Cross-scope failures return existence-blind `SCOPE_MISMATCH`.

Mutation requests require UUIDv4 `Idempotency-Key`, UTC timestamp, and content
checksum. Exact replay returns the original result without a second mutation;
changed content under the same scoped key returns 409
`IDEMPOTENCY_CONFLICT`. Manifest mutation additionally requires
`base_revision`; sync plans/acks bind target revision and checksums.

Common error envelope:

```json
{
  "schema_version": "reagent.api-error/v0.1",
  "code": "MANIFEST_REVISION_CONFLICT",
  "stage": "MANIFEST_CHANGE",
  "retryable": true,
  "action": "Refresh the manifest and review the new base revision."
}
```

No envelope includes tokens, credentials, database URLs, full private Resource
locators, local absolute paths, unbounded exception text, or Artifact bytes.
JSON mutation bodies are at most 64 KiB, a full manifest response 256 KiB, and
a sync plan 1 MiB. Collection defaults are 25, maximum 100, ordered by stable
identity/timestamp, and cursor-paginated. Cursors are opaque, scoped, bounded,
and never authorization substitutes.

## 2. Workflow catalog

### `GET /workflow-definitions`

- **Auth/scope:** project-independent `workflow.catalog.read`; loopback local
  owner in initial product.
- **Request:** `status=AVAILABLE|PLANNED|RETIRED`, optional cursor/limit. Unknown
  filters fail 422.
- **Response:** `reagent.workflow-definition-page/v0.1` with bounded Definition
  summary, latest reviewed version, lifecycle, input/output types, and whether
  selection is enabled. Planned definitions are visible but not selectable.
- **Semantics:** read-only, ETag/cacheable; no local installation claim.
- **Codes:** 200, 304, 401, 403, 422. Empty catalog is valid.

### `GET /workflow-definitions/{workflow_definition_id}`

- **Auth/scope:** `workflow.catalog.read` before lookup.
- **Response:** `reagent.workflow-definition-detail/v0.1`, reviewed versions,
  Capsule versions, required Artifact/Skill contracts, limitations, and Help
  content identifier. No archive bytes.
- **Codes:** 200, 401, 403, 404 `WORKFLOW_DEFINITION_NOT_FOUND`, 422 malformed ID.

## 3. Projects

### `POST /projects`

- **Auth/scope:** `project.create`; idempotency required.
- **Request:** `reagent.project-create/v0.1`: name (1–200), research topic
  (1–4000), selected Workflow Definition IDs (1–5), exact reviewed versions or
  server-recommended reviewed pins, recommended built-in Skill pins, and
  Workspace/expected-output acknowledgement. Initially only Literature Search
  may be active; planned selections return 422.
- **Response:** 201 `reagent.project/v0.1` with new Project/Workspace, manifest
  revision 1, created Workflow Instances, and links. Exact replay returns 200
  with the same identity.
- **Effects/privacy:** one transaction; creates no WorkflowRun, local files,
  Provider call, LLM action, or execution. Topic remains cloud Project metadata
  under current local-product policy.
- **Codes:** 201/200 replay, 409 idempotency conflict, 422 validation or
  `WORKFLOW_NOT_SELECTABLE`, 401/403.

### `GET /projects/{project_id}`

- **Auth/scope:** exact `project.read` before lookup.
- **Response:** `reagent.project/v0.1`; desired revision and bounded cloud-known
  aggregate only. It never says Workspace bytes exist.
- **Codes:** 200, 401, 403, 404, 422.

Existing `GET /projects` remains a separately versioned compatibility endpoint;
future canonical pagination must preserve current V0.x clients during the
declared compatibility period.

## 4. Workflow Instances

### `GET /projects/{project_id}/workflow-instances`

- **Auth/scope:** `project.workflow.read`; cursor/limit/status/definition
  filters.
- **Response:** `reagent.workflow-instance-page/v0.1`, desired state, exact
  pins, latest cloud-known progress, and installation acknowledgement
  qualifier. Multiple instances/type are representable.
- **Codes:** 200, 401, 403, 404 project, 422.

### `POST /projects/{project_id}/workflow-instances`

- **Auth/scope:** `project.manifest.write`; idempotency and `base_revision`.
- **Request:** `reagent.workflow-instance-create/v0.1` with Definition/version,
  reviewed Capsule ID/version/checksum, display name, exact Skill pins,
  Artifact requirements, and optional Resource binding IDs.
- **Response:** 201/200 replay instance plus new manifest revision. Domain
  allows duplicate types; initial UI/service policy returns 409
  `ACTIVE_INSTANCE_TYPE_LIMIT` when one active instance/type already exists.
- **Effects:** desired state only; no Workspace write or execution.
- **Codes:** 409 revision/idempotency/type limit, 422 unreviewed/incompatible
  pins, 424 dependency unavailable, 401/403/404.

### `GET /projects/{project_id}/workflow-instances/{instance_id}`

- **Auth/scope:** exact project+instance `project.workflow.read` before lookup.
- **Response:** `reagent.workflow-instance-detail/v0.1`, desired pins,
  dependencies, progress link, and cloud-qualified sync observation.
- **Codes:** 200, 401, 403 existence-blind mismatch, 404, 422.

### `POST /projects/{project_id}/workflow-instances/{instance_id}/retire`

- **Auth/scope:** `project.manifest.write`; idempotency and `base_revision`.
- **Request:** `reagent.workflow-instance-retire/v0.1` with reason code and
  owner confirmation. No deletion flag exists.
- **Response:** 200 instance `RETIRED`, new manifest revision. Exact replay
  stable.
- **Effects:** desired state only; reports, local files, Artifacts, and pins
  remain historical.
- **Codes:** 409 revision/idempotency/already-conflicting state, 401/403/404/422.

## 5. Desired Manifest

### `GET /projects/{project_id}/manifest`

- **Auth/scope:** exact `project.manifest.read`.
- **Request:** optional `revision`; default current. Conditional ETag supported.
- **Response:** design schema `reagent.project-desired-manifest/v0.1` and ETag
  bound to canonical checksum.
- **Codes:** 200, 304, 401, 403, 404, 409 rollback visibility restriction, 422.

### `POST /projects/{project_id}/manifest/changes`

- **Auth/scope:** exact `project.manifest.write`; UUIDv4 idempotency.
- **Request:** `reagent.project-manifest-change/v0.1`, explicit
  `base_revision`, bounded typed operations `ADD_INSTANCE`, `RETIRE_INSTANCE`,
  `PIN_CAPSULE_VERSION`, `PIN_SKILL`, `BIND_RESOURCE`, or
  `SET_ARTIFACT_REQUIREMENT`. No arbitrary JSON patch.
- **Response:** 201/200 replay complete new manifest, revision, checksum, and
  safe change summary.
- **Concurrency/replay:** revision compare and append occur in one transaction;
  409 conflict returns only current revision/checksum, not hidden entries.
- **Codes:** 409 `MANIFEST_REVISION_CONFLICT`,
  `MANIFEST_ROLLBACK_REJECTED`, or idempotency conflict; 422 semantic/schema;
  424 unavailable reviewed dependency; 401/403/404.

## 6. Workspace synchronization

### `POST /projects/{project_id}/workspace/sync-plan`

- **Auth/scope:** exact Project+Workspace `workspace.sync.plan`; UUIDv4
  idempotency; zero Provider/Hosted/LLM capabilities.
- **Request:** `reagent.workspace-sync-plan-request/v0.1`: Workspace ID, installed
  revision/lock checksum, target revision or current, client/platform
  compatibility, installed Capsule/Skill checksums, and dry-run flag. No local
  paths or secrets.
- **Response:** 200 design schema `reagent.workspace-sync-plan/v0.1`; empty
  action list means `NO_CHANGE`. Exact replay stable.
- **Effects:** creates only bounded plan/audit metadata; never writes local
  filesystem and never claims installation.
- **Codes:** 409 revision/rollback/idempotency; 422 malformed lock/capability;
  424 dependencies; 401/403/404; 413 size.

### `POST /projects/{project_id}/workspace/sync-ack`

- **Auth/scope:** exact Project+Workspace+installation
  `workspace.sync.ack`; short-lived and no execution capability.
- **Request:** design schema `reagent.capsule-installation-ack/v0.1` binding plan,
  manifest, and Installed Lock checksums plus installed Capsule identities.
- **Response:** 200/201 `reagent.workspace-sync-ack-receipt/v0.1`; exact replay
  returns same receipt. Changed content conflicts.
- **Effects:** records locally reported installation observation only. No local
  write and no first-class device inventory.
- **Codes:** 409 idempotency/revision/ack content conflict; 422 checksum/schema;
  401/403/404.

## 7. Progress and Artifacts

### `GET /projects/{project_id}/progress`

- **Auth/scope:** `project.progress.read`.
- **Response:** `reagent.project-progress/v0.1` graph/list of instances,
  dependency edges, cloud-observation timestamp, sync uncertainty, Artifact
  metadata, and recommendations. Cursor pagination applies to instances over
  100. No concrete output bytes.
- **Codes:** 200, 401, 403, 404, 422.

### `GET /projects/{project_id}/workflow-instances/{instance_id}/progress`

- **Auth/scope:** exact project+instance `project.progress.read`.
- **Response:** `reagent.workflow-instance-progress/v0.1`, latest projection and
  paginated immutable report history. Existing v0.2 reports are represented by
  compatibility metadata without byte rewriting.
- **Codes:** 200, 401, 403, 404, 422.

### `GET /projects/{project_id}/artifacts`

- **Auth/scope:** `project.artifact-metadata.read`; optional instance/type/state
  filters; cursor/limit.
- **Response:** `reagent.artifact-reference-page/v0.1`, bounded metadata only.
  Local path is omitted or Workspace-relative; Resource locator is redacted.
- **Codes:** 200, 401, 403, 404, 422. There is no Artifact byte download/upload
  endpoint in this design.

Skill and Resource mutation/read routes are deliberately **deferred** and are
not published as active API contracts. Their schema/table reservations do not
make a product surface.

## 8. Local CLI

New Workspace command discovery is `python reagent_local.py --help` from a
Workspace root. Legacy Package `python reagent_local.py run .` remains
unchanged for V0.x. Proposed Workspace commands are:

```text
python reagent_local.py workspace status . [--json]
python reagent_local.py sync . [--dry-run] [--json]
python reagent_local.py workflow list . [--json]
python reagent_local.py workflow run <instance-id> . [--offline]
python reagent_local.py artifact status . [--json]
python reagent_local.py resource status . [--json]
```

### Common behavior

- Resolve the root by locating and validating `project.json`; never walk into
  another project or accept a symlinked root.
- Obtain local service authentication through the existing loopback bootstrap
  pattern. Tokens stay in process memory or protected OS temporary storage
  outside the Workspace and never appear in arguments/logs.
- Human output is stage-labelled and value-safe. `--json` emits one versioned
  result object to stdout and sends diagnostics to stderr.
- `--dry-run` may fetch and validate a plan but performs no staging/install/ack.
- Offline status and installed Capsule runs use the verified Installed Lock;
  sync and desired-manifest mutation fail with `OFFLINE_SYNC_UNAVAILABLE`.
- A normal `workflow run` may perform a read-only update check and notify the
  owner. It cannot install; explicit `sync` or owner confirmation is required.
- Recovery reads the sync journal before new writes. `ACK_PENDING` retries ack
  only. `RECOVERY_REQUIRED` blocks install/run of affected Capsules until safe
  reconciliation.
- Exit classes are those in the sync error taxonomy. Capsule research failure
  is 70 and never converted into cloud completion.

### Command semantics

- `workspace status`: compare identity, desired cache, lock, pending ack, and
  drift observations without mutation.
- `sync`: retrieve desired state/plan, show actions, require confirmation unless
  `--dry-run`, and execute the atomic state machine.
- `workflow list`: list desired, installed, retired, and blocked instances with
  cloud/local qualifiers.
- `workflow run`: validate exact installed Capsule, Skill pins, dependencies,
  and mutable roots; invoke its local Harness boundary; preserve per-instance
  round state.
- `artifact status`: verify selected local references only when explicitly
  requested; no upload.
- `resource status`: show resolver readiness and pinned revision; it never
  prints credentials or auto-pulls/pushes.
