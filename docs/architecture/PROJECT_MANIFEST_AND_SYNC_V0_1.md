# Project Manifest and Pull-Based Sync Design V0.1

> **Design only.** No route, CLI command, filesystem transition, or schema in
> this document is implemented by ARCH-D1.

## 1. Desired state versus installed state

The Desired Project Manifest is cloud authority for requested configuration:
Workflow Instances, exact Capsule and Skill pins, Artifact requirements,
External Resource bindings, and compatibility constraints. It never asserts
that a local Workspace exists, that bytes are installed, or that execution
succeeded.

The Installed Workspace Lock is a local, checksum-bound observation of verified
Capsules, Skill content, Artifact materializations, Resources, and the last
manifest revision applied. It is not accepted as cloud desired state and is not
an automatic multi-device merge input.

Manifest changes are append-only revisions. A change supplies
`base_revision`; the cloud compares it with the current revision in one
transaction. Mismatch returns `MANIFEST_REVISION_CONFLICT`. A supplied or
cached revision below the installed anti-rollback floor returns
`MANIFEST_ROLLBACK_REJECTED`. Offline local execution may continue against the
Installed Lock; offline authoring of desired configuration is not supported.

## 2. Manifest ownership and checksums

The manifest controls identities and pins, not local paths or availability.
Each revision contains the complete desired snapshot plus its prior revision,
not a patch that requires replay forever. Entry checksums allow indexed
comparison. The manifest canonical checksum is SHA-256 over RFC 8785-style
canonical JSON with `manifest_checksum` omitted. Capsule, Skill, and Artifact
checksums are never derived from mutable Workspace data.

The Installed Lock records the manifest checksum it verified, its own checksum
computed with `lock_checksum` omitted, and exact installed destinations relative
to the Workspace. No cloud response may supply an absolute local path.

## 3. Sync plan

A sync client sends Project/Workspace identity, current installed revision and
lock checksum, and the target manifest revision. The cloud returns an immutable
plan bound to:

- `installation_id` and idempotency key;
- Project and Workspace;
- base and target manifest revisions/checksums;
- missing Capsule versions and expected archive/definition checksums;
- exact Skill pins;
- Artifact requirements and compatibility predicates;
- Resource bindings that need local resolution;
- retire-only desired changes;
- compatibility requirements; and
- bounded archive counts and sizes.

The plan never contains credentials or executable shell fragments. A local
resolver maps typed actions to reviewed client implementations. Replaying the
same request returns the same plan; the same idempotency key with changed
content conflicts.

## 4. State machine

Every state is stored in `.reagent/sync/current.json` by an atomic temp-write,
fsync, and rename. The record contains only identities, revisions, checksums,
safe error code, and timestamps. Staging paths are deterministically owned by
`installation_id`.

| From → To | Trigger and preconditions | Filesystem/API effect | Interruption, rollback, retry, and user status |
|---|---|---|---|
| start → `NO_CHANGE` | Installed revision/checksum equals desired and no ACK pending | Read-only manifest/lock check; no mutation | Idempotent success: “Workspace is current.” |
| start/`NO_CHANGE` → `UPDATE_AVAILABLE` | Newer non-rollback manifest observed | Cache desired manifest only after checksum/scope validation | Offline leaves installed state usable. Status lists changes, not local success. |
| `UPDATE_AVAILABLE` → `PLAN_CREATED` | Owner runs explicit sync (or dry-run); identities, base revision, and lock validate | POST plan; persist canonical plan and checksum in protected staging | Revision conflict writes no install content. Exact retry returns same plan. |
| `PLAN_CREATED` → `STAGING` | Owner confirms non-dry-run; staging destination absent or owned by same installation | Create mode-restricted staging directory and transaction record | Existing unowned/different staging fails safe. Retry resumes verified transaction. |
| `STAGING` → `DOWNLOADING` | Plan contains missing archives; size/count budget accepted | Download through reviewed transport to new temporary files | Partial bytes are never installable. Retry uses expected checksum and safe range policy or restarts one file. |
| `DOWNLOADING` → `VALIDATING` | All planned bytes locally complete | No destination write; validate archive envelope, path set, checksum, signatures if introduced, Capsule manifest, Skills, compatibility | Failed content is quarantined in staging or removed by explicit recovery; installed lock unchanged. |
| `VALIDATING` → `DRIFT_DETECTED` | An existing immutable installed file differs from lock or disk destination conflicts with recorded content | Read-only drift evidence; no overwrite | Non-retryable until owner resolves/adopts explicitly. “Immutable local content changed.” |
| `VALIDATING` → `DEPENDENCY_BLOCKED` | Artifact/Skill/Resource requirement missing, stale, incompatible, or unavailable | Persist value-safe requirement identities/status only | Retry after explicit materialization/resolution; installed state unchanged. |
| `VALIDATING` → `INSTALLING` | All content/dependencies valid, destinations absent, base revision still current | Prepare same-filesystem final directories; acquire Workspace install lock | Interruption before rename leaves only staging. Retry revalidates. |
| `INSTALLING` → `INSTALLED` | Each planned new destination atomically renamed; retire entries recorded as desired metadata only | Add new Capsule directories; never alter old Capsules/Artifacts | Journal lists completed renames. Recovery validates each; no rollback deletes valid installed versions. |
| `INSTALLED` → `LOCK_WRITTEN` | All planned destinations and dependency observations verify | Write a complete new lock to temp, fsync, atomic rename; write append-only installation receipt | Crash before rename keeps old lock and leads to `RECOVERY_REQUIRED`; after rename new lock is authoritative. |
| `LOCK_WRITTEN` → `ACK_PENDING` | Local commit complete; acknowledgement not yet accepted | Write local ack envelope; POST exact ack | Installation remains valid. Network/auth failure never rolls it back. Retry acknowledgement only. |
| `ACK_PENDING` → `ACKNOWLEDGED` | Cloud accepts or replays identical ack | Persist returned safe receipt/ack timestamp | Exact retries return same acknowledgement; no local reinstall. “Installed and reported.” |
| any pre-install state → `REVISION_CONFLICT` | Cloud current revision differs from plan base/target, or manifest changed before install lock | No destination/lock write | Refresh desired state and create a new plan; never merge automatically. |
| interrupted `INSTALLING`/`INSTALLED` → `RECOVERY_REQUIRED` | Startup finds transaction journal/staging and lock/destination disagreement | Read-only reconcile first; block normal sync writes | Owner runs recovery; verify completed renames, then finish lock or fail safe. Never guess/delete research state. |
| any → `FAILED_SAFE` | Malformed identity, scope/checksum/security violation, or unrecoverable local I/O | Store only safe code/stage; revoke session; no further writes | Retry only after identified cause; primary failure not masked by cleanup. |

`DRIFT_DETECTED`, `DEPENDENCY_BLOCKED`, `REVISION_CONFLICT`, and
`RECOVERY_REQUIRED` are explicit states, not generic exceptions. A state may be
re-entered only with the same installation identity and matching transaction
checksum; otherwise a new plan is required.

## 5. Atomic installation contract

The implementation must perform these gates in order:

1. retrieve and authenticate the Desired Manifest and Sync Plan;
2. confirm Project, Workspace, base revision, target revision, and checksums;
3. compare every locked immutable path and detect local drift;
4. download each Capsule archive into a mode-restricted staging root;
5. reject absolute paths, `..`, duplicate/case-colliding paths, symlinks,
   hardlinks, devices, FIFOs, archive bombs, excessive nesting, and undeclared
   files;
6. verify archive and Capsule Definition checksums, exact Skill pins, platform
   and Workspace compatibility, and secret-prohibited content policy;
7. resolve each Artifact dependency by type, schema, checksum, and availability;
8. install only to a previously absent versioned destination using an atomic
   same-filesystem rename;
9. write a complete Installed Lock atomically after all destinations verify;
10. append an Installation Receipt binding plan, lock, destination checksums,
    and `installation_id`;
11. send the exact cloud acknowledgement.

If a destination exists with different content, the terminal error is
`CAPSULE_INSTALL_CONFLICT`. If it exists with the same verified content, the
step is an idempotent no-op only when the transaction/lock binding also agrees.
No existing Capsule or Artifact is overwritten. An acknowledgement failure
after step 10 retains the valid installation, records `ACK_PENDING`, and retries
only step 11.

## 6. Recovery boundaries

- A staging directory without a valid transaction record is untrusted and is
  not resumed or automatically deleted.
- A valid staged archive can be reused only when plan, archive checksum,
  target revision, and installation identity all match.
- A renamed Capsule absent from the old lock is verified against the journal;
  recovery can finish the new lock but cannot remove the Capsule automatically.
- A new lock without a receipt is reconstructed only from the verified lock and
  transaction journal; no Capsule executes during recovery.
- Retirement removes entries from desired active state and may hide them from
  default UI. It never removes directories, Artifacts, reports, or history.
- Upgrade installs the exact new version side by side, validates dependencies,
  then changes the manifest pin. In-place modification and silent Skill update
  are prohibited.

## 7. Error taxonomy

CLI exit codes are stable classes: `0` success/nonterminal acknowledged warning,
`2` usage, `10` identity/schema, `20` connectivity/offline, `30`
authentication/scope, `40` manifest concurrency/rollback, `50`
validation/dependency/drift, `60` installation/recovery, and `70` Capsule-run
failure.

| Error code | HTTP / CLI | Safe frontend message | Recovery | Retryable |
|---|---:|---|---|---|
| `MANIFEST_REVISION_CONFLICT` | 409 / 40 | Project configuration changed elsewhere. | Refresh, review, create a new plan. | Yes, new base |
| `MANIFEST_ROLLBACK_REJECTED` | 409 / 40 | Requested configuration is older than the installed safety floor. | Owner-reviewed rollback plan only. | No automatic |
| `CAPSULE_CHECKSUM_MISMATCH` | 422 / 50 | Downloaded Capsule failed integrity verification. | Discard only owned staging bytes; fetch again. | Bounded |
| `CAPSULE_COMPATIBILITY_FAILURE` | 422 / 50 | Capsule is incompatible with this Workspace/client. | Install supported client/version or choose compatible pin. | After change |
| `IMMUTABLE_DRIFT_DETECTED` | 409 / 50 | Installed immutable Capsule files changed locally. | Inspect; restore or explicitly adopt as new content. | No automatic |
| `CAPSULE_INSTALL_CONFLICT` | 409 / 60 | The target Capsule destination contains different content. | Choose a new version or owner-resolve destination. | No automatic |
| `ARTIFACT_MISSING` | 424 / 50 | A required Artifact is not available locally. | Materialize or run producer Workflow. | After dependency |
| `ARTIFACT_CHECKSUM_MISMATCH` | 422 / 50 | Artifact bytes do not match the registered reference. | Obtain exact bytes; never substitute. | After replacement |
| `ARTIFACT_SCHEMA_INCOMPATIBLE` | 422 / 50 | Artifact schema is incompatible with the consumer. | Select compatible producer or explicit reviewed converter. | After plan |
| `SKILL_UNAVAILABLE` | 424 / 50 | A pinned reviewed Skill is unavailable. | Restore exact built-in version or revise manifest. | After dependency |
| `RESOURCE_UNAVAILABLE` | 424 / 50 | A required external Resource is unresolved. | Use local resolver/credential and verify revision. | After dependency |
| `OFFLINE_SYNC_UNAVAILABLE` | 503 / 20 | Sync requires the local ReAgent service and cloud desired state. | Continue installed offline work or reconnect. | Yes |
| `INSTALLATION_ACK_PENDING` | 202 / 0 warning | Installation is valid locally; cloud acknowledgement is pending. | Retry acknowledgement only. | Yes |
| `LEGACY_PACKAGE_UNSUPPORTED` | 422 / 10 | This legacy Package version is not supported by this client. | Use compatible V0.x client or approved import. | No automatic |
| `SCOPE_MISMATCH` | 403 / 30 | Session is not authorized for this Project or Workspace. | Reopen correctly scoped session; do not reveal existence. | No automatic |
| `MALFORMED_WORKSPACE_IDENTITY` | 422 / 10 | Workspace identity data is invalid. | Restore immutable metadata from trusted bootstrap. | After repair |

Errors expose only code, stage, bounded identity, and action. They never include
bearers, credentials, database URLs, full private locators, archive content, or
free-form exception traces.

## 8. Threat model and controls

| Threat | Required control |
|---|---|
| Rollback or manifest substitution | Monotonic revision floor; Project/Workspace binding; authenticated response; canonical checksum; explicit owner rollback process. |
| Cross-project Capsule installation/access | Exact Project, Workspace, instance, manifest, and capability scope at API and local validation; existence-blind authorization failures. |
| Path traversal, links, archive bombs | Reject unsafe archive types/paths, normalize Unicode/case, preflight expanded count/size/depth, stream within limits, install on same filesystem. |
| Checksum collision assumptions | SHA-256 with domain-separated canonical envelopes; no checksum alone grants authorization; algorithm agility reserved by prefix. |
| Immutable drift or stale Artifact substitution | Lock comparison before sync/run; immutable Artifact identity binds schema, checksum, producer instance/round; mismatch fails. |
| Malicious Capsule or prompt injection | Publication review, static validation without execution, declared permissions/capabilities, local Harness instruction precedence, untrusted Provider/Resource content treated as data. |
| Arbitrary executable Skills | Initial executable tier is `BUILT_IN_REVIEWED_ONLY`; private/imported states disabled/quarantined; exact pins and permission ceilings. |
| Credential-bearing Git URLs or gated metadata leakage | Reject URL userinfo and known secret query keys; locators are bounded/redacted; local credential helpers only; cloud visibility metadata excludes secrets. |
| Partial installation | Transaction journal, absent destination requirement, atomic rename, lock-after-content order, recovery-required state. |
| Acknowledgement replay | Installation ID + plan/lock checksum + idempotency key; exact replay only; changed content conflicts. |
| Offline divergence and multi-device conflict | No offline desired-state authoring; no auto merge; optimistic revision; logical Workspace acknowledgement does not claim device inventory. |
| Untrusted metadata | Schema bounds, unknown-field rejection, canonicalization, value-safe logs, no metadata-driven command execution. |

No design grants cloud direct filesystem write, puts credentials in the
Workspace, permits an unscoped capability, or allows external push without
explicit owner confirmation.
