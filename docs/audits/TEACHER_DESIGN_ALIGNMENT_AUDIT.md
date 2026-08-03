# Teacher Design Alignment Audit

Audit date: 2026-08-03
Scope: read-only architecture and route-correction audit

## 1. Audit Status

**PASS**

The teacher PDF was found, identified, text-extracted, rendered, and inspected
page by page. Repository documentation, history, configuration, implementation,
and user-facing execution paths were inspected. The audit status means the
review completed; it does not mean the implementation is aligned.

## 2. Alignment Verdict

**FUNDAMENTALLY_DIFFERENT_PRODUCT**

For the core audit question, the best-supported choice is **B: a hosted Web
Agent platform in which the cloud/backend itself performs research tasks**.

The repository shares vocabulary and reusable mechanisms with the teacher
design, but its implemented execution model is the opposite of the source's
defining three-part boundary. This is more than incomplete feature coverage:
the current cloud owns live workflow state, schedules steps, executes Skills,
calls providers, writes research artifacts, and resumes work. The teacher
design assigns those concrete activities to an existing local Agent Harness
operating on a downloaded folder, and explicitly says the cloud does not do
them.

## 3. Executive Finding

The teacher described a cloud management-and-supply product: cloud creates and
manages projects, Skills, downloadable workflow folders, Progress Reports, and
an external-API proxy; a local folder carries the complete task state; existing
Claude Code or Codex performs the research. The repository has implemented a
different product: a Next.js interface launches and controls backend-owned
Workflow Runs; FastAPI dispatches a project-owned `AgentRuntime`; PostgreSQL is
the authoritative execution state; backend Skills invoke providers and create
artifacts. They are not the same product. The largest mismatch is the inversion
of research execution and task-state ownership from local folder + external
Harness to cloud backend + PostgreSQL.

This conclusion does not criticize implementation quality. The hosted runtime
is carefully layered and tested. Quality does not make it source-aligned.

## 4. Teacher-source Architecture

### Source identity

- File: `../Background/Meta-Research-Agent-架构.pdf`
- Size: 188,843 bytes
- SHA-256: `fa725dcd5a894f4025a94181e8595226c05d2895ae2f27c6a46c48a2fc5dd23c`
- Pages: 3
- Accessed: 2026-08-03

### Source-supported architecture

Page 1 defines Meta Research Agent as a workflow-standardization system in
which each workflow instance has a local folder containing its prompts, Skills,
memory, and user materials. The user downloads that folder and opens it with
Claude Code or Codex. Page 1 explicitly says cloud manages Skills and project
progress and does not execute concrete research.

Pages 1-2 assign cloud AG Admin, external-Skill normalization, project and
workflow package generation, folder download, Progress Report aggregation,
cross-machine/tool continuity, central credential management, and API proxying.
The local folder holds the complete task state. Page 2 assigns reading,
writing, tool use, user interaction, and actual work to an existing Agent
Harness and says ReAgent does not develop that execution engine.

Page 2 names five independent/composable workflows: Literature Search, Idea
Finding, Writing, Review, and Reproduction/Experiment. Outputs may become the
next workflow's inputs. Pages 2-3 explicitly leave exact folder and prompt
decomposition undecided, while illustrating `AGENT.md`, prompt file(s),
`skills/`, `memory/progress/`, `memory/context.md`, `inputs/`, and `outputs/`.
Page 3's worked journey is cloud creation and download -> local Harness work ->
Progress Report upload -> later continuation with the same or a different
Harness.

The complete requirement mapping is in
`docs/audits/TEACHER_DESIGN_REQUIREMENT_LEDGER.md`.

## 5. Current Repository Architecture

### Implemented execution path

The implemented path is:

```text
Next.js workflow catalog
  -> POST /runs/from-catalog
  -> POST /runs/{id}/resume
  -> FastAPI application services
  -> SyncExecutionDispatcher
  -> backend AgentRuntime.run()
  -> Workflow Engine decision loop
  -> SkillExecutor
  -> research Skills
  -> OpenAlex/fake/synthetic providers
  -> PostgreSQL workflow/checkpoint/memory/event/provider state
  -> local server artifact storage
  -> artifact/event/provider-usage APIs
  -> browser run ledger and artifact viewer
```

Evidence:

- `frontend/api/hooks.ts:63-69` creates a catalog run and immediately resumes
  it.
- `frontend/components/workflow-catalog.tsx:121-189` describes and presents
  “Create & execute run.”
- `backend/api/routers/runs.py:111-117` exposes the resume command.
- `backend/application/execution/dispatcher.py:27-36` invokes `AgentRuntime`
  inline in the API caller's process.
- `backend/agent_runtime/runtime/agent_runtime.py:102-216` restores/starts the
  run, loops over Workflow Engine decisions, and executes ready steps.
- `backend/agent_runtime/runtime/agent_runtime.py:437-506` calls
  `SkillExecutor`, stores emitted artifacts, updates memory, checkpoints, and
  commits.
- `backend/research/skills.py:668-691` calls the configured paper-search
  provider inside a backend Skill.
- `backend/research/adapters/openalex.py:243-319` performs `/rate-limit` and
  `/works` requests from the provider adapter.
- `backend/api/composition.py:250-293` selects OpenAlex and reads its key from
  backend environment configuration.

### Where research execution occurs

Concrete task execution occurs inside the backend process. `AgentRuntime`
chooses/handles Workflow Engine decisions and invokes `SkillExecutor`.
Research Skills invoke paper search, source retrieval, fake/synthetic LLMs, and
artifact persistence. A future activated structured LLM would also be called
from the server-side Skill path through `StructuredGenerationProvider`.

### Current state authority

PostgreSQL is the authoritative live execution state:

- ADR 0001 lines 15 and 23 explicitly designate PostgreSQL and reject a context
  file as lifecycle authority.
- `backend/database/orm/models.py` stores Workflow Runs, Agent Sessions, Step
  Runs, checkpoints, memory revisions, approvals, events, artifacts, and
  ProviderOperations.
- `AgentRuntime.run()` reconstructs execution by run ID from repositories and
  requires persisted checkpoints.

The local filesystem artifact adapter stores immutable bytes under a server
root. Those bytes do not contain a complete runnable workflow folder, and they
cannot restore the task without PostgreSQL. `.agent_read/` is explicitly a
developer-governance handoff layer, not product runtime memory
(`docs/engineering/AGENT_CONTEXT_AND_GIT_POLICY.md:5-8`).

State types must be kept distinct:

| State type | Current repository | Teacher-aligned role |
|---|---|---|
| Cloud project state | Mostly opaque `project_id` values plus hosted runs; no Project CRUD/material-upload model | Project identity, workflow/package selection, uploaded progress, and unified progress view |
| Local task state | No generated product folder | Complete active research state read/written by the Harness |
| Developer repository state | `.agent_read/context.md`, ADRs, progress handoffs | Development governance only; never product task memory |
| Runtime acceptance artifacts | Ignored `runtime_data/` databases/artifacts/evidence | Private engineering evidence; never the user's portable workflow folder |

### User and Harness behavior

The user does not have to download a folder. Claude Code/Codex is not required
to execute a product workflow. Browser actions create, resume, approve, reject,
inspect, and download individual artifacts from hosted execution. No generated
folder can independently resume work, and switching Agent Harnesses is not a
product feature.

## 6. Alignment Matrix

### Major current components

Each component has exactly one primary source-alignment category.

| Current component | Repository role | Primary category | Basis |
|---|---|---|---|
| Versioned Workflow definitions | Immutable static DAGs and pinned Skill refs | ALIGNED_SUPPORTING | Versioning can support source-defined templates, but current definitions are server-execution plans. |
| Domain Core | Hosted execution lifecycle and state transitions | ALIGNED_SUPPORTING | Typed project/workflow metadata is reusable; detailed hosted execution lifecycle is not source-required. |
| Workflow Engine | Schedules and advances server-side steps | MATERIAL_CONTRADICTION | It performs orchestration the PDF assigns to the external Harness. |
| AgentRuntime | Backend execution loop, memory/checkpoints/approval/Skill calls | MATERIAL_CONTRADICTION | It is a project-developed Agent Harness replacement. |
| Skill models/schemas | Immutable typed Skill contracts | ALIGNED_SUPPORTING | Normalization/version concepts support AG Admin and packaging. |
| In-process Skill Registry/Executor | Code-level registration and hosted invocation | PREMATURE_OR_OUT_OF_SCOPE | No operator management/import/package path; execution is hosted. |
| PostgreSQL repositories | Authoritative hosted run/session/step state | MATERIAL_CONTRADICTION | PDF makes local folder files the complete task state. |
| Checkpoints/memory revisions | Server resume state | MATERIAL_CONTRADICTION | Not local folder memory or uploaded Progress Reports. |
| Execution events | Hosted execution audit stream | PREMATURE_OR_OUT_OF_SCOPE | Useful for optional hosted mode, not the required progress round-trip. |
| Approval system | Hosted execution gate that resumes backend work | PREMATURE_OR_OUT_OF_SCOPE | Source does not define cloud approval inside local task execution. |
| Artifact storage/API | Server-owned output bytes and viewer downloads | ALIGNED_SUPPORTING | Storage can serve templates/packages/progress, but current artifacts are hosted execution outputs. |
| FastAPI | Hosted run and query API | ALIGNED_SUPPORTING | Cloud API is required, but routes need management/package/progress/proxy roles. |
| Next.js frontend | Workflow launch, hosted run ledger, approval desk | ALIGNED_SUPPORTING | Web cloud management is source-required; execution UI is the wrong emphasis. |
| OpenAlex adapter | Backend Skill directly performs literature search | MATERIAL_CONTRADICTION | Can back a proxy, but direct hosted research execution violates TMR-004/TMR-008. |
| ProviderOperation | Server provider reservation/settlement/accounting | ALIGNED_SUPPORTING | Strong basis for a true cloud proxy ledger. |
| Grounded report contracts/validators | Typed summaries/evidence/claims/report/provenance | ALIGNED_SUPPORTING | Reusable as delivered local Skills/contracts and deterministic validation. |
| Anthropic adapter substrate | Future backend hosted LLM generation | PREMATURE_OR_OUT_OF_SCOPE | Inactive today; activation would deepen the wrong initial execution route. |
| Automated evaluation/Judge module | Evaluation-side fake/multilingual/judge substrate | PREMATURE_OR_OUT_OF_SCOPE | Not in the teacher's initial product responsibilities. |
| Folder generation/download | Not implemented | MISSING_REQUIRED | Explicit teacher cloud responsibility. |
| Progress Report round-trip | Not implemented | MISSING_REQUIRED | Events/checkpoints do not substitute for report upload/history. |
| AG Admin/import/conversion | Not implemented | MISSING_REQUIRED | Code-level registry is not an operator Skill library. |
| External Agent Harness compatibility | Not implemented as product capability | MISSING_REQUIRED | Repository-level `AGENTS.md` does not satisfy an end-user folder contract. |
| Project management/material upload | Only arbitrary project/actor IDs on run creation | MISSING_REQUIRED | No Project aggregate, project CRUD, material-upload flow, or project package view exists. |

### Three-part boundary audit

| Part | Teacher responsibility | Current implementation | Finding |
|---|---|---|---|
| Cloud | Manage/supply Skills, projects, packages, progress, credentials, and proxy; no concrete research execution | Owns catalog, authoritative run state, scheduler/runtime, Skills, direct providers, approvals, artifacts, and execution UI | MATERIAL_CONTRADICTION |
| Local folder | Complete task state and location where research occurs | No generated/downloadable self-contained folder; only server artifact bytes and developer repository state | MISSING_REQUIRED plus authority inversion |
| Agent Harness | Existing Claude Code/Codex reads/writes files, calls tools, interacts, and performs work | Not part of product execution; backend `AgentRuntime` performs those responsibilities | MATERIAL_CONTRADICTION |

### Five-workflow audit

The PDF defines the workflow taxonomy but does not choose which workflow must be
implemented first.

| Workflow | Source purpose | Repository status | Cloud management | Folder template | Harness instructions/Skill package | Handoff/progress | Actual execution | Primary category |
|---|---|---|---|---|---|---|---|---|
| Literature Search | Search and produce a literature collection | Three hosted `guided-literature-review` versions; fake/synthetic and supervised OpenAlex paths | Catalog/run UI exists | Absent | Absent | Corpus artifacts exist, but no folder/progress round-trip | Backend AgentRuntime | MATERIAL_CONTRADICTION |
| Idea Finding | Find scientific questions/ideas | No first-class workflow implementation; only deferred downstream references | Absent | Absent | Absent | No literature-output-to-Idea-folder handoff | None | MISSING_REQUIRED |
| Writing | Produce research writing | No first-class workflow | Absent | Absent | Absent | No Idea-output-to-Writing-input handoff | None | MISSING_REQUIRED |
| Review | Review a paper/output | Human approval/evaluation features are not the source-defined Review workflow | Absent | Absent | Absent | None | None | MISSING_REQUIRED |
| Reproduction/Experiment | Reproduce work and run experiments | No first-class workflow | Absent | Absent | Absent | None | None | MISSING_REQUIRED |

## 7. Critical Contradictions

### 7.1 Cloud performs concrete research

`POST /runs/{id}/resume`, `POST /approvals/{id}/approve`, and, for an approved
rejection path, approval handling dispatch backend execution. The browser's
create flow automatically calls resume. This violates TMR-004.

Exact execution-causing endpoints:

- `POST /runs/{workflow_run_id}/resume`
- `POST /approvals/{approval_id}/approve`
- `POST /approvals/{approval_id}/reject` also dispatches the runtime to apply
  terminal behavior after staging the decision

`POST /runs/from-catalog` creates durable state but does not itself execute;
the current frontend immediately follows it with resume.

### 7.2 Project-owned AgentRuntime replaces the external Harness

The runtime reads authoritative state, schedules, executes Skills, handles
approval/retry, writes outputs, and commits memory/checkpoints. This is the
functional role the source assigns to Claude Code/Codex. It cannot be called a
neutral management service without changing what it does.

Source-aligned reclassification:

- deterministic Workflow validation/reference resolution can support package
  validation;
- the execution loop can remain an internal test tool or optional future hosted
  mode;
- it must not be the default initial V1 executor.

### 7.3 PostgreSQL replaces the local folder as task-state authority

ADR 0001 explicitly chose PostgreSQL and rejected file-only state. That accepted
ADR conflicts with TMR-009 and is lower authority in this audit. PostgreSQL may
remain authoritative for cloud project metadata, package versions, Skill
catalog, Progress Report history, proxy usage, and uploaded snapshots. It must
not be the sole authoritative state of active local research if V1 follows the
teacher design.

### 7.4 Browser Resume is a research-execution command

The frontend says it “creates the durable run, submits execution” and offers
“Create & execute run.” A source-aligned cloud UI would create/package/download
and later collect progress; it would not start the research agent in cloud.

### 7.5 Direct backend providers are operations, not proxy service

OpenAlex is invoked by a backend research Skill as part of hosted workflow
execution. Central key storage is directionally aligned, but the local Harness
does not call a cloud provider proxy and receive normalized results. Provider
ports and ProviderOperation can be reframed into a true proxy boundary.

## 8. Missing Core Capabilities

Ranked by source criticality:

1. **CRITICAL — workflow folder generation and archive download** (TMR-002,
   TMR-006, TMR-018).
2. **CRITICAL — external Claude Code/Codex execution contract and compatibility
   evidence** (TMR-003, TMR-010, TMR-015).
3. **CRITICAL — local task-state/memory contract sufficient for independent
   continuation** (TMR-009, TMR-016).
4. **HIGH — Progress Report schema, upload, validation, history, aggregation,
   and folder/context update** (TMR-007, TMR-016, TMR-018).
5. **HIGH — cloud Project creation/management and material upload**, rather
   than accepting an arbitrary `project_id` only (TMR-006, TMR-018).
6. **HIGH — AG Admin, normalized external Skill import/conversion, versioning,
   review, and package delivery** (TMR-005, TMR-006).
7. **HIGH — cloud external-API proxy callable by local Harness without exposing
   credentials** (TMR-008).
8. **HIGH — workflow-to-workflow output/input handoff** (TMR-012, TMR-017).
9. **MEDIUM — first-class representation/templates for Idea, Writing, Review,
   and Reproduction/Experiment** (TMR-011). Initial implementation order is a
   source gap.
10. **MEDIUM — folder re-download/update and cross-machine/cross-harness conflict
   handling** (TMR-007, TMR-016, TMR-018).

Folder capability status: **absent**, not partial. Documentation mentions a
workspace-shaped structure in the derived development plan, but no product
implementation writes or packages it.

Progress round-trip status: **absent**. Current events/checkpoints represent
cloud runtime internals, not a local Harness-produced report.

## 9. Premature or Additional Features

Most hosted assumptions first appear together in commit `469beeb` on
2026-07-21, particularly `docs/PROJECT_DEVELOPMENT_PLAN.md`,
`.agent_read/progress/architecture_analysis.md`, the architecture contract, ADR
0001, and the initial backend/frontend implementation. The repository has no
earlier teacher-aligned product implementation; the initial Git commit contains
only README/LICENSE.

| Added assumption | First clear repository evidence | Teacher support | Owner/ADR status | Assessment | Initial-V1 disposition |
|---|---|---|---|---|---|
| Cloud-hosted AgentRuntime | Development plan and architecture analysis; ADR 0001 | Explicitly contradicted | ADR 0001 Accepted | Responsibility inversion | Disable from initial V1; preserve internally |
| Server-side Workflow execution | Architecture analysis/contract and ADR 0001 | Explicitly contradicted as concrete task execution | Accepted with ADR 0001 | Responsibility inversion | Keep validator; internalize executor |
| PostgreSQL live task authority | Architecture analysis lines 278-288; ADR 0001 lines 15, 23, 33 | Explicitly contradicted | Accepted | Responsibility inversion | Reframe DB around cloud metadata/progress/proxy |
| Browser Resume triggers research | Phase 7/8 implementation, commit `469beeb` | Not supported | Implemented under accepted architecture | Contradictory UX | Disable from initial V1 |
| Hosted Agent Session | ADR 0001/domain model | Not source-defined; source uses Harness sessions | Accepted | Misleading/premature | Optional hosted mode only |
| Full hosted web vertical slice | FastAPI/Next.js/PostgreSQL demo | Cloud UI supported, hosted execution not | Implemented | Mixed | Preserve UI/platform, replace initial journey |
| Event timeline as execution UI | Phase 7B/8A | Source requires progress view, not live server events | Implemented | Premature | Reframe as Progress Report timeline |
| Hosted approval gates | AgentRuntime/API/frontend approval desk | Source silent | Implemented | Premature | Defer or reframe for package/proxy approvals |
| Direct server-side OpenAlex research | ADR 0004 and OpenAlex implementation | Source supports cloud API proxy, not cloud research execution | ADR 0004 Accepted for hosted boundary | Contradictory in current role | Reframe adapter behind proxy |
| ProviderOperation accounting | Phase 9A | Supports central proxy accounting | Accepted substrate | Neutral/supporting | Preserve and reframe |
| Hosted grounded-report generation | ADR 0007/V3; ADR 0008 proposal | Contradictory if cloud executes it | ADR 0007 limited synthetic accepted; ADR 0008 Proposed | Premature/optional | Stop activation; package as local Skill candidate |
| Queue/worker planning | Architecture analysis/contract | Source silent | Planning assumption | Premature | Defer |
| Hosted artifact viewer | Phase 8/9 | Cloud progress/output view can be supporting | Implemented | Neutral if reframed | Keep for uploaded outputs/packages |
| Automated Judge/evaluation module | ADRs 0005/0006 | Not source-defined | Limited/deferred | Premature | Defer |

Academic Research Skills should be treated as methodology/reference evidence,
an external Skill source, and an import/conversion candidate for AG Admin. Its
repositories should not automatically become cloud-hosted business logic. The
current influence map also records licensing constraints that require review
before packaging.

## 10. Reusable Infrastructure

This audit recommends no deletion. Minimal source-aligned treatment:

| Subsystem | Treatment | Source-aligned reuse |
|---|---|---|
| Domain Core | KEEP_BUT_REFRAME | Cloud Project, workflow-package identity, Skill/package versions, Progress Report metadata, proxy operations |
| Workflow definitions | KEEP_BUT_REFRAME | Template/package manifests and dependency/handoff validation |
| Workflow Engine | KEEP_AS_INTERNAL_TEST_TOOL | Validate ordered workflow package and test deterministic local contracts; do not execute cloud V1 research |
| AgentRuntime | DISABLE_FROM_INITIAL_V1 | Preserve for tests/optional hosted mode only |
| Skill Registry | KEEP_BUT_REFRAME | Basis for normalized Skill catalog, import validation, and packaging |
| Provider ports | KEEP_BUT_REFRAME | Internal proxy adapters and normalized provider result contracts |
| ProviderOperation | KEEP_BUT_REFRAME | Proxy request idempotency, usage, cost, and audit ledger |
| PostgreSQL repositories | KEEP_BUT_REFRAME | Cloud project/package/progress/proxy authority; not local task authority |
| Execution Events | KEEP_AS_OPTIONAL_FUTURE_MODE | Preserve hosted trace; build separate Progress Report history |
| Approval system | NEEDS_OWNER_DECISION | Could approve packages/proxy scopes; hosted step approval is out of V1 |
| Artifact storage | KEEP_BUT_REFRAME | Store templates, Skill packages, uploaded reports/output snapshots, downloadable archives |
| FastAPI | KEEP_BUT_REFRAME | AG Admin, projects, folder package/download, progress upload, API proxy |
| Next.js frontend | KEEP_BUT_REFRAME | Project/Skill management, package download, progress view, continuation UI |
| OpenAlex adapter | KEEP_BUT_REFRAME | Cloud proxy provider behind a local-Harness-facing route |
| Grounded-report contracts | KEEP_BUT_REFRAME | Deliverable local Skill/prompt schemas and deterministic validators |
| Hosted LLM adapter substrate | DEFER | Optional hosted mode or proxy only after source-aligned V1 and owner decision |
| Optional evaluation module | DEFER | Not initial source scope |
| Docker/Compose | KEEP_BUT_REFRAME | Cloud management/proxy development environment |
| Current tests | KEEP_BUT_REFRAME | Preserve regression value; add folder/harness/progress/proxy alignment tests |

### Terminology audit

| Term | Precise source-aligned meaning | Current ambiguity / recommended usage |
|---|---|---|
| Agent Harness | Existing Claude Code, Codex, or equivalent that performs the task | Do not use `AgentRuntime` as a synonym. |
| Agent Runtime | Current project-owned hosted orchestration/execution subsystem | Call it “hosted execution runtime” when discussing preserved optional work. |
| Cloud execution | Cloud directly schedules/executes research steps | Explicitly mark as optional/out-of-initial-V1, not teacher cloud behavior. |
| Workflow instance | One portable local task folder plus its cloud management identity | Current `WorkflowRun` is a hosted execution record, not this source concept. |
| Workflow Run | Current database-backed server execution aggregate | Qualify as “hosted Workflow Run.” Do not claim it is the teacher's folder instance. |
| Agent Session | Current DB record attached to a hosted run | Not a Claude Code/Codex conversation session and not portable folder memory. |
| Memory | In the source, task files such as compressed context and per-round progress | Current DB memory revisions are hosted-runtime memory; `.agent_read` is developer memory. |
| Checkpoint | Internal hosted execution recovery state | Not a Progress Report and not sufficient for cross-Harness continuation. |
| Progress Report | Harness-produced per-round file uploaded to cloud and retained in history | No implemented equivalent; execution events must not be renamed to imply equivalence. |
| Skill | Portable normalized capability deliverable managed by cloud and usable locally | Current Python implementation registration is only one hosted implementation form. |
| Local folder | Downloaded, self-contained workflow-instance state opened by a Harness | Not the Git repository, server artifact root, or acceptance `runtime_data/`. |
| Project state | Cloud management/progress/package metadata | Must be distinguished from authoritative local task execution state. |
| Execution state | Files in the local folder that let a Harness continue the task | Current PostgreSQL lifecycle state belongs specifically to optional hosted execution. |

## 11. Phase 9C Review

### Direct decisions

1. **Should Phase 9C-2B hosted provider activation stop? — Yes.** It should
   receive no further implementation or execution work before owner realignment
   review. Cloud-hosted report generation would deepen TMR-004/TMR-010 conflict.
2. **Can grounded-report contracts become files/Skills delivered to local
   Codex/Claude Code? — Yes.** Summary/evidence/claim/report schemas, prompts,
   citation labels, provenance rules, and abstract-only disclosures are strong
   candidates for a packaged Literature Search Skill.
3. **Can provenance validators remain cloud-side or folder-side deterministic
   tooling? — Yes, with role clarity.** Folder-side validation can run under the
   Harness; cloud-side validation may verify uploaded outputs/Progress Reports.
   Cloud validation must not silently become cloud generation.
4. **Should Anthropic API-key planning be deferred? — Hosted generation key
   planning should be deferred.** A future cloud proxy credential policy remains
   source-relevant, but its endpoint, payload, user authorization, and local
   Harness protocol require a new owner decision.
5. **What should be retained?** Immutable V3 workflow semantics as reference,
   grounded data contracts, prompt registry, citation/provenance validators,
   artifact schemas, provider ports, ProviderOperation accounting, synthetic
   fixtures, failure tests, and inactive adapter mapping.

### Classification

- V3 as backend-executed workflow: **optional hosted mode and contradictory as
  initial V1**.
- StructuredGenerationProvider: **reusable proxy/local Skill boundary**.
- Anthropic substrate: **inactive optional future work; premature to activate**.
- Phase 9C-2A package: **useful security/cost evidence, but premised on hosted
  execution and therefore not execution authority for the source-faithful V1**.
- ADR 0007: **accepted lower-authority synthetic work; retain without extending**.
- ADR 0008: **Proposed; do not approve on the current hosted route before
  realignment**.

No ADR status is changed by this audit.

## 12. Source-faithful Initial V1

### Cloud V1

- **SOURCE_REQUIRED:** create/manage projects and workflow selections.
- **SOURCE_REQUIRED:** AG Admin Skill catalog with normalized ingestion of
  internal/external Skills.
- **SOURCE_REQUIRED:** generate and deliver a downloadable local workflow
  folder with pinned prompts, Skills, identity, and version information.
- **SOURCE_REQUIRED:** accept, validate, retain, and display Progress Reports
  associated with project/workflow instances.
- **SOURCE_REQUIRED:** centrally hold external API credentials and expose a
  proxy callable by local execution.
- **SOURCE_SUPPORTING:** use PostgreSQL for project/package/report/proxy metadata,
  checksums, histories, and access policy.
- **OWNER_DECISION_REQUIRED:** user/auth model, exact Skill review policy,
  archive format, proxy authentication, quotas, and retention.

Cloud V1 does not execute research Skills or LLM report generation.

### Local Folder V1

- **SOURCE_REQUIRED:** one folder per workflow instance and files sufficient to
  know the task, current state, inputs, and outputs.
- **SOURCE_REQUIRED:** harness-readable start/finish instructions, local memory,
  per-round Progress Reports, user inputs, generated outputs, and packaged
  Skills/prompts.
- **SOURCE_SUPPORTING:** a checksum/version manifest and explicit project/
  workflow identity.
- **OWNER_DECISION_REQUIRED:** exact tree, file formats, prompt decomposition,
  report schema, and update/merge behavior.

The PDF's sample tree is an experiment starting point, not a frozen schema.

### Harness V1

- **SOURCE_REQUIRED:** Claude Code or Codex opens the folder, follows the entry
  instructions, reads/writes files, invokes tools/proxy, interacts with the
  user, and produces outputs plus a Progress Report.
- **SOURCE_SUPPORTING:** compatibility checks using both Harnesses against the
  same synthetic folder fixture.
- **OWNER_DECISION_REQUIRED:** first supported Harness, minimum compatible
  instruction dialect, and whether both are blocking for the first demo.

### Workflow V1

- **SOURCE_REQUIRED:** represent the five-workflow taxonomy and allow independent
  or chained use.
- **SOURCE_SUPPORTING:** implement one folder-based workflow as the first proof,
  while retaining an explicit handoff manifest for later composition.
- **OWNER_DECISION_REQUIRED:** which workflow is first. Literature Search is a
  repository-informed candidate, not a PDF-mandated priority.

### Progress round-trip

- **SOURCE_REQUIRED:** Harness writes a Progress Report in the folder; an upload
  mechanism associates it with the exact project/workflow; cloud shows history
  and latest progress; a regenerated/updated folder enables later continuation.
- **OWNER_DECISION_REQUIRED:** upload automation, schema, conflict handling,
  report signing, and whether outputs are uploaded or only referenced.

### External API proxy

- **SOURCE_REQUIRED:** local Harness calls cloud; cloud injects provider
  credentials, enforces policy, records usage, and returns normalized results;
  the folder never contains the key.
- **SOURCE_SUPPORTING:** reuse provider ports and ProviderOperation.
- **OWNER_DECISION_REQUIRED:** first provider, endpoint shape, caller auth,
  content retention, rate/cost limits, and whether LLM proxying is in the first
  demo.

### Source-faithful user journey

1. User creates a cloud project, uploads inputs, and selects a workflow.
2. Cloud resolves a template and pinned Skills and generates a local package.
3. User downloads/unpacks it and opens it in Claude Code or Codex.
4. Harness reads the entry instructions/memory, performs work locally, and uses
   cloud proxy endpoints when external APIs are needed.
5. Harness writes outputs, updates context, and creates a Progress Report.
6. Report is uploaded and appears in the cloud project's unified progress view.
7. A later session or another Harness reopens the folder or a refreshed package
   and continues from file state.

## 13. Realignment Plan

Dependency-ordered summary; the detailed plan is in
`docs/audits/TEACHER_DESIGN_REALIGNMENT_PLAN.md`.

1. Freeze Phase 9C-2B, real hosted LLM work, new hosted research endpoints,
   automated Judge work, and further hosted Runtime UX (TMR-004, TMR-010).
2. Preserve all current code and evidence; make no deletion decision during
   route correction (TMR-001, TMR-008).
3. Owner reviews the authority conflict between the PDF and ADR 0001/current
   plan; subsequent governance work must explicitly supersede rather than
   silently rewrite accepted decisions (TMR-003, TMR-009, TMR-010).
4. Define an experimental local folder contract without claiming the PDF fixed
   its exact shape (TMR-002, TMR-013-TMR-017).
5. Build one cloud package-generation/download vertical slice for one owner-
   selected workflow (TMR-006, TMR-011).
6. Prove Claude Code/Codex can execute the synthetic package without backend
   AgentRuntime (TMR-010, TMR-015-TMR-018).
7. Add Progress Report upload/history and regenerated-folder continuation
   (TMR-007, TMR-016, TMR-018).
8. Reframe OpenAlex/ProviderOperation as a true local-Harness-facing proxy
   (TMR-008).
9. Build AG Admin/import/conversion and then expand workflow packages/handoffs
   according to owner priority (TMR-005, TMR-011, TMR-012).

## 14. Owner/Teacher Decisions

The PDF explicitly leaves these unresolved or does not decide them:

- exact local folder tree and file naming;
- prompt decomposition and number of prompt files;
- normalized Skill format and import/conversion review process;
- first workflow implementation priority;
- whether one or both of Claude Code/Codex block initial acceptance;
- Progress Report schema, upload automation, and conflict resolution;
- folder update/re-download and cross-machine merge semantics;
- workflow handoff schema and copy/link behavior;
- proxy protocol, authentication, provider priority, quotas, retention, and
  response format;
- cloud authentication/authorization and deployment scale;
- whether any hosted execution mode exists after the initial source-faithful
  product;
- whether grounded-report generation is a local Skill, proxy-assisted Skill,
  or deferred capability.

These decisions must not default to the existing hosted architecture merely
because it is implemented.

## 15. Evidence and Limitations

### Source facts

Source facts are statements directly supported by PDF pages 1-3 and are mapped
to stable TMR IDs in the ledger. The source is short and deliberately leaves
folder/prompt details open.

### Repository facts

Repository facts come from actual code/configuration/history, especially:

- `docs/PROJECT_DEVELOPMENT_PLAN.md`
- `.agent_read/decisions/0001-foundational-architecture.md`
- `backend/api/routers/`
- `backend/api/composition.py`
- `backend/application/execution/dispatcher.py`
- `backend/agent_runtime/runtime/agent_runtime.py`
- `backend/skill_system/`
- `backend/database/orm/models.py`
- `backend/research/skills.py`
- `backend/research/grounded_skills.py`
- `backend/research/adapters/openalex.py`
- `frontend/api/hooks.ts`
- `frontend/components/workflow-catalog.tsx`
- `demo/workflows/`

Documentation describing future work was not counted as implementation.
Searches found no folder/archive generator, AG Admin/import pipeline, Progress
Report upload route, or local-Harness API proxy.

### Inferences

“AgentRuntime acts as a new Agent Harness” is an architectural inference from
its implemented responsibilities, not a class-name comparison. “Fundamentally
different product” is the audit verdict produced by comparing those
responsibilities with the PDF's explicit prohibition.

Runtime tests were not required and were not run. No provider was called. No
secret was read. No production source, existing document, ADR status,
dependency, or `.agent_read/context.md` content was modified by this audit.
