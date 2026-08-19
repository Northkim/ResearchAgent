# R1 exact-input and local-safety change packet

Status: **APPROVED PROGRAM / PRE-WRITE CONTRACT FROZEN**

Date: 2026-08-20

Parent authority:
`.agent_read/progress/2026-08-20_post_d1_repair_program.md` at commit
`ff41b6d462bee18e7e14663a6da5adb798bbf4d5`.

This packet narrows R1 without changing its acceptance. R1 is split into three
clean subphases because the zero-paper consumer precondition has a publication
authority problem that must not be hidden inside the compatible Local repair.

## 1. Change identity

| Subphase | Scope | Primary ledger IDs |
|---|---|---|
| R1A | Local exact binding/materialization/readiness/refresh | `D1-INPUT-RECONCILE-01`, `D1-INPUT-RUNNABLE-01`, `D1-INPUT-RECEIPT-01`, `D1-INPUT-REFRESH-01`; preserve `D1-INPUT-FRESH-01` |
| R1B | Browser accepted-binding continuity, optional evidence decision, published zero-paper consumer precondition | `D1-FRONTEND-KEY-01`, `D1-WRITING-BINDING-01`, `D1-REVIEW-INPUT-LIFECYCLE-01`, `D1-UPSTREAM-ZERO-PAPER-01` |
| R1C | Package/secret/path/OS-metadata classification | `D1-PACKAGE-OS-METADATA-01`, `D1-PACKAGE-PRIVATE-PATH-01` |

The relevant part of `D1-LOCAL-ORCHESTRATION-01` is limited in R1 to removing
the need for a separate Artifact Index refresh before normal materialization.
The one-command full lifecycle remains R2.

## 2. Current authority and recovered root causes

### R1A

Current Cloud authority:

- `ArtifactReferenceService.bind_dependency` retires one exact active binding
  only when `replace_binding_id` exactly names it.
- `materialization_plan` emits only active exact bindings and includes exact
  binding ID, Artifact ID, checksum, producer, target, and an aggregate
  `plan_checksum`.
- no latest/highest selection exists in this service.

Current Local authority:

- each materialization receipt is named by exact binding ID;
- a receipt includes exact Artifact/binding/target/checksum plus the aggregate
  plan checksum;
- `_materialize_one` refuses all different target bytes, even when another
  valid receipt proves those bytes are the prior ReAgent-managed binding;
- an unchanged exact target is rejected when its receipt differs only because a
  sibling changed the aggregate plan checksum;
- `_local_input_state` scans receipts and compares targets only to those
  receipts. It does not compare them to a persisted current Cloud plan;
- `workflow_list` is offline and currently has no durable current-plan snapshot;
- `materialize_artifacts` assumes the Artifact Index was refreshed separately.

Therefore the observed D1 behavior follows directly from source:

1. new binding B has a new receipt filename;
2. target contains A;
3. B's receipt does not exist, so A's ownership proof is ignored and B fails as
   an ambiguous conflict;
4. old A receipt remains internally valid, so offline readiness reports runnable;
5. an unchanged sibling receipt fails whole-document equality because its old
   aggregate plan checksum differs.

### R1B

Current frontend source already keys generic and Idea candidate rows by exact
`artifact_id` and supplies `replace_binding_id` for a changed binding. These
accepted source semantics need regression coverage before any edit; the D1
occurrence must not be recreated by weakening the test.

Downstream custom Detail renders exact input management only while the shared
Cloud next action is `SELECT_INPUT`. Shared readiness moves to `MATERIALIZE` as
soon as required bindings exist, so unresolved optional evidence disappears
without an explicit Owner continue decision.

The published Idea 0.2 / Capsule 0.3 requirement expresses type/schema/exact
cardinality only. The authoritative `selected-paper-library/v1` bytes allow
zero papers, while the Idea Local runtime independently rejects zero papers.
Cloud stores exact Artifact identity/checksum/size but not an authoritative
selected-paper count. Presentation may contain `selected_count`, but it is
optional UI metadata and cannot be scientific readiness authority.

Consequently R1B must not use presentation to classify compatibility. Before
R1B production writes, choose the smallest forward-additive consumer contract
that can state the minimum-content precondition and enforce it before an input
is presented as locally runnable. Historical Idea 0.2/0.3 bytes remain
immutable. If authoritative Cloud pre-evaluation requires a new bounded
Artifact fact, freeze that additive contract and migration separately.

### R1C

Both package validators contain a bounded `.DS_Store` exception, but they scan
file contents for sensitive/machine-path patterns before reaching it. The
Workspace scanner also uses one `_SECRET_PATTERNS` tuple for true credentials
and absolute machine paths, then reports either class as “prohibited credential
material.” Materialized scientific inputs already use the narrower true-
credential subset.

R1C must reorder only the exact bounded OS-metadata decision and split the
classification of true credential vs private path. Unknown undeclared files and
real secrets remain rejected.

## 3. R1A target contract

### 3.1 Current-plan snapshot

The normal materialization operation fetches and validates the exact Cloud plan
and persists it atomically in a ReAgent-owned Workspace control location before
changing any consumer input. This snapshot is not scientific evidence; it is
the last observed exact Cloud coordination state used to fail closed offline.

`workflow list` may report `LOCALLY_MATERIALIZED` only when:

```text
all required requirement keys exist in the snapshot
and every bound snapshot entry has its exact binding receipt
and receipt.plan_checksum == snapshot.plan_checksum
and receipt Artifact/binding/producer/target identities == snapshot entry
and target bytes/checksum/size == snapshot entry
```

No snapshot means “selection or materialization required,” not runnable.

This does not claim that an offline Workspace can discover a later Cloud edit.
Every networked high-level preparation operation must refresh the snapshot; if a
materialization attempt observes a changed binding and fails, the newly observed
plan remains durable so the stale prior receipt cannot advertise runnable.

### 3.2 Ownership-proven replacement

When target bytes differ from new B, replacement is allowed only if exactly one
active ReAgent receipt proves:

- same Project, Workspace, consumer, requirement, and target;
- a different prior binding/Artifact;
- receipt checksum is valid;
- target bytes exactly equal that receipt's target checksum;
- the prior Artifact is present in the verified local Artifact Index with the
  same identity/checksum.

Then:

1. stage B from its verified producer source;
2. validate staged B completely;
3. atomically replace the managed target;
4. write B's exact current-plan receipt;
5. move the prior receipt intact to a ReAgent-managed receipt-history location.

If ownership is absent, conflicting, symlinked, hard-linked, or ambiguous, fail
closed without changing the target.

### 3.3 Unchanged sibling carry-forward

If the target, binding ID, Artifact ID, producer, type/schema, and exact bytes
are unchanged and only the aggregate current-plan checksum changed, rewrite the
same ReAgent-managed receipt under the new plan after revalidation. Preserve the
original `materialized_at` as the copy time; the receipt checksum changes
truthfully because the coordination plan changed.

Any identity or byte difference remains a conflict.

### 3.4 Automatic Artifact Index reconciliation

Normal non-dry-run materialization first performs the existing exact Artifact
Index reconciliation. It does not add auto-latest and does not bypass source
checksum verification. Low-level `artifact refresh` remains available.

Fetch the plan before local mutation, persist it, and verify the plan again
after successful local materialization. If the Cloud plan changed concurrently,
persist the newer plan, return a concurrency failure, and require reconciliation;
never report the just-materialized old plan runnable.

## 4. R1B target contract and decision gate

1. Candidate React identity is exact Artifact identity; multiple candidates are
   never auto-bound.
2. A successful Confirm re-renders from the accepted dependency response/cache
   invalidation, not optimistic radio state.
3. Required completion does not hide optional evidence. The Owner sees selected,
   omitted, and unavailable optional roles and explicitly continues before the
   normal setup/materialization command is exposed.
4. The explicit omission decision is not scientific evidence and does not turn
   an omitted Artifact into a binding.
5. A valid zero-paper library stays valid and selectable for consumers that
   permit it.
6. The forward Idea consumer publishes and enforces its non-empty scientific
   precondition before materialization/run readiness. Presentation is not used
   as authority.

Stop with `HISTORICAL_CONTRACT_CONFLICT` if this cannot be represented without
editing Idea 0.2/0.3 or the library v1 schema in place. Stop with
`OWNER_DECISION_REQUIRED` if an additive authoritative content fact would make
Cloud store information outside the Owner-approved bounded coordination model.

## 5. R1C target contract

| Input class | Required outcome |
|---|---|
| Bounded exact `.DS_Store` | ignored before content scanning and package comparison |
| Oversized `.DS_Store` | rejected |
| Arbitrary undeclared file | rejected |
| Actual credential/private key/database credential | rejected as credential/secret |
| Absolute private local path in an otherwise permitted metadata location | rejected/classified as private machine path, never called an actual credential |
| Materialized exact scientific Artifact containing an honest local path | retain current narrower credential-only policy |

## 6. Source scope

Expected R1A production scope:

- `backend/project_workspaces/workspace_cli.py`
- no database, API, frontend, migration, Workflow, Capsule, or Artifact schema
  change.

Expected R1A tests:

- `backend/project_workspaces/tests/test_artifact_handoff.py`
- one readiness/public command test file only if the public invariant cannot be
  proven in the handoff fixture.

R1B expected owners:

- Progress/input application projection;
- binding hooks and `workflow-input-setup.tsx` / downstream Detail;
- forward Idea publication only if the precondition audit proves necessary;
- focused service/frontend/PostgreSQL/public Workspace tests.

R1C expected owners:

- `backend/workflow_packages/package_validator.py`
- `backend/project_workspaces/workspace_cli.py`
- security/package tests.

If a subphase exceeds roughly 20 production files or 4,000 production lines,
stop and split again before writes.

## 7. Failing/reproduction matrix

R1A tests must first demonstrate:

1. A materialized under old exact receipt; Cloud plan changes to B; ordinary
   materialization atomically produces B and current B receipt.
2. identical setup with target bytes but no matching managed receipt fails and
   leaves bytes unchanged.
3. Literature changes while Idea binding/bytes remain exact; Idea receipt is
   carried to the new aggregate plan.
4. materialization observes new plan then fails; `workflow list`/readiness cannot
   report the old receipt runnable.
5. materialization without an explicit prior `artifact refresh` succeeds after
   exact automatic Index reconciliation.
6. plan changes during materialization: operation returns concurrency failure,
   latest plan is durable, no stale runnable state is reported.
7. fresh first materialization and replay remain idempotent and exact.

R1B tests must demonstrate:

1. two candidates for one role have unique exact component identities;
2. changed confirmation displays the accepted B binding;
3. unresolved optional evidence stays visible and requires explicit continue;
4. omission creates no binding and remains visible in Review scope;
5. zero-paper producer is valid while the forward Idea consumer is blocked at
   its published precondition before materialization/run;
6. a one-paper exact library passes the same path.

R1C tests must cover the complete table in section 5.

## 8. Historical and security regression

Every subphase runs the four D1 regression locks. R1A additionally runs exact
binding/service, sync, public Workspace, and no-auto-latest tests. R1B runs
historical Idea/Literature and optional Review/Revision contracts. R1C runs
unknown file, symlink/hardlink, secret scrub, and immutable Capsule checks.

The protected D1 Project fingerprints from R0 must remain unchanged. All mutable
qualification uses marked disposable PostgreSQL and disposable Workspaces.

## 9. Migration and publication decision

- R1A: `MIGRATION_REQUIRED = NO`; publication change = 0.
- R1C: `MIGRATION_REQUIRED = NO`; publication change = 0.
- R1B: unresolved until the authoritative precondition design is frozen.
  Historical bytes must remain immutable; any required persistence/publication
  is forward-additive and qualified by upgrade/downgrade/re-upgrade before Owner
  use.

## 10. Stop conditions

Stop rather than implement if any repair:

- accepts a target without exact ownership proof;
- uses presentation as readiness/evidence authority;
- adds latest/highest/implicit merge behavior;
- makes Cloud authoritative for complete Local bytes;
- edits an immutable publication/migration;
- changes a repaired D1 lock;
- deletes or rewrites protected D1 evidence;
- requires a second execution engine;
- changes a fixture to encode the broken behavior.

R1A is ready for failing tests and focused implementation. R1B is not ready for
publication writes until its precondition authority is resolved. R1C is ready
after R1A is independently committed.
