# S1 shared Core and user-action contracts

- Status: **PROPOSED — READY FOR OWNER REVIEW**
- Phase: S1 Shared Core Contracts
- Baseline: `main` at `85b85251e005b6bc45d2ef7b98ee73867badc7ae`
- Authority: Owner decisions, published contracts, and source-of-truth policy
- Implementation authorization: **NOT AUTHORIZED**

## 1. Alignment, scope, and change boundary

`PLAN_ALIGNMENT = PASS`. Engineering Harness and B0 remain done/frozen;
UX-A1 remains passed; Writing #2 UX closure is deferred and non-blocking for
S1. The approved next sequence is UI-P0, E1, W1, R1, W2, then incremental
frontend completion.

This packet freezes only the minimum cross-Core scientific boundaries and
derived presentation semantics required before UI-P0 and the first Real Core
vertical slices. It does not implement a Core or frontend, change an API or
database, add a migration, change a Capsule or Registry record, or publish or
mutate an Artifact schema. Experiment 0.4 is frozen and outside scope.

Affected published identities: **NONE**. Production, test, migration, and
frontend file impact: **NONE**. Rollback is removal of this unimplemented
proposal; no runtime or data rollback applies.

## 2. Contract reuse decision

S1 adds no persisted field. Its terms have these authorities:

| Semantic | Classification | Existing authority or future boundary |
|---|---|---|
| Exact Output identity and provenance | `EXISTING_REUSED` | `ArtifactReference`: ID, type, schema, checksum, producer Workflow Instance, Progress receipt/report/round, state, time |
| Workflow research state | `EXISTING_REUSED` | Progress `IN_PROGRESS`, `BLOCKED`, `FAILED`, `CANCELLED`, `COMPLETED`; absence of a report derives `NOT_STARTED` |
| Activity and continuation | `EXISTING_REUSED` | Progress current state, next recommended action, continuation reason/instructions, reports, and timestamps |
| Exact input binding | `EXISTING_REUSED` | Artifact dependency binding: requirement, exact Artifact ID, expected checksum, consumer Workflow Instance |
| Workflow readiness/action | `EXISTING_REUSED` | Workflow Instance projection readiness, missing/bound inputs, result count, installation evidence, and `next_action` |
| Project recommendation | `EXISTING_REUSED` | Project Progress recommendation, instances, activity, dependency edges, and status counts |
| Workflow user-action projection | `DERIVED_PROJECTION` | Derived from the reused authorities below; not a lifecycle or storage contract |
| Project-list attention projection | `DERIVED_PROJECTION` | Server-side list projection justified below; not a new endpoint decision |
| Core stage codes and expected Output contract | `FUTURE_CORE_CONTRACT_REQUIRED` | Defined by E1, W1, or R1 without changing this shared shape |
| Durable approval evidence and evidence locators absent from v1 | `FUTURE_CORE_CONTRACT_REQUIRED` | Per-Core v2 or companion decision; never overload v1 |

`NEW_PERSISTED_FIELD = NONE`.

## 3. Shared scientific boundaries

### 3.1 Artifact versioning

- Published v1 schemas and semantics are immutable.
- Incompatible capability uses a new version or separately named companion
  Artifact. S1 does not select one globally; each Core decides only when its
  concrete contract requires it.
- No consumer reinterprets v1, coerces versions, or selects the latest
  compatible Artifact implicitly. Historical bytes, identity, provenance, and
  consumers remain testable.

### 3.2 Evidence identity

A scientific claim, result, or review issue must resolve directly or through a
validated companion record to:

```text
source Artifact ID, type/schema version, and content checksum
producer Workflow Instance and Progress report/receipt/round
bounded evidence item/location when applicable
availability and limitation
```

The first two lines reuse `ArtifactReference`. Item/location may be a claim,
result, table, section, or structured record ID. Availability uses existing
Artifact state where sufficient. A finer locator or scientific limitation is a
future Core contract only when the Core needs it. Free text alone is not
evidence identity; missing evidence is a limitation, never confidence.

### 3.3 Exact handoff and isolation

- Owners bind exact immutable inputs; changed bindings invalidate dependent
  approval and require renewed approval.
- A Workflow reads only declared, materialized inputs and its own package/local
  state, never a sibling Workflow's private files.
- Cloud stores Artifact metadata/provenance, not general Output bytes.
- Browser actions change Cloud metadata or desired state only. Local Workspace
  bytes are changed only through an authorized local path.

### 3.4 Owner approval checkpoint

An approval checkpoint is a deliberate owner decision over an exact proposal,
not inference from continued conversation. The proposal binds exact input and
Resource identities/checksums plus the plan/action revision being approved;
any material change invalidates it. Approval authorizes one bounded transition,
not later unrelated work or publication.

Existing Progress can present a pending checkpoint using `current_state`,
`next_recommended_action`, `continuation_reason`, and continuation instructions;
exact bindings and checksums already identify the subject. This is sufficient
for UI-P0 presentation. Progress does **not** by itself provide durable proof of
proposal identity, decision, expiry/invalidation, or consumption. Each Real Core
must choose a validated v2/companion/local record before execution relies on
such proof. No shared approval subsystem or persistence model is introduced.

### 3.5 Canonical Progress and derived state

| Meaning | Canonical expression | Presentation rule |
|---|---|---|
| In progress | persisted `IN_PROGRESS` | normal unless a bounded owner checkpoint is declared |
| Needs owner action | no persisted enum | derived from checkpoint/continuation/action metadata; execution waits |
| Blocked | persisted `BLOCKED` | blocker and responsible actor must be shown |
| Failed | persisted `FAILED` | attempted round ended unsuccessfully; evidence is preserved |
| Cancelled | persisted `CANCELLED` | attempt intentionally ended without completion |
| Completed | persisted `COMPLETED` | exact round and declared Outputs finalized for acknowledgement |

No `AWAITING_OWNER` or other persisted state is authorized. Cloud-missing
local completion is recovered by validating/uploading the exact immutable
report, never by rerunning work or manufacturing a repair round.

Resource readiness remains layered: metadata reference → exact revision →
local bytes → verified checksum → accepted license → usable runtime → owner
approval. Current contracts express the early identity/materialization layers;
license, runtime usability, and approval are future E1 contracts. Neither UI nor
execution may collapse metadata existence into “ready.”

## 4. Minimal Workflow user-action projection

This is one logical read projection, not an API schema or persisted lifecycle:

```text
WorkflowActionProjection {
  stage
  actor
  attention_state
  blocker
  next_action
  expected_output
  latest_output
}
```

| Field | Minimum semantics | Classification |
|---|---|---|
| `stage` | Core-defined stable stage code plus user label; the label is primary | Core code `FUTURE_CORE_CONTRACT_REQUIRED`; label `DERIVED_PROJECTION` |
| `actor` | `OWNER`, `AGENT`, `SYSTEM`, or `NONE`; responsibility, not authorization | `DERIVED_PROJECTION` |
| `attention_state` | `NORMAL`, `OWNER_ACTION_REQUIRED`, `BLOCKED`, `ATTENTION_REQUIRED`, or `COMPLETED` | `DERIVED_PROJECTION` |
| `blocker` | nullable `{code, message}`; code selects the correct UI/action, message explains the actual reason | `DERIVED_PROJECTION` |
| `next_action` | one `{surface, code, label, description}`; surface is `BROWSER`, `LOCAL`, `INFORMATIONAL`, or `NONE` | Existing action reused; presentation fields derived |
| `expected_output` | nullable `{label, artifact_type, artifact_schema, state: EXPECTED}` | Type/schema are future Core contract; user label derived |
| `latest_output` | nullable `{label, artifact_id, artifact_type, artifact_schema, checksum, produced_at, state: PRODUCED}` | Exact identity reused; label derived |

`ATTENTION_REQUIRED` combines failed and acknowledged-stale cases without
pretending they share a lifecycle. The blocker retains the distinction. Initial
blocker codes are bounded to current decisions: `MISSING_INPUT`,
`LOCAL_SYNC_REQUIRED`, `OWNER_APPROVAL_REQUIRED`, `RESOURCE_NOT_READY`,
`EXECUTION_FAILED`, `LOCAL_STATE_STALE`, and `INVALID_OR_UNSUPPORTED_STATE`.
Core-specific codes may be added only with their Core contract; this is not a
general error taxonomy.

`next_action` is presentation metadata, not a command bus. A browser action may
name an existing route/action; a local action gives owner-readable instructions
through an existing safe local path; informational means there is no executable
UI action; `NONE` means no next action. Technical provenance remains separately
available. Product copy says **Output** and **Activity**; engineering contracts
retain **Artifact** and **Progress**.

## 5. Projects projection decision

Decision: **B — a future backend projection/API enhancement is justified**.
Current Project detail Progress can derive a recommendation for one Project,
but `/projects` exposes only legacy per-project Progress and cannot coherently
answer attention, actor, blocker, action, and latest Output. Client-side detail
fetches for every Project would duplicate rules and create an N+1 list.

The future list projection should be derived server-side and contain only:

```text
ProjectAttentionProjection {
  project_id, name, research_topic
  recommended_workflow { workflow_instance_id, label, stage }
  actor, attention_state, blocker, next_action
  recent_change { summary, changed_at }
  latest_output
}
```

It reuses the Workflow action projection plus Project/Workflow identities,
`recommended_workflow_instance_id`, latest Activity, and exact Output metadata.
It does not prescribe a new endpoint, persistence, or list ordering beyond
putting attention before recency and recency before inactive Projects.

## 6. Future Real Core interface drafts

Exact Artifact inputs below are `EXISTING_REUSED`. Core-specific briefs, plans,
scopes, stage codes, evidence structures, approval proof, and expected Output
contracts are `FUTURE_CORE_CONTRACT_REQUIRED`; their user labels are derived.

### 6.1 Real Experiment — E1 boundary

- **Required inputs:** exact selected research idea. A bounded plan must be
  produced and owner-approved before execution; it is not an implicit input.
- **Optional inputs:** explicitly bound Resources and prior exact Outputs needed
  by the plan. Network is off by default and never an implicit input.
- **Expected Output:** a validated Experiment Output distinguishing plan,
  actual execution, evaluation, result, failure/non-execution, and limitations.
- **Approval checkpoints:** plan; exact local execution proposal and Resource
  use; separate network authorization if ever requested; final publication.
- **Major stages:** Idea → Requirements → Resource readiness → Plan → Owner
  approval → Local execution → Evaluation → Result.
- **Evidence boundary:** exact inputs/resources, approved plan/action identity,
  execution/log/metric identity, evaluation, result, and limitations.
- **First-slice non-goals:** scheduler, Cloud executor, hosted execution, default
  network, or final command/sandbox/runtime/budget/cancellation design in S1.

### 6.2 Real Writing — W1 boundary

- **Required inputs:** writing brief, exact selected idea, exact literature and
  evidence Outputs.
- **Optional inputs:** exact Experiment Output. Review and prior manuscript are
  W2 inputs, not required by W1.
- **Expected Output:** an evidence-bound initial manuscript with claims and
  citations traceable to the evidence map and unsupported claims visible.
- **Approval checkpoints:** outline; disposition of unsupported claims; owner
  review and final publication.
- **Major stages:** Writing brief → Evidence map → Outline → Owner approval →
  Initial draft → Claim/citation check → Owner review.
- **Evidence boundary:** every scientific claim maps to exact evidence or an
  explicit unsupported/unavailable marker and limitation.
- **First-slice non-goals:** advanced revision intelligence, causal Review
  handling, or W2 automation.

### 6.3 Real Review — R1 boundary

- **Required inputs:** exact manuscript, explicit Review scope, and exact bound
  evidence needed for that scope.
- **Optional inputs:** additional exact supporting Outputs selected by owner.
- **Expected Output:** structured issues and requested revisions anchored to
  manuscript locations and supporting or missing evidence.
- **Approval checkpoints:** Review scope; owner review and final publication.
- **Major stages:** Review scope → Claim/evidence audit → Method/result review →
  Structured issues → Owner review.
- **Evidence boundary:** each issue identifies manuscript claim/location,
  evidence identity or absence, reasoning, and limitation.
- **First-slice non-goals:** acceptance prediction, publication probability,
  numeric scientific score, unsupported confidence, or peer-review-validity
  claims. `ACCEPT_CURRENT_DRAFT` in v1 is not publication acceptance.

## 7. UX-A1 P0 traceability

| UX-A1 P0 | S1 contract decision |
|---|---|
| Projects cannot identify which Project needs attention | Server-derived `ProjectAttentionProjection` with current Workflow, actor, blocker, action, recency, and latest Output |
| No focused Workflow Detail IA exists | One `WorkflowActionProjection` supplies the header/action contract for the focused detail; inputs, Output, Activity, Resources, and technical details remain scoped beneath it |
| System-state dimensions overshadow user state | Stage, actor, attention, blocker, and next action are primary; maturity/readiness/install/Capsule/Manifest/IDs remain secondary technical details |
| Project Overview does not lead with the current research decision | Project recommendation reuses the same action projection and exact current Workflow rather than a parallel summary model |

## 8. Compatibility, safety, and future verification

- API, persistence, migrations, OpenAPI, Registry, Capsules, Artifact schemas,
  frontend, and tests are unchanged by S1.
- Existing v1 readers/writers and Progress states remain authoritative. There is
  no fallback that infers latest inputs, owner approval, evidence, or local
  readiness.
- UI-P0 must test a derivation matrix including completed, blocked,
  owner-action-required, failed, and acknowledged-stale states; one and only one
  primary action; exact latest Output identity; and technical-detail demotion.
- A future Projects enhancement must prove bounded query behavior and identical
  recommendation semantics between list, Overview, and Workflow Detail.
- E1/W1/R1 must add positive, negative, compatibility, provenance, approval,
  interruption/recovery, and relevant real-journey evidence for their concrete
  contracts. S1 itself claims documentation evidence only.

## 9. Decisions and deferrals

Owner review is required to ratify this packet. No additional semantic choice
blocks UI-P0 once the projection and Projects decision are accepted.

E1 must still decide its concrete Output version/companion, approval evidence
carrier, local execution/sandbox/command/runtime/budget/cancellation/log model,
and missing Resource readiness layers. W1 and R1 must later decide their own
version/companion and evidence locators. These are intentionally
`FUTURE_CORE_CONTRACT_REQUIRED`, not silent S1 decisions.

Writing #2 UX closure remains `DEFERRED_NON_BLOCKING` for S1, UI-P0, E1, and W1;
it continues to gate final Real Writing/Review revision contracts. Visual
identity, broad frontend redesign, Harness, B0, UX-A1, Experiment 0.4, Cloud
execution, and deployment remain outside scope.

## 10. Authorization and next phase

```text
PLAN_ALIGNMENT = PASS
S1_CONTRACT_STATUS = READY_FOR_OWNER_REVIEW
NEW_PERSISTED_FIELD = NONE
IMPLEMENTATION_AUTHORIZATION = NOT_AUTHORIZED
SAFE_NEXT_PHASE_AFTER_OWNER_ACCEPTANCE = UI-P0
```

Approval of this packet freezes the shared logical boundaries. It does not
authorize UI-P0, E1, W1, R1, or W2 implementation by itself.
