# Engineering change packet — Post-D1 R3 Generic Experiment

> Completing this packet does not authorize implementation. The Owner's
> Post-D1 Consolidated Repair Program separately authorizes the bounded R3 work.

## 1. Objective

Make the existing Generic Experiment lifecycle a normal, provenance-safe Agent
Harness path when no exact reviewed ExperimentCapability supports the approved
scientific contract. Preserve the existing bounded local runner, exact Owner
approvals, experiment-record/v5 authority, and Cloud/Local boundary.

## 2. Owner intent

ReAgent freezes and preserves the scientific contract. Codex or another qualified
Harness plans, implements, validates, and executes locally. Reviewed Capabilities
are qualified accelerators, not a scientific-method allow-list. Implementation
freedom never becomes scientific authority.

## 3. Recovered source of truth

- Experiment 0.7 / Capsule 0.10 is the current Full Research pin and produces
  `experiment-record/v5`.
- Its public runtime materializes one exact selected Research Idea, asks Codex only
  for `memory/methodology-proposal.json`, hardcodes the reviewed sklearn reference
  Capability, and stops at methodology/capability assessment. It cannot prepare,
  execute, evaluate, or finalize the public v5 Artifact.
- `GenericExperimentCoordinator` already defines exact methodology, design
  approval, package validation, runtime compatibility, run approval/consumption,
  execution evidence, evaluation, result review, and v4 lifecycle finalization.
  It currently admits only an `ExperimentCapability` binding.
- `experiment-record/v5` already wraps that exact lifecycle record with bounded,
  checksummed scientific evidence and is accepted by forward Writing/Review.
- The controlled-local approval API already authorizes one exact plan without
  dispatching Cloud execution.
- The existing bounded runner owns process isolation/no-egress execution. It is a
  single foreground-process boundary and must not be replaced by a second engine.
- Mutable implementation/preflight/result files have no supported Workspace-owned
  namespace outside Capsule validation. The current runtime writes only Capsule
  memory and does not discover compatible local environments.
- The Experiment frontend is a custom detail surface. It may derive an objective
  from upstream presentation/progress even when the required exact binding is not
  accepted, and therefore must defer to generic input setup/readiness first.

## 4. Root findings

- `D1-EXPERIMENT-ENTRY-01`
- `D1-EXPERIMENT-CAPABILITY-01`
- `D1-EXPERIMENT-INGEST-01`
- `D1-EXPERIMENT-OPERATOR-01`
- `D1-EXPERIMENT-ENV-01`
- `D1-EXPERIMENT-DURABILITY-01`
- remaining Experiment evidence for `D1-CHECKPOINT-PRESENTATION-01` and
  `D1-APPROVAL-BRIDGE-01`

## 5. Architecture decision for implementation

Use one forward-additive Experiment publication. Historical 0.7/0.10 bytes and
current v5 schema remain immutable.

The forward runtime supports two implementation-path classifications:

1. `REVIEWED_EXPERIMENT_CAPABILITY` — existing exact fast path.
2. `GENERIC_AGENT_HARNESS` — system-owned fallback when no reviewed Capability
   exactly supports the approved methodology.

The generic path may structurally use the existing exact Capability lifecycle
carrier so v5 lineage remains compatible, but its exact descriptor and Owner-facing
provenance must identify `GENERIC_AGENT_HARNESS`, never reviewed Capability or User
Skill authority. It uses no user-managed Skill as evaluator or qualification.

Generic Harness artifacts live under the Workspace-owned path:

`.reagent/experiments/<workflow-instance-id>/`

with bounded subtrees for contracts, implementation candidates, validated package,
environment receipts, execution state, outputs, evaluation, and pending sync. The
Capsule holds only immutable instructions and bounded Workflow checkpoint pointers;
its package comparison does not traverse the managed execution tree.

## 6. Lifecycle contract

`exact Research Idea`
→ `methodology/scientific contract`
→ natural exact design approval
→ reviewed Capability if exactly supported, otherwise Generic Harness
→ Harness implementation/package
→ contract/package validation
→ environment discovery
→ exact run-plan approval
→ existing bounded local runner
→ durable execution manifest/checkpoints
→ evaluation/evidence validation
→ natural exact result review
→ exactly one authoritative `experiment-record/v5`
→ normal Artifact/Progress/presentation reporting.

Every durable local write precedes bounded Cloud sync. A replay may upload exact
pending state but must not rerun implementation or science.

## 7. Generic implementation contract

The Harness must produce bounded exact documents for:

- implementation specification bound to methodology and objective;
- package manifest, launch target, dependencies, inputs, configuration, expected
  outputs, and runtime requirement;
- preflight validation receipt;
- execution manifest with stable unit IDs and expected output identities;
- evaluated result payload and bounded evidence blocks;
- limitations and claim boundaries.

ReAgent independently recomputes package/file/output checksums, validates exact
lineage and safe shape, and records approvals. Harness prose or chat is not
authority. Generic evaluation may report `VALID`, `INVALID`, or `INDETERMINATE`;
successful execution alone never implies valid scientific evidence.

## 8. Execution resume

The generated package owns deterministic execution-unit semantics. The existing
bounded runner launches the package's one approved entrypoint. That entrypoint
must atomically checkpoint stable unit IDs and checksums in the managed execution
namespace and verify completed units before reuse. ReAgent does not add another
execution engine or blindly trust a unit merely because a file exists.

## 9. Environment UX

Discover only explicit, existing local candidates (current interpreter and bounded
configured candidates). Recompute runtime/dependency identities; never scan or
execute arbitrary PATH entries. If none is compatible, report required runtime,
version, capabilities, and packages plus practical Owner-controlled preparation
options. Never install, upgrade, download, create an environment, or select a
different scientific method silently.

## 10. Artifact/API/persistence impact

- Scientific output remains `experiment-record/v5`; no v6 is introduced unless
  implementation proves v5 cannot truthfully encode the exact generic path. That
  condition is `HISTORICAL_CONTRACT_CONFLICT` and stops R3 before publication.
- Presentation remains optional Artifact-bound UI metadata.
- Existing controlled-local run approval endpoints are reused.
- One schema-free forward migration is expected for the new immutable Definition,
  Capsule, exact requirement, and new-project preset pin. Any mutable Cloud schema
  need requires a packet amendment.
- Owner database remains untouched during R3 qualification.

## 11. Security and trust

- No credentials, arbitrary absolute paths, complete source/package/output bytes,
  or transcripts are uploaded to Cloud.
- Generated code executes only after exact package validation and one-use Owner run
  approval through the existing bounded runner.
- The generic path does not claim hostile-code containment. Network remains
  disabled unless a future separately reviewed contract authorizes otherwise.
- User Skills may guide the Harness but never become ExperimentCapability,
  evaluator, package-preparation authority, or scientific authority.

## 12. Compatibility/versioning

Expected forward identities, subject to exact checksum generation:

- Experiment Definition `0.8.0`
- Capsule `0.11.0`
- output `experiment-record/v5`

Experiment 0.7/0.10 and earlier publications remain byte-identical and installable.
Fresh Full Research advances only after source/database equivalence, public
Workspace qualification, and downstream v5 compatibility pass. Existing Projects
remain unchanged.

## 13. Bounded subphases

### R3A — generic Harness contracts and managed Local state

Add new source modules only; do not modify modules whose bytes define historical
0.7/0.10 checksums. Qualify exact generic-path classification, package/evidence
validation, managed namespace ownership, environment discovery, and execution-unit
resume primitives. No production preset or migration yet.

### R3B — forward publication and Local lifecycle

Publish 0.8/0.11, integrate the new runtime with the existing coordinator/runner,
natural methodology/run/result decisions, exact v5 finalization, Progress and
presentation reporting. Add at most one schema-free migration.

### R3C — browser entry and Owner checkpoints

Make exact Research Idea input selection/materialization precede Experiment Run.
Render methodology, environment, run plan, execution progress, result evidence,
and natural actions from bounded Cloud projection. Do not add browser Workspace
access.

### R3D — controlled end-to-end qualification

Use a deterministic small sklearn-equivalent fixture and fake Harness/provider.
Prove no matching reviewed Capability, generated implementation, no silent install,
interruption/resume, one v5, downstream exact Writing binding, and historical
regressions. No real research/provider call.

Each subphase stays below 20 production files / 4,000 net production lines and has
its own clean commit. Scope expansion stops before writing.

## 14. Test matrix

- exact Research Idea binding required before custom Experiment state;
- unresolved methodology cannot prepare;
- natural approval is bound to exact methodology/plan/result and survives resume;
- reviewed Capability match remains a valid fast path;
- no match selects truthful Generic Harness path, not unsupported terminal state;
- generated package drift, methodology drift, output drift, or evidence-source
  drift fails closed;
- user Skill cannot satisfy generic implementation/evaluation authority;
- compatible existing environment is discovered; incompatible state explains but
  never installs;
- interrupted work units preserve verified completed units and resume remaining
  units;
- mutable generic state never enters Capsule validation;
- exact run approval is consumed once;
- exactly one v5 and terminal Progress publish; replay creates no duplicate;
- Writing consumes the exact v5 Artifact, never presentation;
- historical 0.7/0.10 and the four D1 repair locks remain passing.

## 15. Stop conditions

Stop with the named program status if R3 requires:

- changing historical 0.7/0.10 or v5 bytes;
- a second execution engine;
- Cloud access to arbitrary Workspace files;
- User Skill capability/scientific authority;
- implicit Artifact selection;
- real Provider calls for qualification;
- destructive Owner D1 mutation;
- more than one forward publication migration without a packet amendment;
- v5 provenance that would falsely claim a reviewed Capability.

## 16. Acceptance boundary

R3 closes only after controlled public Workspace and browser evidence proves the
complete Generic Harness path and downstream exact v5 consumption. Unit tests alone
cannot close it. R4–R6 remain deferred.
