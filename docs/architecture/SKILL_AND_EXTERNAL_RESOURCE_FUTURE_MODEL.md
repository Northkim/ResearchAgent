# Skill and External Resource Future Model

> **Design reservation, not implementation.** Initial executable Skill scope is
> `BUILT_IN_REVIEWED_ONLY`; external integration is metadata plus local resolver
> guidance. No marketplace, cloud connector, token storage, or automatic push
> is authorized.

## 1. Skill model

A Skill version is immutable and includes identity/version/checksum, owner and
visibility, supported Workflow Definitions/versions, input/output schema IDs,
required tools, required capabilities, permission ceiling, side-effect class,
source/provenance, license, trust tier, review status, and quarantine status.

Trust tiers and execution policy:

| Trust tier | Review status | Initial behavior |
|---|---|---|
| `BUILT_IN_REVIEWED` | `REVIEWED` | Executable when exact version/checksum is pinned and Capsule permission ceiling permits it. |
| `PRIVATE_DISABLED` | any | Metadata may be represented in future; execution rejected. |
| `IMPORTED_QUARANTINED` | `PENDING`/`QUARANTINED` | Store no executable content in the initial product; execution rejected. |
| any | `REJECTED`/`RETIRED` | Cannot be newly pinned or executed. Historical pin remains auditable. |

Each Capsule pins exact Skill versions and checksums. Workflow-level
requirements constrain acceptable Skills; Project pins choose exact reviewed
versions. Running Workflows never resolve a floating version and never update a
Skill silently. Required tools and capabilities are data contracts, not shell
commands. Side effects are `READ_ONLY`, `LOCAL_DECLARED_WRITE`,
`EXTERNAL_READ`, or `EXTERNAL_WRITE`; external writes always require explicit
owner confirmation even for a reviewed Skill.

Future private/imported support requires a separate threat review, sandbox,
license/provenance policy, quarantine pipeline, owner-visible permissions, and
revocation response. This design does not define a recommendation or ranking
algorithm for a Skill marketplace.

## 2. External Resource binding

A binding records structured, bounded metadata:

- provider and resource type;
- credential-free locator;
- immutable revision and optional checksum;
- Workspace-relative materialization path;
- access mode and sync policy;
- last locally reported availability;
- allow/ignore patterns;
- license/access warning; and
- timestamps/retirement.

The initial resolver interface maps a provider/type to a reviewed local command
implementation. Authentication uses the owner's existing local credential
helper or tool configuration. ReAgent neither receives nor stores the secret.
Resolution is explicit; pushes require separate owner confirmation and are not
part of automatic sync.

### 2.1 Git and GitHub

- `GIT` and `GITHUB` locators are HTTPS or SSH repository identities without
  URL userinfo, embedded tokens, or secret query parameters.
- A branch or tag may be an owner input for discovery, but availability cannot
  become verified until it resolves to a full commit SHA. The pinned commit SHA
  is authoritative.
- Submodules are enumerated and each URL/revision is separately validated and
  pinned. Recursive implicit trust is prohibited.
- Git LFS pointers are metadata until each required object OID/size is present
  and verified locally. Cloud does not proxy LFS credentials or large bytes.
- Dirty local clones are reported as drift; automatic push, reset, checkout, or
  overwrite is forbidden.

### 2.2 Hugging Face

- Provider `HUGGING_FACE` requires `repo_type` (`dataset`, `model`, or `space`),
  repository ID, and immutable commit revision.
- Bounded allow/ignore patterns are data, not glob-expanding commands supplied
  by cloud.
- Gated/private availability is explicit (`GATED` or `PRIVATE`), with details
  value-safe. Local CLI credentials remain local.
- File checksums/OIDs are recorded when the service exposes them; otherwise the
  local materialization computes a ReAgent checksum and records the limitation.

### 2.3 Local and generic stores

- `LOCAL_DIRECTORY` is a logical binding to an owner-selected local directory.
  Cloud stores no absolute path; a machine-local index maps it to a path.
- `EXTERNAL_STORE` requires a reviewed provider namespace, opaque credential-
  free locator, immutable version when possible, and explicit checksum policy.
- Resource bytes never become shared writable Workspace state. Consumers use
  verified materialization or read-only resolver access.

## 3. Locator safety

Locators reject URL userinfo, fragments used as secrets, known credential query
keys (`token`, `key`, `signature`, `credential`, `password`), control
characters, shell syntax intended for execution, and excessive length. Logs and
cloud UI display provider, resource type, and a bounded redacted identifier,
not a private URL or local path.

## 4. Deferred product surfaces

Skill upload/import/catalog UI, arbitrary Skill execution, GitHub Apps/OAuth,
Hugging Face token storage, cloud pulls, automatic push, general large-file
storage, and background resource synchronization remain deferred. Future API
names are intentionally not published as active endpoints in V0.1 design.
