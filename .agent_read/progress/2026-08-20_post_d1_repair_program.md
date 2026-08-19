# Post-D1 consolidated repair program

Status: **R1 COMPLETE — R2 NEXT**

Date: 2026-08-20

Program authority: Owner authorization in the Post-D1 Consolidated Repair
Program prompt, constrained by
`docs/PROJECT_DEVELOPMENT_PLAN.md`,
`docs/engineering/SOURCE_OF_TRUTH_POLICY.md`, and the authoritative D1 ledger
`.agent_read/progress/2026-08-20_final_d1_defect_ledger.md`.

This record is the R0 architecture and verification matrix. It changes no
production behavior, test expectation, migration, publication, database row,
Workflow, Capsule, Artifact, binding, Progress report, or research content. A
phase entry below is a routing decision, not permission to blur phase scope.
The Owner's program prompt is the separate implementation authorization; each
behavioral phase must still freeze its exact pre-write contract and pass its
phase gate before code is written.

Implementation progress through 2026-08-20:

- R0 governance matrix: `ff41b6d`.
- R1A exact Local input reconciliation/readiness: `5124fc1`.
- R1B1 explicit optional-input setup decision: `54a26fc`.
- R1B2a forward Idea content precondition/publication: `4b19881`.
- R1B2b server-qualified browser candidates: `5dec904`.
- R1B2 governance: `58992e6`.
- R1C bounded platform metadata/private-path classification: `70a97d2`.
- Current-head migration qualification correction: `6df58be`.
- R1 controlled-browser fixture alignment: `ffadc38`.

R1B2 publishes forward Idea Definition 0.3 / Capsule 0.4 under migration
`20260820_0036`. It preserves the valid zero-paper producer Artifact while a
single shared evaluator blocks it as input to the forward Idea consumer. The
bounded exact content qualification is derived from Local Artifact bytes and
does not become presentation or evidence authority. R1C implements ADR 0052's
bounded managed `.DS_Store` handling and distinct private-path diagnosis without
weakening unknown-file or real-secret rejection. Consolidated R1 qualification is
recorded in `2026-08-20_post_d1_r1_complete.md`; R2 is next.

## 1. Recovered baseline

### Repository

| Item | Recovered value |
|---|---|
| Repository root | `/Volumes/tb/个人资料/暑研/UCInspire26/MetaResearchAgent/ResearchAgent` |
| Branch | `main` |
| R0 starting HEAD | `e665d2dc6c283874f4a9dbe2c1b00597b36b3db5` |
| Starting status | clean |
| Worktrees | one; the repository root only |
| Alembic sole head | `20260819_0034` |
| Owner runtime revision | `20260819_0034` |

The migration graph is one linear chain. Its current forward tail is:

```text
20260817_0028 generic Experiment publication
  -> 20260817_0029 Artifact presentations
  -> 20260817_0030 controlled-local Run Approval
  -> 20260818_0031 Experiment 0.7 / Capsule 0.10 / experiment-record/v5
  -> 20260818_0032 forward downstream v5 chain
  -> 20260818_0033 user-managed Skills
  -> 20260819_0034 Writing Revision optional causal-Review support (sole head)
```

No historical migration or immutable publication may be edited by this
program. Publication-affecting work must be forward-additive.

### Published production authority

The current forward product pins recovered from the production catalog and the
protected D1 Project are:

| Role | Definition | Capsule | Artifact / role note |
|---|---:|---:|---|
| Literature Search | 0.4.0 | 0.6.0 (`capsule-e9e6a2e0aa46146818fb6123e03877f3`) | `selected-paper-library/v1` |
| Idea Discovery | 0.2.0 | 0.3.0 (`capsule-3976596c49e3df30e08774233055bcce`) | `selected-research-idea/v1` |
| Reproduction & Experiment | 0.7.0 | 0.10.0 (`capsule-cd7ff18e9857b6d20fbe9ba2ccab7ba6`) | `experiment-record/v5`; Full Research pin is intentionally newer than the catalog's historical recommendation |
| Initial Writing | 0.5.0 | 0.7.0 (`capsule-2abb078c2c2112b284f9a7dae8ea2854`) | `INITIAL`; `manuscript-draft/v4` |
| Review | 0.4.0 | 0.6.0 (`capsule-133692a783abb9a5061ebd315159a90e`) | `review-report/v3` |
| Historical Writing Revision | 0.6.0 | 0.8.0 (`capsule-ff1975990022b65f0bfd83514820dd3b`) | immutable equality contract; historical only |
| Forward Writing Revision | 0.7.0 | 0.9.0 (`capsule-c9b068dd677efa8098f6ff4ddbdcf5e8`) | `REVISION`; subset semantics; `manuscript-draft/v5` |

Exact publication checksums remain governed by migrations 0031, 0032, and
0034 and their source builders. R0 did not reproduce or rewrite publication
bytes.

### Test baseline

The default commands were run without inventing a disposable database or
relaxing the environment:

| Surface | Result | Interpretation |
|---|---|---|
| Frontend `npm test` | **20 files, 70 tests passed** | Clean default frontend baseline. |
| Backend `make test-backend` | **1023 passed, 72 skipped, 26 failed, 18 errors** | Red baseline recorded, not repaired in R0. All 18 setup errors require an explicit `REAGENT_TEST_DATABASE_URL`; several failures require loopback or enforceable macOS no-egress privileges; the remainder include stale published-version/fixture expectations and affected product-route assumptions. |

The backend result is not treated as product acceptance. Each phase must use
the correct marked PostgreSQL, loopback, no-egress, and publication fixtures,
then R7 must run the full qualified matrix. Tests may not be weakened merely to
make the default aggregate command green.

## 2. Protected D1 acceptance evidence

Protected Project:
`project-4c73c4c95e1d4535884f671b2f4b4b6f`.

R0 used read-only Owner API calls only. Canonical JSON snapshots live outside
the repository under `/private/tmp/post-d1-r0-owner-fingerprint/`; they are
ephemeral operator evidence, not product state.

| Projection | Count / identity | Canonical SHA-256 |
|---|---|---|
| Project | one exact Project | `29317a608aa6f98e0b07d30032fcc9652a81b0d9bda62e563a66d9abdef283f6` |
| Workflow Instances | 8 total; 7 active, 1 retired | `0d34b996b5dfee4367a72a7c91d1572fbad2f445f813e4f332a4c72b42e2f5e5` |
| Artifact references | 6 | `22112e6f279d49d1634fd8c8581a9ca666f494c7d5fff32bfc8c5ce4f408cd59` |
| Progress reports | 8 accepted | `3d1887e6cf123508e147649cb4882e4d8cf44e3a9850bf4acf9f371fe7249d96` |
| Project-Skill associations | 1 | `b0a6ceedacd4093a96fd3d1ed258f47d37e328c3a6edb54bba7f3463345ce5b5` |
| Desired Manifest | revision 5 | `ee25e44e47d03b60dd74f5c71a878d2e6e5dce70fe7e31350e3a0f08511c5336` |
| Bootstrap | exact current descriptor | `be7e3e34e52e4eb9138953c724a1f0292fb8e35c277389a5803ce10a7b3993ff` |

The exact active/retired Workflow identities and the six Artifact IDs/checksums
remain as recorded in the authoritative D1 ledger. The active Revision is
0.7/0.9; the retired Revision is 0.6/0.8. The Experiment has no authoritative
`experiment-record/v5`. Future phases must compare these read-only fingerprints
before and after qualification. A schema migration may reach the Owner database
only after its entire phase passes on disposable PostgreSQL and the Owner later
authorizes the upgrade.

## 3. Non-negotiable program contracts

1. Cloud coordinates; Local Workspace executes; complete scientific bytes stay
   Local unless an existing bounded contract explicitly permits a projection.
2. Presentation is optional UI metadata and never evidence authority.
3. User-managed Skill is neither reviewed Skill nor ExperimentCapability nor
   scientific authority.
4. Exact Artifact binding is mandatory. No latest/highest/implicit merge may be
   introduced.
5. Runnable means exact equality among all current required Cloud bindings,
   Local materializations, current valid per-input receipts, and the complete
   current plan.
6. Managed replacement is allowed only after proving the existing bytes are the
   previous ReAgent-managed exact input. Ambiguous or user-owned content fails
   closed.
7. Historical publication and migrations are immutable. Semantic publication
   changes are forward-additive.
8. Scientific completion must never rerun merely to synchronize bounded Cloud
   state.
9. The protected D1 Project is evidence, not a repair fixture.
10. Tests reproduce production contracts; fixtures may not be changed to avoid
    a real failure.

## 4. D1 regression locks

These four rows remain historical `FOUND_AND_REPAIRED_DURING_D1` findings and
must pass in every affected phase and R7:

| Lock | Required invariant | Existing focused owners |
|---|---|---|
| `D1-WRITING-LIFECYCLE-01` | Real Writing provenance dispatch; pending terminal upload recovers without Harness or duplicates. | `backend/project_workspaces/tests/test_scaffold_progress_recovery_readiness.py`, `test_workspace_cli.py` |
| `D1-REVIEW-CONTRACT-01` | Optional Review evidence remains optional; bound/used evidence is exact; omitted evidence is unverified. | `backend/project_workspaces/tests/test_forward_review_optional_evidence_recovery.py`, Artifact contract tests |
| `D1-REVISION-CONTRACT-01` | `CAUSAL_REVIEW_SUPPORT` is a subset of inherited Revision context with exact overlap. | `backend/artifact_references/tests/test_revision_optional_review_support.py` |
| `D1-REVISION-LIFECYCLE-01` | Existing exact Revision Plan approval is a resume checkpoint; one v5 and one terminal Progress. | `backend/project_workspaces/tests/test_forward_revision_lifecycle_recovery.py` |

## 5. Complete ledger-to-phase map

Every authoritative ledger ID has one primary repair/audit phase. `R7` verifies
all completed contracts; it is not a second owner. `LOCK` means an already
repaired invariant carried through every relevant phase.

| Ledger ID | Primary phase | Known root / disposition | Owning components | Required evidence | Migration expectation |
|---|---|---|---|---|---|
| D1-SKILL-NAV-01 | R5 | Scoped query survives same-path global navigation. | `frontend/components/app-shell.tsx`, Skills page | navigation component + browser | 0 |
| D1-SKILL-EMPTY-01 | R5 | Empty state has attach-only actions. | `frontend/app/skills/page.tsx`, Project Overview | component + browser | 0 |
| D1-SKILL-DETAIL-01 | R5 | M1 omitted a secondary detail surface. | user-Skill API/page | API/component/browser | 0 |
| D1-SKILL-LIFECYCLE-01 | R5 | Backend delete seam exists; safe associated-record policy/UX must be proven. | `backend/user_skills.py`, routers, Skills page | service/API/PostgreSQL/browser | 0 expected |
| D1-SKILL-SUBTRACTIVE-01 | R5 | Audit first; do not infer behavior from unbounded visual concern. | Skills UI | bounded screenshot review | 0 |
| D1-PROJECT-NAV-01 | R5 | Current-task CTA displaced stable Project entry. | Project list/navigation | component + browser | 0 |
| D1-LOCAL-GUIDANCE-IA-01 | R5 | Contextual Help and global guide evolved independently. | project Help, global Local guide | IA component + browser | 0 |
| D1-PROJECT-LIFECYCLE-01 | R5 | Cloud deletion lifecycle absent. | Project service/repository/router/UI; FK ownership | service/API/PostgreSQL/local-orphan E2E/browser | 0 expected; stop if schema ownership is insufficient |
| D1-LOCAL-ORCHESTRATION-01 | R2 | Operator commands became the Owner protocol. R1 supplies safe primitives first. | `workspace_cli.py`, Local handoff UI | controlled high-level command E5/E6 | 0 expected |
| D1-INPUT-FRESH-01 | R1 | Positive invariant, not a defect. | binding/materialization services | exact no-auto-latest regression | 0 |
| D1-INPUT-RECONCILE-01 | R1 | No ownership-proven atomic A→B replacement. | Artifact reference service, `workspace_cli.py` | managed vs ambiguous replacement tests + E5 | 0 |
| D1-INPUT-RUNNABLE-01 | R1 | Old receipt/local bytes can satisfy readiness under a new binding. | readiness/materialization plan | stale-byte negative tests + CLI E5 | 0 |
| D1-INPUT-RECEIPT-01 | R1 | Per-input receipt is coupled to aggregate plan checksum. | materialization receipt contract/runtime | changed sibling + unchanged sibling matrix | 0 unless receipt schema cannot evolve compatibly; stop and packet if not |
| D1-INPUT-REFRESH-01 | R1 | Artifact Index refresh is a separate manual step. | transport/index/materializer | Cloud-new Artifact high-level preparation E5 | 0 |
| D1-FRONTEND-KEY-01 | R1 | Candidate identity used role rather than exact Artifact identity. | `workflow-input-setup.tsx`, relevant custom setup | multi-candidate component/browser | 0 |
| D1-WRITING-BINDING-01 | R1 | Optimistic UI projection diverged from accepted dependency. | binding API/hooks/input setup | accepted-binding response + browser exact ID | 0 |
| D1-REVIEW-INPUT-LIFECYCLE-01 | R1 | Required completion locks setup before explicit optional decision. | Workflow Detail/input setup + dependency service | omitted/selected optional cases E3/E6 | 0 |
| D1-UPSTREAM-ZERO-PAPER-01 | R1B2 COMPLETE | Forward Idea 0.3/0.4 declares an exact one-paper content precondition; one shared evaluator now governs candidates, bind, readiness, and materialization. | Artifact qualification/reporting, Idea requirement/readiness/runtime, input-selection UI | valid zero-paper producer + blocked forward consumer; one-paper candidate/bind/materialize; historical Idea 0.2; PostgreSQL publication cycle | `20260820_0036`; forward-additive only; historical 0.2/0.3 unchanged |
| D1-CHECKPOINT-PRESENTATION-01 | R2 | Durable file creation is not a human checkpoint renderer. | Workflow runtimes/runner bridge + Workflow Detail | checkpoint contract/component/browser across four roles | 0 expected |
| D1-APPROVAL-BRIDGE-01 | R2 | Chat decision and exact approval recorder are disconnected. | approval contracts/services/routes/launcher | natural decision → exact durable record; replay | additive persistence only if existing approval stores cannot represent the shared contract |
| D1-HARNESS-TERMINATION-01 | R2 | Phase completion lacks a terminal launcher/session handshake. | Workflow runtimes and `workspace_cli.py` process management | clean exit/cancel/resume process tests | 0 |
| D1-PROGRESS-SYNC-01 | R2 | Local completion, report round, session exit, backlog receipt are separate lifecycles. | Progress package/client/service and launcher | pending-sync/network-loss/exactly-once E3/E5 | 0 expected |
| D1-RESUME-DECISION-01 | R2 | Human decisions are not restored before Agent inference. | Literature/Workflow durable memory and resume | interrupt/restart exact decision fingerprints | additive persistence only if current durable state is insufficient |
| D1-EXPERIMENT-DURABILITY-01 | R3 | Session/round state lacks execution-unit manifests. | generic Experiment workspace/coordinator | interrupted work-unit reuse and checksums | architecture packet decides; forward additive only |
| D1-EXPERIMENT-ENTRY-01 | R3 | Objective presentation bypasses exact input binding/readiness. | Experiment Detail + generic input lifecycle | exact selection before run E3/E6 | 0 |
| D1-EXPERIMENT-CAPABILITY-01 | R3 | Reviewed Capability is acting as a method allow-list. | generic coordinator/capability resolver | no-match Generic Harness path | likely forward-additive publication; never mutate 0.7/0.10 |
| D1-EXPERIMENT-INGEST-01 | R3 | No generic provenance-safe v5 admission. | generic contracts/validator/publisher/coordinator | exactly one v5 with truthful generic provenance | forward-additive publication/migration expected; exact packet required |
| D1-EXPERIMENT-OPERATOR-01 | R3 | Mutable operator state lacks a namespace outside Capsule comparison. | Workspace layout, package validator, generic runtime | scratch/evidence isolation + immutable Capsule regression | 0 schema DB; local format may be additive |
| D1-EXPERIMENT-ENV-01 | R3 | No normal environment candidate discovery/Owner preparation checkpoint. | generic preflight/runtime UI | compatible/incompatible/no-silent-install cases | 0 |
| D1-SKILL-AUTHORITY-01 | R4 | Audit wording; no authority escalation proven. | Literature runtime/presentations | trust-boundary wording + capability separation | 0 |
| D1-WRITING-LIFECYCLE-01 | LOCK / R7 | Repaired Real Writing provenance dispatch. | Workspace readiness/recovery | focused lock + controlled chain | 0 |
| D1-REVIEW-CONTRACT-01 | LOCK / R7 | Repaired optional-evidence publication semantics. | Review validators/publisher | focused lock + omitted-evidence E2E | 0 |
| D1-REVISION-CONTRACT-01 | LOCK / R7 | Repaired forward 0.7/0.9 subset semantics. | Revision validators/publication | focused lock + exact-overlap negatives | 0; 0034 immutable |
| D1-REVISION-LIFECYCLE-01 | LOCK / R7 | Repaired approval resume checkpoint. | Revision runtime/recovery | focused lock + exactly-once E2E | 0 |
| D1-REVIEW-SEMANTICS-01 | R4 | Authoring provenance, Review availability, and verified support are conflated in language. | Review contracts/runtime/presentation | semantic validator/presentation cases | Forward-additive only if scientific payload semantics must change |
| D1-LIT-QUERY-01 | R4 | Query-shaped prompt rather than research-strategy checkpoint. | Literature runtime/contracts | controlled query-family checkpoint | Forward-additive publication likely if immutable Capsule instructions change |
| D1-LIT-ITERATIVE-01 | R4 | Singular exact downstream contract; no explicit composition. | Artifact contracts/Idea/Writing input requirements | exact multi-source/composition negatives and positives | architecture decision and forward-additive schema/publication if implemented |
| D1-LIT-SCHEMA-01 | R4 audit | Observe only unless consumers lose uncertain/excluded semantics. | selected-paper-library contracts/consumers | round-trip semantic audit | 0 unless audit proves a forward schema is needed |
| D1-WORKFLOW-ORDINAL-01 | R6 | Cloud/Local sort independently, Writing family shares ordinal namespace, and downstream Detail hard-codes Revision 0.6 so forward 0.7/0.9 routes as generic Writing. | Progress projection + Workspace CLI + role-aware Detail routing | repeated-role projection/browser | 0 |
| D1-WRITING-ENTRY-01 | R6 | “Ready” conflates Cloud selection and Local run readiness. | Workflow Detail | component/browser state table | 0 |
| D1-WRITING-UX-02 | R6 | Generic resume copy reused for materialization. | Local handoff presenter | component/browser | 0 |
| D1-WORKSPACE-UX-01 | R6 | Project acknowledgement drift is rendered per Workflow. | Overview/board sync projections | component/browser | 0 |
| D1-OVERVIEW-PRIORITY-01 | R6 | Attention priority hides achieved terminal research outcome. | Progress aggregation + Overview | projection/component/browser | 0 |
| D1-OUTPUT-LABEL-01 | R6 | Shared type-label registry lacks forward v3/v4/v5 types. | aggregation/presentation/UI | typed projection across surfaces | 0 |
| D1-RETIRED-UX-01 | R6 | Provenance history has peer-level hierarchy. | Workflow board/overview | active-vs-history browser | 0 |
| D1-PROGRESS-HISTORY-01 | R6 | Workflow and report-round statuses are mixed without scope. | Progress aggregation/panel | component/browser | 0 |
| D1-REVIEW-PRESENTATION-01 | R6 | Severity/limitations dominate issue identity/action. | Artifact presentation + Review UI | compact RR issue component/browser | 0 |
| D1-OUTPUTS-LAYOUT-01 | R6 | Fixed layout wastes width and compresses previews. | Outputs page/CSS | responsive screenshot review | 0 |
| D1-PRESENTATION-CONTINUITY-01 | R6 | Upload-only recovery skipped optional presentation reporting/backfill. | presentation reporting/API/Local recovery | idempotent backfill without science rerun | 0 |
| D1-OVERVIEW-VISUAL-01 | R6 | CSS/render root not yet isolated. | Overview/CSS | responsive visual regression | 0 |
| D1-PACKAGE-OS-METADATA-01 | R1 | Known OS metadata entered strict package comparison; current source contains a narrow `.DS_Store` path that must be audited against the D1 reproduction before any edit. | package validator/compiler/Workspace sync | benign file positive; arbitrary undeclared negative | 0 |
| D1-PACKAGE-PRIVATE-PATH-01 | R1 | Secret classifier conflated private path metadata with credentials, compounded by unsupported operator namespace. | package/security validator; R3 namespace | secret/path/benign classification matrix | 0 |

Coverage check: **52 ledger IDs mapped exactly once** (including four locks and
one expected-behavior invariant).

## 6. Phase contracts, stop conditions, and evidence

### R1 — exact input, materialization, readiness, and local safety

Primary owners: `backend/artifact_references/service.py`,
`backend/project_workspaces/workspace_cli.py`, materialization schemas,
Artifact-reference routers, `frontend/components/workflow-input-setup.tsx`,
`frontend/components/workflow-detail.tsx`, and package validation.

Contract:

```text
RUNNABLE
  == every current required Cloud binding
  == every current Local materialization (Artifact ID + checksum)
  == every current valid per-input receipt
  == one complete current plan
```

The materializer may atomically replace only an ownership-proven prior managed
input. It carries/reissues an unchanged sibling only after exact byte/identity
verification. High-level preparation reconciles the Artifact Index. Optional
evidence stays visible until the Owner explicitly continues. Cloud and Local
enforce the same published consumer precondition.

Stop if this needs global comparator weakening, implicit latest/merge, an
in-place publication edit, or ambiguous file replacement. A consumer-publication
gap becomes a separate forward-additive R1 subphase before code changes.

Evidence: service/CLI unit tests, managed/ambiguous filesystem tests, UI tests,
marked PostgreSQL binding tests, disposable public Workspace, focused browser,
plus all four regression locks. Migration target: zero unless a narrowly proven
forward consumer publication is required.

### R2 — Owner decisions, Harness lifecycle, Progress, and orchestration

Primary owners: Workflow runtimes, `workspace_cli.py`, Progress contracts/client/
service, exact approval persistence/routes, and checkpoint UI.

Contract: natural Owner actions are converted by a supported bridge into one
exact durable decision bound to checkpoint, Workflow, current input plan, and
causal Artifact identities. Local durable commit precedes idempotent Cloud sync.
A completed phase exits its managed Harness normally; resume restores decisions
and validated outputs before any Agent inference. One high-level Owner command
composes safe R1 primitives; low-level commands remain operator tools.

Stop if chat text would become scientific authority, science must rerun to sync,
or a second runner is proposed. A new persistence need requires a dedicated
additive migration packet and disposable downgrade/re-upgrade before Owner use.

Evidence: each checkpoint type, network-loss/pending-sync replay, clean terminal
exit, bounded cancellation, repeated resume, exactly-once Artifact/Progress,
browser checkpoint review, and four regression locks.

### R3 — Generic Experiment normal path

Before any R3 production write, refresh a bounded architecture/change packet
against ADRs 0041–0046 and the Owner Experiment Product Design Intent preserved
in the D1 ledger.

Primary owners: generic Experiment contracts/coordinator/publication,
Capability resolver, Workspace runtime/layout, execution runner, v5 validator/
publisher, environment preflight, and Experiment Detail.

Contract: exact Idea → approved Scientific Contract → reviewed Capability fast
path or Generic Harness implementation → contract validation → exact Owner run
approval → Local execution → evidence validation → Owner result review → one
authoritative `experiment-record/v5`. Generic provenance never claims reviewed
Capability authority. Mutable execution state lives outside immutable Capsule
comparison. Environment setup is explicit and never silently installed.

Stop for a second execution engine, arbitrary Cloud filesystem access,
Capability trust fabrication, in-place 0.7/0.10 mutation, or unbounded provider/
research execution. Publication/persistence changes must be forward-additive and
may require bounded R3 subphases.

Evidence: deterministic sklearn-scale controlled experiment, no Capability
match, environment selection, no silent install, natural approvals, interrupted
work-unit resume, exact generic provenance, one v5, and downstream exact Writing
binding. E7 real research is not part of engineering qualification.

### R4 — scientific Workflow semantics

Primary owners: Literature/Idea/Review contracts, runtimes, prompts, validators,
and bounded presentations.

Contract: Literature forms research query families from Owner direction;
iterative evidence remains explicit and exact, never implicit latest/merge;
Review distinguishes authoring provenance, available scope, and independently
verified evidence; user Skill is guidance only.

`D1-LIT-SCHEMA-01` and `D1-SKILL-AUTHORITY-01` are audits first. Do not change a
schema from an observation alone. Stop if explicit composition cannot preserve
exact Owner source selection, or if a Skill would gain evidence authority.

Evidence: deterministic retrieval fixtures, explicit composition/multi-input
contract if authorized by audit, Review semantic cases, trust-boundary wording,
historical Artifact validators, and four regression locks. Immutable instruction
changes require forward publication.

### R5 — Project / Skill lifecycle and stable navigation

Primary owners: Project and user-Skill services/repositories/routers, Workspace
orphan handling, Project list/navigation, Skills pages, Project Help, Local guide.

Contract: Project title/body always opens Overview. Global Skills always opens
unscoped `/skills`. Skill detail and safe delete remain lightweight. Attached
Skill deletion is rejected; unattached deletion is allowed. Project deletion is
one transactional Cloud-only operation; global Skills and all Local bytes remain
untouched. A deleted Project's old Workspace fails clearly without mutation or
implicit relinking.

Stop if FK ownership cannot support transactional deletion without ad hoc row
surgery, or if any local deletion/remote filesystem action is proposed. Expected
migration count is zero; prove otherwise before writing one.

Evidence: service/API/PostgreSQL cascade inventory, multi-Project Skill use,
attach/detach/delete, Project delete rollback, byte-identical orphan Workspace,
navigation/browser, subtractive screenshots, and ExperimentCapability separation.

### R6 — subtractive Owner UX and information hierarchy

Primary owners: Progress aggregation/projection, Workspace CLI labels, Overview,
Board, Activity, Workflow Detail, Outputs, Artifact presentations, and CSS.

Contract: central role-aware stable labels, central typed output labels, Project-
level sync messaging, active workflows before retired history, explicit workflow
vs report-round status, completed outcomes alongside unresolved evidence, and
idempotent presentation backfill independent of scientific rerun.

Use REMOVE/COLLAPSE/SHORTEN/CENTRALIZE. Stop if a semantic readiness change is
needed; route it back to R1/R2 rather than hiding it with copy. No migrations or
publication changes expected.

Evidence: projection/component tests, responsive screenshots, repository-native
browser on the controlled completed chain, presentation-absent safety, and four
regression locks.

### R7 — full-system qualification

R7 changes no product behavior. It uses real FastAPI, real Next.js, marked
disposable PostgreSQL, a public copied disposable Workspace, system Chrome,
repository-native Playwright, and deterministic controlled providers. It covers
the exact scenarios specified by the Owner program: A→B, zero-paper consumer
precondition, explicit optional omission, natural approvals, clean Harness exit,
pending-sync recovery, Generic Experiment admission, v4→v3→v5, Skill lifecycle,
Cloud-only Project deletion, platform robustness, and subtractive screenshots.

Final gates: full qualified backend/frontend suites, TypeScript, ESLint,
compileall, Next build, diff check, Alembic check, disposable
upgrade/downgrade/re-upgrade, sole head, immutable publication checksums, all
four locks, protected D1 fingerprints, database/process cleanup, clean repository.

## 7. Reusable D1 regression fixture matrix

Fixtures are composable authorities, not shortcuts that bypass production
validators.

| Fixture | Minimal controlled state | Reused by | Core assertions |
|---|---|---|---|
| `repeated_literature` | Two exact Literature instances with distinct IDs and Artifacts | R1, R6, R7 | Stable Cloud/Local labels; no role-key collision; exact selection |
| `multi_candidate_one_role` | Two compatible paper-library candidates for one requirement | R1, R7 | Unique React identity; no auto-select; accepted binding rendered |
| `binding_replace_a_b` | A bound/materialized with valid receipt; Owner accepts B | R1, R2, R7 | Managed A atomically replaced; B exact; A never runnable |
| `unchanged_sibling` | Literature changes A→B while exact Idea is unchanged | R1, R7 | Idea bytes/identity reverified and safely reissued; complete plan valid |
| `ambiguous_local_target` | Target bytes have no matching ReAgent ownership receipt | R1, R7 | Fail closed; bytes untouched |
| `zero_paper_library` | Valid INSUFFICIENT v1 with zero selected papers | R1, R7 | Producer stays valid; Idea readiness blocks before materialization/run |
| `optional_evidence_omitted` | Required Review inputs exact; Idea deliberately omitted | R1, R4, R7 | Explicit continue decision; omitted evidence unavailable/unverified; v3 valid |
| `natural_owner_approval` | Exact checkpoint plus current inputs and causal identity | R2, R3, R7 | Natural Approve produces exact one-use durable record; no SHA echo |
| `interrupted_harness` | Durable checkpoint written before managed process interruption | R2, R3, R7 | Clean cancellation; new session resumes same decisions/phase |
| `pending_terminal_progress` | Valid terminal Artifact/Progress local, Cloud unavailable | R2, R7 | Pending sync survives; replay uploads once without Harness/science rerun |
| `generic_experiment` | Exact Idea, no matching Capability, deterministic sklearn-scale contract | R3, R7 | Generic implementation/provenance, explicit environment/run approval, one v5 |
| `generic_execution_units` | Small manifest with stable units and a mid-run interruption | R3, R7 | Completed checksums reused; resume remaining units only |
| `forward_writing_review_revision` | v4 → limited-scope v3 → 0.7/0.9 v5 | all phases as lock, R7 | Optional Review + subset Revision + exactly-once lifecycle locks |
| `retired_revision_history` | Retired 0.6/0.8 plus active completed 0.7/0.9 | R6, R7 | Active primary; history preserved; counts separated |
| `skill_multi_project_lifecycle` | One Skill attached to Projects A and B | R5, R7 | Detach isolation; delete blocked until zero associations; no Capability authority |
| `project_delete_cloud_only` | Disposable Project with Workflows, Artifacts, Progress, Skill link, copied Workspace | R5, R7 | Transactional Cloud removal; global Skill and Local tree unchanged; orphan fails safely |
| `platform_metadata_matrix` | `.DS_Store`, arbitrary undeclared file, private path metadata, real secret marker | R1, R7 | Benign narrow allowlist; unknown and secret fail; path correctly classified |
| `presentation_backfill` | Exact Artifact present, optional presentation absent | R6, R7 | Artifact remains final; idempotent preview backfill without research rerun |

## 8. Evidence levels and non-substitution rules

| Level | Program use |
|---|---|
| E1 | contracts, validators, deterministic unit tests |
| E2 | services, reporting, components |
| E3 | application orchestration, exact binding, approval, deletion, publication |
| E4 | marked disposable PostgreSQL and migration qualification |
| E5 | public copied disposable Workspace and controlled Harness/provider |
| E6 | repository-native browser against real controlled services |
| E7 | not rerun; real D1 research evidence cannot be substituted by controlled engineering tests |
| E8/E9 | protected D1 recovery/Owner evidence retained as historical fingerprints, never mutated for qualification |

Unit tests cannot substitute for PostgreSQL lifecycle evidence, Local filesystem
ownership cannot be proven by a mocked Cloud response, and browser copy cannot
prove exact Artifact identity. Each phase report must name the evidence level and
the independence limits of its verifier.

## 9. Phase gate and new-defect audit

Before moving to the next phase, record yes/no answers to:

1. Was any exact scientific boundary weakened?
2. Was implicit latest or merge introduced?
3. Was Cloud made authoritative for complete Local bytes?
4. Did a user Skill gain Capability/evaluation authority?
5. Must a completed Workflow rerun to synchronize?
6. Was a new manual Owner orchestration step introduced?
7. Was an immutable publication changed in place?
8. Did any D1 regression lock change?
9. Was a fixture altered to avoid production semantics?
10. Did the UI become more verbose instead of simpler?

Any `yes` stops the phase unless it is the explicit, separately reviewed target
contract and still satisfies the program invariants. Other stop statuses are
`REPAIR_SCOPE_EXPANSION`, `OWNER_DECISION_REQUIRED`, `NEW_PRODUCT_DEFECT`,
`MIGRATION_BLOCKED`, and `HISTORICAL_CONTRACT_CONFLICT`.

## 10. R0 verification result

- Production files changed: **0**.
- Test/fixture files changed: **0**.
- Migrations/publications changed: **0**.
- Owner database writes: **0**.
- Ledger IDs mapped: **52 / 52**, exactly once.
- Required reusable fixture scenarios represented: **18**, including all 12
  minimum R0 scenarios.
- Protected Project fingerprinted read-only: **yes**.
- Four repaired-D1 locks explicitly retained: **yes**.
- R1 entry condition: freeze the narrow R1 change packet from the current source
  and turn the ledger reproductions into failing tests before behavior edits.

R0 status: **PASS_POST_D1_R0_REPAIR_ARCHITECTURE**.
