# Final D1 Owner-acceptance defect ledger

Status: **AUTHORITATIVE, DEDUPLICATED, RECORD ONLY**

Date: 2026-08-20

Scope: the completed real Owner D1 journey for Project
`project-4c73c4c95e1d4535884f671b2f4b4b6f`; no repair phase is authorized by
this ledger.

## Evidence and status rules

This ledger reconciles the Owner-observed D1 record (E9), the long-lived
Workspace recovery records (E8), the four bounded D1 repair packets, the EP-D2
and SKILL-M1 records, ADRs 0038/0039/0040/0043/0044/0047/0048, current source
inspection, and read-only queries of the Owner runtime. Workflow-specific
reproductions are retained as evidence under one root finding where appropriate.

- `OPEN`: accepted unresolved gap whose exact implementation root still needs a
  repair-phase audit.
- `CONFIRMED`: unresolved product defect/gap supported by direct Owner or current
  state/source evidence.
- `CONFIRMED_CROSS_WORKFLOW`: the same unresolved root occurred in more than one
  Workflow or product surface.
- `FOUND_AND_REPAIRED_DURING_D1`: the occurrence remains historical evidence, but
  the bounded repair and real D1 recovery passed.
- `FOUND_AND_REPAIRED_POST_D1`: the D1 occurrence remains historical evidence,
  and the assigned consolidated-repair acceptance case passed after D1.
- `OBSERVATION_NEEDS_CONFIRMATION`: concerning semantics or UX were observed, but
  a repair contract should not be inferred yet.
- `EXPECTED_BEHAVIOR`: a verified safety/product boundary, included to prevent it
  being misclassified as a defect.
- `DEFERRED_PRODUCT_DESIGN`: Owner intent is recorded, but implementation is not
  authorized and requires a later architecture/change packet.

`CONFIRMED` and `CONFIRMED_CROSS_WORKFLOW` are unresolved even though the
occurrence is proven. `OPEN` is reserved for unresolved gaps needing a narrower
root-cause audit. Thus the unresolved evidenced inventory is larger than the
literal `OPEN` status count.

## Verified final D1 state

Read-only Owner API evidence at repository baseline
`7852761b25cd34eb0444ef9b42142dfd7a63f0f3` showed:

| Workflow | Exact instance | Version | Lifecycle | Research state |
|---|---|---:|---|---|
| Literature Search #1 | `wfi-fa3ac0f41de25219a17ba55acc39c167` | 0.4.0 | ACTIVE | COMPLETED |
| Literature Search #2 | `wfi-abc191b75d944958a5f19391033fe486` | 0.4.0 | ACTIVE | COMPLETED |
| Idea Discovery | `wfi-9952d736df6945b6a1596487a801f931` | 0.2.0 | ACTIVE | COMPLETED |
| Reproduction & Experiment | `wfi-bbcc75e6f6cc4775a35eb047eaefdbe5` | 0.7.0 | ACTIVE | NOT_STARTED / NEEDS_MATERIALIZATION |
| Initial Writing | `wfi-b3a74396f2714bb68d30196c542776a0` | 0.5.0 | ACTIVE | COMPLETED |
| Review | `wfi-b34be5d4c85343c598e65577c0407781` | 0.4.0 | ACTIVE | COMPLETED |
| Writing Revision #1 | `wfi-20d46c8419fe5fa3809fb3a57a26f39b` | 0.6.0 | RETIRED | NOT_STARTED / RETIRED |
| Writing Revision #2 | `wfi-7f5a9b0453485cada13412f8cb468073` | 0.7.0 | ACTIVE | COMPLETED |

Totals are 8 Workflow records, 7 active, 1 retired, 6 completed, 2 without
terminal Progress, 8 accepted Progress reports, and 6 Cloud Artifact references.
The authoritative products are two `selected-paper-library/v1`, one
`selected-research-idea/v1`, one `manuscript-draft/v4`, one `review-report/v3`,
and one `manuscript-draft/v5`. No `experiment-record/v5` exists. The Generic
Harness experiment was genuinely implemented, executed, and scientifically
validated as operator evidence, but it was not admitted into the authoritative
Artifact chain.

## Authoritative deduplicated ledger

| ID | Area | Finding | Severity | Status | Evidence | Root cause if known | Workaround | Desired direction |
|---|---|---|---|---|---|---|---|---|
| D1-SKILL-NAV-01 | Skills / navigation | Global Skills did not escape `/skills?project=…` when already on the Skills pathname. | MAJOR_UX | FOUND_AND_REPAIRED_POST_D1 | `D1_SKILL_NAVIGATION_01`; R5 component and real controlled-browser navigation from scoped Skills to exact `/skills`. | Same-path client navigation preserved the project query state. | Historical D1 navigated through Projects; R5 global navigation now enters the unscoped library explicitly. | Preserve one stable unscoped global Skills destination. |
| D1-SKILL-EMPTY-01 | Skills / project | Project Skills empty state had no direct Add Skill or Skill Library action. | MAJOR_UX | FOUND_AND_REPAIRED_POST_D1 | `D1_OBSERVATION_SKILL_EMPTY_PROJECT_PAGE`; R5 component and E6 empty-state journey. | Empty-state action model covered attachable records only. | Historical D1 used global navigation; R5 exposes one compact Add-a-skill escape. | Preserve a direct unscoped library action without adding tutorial copy. |
| D1-SKILL-DETAIL-01 | Skills | No discoverable per-Skill detail/provenance/usage view. | MAJOR_UX | FOUND_AND_REPAIRED_POST_D1 | `D1_SKILL_DETAIL_01`; R5 API/component/E6 detail and Project-usage evidence. | M1 shipped list/create/attach but no secondary detail surface. | Historical D1 inspected source externally; R5 adds a bounded secondary view. | Keep purpose/usage/source primary and exact provenance under Technical details. |
| D1-SKILL-LIFECYCLE-01 | Skills | User-managed Skills could not be safely removed from the library. | MAJOR_PRODUCT_GAP | FOUND_AND_REPAIRED_POST_D1 | `D1_SKILL_LIFECYCLE_01`; R5 service/API/PostgreSQL/E6 attached-conflict, detach, and unattached-delete cases. | Safe backend semantics existed but had no discoverable lifecycle UI. | Historical records accumulated; R5 rejects attached deletion and deletes only unattached exact records. | Preserve explicit detach-first shared-record safety. |
| D1-SKILL-SUBTRACTIVE-01 | Skills / presentation | Skill actions/status relationships needed bounded visual review against the three-question M1 goal. | MINOR_UX | EXPECTED_BEHAVIOR | R5 bounded screenshots show compact empty/list/detail/Project states; provenance and deletion remain secondary. | No distinct product defect was reproduced after the R5 lifecycle/navigation repair. | None required. | Preserve the current REMOVE/COLLAPSE/SHORTEN baseline in later shared-style changes. |
| D1-PROJECT-NAV-01 | Projects / navigation | Portfolio entry could send the Owner to Project Help instead of Overview. | MAJOR_UX | FOUND_AND_REPAIRED_POST_D1 | `D1_PROJECT_NAVIGATION_01`; R5 component/E6 verifies Project identity opens Overview and Help is explicit secondary navigation. | Primary row action had displaced stable Project-entry semantics. | Historical D1 clicked the title; R5 makes the Project identity the stable Overview destination. | Preserve task CTA and Project identity as separate targets. |
| D1-LOCAL-GUIDANCE-IA-01 | Navigation / information architecture | Project Help and global Local guide overlapped without a clear authority boundary. | MAJOR_UX | FOUND_AND_REPAIRED_POST_D1 | `D1_LOCAL_GUIDANCE_IA_01`; R5 component/build/browser review of contextual Help and generic Local reference. | Two guidance surfaces evolved independently. | Historical D1 inferred the distinction; R5 makes it explicit and removes duplicated onboarding. | Project Help stays contextual; Local Guide stays generic reference. |
| D1-PROJECT-LIFECYCLE-01 | Projects | Cloud Projects could not be deleted. | MAJOR_PRODUCT_GAP | FOUND_AND_REPAIRED_POST_D1 | `D1-PROJECT-LIFECYCLE-01`; R5 transactional PostgreSQL graph deletion, rollback, browser confirmation, and orphan-Workspace E5. | Project deletion service/API/UX and centralized persistence ownership operation were absent. | Historical obsolete Projects remained; R5 adds explicit Cloud-only deletion. | Preserve transactional Cloud deletion, global Skill/publication survival, and zero Local Workspace access. |
| D1-LOCAL-ORCHESTRATION-01 | Local workflow / IA | Normal Owner flow exposed sync, refresh, materialize, run, resume, paths, checksums, and Capsule-relative internals as a protocol. | MAJOR_UX | FOUND_AND_REPAIRED_POST_D1 | Literature→Idea, Idea→Experiment, Writing→Review, Review→Revision; R2 controlled continuation and exact-materialization tests. | Fine-grained operator commands became primary UX; orchestration was not composed. | Historical D1 followed the exact operator sequence; public `run` now composes the safe path. | Preserve one high-level continue/run operation; advanced commands remain troubleshooting tools. |
| D1-INPUT-FRESH-01 | Exact input | Fresh explicit selection and first materialization can preserve exact Artifact authority. | — | EXPECTED_BEHAVIOR | Successful fresh Idea/Writing/Review materializations; exact IDs/checksums survived. | Existing exact binding/materialization design works in the no-replacement case. | Normal supported path. | Preserve exact selection, no auto-latest, and fail-closed ownership. |
| D1-INPUT-RECONCILE-01 | Exact input / materialization | Changing an exact binding could not safely replace a proven prior ReAgent-managed materialization. | HIGH_CORE_CONTRACT | FOUND_AND_REPAIRED_POST_D1 | `D1-INPUT-02`; R1A managed A→B, unmanaged-target, and interrupted-publication tests. | Materializer treated all differing target bytes as ambiguous and ignored the prior exact ownership receipt. | Historical D1 used an operator move; R1A now stages, verifies, and atomically replaces only proven managed bytes. | Preserve ADR 0049 ownership proof and fail closed for user-owned/ambiguous bytes. |
| D1-INPUT-RUNNABLE-01 | Readiness | Stale or incomplete materialization could still be reported as Locally Materialized / Next: Run. | CRITICAL_CORE_CONTRACT | FOUND_AND_REPAIRED_POST_D1 | `D1-INPUT-03` in Idea and Initial Writing; R1A stale/concurrent-plan negative tests. | Readiness trusted self-consistent old receipts without a durable current-plan comparison. | Historical D1 required operator identity checks; R1A now requires current-plan/receipt/byte equality. | Preserve the ADR 0049 runnable invariant and current-plan fail-closed behavior. |
| D1-INPUT-RECEIPT-01 | Materialization receipts | Changing one sibling binding invalidated unchanged input receipts through aggregate plan checksum coupling. | HIGH_CORE_CONTRACT | FOUND_AND_REPAIRED_POST_D1 | `D1-INPUT-04`; R1A changed-sibling/unchanged-sibling exact carry-forward test. | Per-input receipt equality coupled unchanged identity/bytes to an old aggregate plan checksum. | Historical D1 reconciled manually; R1A reissues only a fully verified unchanged receipt under the new plan. | Preserve exact per-input identity plus atomic whole-plan completion. |
| D1-INPUT-REFRESH-01 | Artifact index | Newly available upstream Artifacts were not automatically reconciled before downstream materialization. | MAJOR_PRODUCT_DEFECT | FOUND_AND_REPAIRED_POST_D1 | `D1-INPUT-01` at Writing→Review and Review→Revision; R1A public materialize-without-refresh test. | Local Artifact Index refresh was a separate manual lifecycle step. | Historical D1 ran `artifact refresh`; R1A normal materialization now performs exact reconciliation. | Keep low-level refresh for diagnostics/backfill, not normal preparation. |
| D1-FRONTEND-KEY-01 | Exact-selection UI | Multiple Artifact candidates sharing one role use duplicate React key `paper_library`. | HIGH_UI_IDENTITY_RISK | FOUND_AND_REPAIRED_POST_D1 | `D1-FRONTEND-01`; React duplicate-key warning with two Literature Artifacts; R1B1 exact-candidate identity regression. | Candidate identity was keyed by role/requirement instead of unique Artifact/candidate identity. | Historical D1 required exact binding verification; R1B1 keys each candidate by requirement plus exact Artifact ID. | Preserve exact candidate identity and explicit selection. |
| D1-WRITING-BINDING-01 | Exact-selection UI / Cloud binding | Writing appeared Ready with Literature #2 selected while authoritative binding/materialization still referenced Literature #1. | HIGH_PRODUCT_DEFECT | FOUND_AND_REPAIRED_POST_D1 | Writing diagnosis/recovery: UI showed 1-paper result while Cloud binding was 0-paper result; R1B1 accepted-binding regression. | Browser selection state could outlive or visually outrun the authoritative dependency mutation. | Historical D1 read and replaced the exact dependency through the supported API; R1B1 now clears local choice only after mutation and renders the accepted server binding. | Preserve server-authoritative confirmation and query invalidation before showing Selected. |
| D1-REVIEW-INPUT-LIFECYCLE-01 | Review inputs | Required-input confirmation collapses early, hides unresolved optional evidence, and optional evidence cannot be added after setup/materialization. | HIGH_PRODUCT_DEFECT | FOUND_AND_REPAIRED_POST_D1 | `D1-REVIEW-UX-01/02`, `D1-REVIEW-INPUT-01/02`; Idea was missed; R1B1 durable omission and materialization-gate regressions. | Readiness transitioned on required inputs only and had no durable exact decision for intentionally omitted optional evidence. | Historical D1 proceeded with a limited scope; R1B1 keeps setup open until an exact binding-bound omission decision is current. | Preserve ADR 0050 explicit optional-evidence decision and post-materialization immutability. |
| D1-UPSTREAM-ZERO-PAPER-01 | Literature→Idea contract | Cloud accepted a valid 0-paper INSUFFICIENT library as compatible while Idea runtime required at least one selected paper. | BLOCKER_CONTRACT_DEFECT | FOUND_AND_REPAIRED_POST_D1 | `D1-UPSTREAM-01`; R1B2 zero/one-paper shared-evaluator cases, exact SQL qualification round-trip, and forward publication cycle. | Historical Cloud compatibility checked type/schema but could not express the stricter consumer content precondition. | Owner ran a second Literature round during D1; R1B2 now preserves the zero-paper producer while excluding it from forward Idea candidates/binding/materialization. | Preserve forward Idea 0.3 / Capsule 0.4 and ADR 0051; content qualification remains exact bounded metadata, not evidence authority. |
| D1-CHECKPOINT-PRESENTATION-01 | Owner checkpoints | Methodology, Writing outline, Review scope, and Revision plan are often written internally without a human-readable approve/revise checkpoint. | MAJOR_UX | FOUND_AND_REPAIRED_POST_D1 | `D1-EXPERIMENT-UX-01`, `D1-WRITING-UX-03`, `D1-REVIEW-UX-03`, `D1-REVISION-UX-01`; R2 exact downstream checkpoint tests and R3D methodology/run/result browser journey. | Harness contract emphasized durable files without a reliable structured Owner-facing rendering before exit. | Historical D1 used operator-rendered summaries; the normal forward paths now present bounded evidence before natural decisions. | Preserve concise evidence, tradeoffs, and limitations before Approve/Revise/Explain/Abort. |
| D1-APPROVAL-BRIDGE-01 | Human decisions | Natural interactive approval does not automatically become runner-owned exact durable approval; Review may demand a SHA-256 echo. | HIGH_HUMAN_CHECKPOINT_CONTRACT | FOUND_AND_REPAIRED_POST_D1 | `D1-EXPERIMENT-GATE-02`, `D1-WRITING-GATE-01`, `D1-REVIEW-GATE-01`, `D1-REVISION-GATE-01`; R2 natural downstream decisions and R3D methodology, one-use run, and result-review decisions persisted exactly. | Harness conversation and runner approval recorder were separate authorities with no supported decision bridge. | Historical D1 required operator invocation; supported forward flows now bind natural decisions internally to exact checkpoint/input identities. | Preserve exact durable decisions without exposing SHA-256 as the Owner interaction. |
| D1-HARNESS-TERMINATION-01 | Harness lifecycle | Harness sessions did not reliably terminate after reporting completion; Owner interruption exposed nested Python `KeyboardInterrupt` traces and could trigger later invalid phases. | HIGH_LIFECYCLE_DEFECT | FOUND_AND_REPAIRED_POST_D1 | Idea, Writing, Review, and Revision D1 evidence; R2 managed-phase completion/cancellation tests. | Launcher/session-end handshake did not make phase completion terminal for the process tree. | Historical D1 used bounded operator recovery; the managed launcher now regains control on phase completion. | Preserve structured normal exit and bounded cancellation without raw stack traces. |
| D1-PROGRESS-SYNC-01 | Progress / finalization | Successful local scientific completion could end with ambiguous/failed Cloud finalization or require manual upload/recovery. | HIGH_STATE_MACHINE_DEFECT | FOUND_AND_REPAIRED_POST_D1 | `D1-PROGRESS-01`; D1 upload-only recoveries; R2 pending terminal replay and exactly-once tests. | Durable phase completion, report sequencing, launcher termination, and backlog acknowledgement were separate lifecycles. | Historical D1 preserved local results and used recovery; normal run now retries the same exact pending report. | Preserve local commit → pending sync → idempotent Cloud upload/receipt without rerunning science. |
| D1-RESUME-DECISION-01 | Resume / scientific decisions | Resume could preserve files while losing a prior Owner screening disposition. | HIGH_SCIENTIFIC_STATE_DEFECT | FOUND_AND_REPAIRED_POST_D1 | `D1-RESUME-02`; R2 forward Literature/Idea exact decision snapshot and candidate-drift tests. | Accepted upstream packages lacked a declared exact durable pre-finalization Owner-decision state. | Historical D1 required Owner recheck; new Projects use forward durable-decision publications. | Preserve candidate-checksummed decisions and restore them before Agent inference. |
| D1-EXPERIMENT-DURABILITY-01 | Experiment / durability | Long-running Generic Harness work lacks execution-unit resume and an explicit local-commit-before-Cloud-sync lifecycle. | ARCHITECTURE | FOUND_AND_REPAIRED_POST_D1 | Owner Experiment Product Design Intent §§10–15; R3D interrupted after one exact work unit, preserved its checksum/attempt count, resumed the remaining unit, and synchronized one terminal report. | Historical lifecycle was session/round oriented rather than execution-manifest/unit oriented. | Historical D1 preserved operator evidence manually; forward 0.8 uses managed execution manifests and pending terminal replay. | Preserve stable unit IDs/checksums, verified partial reuse, local-first state, and idempotent bounded Cloud sync. |
| D1-EXPERIMENT-ENTRY-01 | Experiment UX / exact input | Experiment displays the Idea as objective metadata and offers Run although no exact `research_idea` binding is accepted/materialized; custom page hides input selection. | BLOCKER_OWNER_FLOW | FOUND_AND_REPAIRED_POST_D1 | `D1-EXPERIMENT-ENTRY-01/02`; R3C component tests and R3D real browser require the accepted exact Idea binding before preparation/run. | Presentation/objective projection had been independent of exact dependency binding and the custom detail bypassed generic SELECT_INPUT UI. | Historical D1 used the generic binding API; forward 0.8 exposes shared exact selection and accepted server state. | Preserve exact input selection/preparation before Run; never infer binding from presentation. |
| D1-EXPERIMENT-CAPABILITY-01 | Experiment architecture | Reviewed ExperimentCapability acts as a mandatory scientific-method implementation whitelist. | ARCHITECTURE_PRODUCT_GAP | FOUND_AND_REPAIRED_POST_D1 | `D1-EXPERIMENT-CAP-01`, `D1-EXPERIMENT-ARCH-01`; R3 adapter/contract tests and R3D selected `GENERIC_AGENT_HARNESS` when no reviewed Capability matched, without `REVIEWED` provenance. | Historical Generic Experiment required a pre-published Capability to encode methodology. | Historical D1 used an operator-only implementation; forward 0.8 provides a supported system Generic Harness path. | Preserve reviewed capabilities as qualified fast paths and contract-validated Generic Harness as the normal fallback. |
| D1-EXPERIMENT-INGEST-01 | Experiment evidence | Validated Generic Harness evidence has no provenance-safe supported admission path to `experiment-record/v5`. | BLOCKER_PRODUCT_GAP | FOUND_AND_REPAIRED_POST_D1 | `D1-EXPERIMENT-INGEST-01`; R3D published exactly one exact generic-provenance v5, one COMPLETED Progress report, bounded v0.2 presentation, and Writing materialized that exact v5. | Historical publisher/finalizer accepted only managed reviewed lifecycle/package evidence. | Historical operator evidence remained outside authority; forward 0.8 now validates scientific contract, package, run approval, evaluation, and Owner review before admission. | Preserve truthful generic provenance and exactly-once authoritative admission. |
| D1-EXPERIMENT-OPERATOR-01 | Experiment workspace boundary | Operator implementation/preflight/result state inside managed Capsule memory contaminates package validation. | HIGH_ARCHITECTURE_DEFECT | FOUND_AND_REPAIRED_POST_D1 | `D1-EXPERIMENT-OPERATOR-01`; R3 workspace tests and R3D retain implementation, execution state, outputs, and receipts under `.reagent/experiments/<workflow-instance-id>/` while Capsule validation remains exact. | Historical path lacked a supported scratch/execution/evidence namespace outside Capsule comparison. | Historical D1 moved proven operator files intact; forward 0.8 uses the explicit ReAgent-managed namespace. | Preserve the managed namespace outside immutable Capsule package comparison. |
| D1-EXPERIMENT-ENV-01 | Experiment environment | Owner-facing runtime preparation does not discover compatible environments or explain practical setup without taking silent action. | MAJOR_PRODUCT_GAP | FOUND_AND_REPAIRED_POST_D1 | `D1-EXPERIMENT-ENV-01`; R3 environment tests cover compatible/incompatible candidates and no-install behavior; R3D reports the exact existing Python runtime in the run summary. | Environment discovery/provisioning was absent from the normal generic path. | Historical D1 required operator inspection; forward 0.8 discovers declared existing candidates and fails with bounded preparation guidance when none matches. | Preserve discover-and-explain behavior; never silently install, upgrade, or download. |
| D1-SKILL-AUTHORITY-01 | Trust boundary | Literature wording said a pinned user Skill’s evidence rules “determined” scientific disposition. | SEMANTIC_TRUST_OBSERVATION | FOUND_AND_REPAIRED_POST_D1 | `D1-SKILL-07` remains preserved; R4 forward Literature 0.6/0.8 and consolidation 0.1 explicitly state that Skills are guidance, while provider records, Owner decisions, and validators remain authority. | Historical wording conflated Harness guidance with scientific admissibility, although no actual Capability escalation was proven. | None needed for forward Workflows; historical publications remain immutable. | Preserve user Skill ≠ reviewed Capability ≠ scientific authority in all future publications. |
| D1-WRITING-LIFECYCLE-01 | Initial Writing / recovery | Completed Real Writing was evaluated with Scaffold provenance and became `LOCAL_PROGRESS_INVALID` after successful finalization. | CORE_LIFECYCLE_DEFECT | FOUND_AND_REPAIRED_DURING_D1 | Change packet and E8 recovery; v4/Owner review/Progress unchanged, exactly one Cloud upload. | Shared readiness dispatch used `_scaffold_provenance_is_exact` for Writing 0.5. | Before repair, upload-only operator recovery was blocked. | Retain exact Real Writing provenance dispatch and no-Harness idempotent backlog recovery. |
| D1-REVIEW-CONTRACT-01 | Review contract | Optional Review evidence conflicted with publisher equality to complete manuscript provenance. | CORE_CONTRACT_DEFECT | FOUND_AND_REPAIRED_DURING_D1 | Change packet; limited-scope Review published v3 exactly once with Idea unbound. | Contextual validator required Review bindings to equal manuscript source set. | None needed after repair. | Require exact identity for evidence actually bound/used; omitted provenance remains unverified, not Review evidence. |
| D1-REVISION-CONTRACT-01 | Revision contract | Revision required causal Review support to equal full inherited manuscript context. | CORE_CONTRACT_DEFECT | FOUND_AND_REPAIRED_DURING_D1 | ADR 0048/change packet; old 0.6 retired, forward 0.7/0.9 recovered. | Immutable Capsule 0.8 encoded equality instead of subset semantics. | Supported retire/create/sync/materialize path. | `CAUSAL_REVIEW_SUPPORT ⊆ REVISION_CONTEXT` with exact identity on overlap; additive publication `20260819_0034`. |
| D1-REVISION-LIFECYCLE-01 | Revision / recovery | Existing exact Revision Plan approval was treated as a terminal error rather than a resume checkpoint. | CORE_LIFECYCLE_DEFECT | FOUND_AND_REPAIRED_DURING_D1 | 2026-08-20 packet; one v5, one COMPLETED report/receipt, idempotent replay, no Harness. | Public runner always re-entered plan approval in the single-pass Capsule runner. | None needed after repair. | Keep exact checkpoint-aware root recovery; published 0.7/0.9 bytes unchanged. |
| D1-REVIEW-SEMANTICS-01 | Review semantics | Review can conflate evidence unavailable in Review scope with evidence unavailable during manuscript authoring. | MAJOR_SCIENTIFIC_SEMANTICS | FOUND_AND_REPAIRED_DURING_D1 | `D1-REVIEW-SEMANTICS-01` remains preserved; the accepted optional-evidence repair keeps manuscript Idea provenance, projects it as unavailable/not independently verifiable when unbound, and rejects Review issue use of that omitted source. R4 added an explicit regression. | The pre-repair validator/publisher conflated complete authoring provenance with Review-bound evidence. | None needed after the accepted Review repair. | Preserve separate authoring provenance, Review-available evidence, and Review-verified support. |
| D1-LIT-QUERY-01 | Literature research design | Retrieval/screening overfits the exact research-question wording instead of forming adaptive query families. | MAJOR_RESEARCH_WORKFLOW_DESIGN | FOUND_AND_REPAIRED_POST_D1 | `D1-LIT-01` remains preserved; forward Literature 0.6/0.8 requires bounded DIRECT, SUPPORTING, CONTEXTUAL, and BACKGROUND families, Owner-reviewed adaptation, and no global novelty claim. | Historical Literature prompt/checkpoint was query-shaped rather than research-strategy-shaped. | None needed for new Projects; historical 0.5/0.7 remains immutable. | Preserve researcher-direction input and bounded adaptive query-family planning. |
| D1-LIT-ITERATIVE-01 | Literature research design | Multiple Literature rounds exist but cannot be explicitly consolidated/composed for downstream evidence. | MAJOR_PRODUCT_DESIGN | FOUND_AND_REPAIRED_POST_D1 | `D1-LIT-02/03` remains preserved; Literature Consolidation 0.1 binds exactly two explicit v1 libraries, combines locally, records exact Owner dispositions, emits one new v1, and is recursively composable. Controlled E5/E6 prove no auto-binding/latest. | Downstream contracts correctly accept one exact library but previously had no explicit composition producer. | Create/select the reviewed Literature Consolidation Workflow when complementary rounds are needed. | Preserve ADR 0054 exact composition; never implicit latest or Project-wide merge. |
| D1-LIT-SCHEMA-01 | Literature schema semantics | `selected_papers.exclusions` structurally contains both genuinely excluded and uncertain-withheld candidates. | SCHEMA_SEMANTICS | EXPECTED_BEHAVIOR | `D1-LIT-SCHEMA-01` remains preserved; R4 audit proves the exact durable Owner-decision snapshot retains `UNCERTAIN` and `EXCLUDED` separately and final output must agree with it. | v1 intentionally uses one transport container for all withheld records while authoritative decision semantics live in the exact Owner snapshot. | Preserve explicit status/reason and the durable decision snapshot. | Do not version the Artifact schema unless a consumer is proven unable to retain the distinction. |
| D1-WORKFLOW-ORDINAL-01 | Workflow labels | Owner-facing ordinals differ between Cloud/Local and are wrongly shared across Initial/Revision Writing roles. | MAJOR_IDENTITY_PRESENTATION | CONFIRMED_CROSS_WORKFLOW | `D1-WORKFLOW-LABEL-01/02`; current API still labels Revision #1/#2; R1 browser qualification also proved downstream Detail recognizes only version 0.6 as Revision and routes forward 0.7/0.9 as generic Writing. Exact IDs remain correct. | Multiple projections derive order independently and group by Workflow family; downstream Detail also guesses role from a hard-coded version instead of exact published role authority. | Use exact Workflow Instance ID and role, not ordinal. | One deterministic role-aware projection for labels and Detail routing; Initial Writing and Writing Revision use distinct namespaces without ordinals. |
| D1-WRITING-ENTRY-01 | Writing readiness UX | Input cards say Ready after Cloud selection while Local still needs materialization. | MAJOR_UX | CONFIRMED | `D1-WRITING-ENTRY-01`; command itself was correct. | One label conflates accepted Cloud binding with local execution readiness. | Read Local Workflow state/command. | Use Selected / Ready to prepare locally; reserve Ready to run for exact completed materialization. |
| D1-WRITING-UX-02 | Writing local guidance | Materialization instruction says “resume saved work” rather than preparing verified selected inputs. | MINOR_UX | OPEN | `D1-WRITING-UX-02`; copy root not separately audited. | Generic resume copy reused for materialization. | Follow the displayed materialize command. | State that the command prepares verified local copies of selected inputs. |
| D1-WORKSPACE-UX-01 | Workspace sync presentation | A Project manifest change is shown as every Workflow being “Local Workspace out of date.” | MAJOR_UX | CONFIRMED | `D1-WORKSPACE-UX-01`; local list showed six existing Workflows valid and only new Revision missing. | Sync stage is projected per Workflow from Project-level acknowledgement revision. | Run one Project sync. | One Project-level “Project changed—sync to add Writing Revision”; do not imply completed Workflows are invalid. |
| D1-OVERVIEW-PRIORITY-01 | Project Overview | After final revised manuscript, dominant Current Task is still early Experiment input preparation. | MAJOR_UX | CONFIRMED | Final screenshot; current projection recommends Experiment `MATERIALIZE` while project latest output is v5. | Readiness priority chooses unresolved active Workflow without balancing completed terminal research outcome. | Use Outputs to find the final manuscript; interpret Experiment as unresolved evidence chain. | Surface completed chain and unresolved official Experiment separately, then state the true optional/next action. |
| D1-OUTPUT-LABEL-01 | Overview / Board / Activity | Typed downstream results become generic “Workflow Output” / “Review workflow output”; latest/recent projections can look stale despite v5. | MAJOR_UX | CONFIRMED_CROSS_WORKFLOW | Owner screenshots; source `_OUTPUT_LABELS` omits v3/v4/v5 forward types and falls back to `Workflow Output`; current latest output is v5. | Shared output-label registry lagged forward Artifact types; recent-change copy follows generic projection. | Use Outputs typed cards. | Central typed labels for v4/v5/v3 and use authoritative latest product in Overview/Activity. |
| D1-RETIRED-UX-01 | Workflow Board | Retired Revision remains a full peer row and top-level count can read as eight Workflows. | MAJOR_UX | CONFIRMED | Final state: 7 active, 1 retired; owner screenshot shows both peer-level. | Board preserves history without sufficient active/history hierarchy. | Read lifecycle badges and Activity counts. | Active/current primary; retired/replaced secondary/history; preserve provenance and separate counts. |
| D1-PROGRESS-HISTORY-01 | Progress history | A historical Idea card can say workflow completed while its round badge says in progress. | MAJOR_UX | CONFIRMED | Final screenshot observation. | Workflow-level terminal projection and historical report/checkpoint status are rendered together without scope labels. | Inspect exact round/history details. | Label workflow vs report-round status explicitly or avoid mixing them in one card. |
| D1-REVIEW-PRESENTATION-01 | Review presentation | Review preview repeats large “major issue · blocking” blocks with weak issue identity and repeated limitations. | MAJOR_UX | CONFIRMED | Final screenshot; Cloud payload has RR IDs/severity but several concise issue fields are null and limitations dominate. | Bounded projection/UI foregrounds severity and long limitations rather than compact issue identity/action. | Inspect technical Review Artifact locally. | RR ID, category, severity, one-line problem, requested revision, status; details progressively disclosed. |
| D1-OUTPUTS-LAYOUT-01 | Outputs layout | Large whitespace, narrow preview column, long pages, compressed content, and wrapping COMPLETED labels reduce scanability. | MAJOR_UX | CONFIRMED | Final D1 Outputs screenshot. | Fixed layout proportions do not adapt to long typed previews/status width. | Scroll and open individual output cards. | Subtractive responsive layout; widen useful preview, reduce blank space, stabilize status label. |
| D1-PRESENTATION-CONTINUITY-01 | Artifact presentation | Valid completed initial manuscript v4 has no Cloud preview while Review and revised manuscript do. | MAJOR_UX | CONFIRMED | Owner `D1-REVIEW-PREVIEW-01`; current API: v4 `presentation=null`, v3/v5 presentations present. | Initial Writing upload-only D1 recovery registered exact Artifact/Progress without downstream presentation reporting/backfill. | Exact selection remains safe; inspect complete manuscript Local. | Idempotent presentation backfill/retry independent of scientific rerun; never treat absence as evidence failure. |
| D1-OVERVIEW-VISUAL-01 | Project Overview | Large translucent/duplicated research-question hero text overlaps the Project header. | MAJOR_FRONTEND_VISUAL | CONFIRMED | Final Owner screenshot. | Exact CSS/layout root not audited in this record-only pass. | Scroll past/ignore overlay. | Remove duplicate layer and verify responsive visual hierarchy. |
| D1-PACKAGE-OS-METADATA-01 | Platform / package validation | Benign `.DS_Store` repeatedly invalidated a managed Capsule. | MAJOR_ROBUSTNESS | FOUND_AND_REPAIRED_POST_D1 | `D1-PACKAGE-01`; ADR 0052; R1C direct/public copied-CLI tests prove bounded managed metadata handling while unknown files still fail. | Strict manifest comparison treated known OS metadata as substantive undeclared package content. | None needed after R1C for bounded regular `.DS_Store`. | Preserve ADR 0052's explicit size/type allowlist; never generalize to arbitrary undeclared files. |
| D1-PACKAGE-PRIVATE-PATH-01 | Platform / security validation | Generic operator preflight with local absolute-path metadata was classified as prohibited credential material although no secret existed. | MAJOR_ROBUSTNESS | FOUND_AND_REPAIRED_POST_D1 | Operator recovery diagnosis; ADR 0052; R1C classification regressions; no credential value was present or exposed. | Credential/private-path pattern conflated sensitive location metadata with actual credentials, inside an unsupported operator namespace. | Unsupported Generic operator state still belongs outside Capsule until R3. | Preserve separate real-secret and private-path classes; keep actual-secret rejection fail closed. |

## Experiment product-design authority preserved by this ledger

The following Owner intent constrains later repair design but authorizes no
implementation here:

1. Experiment starts from one exact selected Research Idea and first freezes a
   human-reviewable scientific contract.
2. Codex/Claude Code owns local implementation planning, decomposition, coding,
   debugging, environment inspection, package preparation, and execution.
3. Reviewed ExperimentCapabilities are qualified accelerators/adapters/
   validators, not a whitelist of all permissible scientific methods.
4. Generic Harness implementation is a supported normal path, but implementation
   freedom confers no scientific authority.
5. Methodology conformity, pre-run validation, exact Owner run approval,
   post-run evidence validation, and exact Owner result review remain mandatory.
6. User-managed Skill guidance never becomes ExperimentCapability or evaluation
   authority.
7. Session is disposable; Workspace state and human decisions are durable.
8. Local checkpoint commit precedes bounded Cloud synchronization; pending sync
   is automatically retryable.
9. Generic implementation/scratch/execution evidence needs an explicit namespace
   outside immutable Capsule package comparison.
10. Long-running execution needs unit-level manifests, checksums, retry, and
    resume rather than conversation-level restart.
11. Cloud coordinates bounded state; complete code, data, raw outputs, and
    evidence remain Local.

## Grouped repair map (planning only)

This ordering is a dependency map, not authorization to repair.

### A. Navigation / information architecture

`D1-SKILL-NAV-01`, `D1-PROJECT-NAV-01`, `D1-LOCAL-GUIDANCE-IA-01`, and
`D1-LOCAL-ORCHESTRATION-01`. Establish stable top-level destinations and one
normal Owner continuation path before polishing explanatory copy.

### B. Exact input and materialization lifecycle

`D1-INPUT-RECONCILE-01`, `D1-INPUT-RUNNABLE-01`,
`D1-INPUT-RECEIPT-01`, `D1-INPUT-REFRESH-01`, `D1-FRONTEND-KEY-01`,
`D1-WRITING-BINDING-01`, `D1-REVIEW-INPUT-LIFECYCLE-01`, and
`D1-UPSTREAM-ZERO-PAPER-01`. Highest priority is the runnable invariant and
atomic reconciliation of proven ReAgent-managed prior inputs.

### C. Human decision / durable approval lifecycle

`D1-CHECKPOINT-PRESENTATION-01` and `D1-APPROVAL-BRIDGE-01`. Build one exact
decision bridge reused by Experiment, Writing, Review, and Revision; never ask a
researcher to transport a checksum manually.

### D. Harness termination / Progress / automatic sync / resume

`D1-HARNESS-TERMINATION-01`, `D1-PROGRESS-SYNC-01`,
`D1-RESUME-DECISION-01`, and `D1-EXPERIMENT-DURABILITY-01`. Make phase completion
terminal, commit locally first, preserve human decisions, and recover pending
Cloud sync without rerunning science.

### E. Generic Experiment architecture

`D1-EXPERIMENT-ENTRY-01`, `D1-EXPERIMENT-CAPABILITY-01`,
`D1-EXPERIMENT-INGEST-01`, `D1-EXPERIMENT-OPERATOR-01`, and
`D1-EXPERIMENT-ENV-01`. The generic implementation/admission boundary must be
designed as one coherent path rather than another reviewed-method catalog.

### F. Review / Revision evidence contracts

Preserve the completed repairs `D1-REVIEW-CONTRACT-01` and
`D1-REVISION-CONTRACT-01`; address only the still-open
`D1-REVIEW-SEMANTICS-01`. Do not regress subset semantics or historical
publication immutability.

### G. Skill / Project lifecycle

`D1-SKILL-EMPTY-01`, `D1-SKILL-DETAIL-01`, `D1-SKILL-LIFECYCLE-01`,
`D1-SKILL-SUBTRACTIVE-01`, `D1-PROJECT-LIFECYCLE-01`, and
`D1-SKILL-AUTHORITY-01`. Cloud deletion must never delete Local Workspace files;
global Skills must survive Project deletion.

### H. Presentation / subtractive UX / labels

`D1-WORKFLOW-ORDINAL-01`, `D1-WRITING-ENTRY-01`, `D1-WRITING-UX-02`,
`D1-WORKSPACE-UX-01`, `D1-OVERVIEW-PRIORITY-01`, `D1-OUTPUT-LABEL-01`,
`D1-RETIRED-UX-01`, `D1-PROGRESS-HISTORY-01`,
`D1-REVIEW-PRESENTATION-01`, `D1-OUTPUTS-LAYOUT-01`,
`D1-PRESENTATION-CONTINUITY-01`, and `D1-OVERVIEW-VISUAL-01`. Prefer removing,
collapsing, shortening, and centralizing typed labels over adding prose.

### I. Platform / local-package robustness

`D1-PACKAGE-OS-METADATA-01` and `D1-PACKAGE-PRIVATE-PATH-01`. Narrowly classify
known benign metadata and private-path metadata while preserving strict unknown
file and real-secret rejection.

## Reconciliation counts

- Unique root findings/records: **52**.
- Literal `OPEN`: **3**.
- `CONFIRMED`: **20**.
- `CONFIRMED_CROSS_WORKFLOW`: **7**.
- Unresolved evidenced (`OPEN` + both confirmed statuses): **30**.
- `FOUND_AND_REPAIRED_DURING_D1`: **4**.
- `FOUND_AND_REPAIRED_POST_D1`: **10**.
- `OBSERVATION_NEEDS_CONFIRMATION`: **3**.
- `EXPECTED_BEHAVIOR`: **1**.
- `DEFERRED_PRODUCT_DESIGN`: **4**.

The repaired findings remain in the ledger and do not erase their E9/E8
occurrence. No overall release/Q1 claim follows from this reconciliation.
