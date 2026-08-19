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
| D1-SKILL-NAV-01 | Skills / navigation | Global Skills does not escape `/skills?project=…` when already on the Skills pathname. | MAJOR_UX | CONFIRMED | `D1_SKILL_NAVIGATION_01`; Owner needed Projects → Skills. | Same pathname navigation preserves the project query state. | Navigate through another top-level route. | Global Skills must explicitly navigate to unscoped `/skills`. |
| D1-SKILL-EMPTY-01 | Skills / project | Project Skills empty state has no direct Add Skill or Skill Library action. | MAJOR_UX | CONFIRMED | `D1_OBSERVATION_SKILL_EMPTY_PROJECT_PAGE`. | Empty-state action model covers attachable records only. | Use global Skills, create, return, attach. | Add one compact Create/View library escape action. |
| D1-SKILL-DETAIL-01 | Skills | No discoverable per-Skill detail/provenance/usage view. | MAJOR_UX | CONFIRMED | `D1_SKILL_DETAIL_01`. | M1 shipped list/create/attach but no secondary detail surface. | Inspect at creation time or source externally. | Small secondary detail with source, revision/provenance, and Project usage. |
| D1-SKILL-LIFECYCLE-01 | Skills | User-managed Skills cannot be safely removed from the library. | MAJOR_PRODUCT_GAP | CONFIRMED | `D1_SKILL_LIFECYCLE_01`; safe-delete semantics were already intended. | Delete service/UX was outside frozen M1 slice. | None; obsolete records accumulate. | Refuse attached deletion, then safely delete unattached records. |
| D1-SKILL-SUBTRACTIVE-01 | Skills / presentation | Some Skill actions/status relationships may still be less direct than the three-question M1 goal. | MINOR_UX | OBSERVATION_NEEDS_CONFIRMATION | Owner requested preservation of minor subtractive Skill findings; no bounded screenshot inventory is stored. | Not isolated. | None required. | Re-review cards for REMOVE/COLLAPSE/SHORTEN before changing behavior. |
| D1-PROJECT-NAV-01 | Projects / navigation | Portfolio entry can send the Owner to Project Help instead of Overview. | MAJOR_UX | CONFIRMED | `D1_PROJECT_NAVIGATION_01`; current row CTA still maps `SETUP` to `/help`, while title maps Overview. | Primary row action is derived from current task rather than stable Project entry semantics. | Click the Project title or navigate back to Overview. | Project title/body opens Overview; Help remains explicit secondary action. |
| D1-LOCAL-GUIDANCE-IA-01 | Navigation / information architecture | Project Help and global Local guide overlap without a clear authority boundary. | MAJOR_UX | CONFIRMED | `D1_LOCAL_GUIDANCE_IA_01`; both surfaces explain Local use. | Two guidance surfaces evolved independently. | Infer Project Help is contextual and Local guide generic. | Overview primary; Help concise/project-specific; Local guide generic reference. |
| D1-PROJECT-LIFECYCLE-01 | Projects | Cloud Projects cannot be deleted. | MAJOR_PRODUCT_GAP | OPEN | `D1-PROJECT-LIFECYCLE-01`; Owner product intent defines Cloud-only deletion. | Project deletion lifecycle/API/UX is absent. | Leave obsolete Projects in Cloud. | Transactional Cloud deletion with explicit confirmation; never touch Local Workspace files or global Skills. |
| D1-LOCAL-ORCHESTRATION-01 | Local workflow / IA | Normal Owner flow exposes sync, refresh, materialize, run, resume, paths, checksums, and Capsule-relative internals as a protocol. | MAJOR_UX | CONFIRMED_CROSS_WORKFLOW | Literature→Idea, Idea→Experiment, Writing→Review, Review→Revision; `D1-EXPERIMENT-UX-02`. | Fine-grained operator commands became primary UX; orchestration is not composed. | Follow the exact displayed/operator command sequence. | One high-level continue/run operation; advanced commands under troubleshooting. |
| D1-INPUT-FRESH-01 | Exact input | Fresh explicit selection and first materialization can preserve exact Artifact authority. | — | EXPECTED_BEHAVIOR | Successful fresh Idea/Writing/Review materializations; exact IDs/checksums survived. | Existing exact binding/materialization design works in the no-replacement case. | Normal supported path. | Preserve exact selection, no auto-latest, and fail-closed ownership. |
| D1-INPUT-RECONCILE-01 | Exact input / materialization | Changing an exact binding could not safely replace a proven prior ReAgent-managed materialization. | HIGH_CORE_CONTRACT | FOUND_AND_REPAIRED_POST_D1 | `D1-INPUT-02`; R1A managed A→B, unmanaged-target, and interrupted-publication tests. | Materializer treated all differing target bytes as ambiguous and ignored the prior exact ownership receipt. | Historical D1 used an operator move; R1A now stages, verifies, and atomically replaces only proven managed bytes. | Preserve ADR 0049 ownership proof and fail closed for user-owned/ambiguous bytes. |
| D1-INPUT-RUNNABLE-01 | Readiness | Stale or incomplete materialization could still be reported as Locally Materialized / Next: Run. | CRITICAL_CORE_CONTRACT | FOUND_AND_REPAIRED_POST_D1 | `D1-INPUT-03` in Idea and Initial Writing; R1A stale/concurrent-plan negative tests. | Readiness trusted self-consistent old receipts without a durable current-plan comparison. | Historical D1 required operator identity checks; R1A now requires current-plan/receipt/byte equality. | Preserve the ADR 0049 runnable invariant and current-plan fail-closed behavior. |
| D1-INPUT-RECEIPT-01 | Materialization receipts | Changing one sibling binding invalidated unchanged input receipts through aggregate plan checksum coupling. | HIGH_CORE_CONTRACT | FOUND_AND_REPAIRED_POST_D1 | `D1-INPUT-04`; R1A changed-sibling/unchanged-sibling exact carry-forward test. | Per-input receipt equality coupled unchanged identity/bytes to an old aggregate plan checksum. | Historical D1 reconciled manually; R1A reissues only a fully verified unchanged receipt under the new plan. | Preserve exact per-input identity plus atomic whole-plan completion. |
| D1-INPUT-REFRESH-01 | Artifact index | Newly available upstream Artifacts were not automatically reconciled before downstream materialization. | MAJOR_PRODUCT_DEFECT | FOUND_AND_REPAIRED_POST_D1 | `D1-INPUT-01` at Writing→Review and Review→Revision; R1A public materialize-without-refresh test. | Local Artifact Index refresh was a separate manual lifecycle step. | Historical D1 ran `artifact refresh`; R1A normal materialization now performs exact reconciliation. | Keep low-level refresh for diagnostics/backfill, not normal preparation. |
| D1-FRONTEND-KEY-01 | Exact-selection UI | Multiple Artifact candidates sharing one role use duplicate React key `paper_library`. | HIGH_UI_IDENTITY_RISK | CONFIRMED | `D1-FRONTEND-01`; React duplicate-key warning with two Literature Artifacts. | Candidate identity was keyed by role/requirement instead of unique Artifact/candidate identity. | Verify resulting exact Cloud binding; avoid trusting card identity alone. | Key by requirement plus exact Artifact ID; retain explicit selection. |
| D1-WRITING-BINDING-01 | Exact-selection UI / Cloud binding | Writing appeared Ready with Literature #2 selected while authoritative binding/materialization still referenced Literature #1. | HIGH_PRODUCT_DEFECT | CONFIRMED | Writing diagnosis/recovery: UI showed 1-paper result; Cloud binding was 0-paper result. | Selection confirmation/projection and authoritative dependency mutation diverged; exact transaction root not yet isolated. | Read exact dependency API and repair through supported replace binding. | Confirmation must display and verify accepted binding ID/Artifact/checksum before Ready. |
| D1-REVIEW-INPUT-LIFECYCLE-01 | Review inputs | Required-input confirmation collapses early, hides unresolved optional evidence, and optional evidence cannot be added after setup/materialization. | HIGH_PRODUCT_DEFECT | CONFIRMED | `D1-REVIEW-UX-01/02`, `D1-REVIEW-INPUT-01/02`; Idea was missed. | Readiness transitions on required inputs only; optional-evidence decision has no explicit completion gate and bindings become read-only after materialization. | Proceed with a limited scope or restart/recreate outside the active pass; no safe in-pass recovery. | Keep compact selected/optional summary and require explicit “continue without optional evidence” before locking setup. |
| D1-UPSTREAM-ZERO-PAPER-01 | Literature→Idea contract | Cloud accepts a valid 0-paper INSUFFICIENT library as compatible while Idea runtime requires at least one selected paper. | BLOCKER_CONTRACT_DEFECT | CONFIRMED | `D1-UPSTREAM-01`; binding/materialization succeeded, runtime returned `DEPENDENCY_UNRESOLVED`. | Cloud compatibility checks type/schema, not the stricter consumer scientific precondition. | Owner ran a second Literature round and explicitly selected its 1-paper Artifact. | Align readiness with the consumer’s published minimum-content precondition without invalidating the valid Literature Artifact. |
| D1-CHECKPOINT-PRESENTATION-01 | Owner checkpoints | Methodology, Writing outline, Review scope, and Revision plan are often written internally without a human-readable approve/revise checkpoint. | MAJOR_UX | CONFIRMED_CROSS_WORKFLOW | `D1-EXPERIMENT-UX-01`, `D1-WRITING-UX-03`, `D1-REVIEW-UX-03`, `D1-REVISION-UX-01`; later operator checkpoints passed. | Harness contract emphasizes durable files, but does not reliably require a structured Owner-facing rendering before exit. | Operator reads validated files and presents a manual bounded summary. | Evidence first: concise decision, tradeoffs, limitations, then Approve/Revise/Explain/Abort. |
| D1-APPROVAL-BRIDGE-01 | Human decisions | Natural interactive approval does not automatically become runner-owned exact durable approval; Review may demand a SHA-256 echo. | HIGH_HUMAN_CHECKPOINT_CONTRACT | CONFIRMED_CROSS_WORKFLOW | `D1-EXPERIMENT-GATE-02`, `D1-WRITING-GATE-01`, `D1-REVIEW-GATE-01`, `D1-REVISION-GATE-01`. | Harness conversation and runner approval recorder are separate authorities with no supported decision bridge. | Operator invokes the existing exact approval routine; never fabricate a receipt. | UI/Harness submits a natural decision; ReAgent binds it internally to exact checkpoint/input identities and persists once. |
| D1-HARNESS-TERMINATION-01 | Harness lifecycle | Harness sessions do not reliably terminate after reporting completion; Owner interruption can expose nested Python `KeyboardInterrupt` traces and trigger later invalid phases. | HIGH_LIFECYCLE_DEFECT | CONFIRMED_CROSS_WORKFLOW | Idea, Writing, Review, and Revision sessions required manual interruption or stale-runner recovery. | Launcher/session-end handshake does not make phase completion terminal for the process tree. | Verify durable state, interrupt the exact managed process group, then use recovery. | Structured normal exit at terminal phase; bounded cancellation without raw stack traces. |
| D1-PROGRESS-SYNC-01 | Progress / finalization | Successful local scientific completion can end with ambiguous/failed Cloud finalization or require manual upload/recovery. | HIGH_STATE_MACHINE_DEFECT | CONFIRMED_CROSS_WORKFLOW | `D1-PROGRESS-01` round increment error followed by “Progress Synchronized”; Initial Writing/Review/Revision upload-only recoveries. | Durable phase completion, report sequencing, launcher termination, and backlog acknowledgement are not one idempotent lifecycle. | Preserve local result, inspect reports, run the exact recovery command. | Local commit → pending sync → automatic idempotent Cloud upload/receipt at every durable checkpoint and session end. |
| D1-RESUME-DECISION-01 | Resume / scientific decisions | Resume can preserve files while losing a prior Owner screening disposition. | HIGH_SCIENTIFIC_STATE_DEFECT | CONFIRMED | `D1-RESUME-02`: Paper 2 reverted from Uncertain to Likely Relevant. | Human decision state was not restored as authoritative durable Workflow state. | Owner rechecks decisions before finalization. | Persist and checksum human decisions; resume must restore them before Agent inference. |
| D1-EXPERIMENT-DURABILITY-01 | Experiment / durability | Long-running Generic Harness work lacks execution-unit resume and an explicit local-commit-before-Cloud-sync lifecycle. | ARCHITECTURE | DEFERRED_PRODUCT_DESIGN | Owner Experiment Product Design Intent §§10–15 and D1 session interruptions. | Current lifecycle is session/round oriented, not execution-manifest/unit oriented. | Preserve operator evidence manually; restart only with explicit verification. | Durable manifests, stable unit IDs/checksums, partial-result reuse, pending-sync recovery, automatic session-end sync. |
| D1-EXPERIMENT-ENTRY-01 | Experiment UX / exact input | Experiment displays the Idea as objective metadata and offers Run although no exact `research_idea` binding is accepted/materialized; custom page hides input selection. | BLOCKER_OWNER_FLOW | CONFIRMED | `D1-EXPERIMENT-ENTRY-01/02`; Run returned `DEPENDENCY_UNRESOLVED`. | Presentation/objective projection is independent of exact dependency binding; custom detail bypasses generic SELECT_INPUT UI. | Operator uses the existing generic binding API, then refresh/materialize; do not run first. | Show exact input selection/preparation before Run and verify accepted binding. |
| D1-EXPERIMENT-CAPABILITY-01 | Experiment architecture | Reviewed ExperimentCapability acts as a mandatory scientific-method implementation whitelist. | ARCHITECTURE_PRODUCT_GAP | DEFERRED_PRODUCT_DESIGN | `D1-EXPERIMENT-CAP-01`, `D1-EXPERIMENT-ARCH-01`; approved KNN methodology could not enter preparation. | Generic path still requires a pre-published capability to encode methodology. | Operator-only Generic Harness implementation, not authoritative admission. | Reviewed capabilities are qualified fast paths; Generic Harness implementation is a supported normal path validated against the approved scientific contract. |
| D1-EXPERIMENT-INGEST-01 | Experiment evidence | Validated Generic Harness evidence has no provenance-safe supported admission path to `experiment-record/v5`. | BLOCKER_PRODUCT_GAP | CONFIRMED | `D1-EXPERIMENT-INGEST-01`; final Cloud Artifact list has no Experiment Artifact. | Artifact publisher/finalizer accepts only managed reviewed lifecycle/package evidence. | Preserve checksummed operator evidence outside the authoritative chain; Writing treats Experiment unavailable. | Contract-valid generic package/evidence admission with pre-run approval, post-run validation, exact lineage, and Owner result review. |
| D1-EXPERIMENT-OPERATOR-01 | Experiment workspace boundary | Operator implementation/preflight/result state inside managed Capsule memory contaminates package validation. | HIGH_ARCHITECTURE_DEFECT | CONFIRMED | `D1-EXPERIMENT-OPERATOR-01`; normal `workflow list` failed until proven operator files were moved intact. | No supported Generic Harness scratch/execution/evidence namespace; strict Capsule validator sees operator additions as managed package content. | Move only proven operator-owned files intact outside Capsule and retain checksums. | Dedicated managed execution/scratch/evidence namespace outside immutable Capsule package comparison. |
| D1-EXPERIMENT-ENV-01 | Experiment environment | Owner-facing runtime preparation does not discover compatible environments or explain practical setup without taking silent action. | MAJOR_PRODUCT_GAP | OPEN | `D1-EXPERIMENT-ENV-01`; approved methodology reached an unsuitable/unprepared runtime boundary. | Environment candidate discovery/provisioning UX is not part of the normal generic path. | Operator inspects environments and asks Owner to prepare one. | Discover and explain; suggest options; never silently install/upgrade/download; rerun preflight after explicit Owner action. |
| D1-SKILL-AUTHORITY-01 | Trust boundary | Literature wording said a pinned user Skill’s evidence rules “determined” scientific disposition. | SEMANTIC_TRUST_OBSERVATION | OBSERVATION_NEEDS_CONFIRMATION | `D1-SKILL-07`; no downstream authority escalation was proven. | Wording may conflate guidance with evaluation authority. | Treat Skill as instructions only and verify Artifact evidence independently. | Explicitly state user Skill ≠ reviewed Capability ≠ scientific authority; audit later Workflow wording. |
| D1-WRITING-LIFECYCLE-01 | Initial Writing / recovery | Completed Real Writing was evaluated with Scaffold provenance and became `LOCAL_PROGRESS_INVALID` after successful finalization. | CORE_LIFECYCLE_DEFECT | FOUND_AND_REPAIRED_DURING_D1 | Change packet and E8 recovery; v4/Owner review/Progress unchanged, exactly one Cloud upload. | Shared readiness dispatch used `_scaffold_provenance_is_exact` for Writing 0.5. | Before repair, upload-only operator recovery was blocked. | Retain exact Real Writing provenance dispatch and no-Harness idempotent backlog recovery. |
| D1-REVIEW-CONTRACT-01 | Review contract | Optional Review evidence conflicted with publisher equality to complete manuscript provenance. | CORE_CONTRACT_DEFECT | FOUND_AND_REPAIRED_DURING_D1 | Change packet; limited-scope Review published v3 exactly once with Idea unbound. | Contextual validator required Review bindings to equal manuscript source set. | None needed after repair. | Require exact identity for evidence actually bound/used; omitted provenance remains unverified, not Review evidence. |
| D1-REVISION-CONTRACT-01 | Revision contract | Revision required causal Review support to equal full inherited manuscript context. | CORE_CONTRACT_DEFECT | FOUND_AND_REPAIRED_DURING_D1 | ADR 0048/change packet; old 0.6 retired, forward 0.7/0.9 recovered. | Immutable Capsule 0.8 encoded equality instead of subset semantics. | Supported retire/create/sync/materialize path. | `CAUSAL_REVIEW_SUPPORT ⊆ REVISION_CONTEXT` with exact identity on overlap; additive publication `20260819_0034`. |
| D1-REVISION-LIFECYCLE-01 | Revision / recovery | Existing exact Revision Plan approval was treated as a terminal error rather than a resume checkpoint. | CORE_LIFECYCLE_DEFECT | FOUND_AND_REPAIRED_DURING_D1 | 2026-08-20 packet; one v5, one COMPLETED report/receipt, idempotent replay, no Harness. | Public runner always re-entered plan approval in the single-pass Capsule runner. | None needed after repair. | Keep exact checkpoint-aware root recovery; published 0.7/0.9 bytes unchanged. |
| D1-REVIEW-SEMANTICS-01 | Review semantics | Review can conflate evidence unavailable in Review scope with evidence unavailable during manuscript authoring. | MAJOR_SCIENTIFIC_SEMANTICS | CONFIRMED | `D1-REVIEW-SEMANTICS-01`; Idea provenance existed in manuscript but was omitted from Review. | Availability is projected primarily from Review bindings without always preserving authoring provenance distinction. | Interpret as “not independently verifiable in this scope,” not invalid provenance. | Separate authoring provenance, Review-available evidence, and Review-verified support in issue language. |
| D1-LIT-QUERY-01 | Literature research design | Retrieval/screening overfits the exact research-question wording instead of forming adaptive query families. | MAJOR_RESEARCH_WORKFLOW_DESIGN | DEFERRED_PRODUCT_DESIGN | `D1-LIT-01`; Owner expects problem + domain keywords, not engineered search strings. | Current Literature prompt/checkpoint is query-shaped rather than research-strategy-shaped. | Owner manually refines query terms. | Agent proposes direct/supporting/contextual/background query families and seeks direction approval. |
| D1-LIT-ITERATIVE-01 | Literature research design | Multiple Literature rounds exist but cannot be explicitly consolidated/composed for downstream evidence. | MAJOR_PRODUCT_DESIGN | DEFERRED_PRODUCT_DESIGN | `D1-LIT-02/03`; Idea accepts one exact library. | Downstream contract is singular and intentionally forbids implicit merging/latest. | Select one superseding exact library. | Explicit composition Artifact or deliberate multi-input contract with Owner-selected exact sources. |
| D1-LIT-SCHEMA-01 | Literature schema semantics | `selected_papers.exclusions` structurally contains both genuinely excluded and uncertain-withheld candidates. | SCHEMA_SEMANTICS | OBSERVATION_NEEDS_CONFIRMATION | `D1-LIT-SCHEMA-01`; labels/reasons preserve distinction, container does not. | v1 schema uses one non-selected container. | Preserve explicit status/reason in each record. | Assess a forward schema only if consumers cannot reliably retain the distinction. |
| D1-WORKFLOW-ORDINAL-01 | Workflow labels | Owner-facing ordinals differ between Cloud/Local and are wrongly shared across Initial/Revision Writing roles. | MAJOR_IDENTITY_PRESENTATION | CONFIRMED_CROSS_WORKFLOW | `D1-WORKFLOW-LABEL-01/02`; current API still labels Revision #1/#2; exact IDs remain correct. | Multiple projections derive order independently and group by Workflow family rather than exact role authority. | Use exact Workflow Instance ID and role, not ordinal. | One deterministic role-aware label projection; Initial Writing and Writing Revision use distinct namespaces without ordinals. |
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
| D1-PACKAGE-OS-METADATA-01 | Platform / package validation | Benign `.DS_Store` repeatedly invalidates a managed Capsule. | MAJOR_ROBUSTNESS | CONFIRMED | `D1-PACKAGE-01`; normal Writing launch blocked on undeclared `.DS_Store`. | Strict manifest comparison treats known OS metadata as substantive undeclared package content. | Operator proves/removes only benign metadata before validation. | Prevent/ignore an explicit tiny allowlist of platform metadata without weakening arbitrary-file checks. |
| D1-PACKAGE-PRIVATE-PATH-01 | Platform / security validation | Generic operator preflight with local absolute-path metadata was classified as prohibited credential material although no secret existed. | MAJOR_ROBUSTNESS | CONFIRMED | Operator recovery diagnosis; no credential value was present or exposed. | Credential/private-path pattern conflated sensitive location metadata with actual credentials, inside an unsupported operator namespace. | Preserve operator state outside Capsule; do not edit evidence. | Distinguish secrets, private paths, and benign metadata; keep real-secret rejection fail closed. |

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
- `CONFIRMED`: **26**.
- `CONFIRMED_CROSS_WORKFLOW`: **7**.
- Unresolved evidenced (`OPEN` + both confirmed statuses): **36**.
- `FOUND_AND_REPAIRED_DURING_D1`: **4**.
- `FOUND_AND_REPAIRED_POST_D1`: **4**.
- `OBSERVATION_NEEDS_CONFIRMATION`: **3**.
- `EXPECTED_BEHAVIOR`: **1**.
- `DEFERRED_PRODUCT_DESIGN`: **4**.

The four repaired findings remain in the ledger and do not erase their E9/E8
occurrence. No overall release/Q1 claim follows from this reconciliation.
