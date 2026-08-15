# E1 Real Experiment narrow-slice contract

- Status: **PROPOSED — READY FOR OWNER REVIEW**
- Phase: E1-P0 Real Experiment narrow-slice contract
- Baseline: `main` at `689812051f97cd633b7df776ac002c47c63a4549`
- Starting working tree: **clean**; migration sole head: `20260813_0021`
- Implementation authorization: **NOT AUTHORIZED**
- Published identities changed by E1-P0: **NONE**

## 1. Alignment, authority, and user job

`PLAN_ALIGNMENT = PASS`. Engineering Harness and B0 remain done/frozen; UX-A1 is done, S1 is accepted, and UI-P0 is owner-accepted. E1-P0 is current; E1-I1 is next, followed by W1, R1, W2, and incremental frontend completion. Experiment 0.4 remains frozen and was not inspected as owner state.

This contract preserves the original architecture: Cloud coordinates and stores metadata; the Local Workspace executes; Codex remains the qualified research Harness; the browser neither executes research work nor writes Workspace bytes; Artifact handoff is exact; v1 remains immutable; Experiment network is default-off; and Hosted gains no capability.

The S1 document header still says `PROPOSED`, while the current owner instruction says `S1 = ACCEPTED`. Owner authority controls, so its content is used as accepted. The stale header is `DEFERRED_NON_BLOCKING` and is not edited.

**First-slice user job:** Given one selected research idea, ReAgent determines bounded requirements for a supported local experiment, identifies what is missing, freezes and obtains approval for one exact plan, runs one bounded local attempt, evaluates declared metrics, and returns an evidence-backed result for owner review.

## 2. Existing reuse and change boundary

| Semantic | Decision |
|---|---|
| Selected Idea and exact upstream inputs | `EXISTING_REUSED`: exact Artifact ID/type/schema/checksum and binding |
| Resource identity | `EXISTING_REUSED`: Resource Reference, exact revision/content checksum, exact Workflow binding |
| Local Resource bytes | `EXISTING_REUSED`: Workspace Resource Index and manifest verification; E1 adds a safe owner-staging path |
| Workflow terminal state | `EXISTING_REUSED`: Progress `IN_PROGRESS`, `BLOCKED`, `FAILED`, `CANCELLED`, `COMPLETED` |
| Continuation and action copy | `EXISTING_REUSED`: Progress current state, next action, reason, instructions, and immutable reports |
| Output identity/provenance | `EXISTING_REUSED`: Artifact Reference and producer Workflow Instance/Progress receipt/round |
| E1 stage/action presentation | `DERIVED`: S1 `WorkflowActionProjection`; no new persisted lifecycle |
| Exact plan, approval, attempt, evaluation, and v2 Output | `FUTURE_CORE_CONTRACT_REQUIRED` |

The legacy Hosted approval/runtime path is not reused. No E1-P0 API, persistence, Registry, Capsule, migration, frontend, test, or production change is authorized. Experiment Definition `0.3.0`, Capsules through `0.5.0`, `experiment-record/v1`, Progress v0.2, Resource v0.1, and historical data remain unchanged.

## 3. E1-I1 supported mode and requirements

E1-I1 supports one mode: `OWNER_STAGED_LOCAL_PACKAGE_V1`.

- Required inputs: one exact `selected-research-idea/v1` Artifact and one active, exact-bound `SOURCE_REPOSITORY` Resource using the existing `GITHUB` identity contract.
- The owner gives already-local package bytes to a public Workspace staging command. ReAgent does not clone, download, install, or choose a revision. Staging admits only regular non-linked files, verifies the full manifest against Cloud's expected checksum, and atomically updates the existing Resource Index.
- The package contains one relative Python entrypoint, bounded input files, and an environment/lock description. Embedded data/model/checkpoint items receive paths and checksums in the plan.
- Runtime and dependencies already exist locally; E1 neither creates nor mutates an environment.
- Any Idea needing another provider, multiple packages, remote access, installation, distributed work, or an unavailable runtime is `UNSUPPORTED_FOR_E1` and blocked rather than approximated.

The Agent derives one compact `ExperimentRequirements` record:

```text
question; hypothesis?
needs[] {kind: SOURCE_CODE|DATASET|EVENTS|MODEL|CHECKPOINT|BASELINE|RUNTIME,
         required, research_role, acceptance_criterion}
design {factors/configuration, seeds, repetitions}
evaluation[] {metric, definition, direction?, acceptance_rule?}
safety {limits, stopping_conditions}
support {SUPPORTED_FOR_E1|UNSUPPORTED_FOR_E1, reasons[]}
```

This describes research needs, not provider or installation taxonomy. Optional sections may be empty; required needs must resolve before planning.

## 4. Major state contract

Stage codes are canonical only inside the future E1 local continuation contract; UI labels/actions are derived. They are not database or Progress enums.

| Stage | Purpose / actor | Entry → exit | Owner action | Produced evidence |
|---|---|---|---|---|
| `INPUT_REVIEW` | Verify exact Idea / Agent | Materialized exact Idea → question is unambiguous | Clarify only if needed | Input identity snapshot |
| `EXPERIMENT_REQUIREMENTS` | Derive bounded needs / Agent | Valid Idea → requirements and support verdict validate | Resolve bounded ambiguity | Requirements + checksum |
| `RESOURCE_READINESS` | Prove package readiness / Owner then System | Requirements → every pre-approval layer passes | Bind/stage exact package | Binding, index, readiness record |
| `EXPERIMENT_PLAN` | Freeze one attempt / Agent | Ready requirements → canonical plan checksum exists | None | Plan + checksum |
| `OWNER_APPROVAL` | Authorize exact attempt / Owner | Frozen plan → explicit approve or reject | Review and type checksum-bound decision | Approval record + checksum |
| `PREPARATION` | Revalidate immediately / System | Approval → identities, runtime, limits, network policy pass | Repair outside E1, then re-enter | Preflight record |
| `LOCAL_EXECUTION` | Run one foreground process / System | Passing preflight → terminal process fact | May cancel | Attempt record and logs |
| `EVALUATION` | Validate declared results / Agent | Terminal attempt → evaluation verdict | Clarify no scientific facts | Metric/evidence record |
| `RESULT_REVIEW` | Review truth and limitations / Owner | Evaluated attempt → finalize truthful result or decline | Finalize/reject publication | Review/finalization record |
| `COMPLETED` | Publish successful Output / None | Owner-finalized `SUCCEEDED` v2 → Progress/receipt acknowledged | None | `experiment-record/v2` reference |

Recoverable prerequisites use Progress `BLOCKED`; active/owner-waiting stays `IN_PROGRESS`; terminal attempt/evaluation failure uses `FAILED` even when its truthful v2 evidence Output is published; explicit termination uses `CANCELLED`; `COMPLETED` requires every declared success obligation. Output presence never overwrites Progress truth. Owner action is derived, never persisted.

## 5. Resource readiness contract

| Layer | Meaning and E1 gate |
|---|---|
| `RESOURCE_REFERENCE_EXISTS` | Active Project Resource and exact Workflow binding exist; not ready by itself |
| `EXACT_REVISION_KNOWN` | Existing immutable revision and expected content checksum validate; required |
| `LOCAL_BYTES_AVAILABLE` | Owner-staged canonical Workspace path exists; required |
| `CHECKSUM_VERIFIED` | Full local manifest equals the bound expected checksum at staging and preflight; required |
| `LICENSE_ACCEPTED` | Package use terms are available and owner-accepted when applicable; required before runtime use |
| `RUNTIME_USABLE` | Exact interpreter/version, lock snapshot, entrypoint, permissions, disk and limits pass without install; required |
| `OWNER_APPROVED` | The current plan binds the preceding identities and the owner approved its checksum; required last |

Cloud metadata, a GitHub locator, or a commit alone never means executable. Readiness invalidates on binding, revision, content, license, entrypoint, environment, plan, or policy drift.
The `RESOURCE_READINESS` stage exits after `RUNTIME_USABLE`; execution readiness is achieved only after `OWNER_APPROVED` and Preparation revalidation.

## 6. Exact Experiment Plan and approval evidence

The owner approves one canonical plan containing:

- research question/hypothesis and requirements checksum;
- exact source Artifact references and exact Resource binding/revision/checksum;
- package-relative entrypoint plus entrypoint checksum;
- fully expanded argument vector (no shell), working directory, configuration, seeds/repetitions, metrics and definitions;
- expected files/metrics and evaluation rules;
- network policy fixed to `DISABLED`;
- launcher-supported wall-time, output-size, process-count, CPU/memory limits, stopping conditions, and cancellation policy;
- interpreter/platform/distribution-lock identity; and
- known limitations and trust-boundary warning.

Canonical JSON bytes produce `plan_checksum`. No field may be filled or changed after approval. Timestamps and attempt ID are execution facts, not mutable plan content.

Approval is `FUTURE_CORE_CONTRACT_REQUIRED`, with identity/checksum mechanics `EXISTING_REUSED` and presentation `DERIVED`. The local command displays the complete plan/checksum and requires an interactive decision bound to it. An immutable record contains Workflow Instance, Progress round, plan checksum, exact input/resource/environment identities, decision, time, and one-attempt authorization; execution records its checksum. Conversation, Progress copy, or browser state is not approval. Material drift invalidates it; each retry needs a new approval even if the plan is unchanged.

## 7. Local execution and safety boundary

E1-I1 launches one foreground child from an argument vector inside a new Experiment Capsule attempt directory. It has no shell, daemon, scheduler, Cloud executor, distributed worker, implicit retry, package installation, or background job.

`REQUIRED_FOR_E1`:

- normalize ReAgent-managed paths under allowed Workspace roots; reject traversal, links, special files, and changed manifests;
- atomically create one attempt ID/receipt; never execute an existing attempt;
- rehash plan, approval, package, entrypoint, evidence, and environment immediately before launch; pass canonical-file configuration;
- scrub ReAgent secrets, credentials, proxy settings, and unrelated environment;
- apply a tested process-level no-egress profile; if unavailable, preflight is `BLOCKED/NETWORK_ISOLATION_UNAVAILABLE` and never degrades;
- enforce timeout/output/process/resource bounds, separately capture stdout/stderr, record start/end/exit/signal, and terminate on cancel;
- preserve partial evidence without converting it into success.

`DEFERRED`: containing malicious owner-approved code from all host files, runtime plugins, Docker/Kubernetes, remote or network-enabled execution, secrets, and general multi-process work. E1 accepts only owner-trusted code; the limitation appears at approval and in the Output. E1 is not a hostile-code sandbox.

## 8. Output strategy and provenance

**Decision: A — define `experiment-record/v2`.** Do not introduce a companion.
Version 1 has only a coarse execution status, simple plan, summary metrics, and
limitations. It cannot bind an exact approval, Resource/environment/command,
attempt/log/raw evidence, or separate process success from evaluation validity.
Adding those meanings to v1 would violate immutability. A companion would split
one scientific truth across two correlated Artifacts and force Writing to bind
both. V2 gives W1 one authoritative, compatible new Output while all v1 bytes,
validators, producers, Capsules, and readers remain unchanged. E1-P0 does not
publish the schema; E1-I1 must add it under a new Definition/Capsule version.

Logical v2 content is limited to: exact sources; requirements identity; frozen
plan identity/content; approval identity; execution facts; evaluation verdict
and metric definitions/results; evidence item/location/availability/limitation;
result status; and checksums.

`MUST_HAVE`: approved plan/checksum; Idea and package/revision/manifest identity;
every used dataset/event/model/checkpoint identity; entrypoint/command/configuration;
environment identity; seeds/repetitions used; network/limits; attempt ID and
timestamps; exit/signal/timeout/cancel fact; stdout/stderr and raw-result
references/checksums; metric definitions; summarized results; evaluation verdict;
limitations; and producer Workflow/Progress identity from Artifact Reference.

`OPTIONAL`: resource-use measurements when reliably supplied and human
observations clearly labeled as such. `DEFERRED`: full environment
images, exhaustive telemetry, log warehouse, general evidence database,
confidence scoring, and unsupported causal claims.

## 9. Result truth, failure, and retry

- `EXECUTED` is an evidence predicate: a checksum-bound approved attempt reached
  process start and has start/terminal-or-interruption evidence. A plan alone is
  never executed.
- `SUCCEEDED` requires process exit zero, every declared output present and
  checksummed, metric parsing valid, all required evaluation rules completed,
  and evaluation verdict `VALID`. Exit zero alone is insufficient.
- `FAILED` requires terminal evidence that execution or evaluation failed and no
  success claim is supportable; the failing phase and evidence remain explicit.
- `PARTIAL` requires an attempt plus preserved usable evidence, but one or more
  success conditions are missing because of timeout, interruption, cancellation,
  missing output, or invalid/incomplete evaluation.

V2 keeps process outcome, evaluation verdict, and overall result status separate.
Pre-execution failure produces no executed-result claim. Process non-zero,
timeout, evaluation failure, cancellation, and interrupted recovery all fail
closed and preserve evidence. `NO_AUTOMATIC_RETRY` is mandatory. A retry is a new
attempt with a new owner approval and immutable prior attempt; uncertain prior
state is never rerun automatically.

## 10. Writing handoff and Workflow action mapping

Without private Experiment files, W1 can read from v2 and Artifact metadata:
whether execution occurred; process and evaluation outcomes; final
`SUCCEEDED|FAILED|PARTIAL` truth; metrics/results and definitions; exact evidence
locations/checksums; provenance; and limitations. A planned-only or cancelled
pre-execution Workflow has no v2 executed Output and is distinguishable by
Progress/absence. W1 must never infer execution from a plan or v1 placeholder.

For every row, `expected_output` is `Experiment Output (experiment-record/v2)`; `latest_output` is null until a truthful v2 is finalized, then holds its exact Artifact Reference even when Progress is `FAILED`.

| Stage | Actor / attention | Blocker | Primary next action |
|---|---|---|---|
| Input review | Agent / normal | Invalid or ambiguous input if present | Inspect exact Idea; ask bounded clarification |
| Requirements | Agent / normal | Unsupported requirement if present | Derive and validate requirements |
| Resource readiness | Owner / blocked when incomplete | `RESOURCE_NOT_READY` with failing layer | Bind/stage package locally |
| Experiment plan | Agent / normal | None | Generate and checksum exact plan |
| Owner approval | Owner / owner action required | `OWNER_APPROVAL_REQUIRED` | Review and approve/reject locally |
| Preparation | System / normal or blocked | Exact drift, runtime, or network-isolation code | Revalidate or show repair instruction |
| Local execution | System / normal | Execution failure only after terminal fact | Wait or cancel local attempt |
| Evaluation | Agent / normal | Invalid/missing result if present | Evaluate declared evidence |
| Result review | Owner / owner action required | Result/limitation requiring disposition | Finalize truthful Output or decline |
| Completed | None / completed | None | None; inspect Output |

Failure overlays keep the current stage, set attention to `ATTENTION_REQUIRED`,
and use a bounded failure code. Acknowledged local-stale state uses
`LOCAL_STATE_STALE` and a local sync action; neither creates a lifecycle value.

## 11. E1-I1 implementation boundary and impact forecast

**Vertical slice:** Given one exact selected Idea and one exact GitHub-identified,
owner-staged local experiment package, ReAgent can derive/confirm bounded
requirements, prove readiness, freeze and approve one exact plan, execute one
bounded foreground local command with network denied, evaluate declared metrics,
obtain result review, and finalize one evidence-backed
`experiment-record/v2` Output.

Non-goals: general Experiment management, auto-download, package/environment
installation, multiple packages, remote/Cloud/Hosted execution, scheduler,
daemon, distributed work, network-on execution, automatic retry, hostile-code
filesystem sandbox, generic workflow language, frontend implementation, and any
change to Experiment 0.4 or v1 contracts.

Smallest likely E1-I1 areas: a new immutable Workflow Definition/Capsule version;
v2 validator/producer; E1 continuation/plan/approval/evaluation records; owner
staging and readiness checks in the Workspace boundary; bounded process runner;
Progress/action derivation; Registry seed migration; and focused tests. No new
Cloud execution service, approval subsystem, database domain model, API mutation,
or production frontend is expected. Estimated budget: **18–24 files total**
(8–12 production, 1 seed migration, 7–10 tests/fixtures, at most 1–2 docs). Stop
and re-packet if the implementation needs more than 24 files or a new persisted
approval/resource lifecycle.

## 12. Verification, compatibility, rollback, and stop conditions

Required E1-I1 evidence:

- E1 schema/contract tests for v2 truth combinations, provenance, bounds, and
  negative cases, plus unchanged v1 golden tests (`E1`);
- service integration for exact bindings, readiness layers, approval drift,
  idempotency, cancellation, partial evidence, and retry isolation (`E3`);
- disposable PostgreSQL proof for new Registry publication, Progress, Artifact
  metadata, receipts, and restart/reconciliation where applicable (`E4`);
- one supported public Workspace command lifecycle with fake Harness and a tiny
  disposable package, including path/network/timeout canaries (`E5`);
- one complete controlled real-Codex lifecycle, not startup-only, using no owner
  data (`E7`); and
- owner review of the displayed plan, approval evidence, metrics, limitations,
  and final Output (`E9`, bounded product evidence).

Browser `E6` is not execution evidence; E8 is separately required only for a
long-lived upgrade/recovery claim. Before W1, the E1 claim must achieve the
listed cumulative evidence through E7 plus bounded E9 owner observation. Tests
must prove no network request succeeds and no v1 reader/writer changes.

Compatibility is additive: old Definitions/Capsules and v1 Artifacts remain
readable and producible only under their existing rules; no historical Artifact
or Workspace is migrated. Rollback stops publication/selection of the new
Definition/Capsule while retaining already-published v2 evidence for audit.

Stop E1-I1 and return to owner review if exact local bytes cannot be verified,
network denial cannot fail closed, approval cannot bind one exact attempt,
process/evaluation truth cannot remain separate, v1 would need mutation, a new
Cloud executor/Hosted capability is required, or the file budget is exceeded.

## 13. Owner decisions and deferred questions

E1-I1 is blocked until the owner accepts this packet's four coupled decisions:

1. `experiment-record/v2` is the single Real Experiment Output; no companion.
2. The first slice accepts one exact owner-staged GitHub package and performs no
   resolver download or environment installation.
3. Approval authority is the local checksum-bound interactive record, not
   conversation, browser state, or the legacy Hosted approval runtime.
4. The owner-trusted-code boundary plus mandatory no-egress launcher is accepted;
   hostile-code host-filesystem containment is not claimed by E1.

`DEFERRED_NON_BLOCKING`: broader Resource resolvers/providers; multiple packages;
external model/checkpoint workflows; environment creation; network-enabled
execution; stronger hostile-code sandboxing; scheduler/Cloud/distributed work;
automatic retry; background jobs; generalized approval/evidence databases;
production frontend; long-lived recovery qualification; and Experiment 0.4.
