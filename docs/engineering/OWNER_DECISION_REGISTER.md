# Owner decision register

Status: ratified by explicit Owner authority on 2026-08-14

Last repository review: 2026-08-14

Allowed statuses are `PROPOSED`, `ACCEPTED`, `DEFERRED`, `BLOCKED`, and
`SUPERSEDED`. Changing a status to `ACCEPTED` requires explicit owner approval.
When an accepted decision is architectural, record or supersede an ADR under
the repository ADR convention; this register does not replace accepted ADRs.

## Entry schema

Each entry contains:

`decision_id`, `title`, `status`, `owner_authority`,
`current_repository_evidence`, `proposed_decision`, `alternatives`,
`affected_contracts`, `migration_or_versioning_impact`, `frontend_impact`,
`testing_impact`, `security_impact`, `blocking_scope`, and `review_date`.

## Ratified decisions

The ratifying Owner prompt is the authority for every `ACCEPTED` status below.
Limitations are recorded as scope and deferral, not as a separate status.

| ID | Title | Status | Owner authority | Current repository evidence | Accepted scope, deferred details, and future trigger | Alternatives |
|---|---|---|---|---|---|---|
| ODR-001 | Do not persist `REAL_CORE` yet | ACCEPTED | Explicit Owner ratification | `CoreCapabilityMaturity` currently has only `REVIEWED_CORE` and `SCAFFOLD_CORE`; API/frontend mirror them | **Scope:** `REAL_CORE` remains planning language only. **Deferred:** none. **Trigger:** any proposal to persist or expose a new maturity value. | Add `REAL_CORE`; rename `REVIEWED_CORE`; derive maturity from capability sets |
| ODR-002 | Preserve Artifact v1 contracts | ACCEPTED | Explicit Owner ratification | ADR 0030 and published Artifact contracts are immutable; v1 lacks some real-core evidence fields | **Scope:** published v1 contracts remain immutable; incompatible capability cannot mutate v1. **Deferred:** v2 versus companion per Core. **Trigger:** S1/E1/W1/R1 contract design. | Expand v1 in place; overload unstructured fields; create one universal Artifact |
| ODR-003 | Narrow first Real Experiment mode | ACCEPTED | Explicit Owner ratification | Experiment is currently a non-executing scaffold; Resource is metadata/local resolution only | **Scope:** bounded local execution; no scheduler, Cloud executor, or hosted expansion. **Deferred:** command, sandbox, runtimes, budgets, cancellation, logs, checkpoints, Resource resolution. **Trigger:** E1. | General scheduler; hosted executor; notebook-only informal execution |
| ODR-004 | Experiment network off by default | ACCEPTED | Explicit Owner ratification | Controlled mode rejects live Provider access; GitHub/Hugging Face resolvers are metadata-only; Codex itself has no OS egress sandbox | **Scope:** network disabled by default. **Deferred:** network-enabled model. **Trigger:** separately approved security contract and explicit Owner authorization. | Always offline; always online; inherit arbitrary Harness network configuration |
| ODR-005 | Writing starts with evidence-bound initial drafting | ACCEPTED | Explicit Owner ratification | Writing 0.4 is scaffold-only; reusable grounded evidence contracts exist only in preserved hosted code | **Scope:** W1 is evidence-bound initial drafting. **Deferred:** revision intelligence. **Trigger:** W2 after its prerequisites. | Initial and revision together; prose-only v1; hosted writing |
| ODR-006 | Review starts as bounded evidence audit | ACCEPTED | Explicit Owner ratification | Review 0.4 is scaffold-only and exact-input-bound | **Scope:** bounded evidence audit and structured revision guidance. **Deferred:** final recommendation model. **Trigger:** R1 contract design. | Full peer-review simulation; acceptance predictor; free-form comments only |
| ODR-007 | No acceptance prediction or scores | ACCEPTED | Explicit Owner ratification | `review-report/v1` excludes scores/probabilities but permits `REVISION`, `ACCEPT_CURRENT_DRAFT`, and `INSUFFICIENT_EVIDENCE` | **Scope:** no accept/reject prediction, probability, venue recommendation, numeric scientific score, unsupported confidence, or peer-review-validity claim. Historical values remain immutable and `ACCEPT_CURRENT_DRAFT` is not publication acceptance. **Deferred:** future recommendation model. **Trigger:** R1. | Keep draft-level compatibility values; design a new bounded model later |
| ODR-008 | Revision identifies causal Review Artifact | ACCEPTED | Explicit Owner ratification | Current manuscript source map can carry exact `review_feedback`; cross-object validator does not independently prove the supplied review payload's Artifact identity | **Scope:** every revised manuscript identifies the causal Review Artifact. **Deferred:** exact schema location. **Trigger:** W2. | Rely only on Workspace binding; infer latest Review; use free-text provenance |
| ODR-009 | Cloud remains Artifact-metadata-only | ACCEPTED | Explicit Owner ratification | Accepted ADRs 0022/0026 and current APIs store metadata/provenance, not general bytes | **Scope:** current architecture stores general Artifact bytes locally and metadata in Cloud. **Deferred:** alternate storage model. **Trigger:** separately approved contract change. | General byte upload; encrypted Workspace backup; per-Artifact optional storage |
| ODR-010 | Browser never writes Workspace | ACCEPTED | Explicit Owner ratification | Accepted architecture and current browser/API split already enforce this | **Scope:** browser operations never directly mutate Local Workspace bytes. **Deferred:** none. **Trigger:** any proposed browser/local bridge. | Browser filesystem bridge; local helper invoked by browser; hosted execution |
| ODR-011 | Frontend IA is task-first | ACCEPTED | Explicit Owner ratification | Current UI derives next actions but exposes maturity/manifest/install/readiness terms; early IA is stale | **Scope:** primary UX is task/action-first; Capsule, manifest, requirement-key, installation, and readiness taxonomy move to technical details where possible. **Deferred:** concrete redesign. **Trigger:** UX-A1/UI-P0/FE-M. | Taxonomy-first admin UI; hide all provenance; separate operator product |
| ODR-012 | Codex qualified; Claude experimental | ACCEPTED | Explicit Owner ratification | Codex has PTY/real completion evidence; Claude Code is named but untested | **Scope:** support claims name Codex as qualified. **Deferred:** Claude qualification. **Trigger:** equivalent separate qualification. | Require both; remove Claude references; allow any executable without qualification |
| ODR-013 | Loopback single-user remains current deployment | ACCEPTED | Explicit Owner ratification | Deployment profile and owner runtime enforce loopback; no user/tenant authorization exists | **Scope:** loopback, single owner, trusted local machine. **Deferred:** network/multi-user deployment. **Trigger:** authentication, authorization, tenancy, secrets, and audit design. | Add authenticated multi-user now; local desktop packaging; private shared service |
| ODR-014 | Hosted Runtime is compatibility-only | ACCEPTED | Explicit Owner ratification | ADR 0009 freezes hosted product development while preserving code/routes/tables | **Scope:** frozen hosted runtime receives no new capability. **Deferred:** any future disposition. **Trigger:** explicit superseding Owner contract. | Delete it; reactivate it; maintain full feature parity |
| ODR-015 | Experiment 0.4 remains frozen non-blocking debt | ACCEPTED | Explicit Owner ratification | Synthetic recovery documents say PASS; owner long-lived state remains `LOCAL_PROGRESS_INVALID` | **Scope:** `KNOWN_LEGACY_ISSUE`, `FROZEN`, `NON_BLOCKING`; do not inspect, repair, rerun, retire, delete, or reinterpret owner state. **Deferred:** none in the active sequence. **Trigger:** explicit superseding Owner authorization only. | Continue forensic repair; manual mutation; retire/rerun owner execution |
| ODR-016 | Writing #2 owner UX evidence gates final Writing/Review contracts | ACCEPTED | Explicit Owner ratification | Instructions and synthetic/controlled qualification exist; no completed owner observation record exists | **Scope:** owner UX evidence gates final Real Writing, Real Review, and revision contracts; H2A is not blocked. **Deferred:** closure. **Trigger:** bounded owner evidence records the Writing #2 outcome. | Treat synthetic chain as UX acceptance; proceed without revision UX; defer revision indefinitely |

## Impact register

| ID | Affected contracts | Migration/versioning impact | Frontend impact | Testing impact | Security impact | Blocking scope | Review date |
|---|---|---|---|---|---|---|---|
| ODR-001 | Workflow Definition maturity, API DTOs, frontend unions | None while unchanged; new enum would require schema/data/API/frontend review | Avoid introducing a third badge now | Assert current two-value contract | None direct | Blocks any proposal that assumes persisted `REAL_CORE` | 2026-08-14 |
| ODR-002 | manuscript/review/experiment Artifact schemas and consumers | Incompatible capability requires v2/companion plus new Definition/Capsule | New renderers for versioned data | Golden v1 + consumer compatibility + v2 negatives | Prevents ambiguous/unvalidated evidence | Blocks final Core schemas | 2026-08-14 |
| ODR-003 | Experiment Workflow, Resource readiness, execution evidence, Progress | New Definition/Capsule; likely new/companion Artifact; migration only for publication metadata | Plan/approval/run/result states | Local sandbox, command, crash, provenance, real Codex | Highest-risk command/resource boundary | Blocks E1 | 2026-08-14 |
| ODR-004 | Experiment execution/network policy | No persistence decision yet | Network approval and denied/expired states | Network canaries and explicit authorization | Prevents silent egress and secret exposure | Blocks E1 network behavior | 2026-08-14 |
| ODR-005 | Writing Workflow and manuscript evidence contract | New Definition/Capsule; likely v2/companion | Brief, evidence map, outline, drafting, claim check | Evidence-grounding and unsupported-claim negatives | Provider/data disclosure policy required | Blocks W1 | 2026-08-14 |
| ODR-006 | Review Workflow and review evidence contract | New Definition/Capsule; likely v2 | Scope, evidence audit, structured issues | Claim/evidence anchors and missing-evidence behavior | Avoids unsupported scientific judgments | Blocks R1 | 2026-08-14 |
| ODR-007 | Review recommendation semantics | May require v2 if v1 enum is incompatible | Do not show scores/acceptance predictions | Schema rejects forbidden score/confidence fields | Reduces misleading high-stakes output | Blocks final R1 recommendation contract | 2026-08-14 |
| ODR-008 | manuscript revision provenance and cross-object validation | Likely v2 or stronger companion/validator | Show causal Review and immutable Draft lineage | Wrong-review/cross-instance/auto-latest negatives | Prevents provenance substitution | Blocks W2 | 2026-08-14 |
| ODR-009 | Artifact storage/API/privacy boundary | No migration while unchanged | Browser shows metadata/provenance; bytes remain local | Assert no byte upload/read route | Limits retention/privacy scope | Blocks proposals requiring Cloud byte preview | 2026-08-14 |
| ODR-010 | Browser/API/Workspace boundary | None while unchanged | Local actions remain copyable commands/status | Browser mutation boundary tests | Prevents browser-origin filesystem writes | Blocks frontend filesystem bridge | 2026-08-14 |
| ODR-011 | Frontend routes, view models, terminology | None until frontend implementation | Major IA/copy/state hierarchy impact | Controlled browser and accessibility evidence | Technical details must not leak secrets/paths | Blocks frontend redesign approval | 2026-08-14 |
| ODR-012 | Harness capability/support statement | New Capsule only if transport differs | Help names qualified Harnesses accurately | Equivalent startup/completion/recovery qualification | Environment/credential scrubbing parity | Blocks Claude support claim | 2026-08-14 |
| ODR-013 | Deployment/auth/API scope | No migration in current phase | No account/team UX | Loopback/controlled regressions | Shared users remain unsafe | Blocks public/shared deployment | 2026-08-14 |
| ODR-014 | Hosted APIs/runtime/tables/UI | No deletion or migration | Legacy pages remain compatibility/internal | Preservation regressions only | Avoids reopening server execution | Blocks hosted feature work | 2026-08-14 |
| ODR-015 | Workspace readiness legacy exception | No change authorized | Do not promise recoverability for real instance | Owner evidence remains E9 FAIL/unknown gate | Prevents unsafe relaxation | Does not block H2/B0; blocks claim of full legacy recovery | 2026-08-14 |
| ODR-016 | Writing/Review UX and revision contract | No migration in evidence phase | Revision flow depends on observed owner friction | Owner manual UX evidence required | No owner data copied into repository | Blocks final W1/R1/W2 contract approval, not H2 | 2026-08-14 |

## Current evidence and affected path index

These are the concrete current paths affected by each proposed decision. A
future change packet must refresh this inventory and add every newly discovered
consumer before implementation.

| ID | Current evidence and affected paths |
|---|---|
| ODR-001 | `backend/project_workspaces/contracts.py`; `backend/progress_reports/contracts.py`; `backend/database/orm/models.py`; `frontend/types/api.ts`; `frontend/components/workflow-status-badge.tsx`; Workflow Definition/Capsule manifests in `backend/workflow_packages/production_workflows.py` |
| ODR-002 | `backend/artifact_references/research_flow_contracts.py`; `backend/workflow_packages/scaffold_validator.py`; `backend/workflow_packages/production_workflows.py`; `backend/project_workspaces/production_workflows.py`; ADR 0030; relevant migration seed rows and frontend Artifact consumers |
| ODR-003 | Experiment builders/runners/validators in `backend/workflow_packages/`; Resource contracts in `backend/resource_references/`; Workspace materialization in `backend/project_workspaces/`; Experiment API/frontend states |
| ODR-004 | Experiment prompt/runtime and command boundary in `backend/workflow_packages/`; proxy and credential boundaries in `backend/cloud_api_proxy/`; controlled-testing security/runbook documents; future approval/API/UI contracts |
| ODR-005 | Writing builders/prompts/validators in `backend/workflow_packages/production_workflows.py` and `scaffold_validator.py`; `manuscript-draft/v1` in `backend/artifact_references/research_flow_contracts.py`; Writing Workspace/API/frontend consumers |
| ODR-006 | Review builders/prompts/validators in `backend/workflow_packages/production_workflows.py` and `scaffold_validator.py`; `review-report/v1` in `backend/artifact_references/research_flow_contracts.py`; Review Workspace/API/frontend consumers |
| ODR-007 | `_RECOMMENDATIONS` in `backend/artifact_references/research_flow_contracts.py`; fixed scaffold recommendation in `backend/workflow_packages/scaffold_validator.py`; future Review schema/API/frontend copy |
| ODR-008 | manuscript/review provenance validation in `backend/artifact_references/research_flow_contracts.py`; binding/materialization in `backend/project_workspaces/`; Writing revision builder/validator/tests and frontend binding UI |
| ODR-009 | accepted ADRs 0022 and 0026; Artifact metadata services/routes in `backend/artifact_references/` and `backend/api/`; Workspace Artifact bytes and frontend metadata consumers |
| ODR-010 | accepted local product architecture; Workspace command/rendering in `backend/project_workspaces/workspace_cli.py`; Cloud API mutations; frontend action surfaces and E2E tests |
| ODR-011 | current routes/components/types under `frontend/`; `docs/frontend/PROJECT_WORKSPACE_INFORMATION_ARCHITECTURE.md`; backend projection/readiness DTOs consumed by the UI |
| ODR-012 | Harness launch/compiler/runtime in `backend/workflow_packages/`; real/fake Harness qualification under `backend/workflow_packages/tests/`; getting-started and acceptance docs |
| ODR-013 | loopback/readiness/runtime configuration in `backend/api/readiness.py`, `frontend/next.config.ts`, `Makefile`, and owner/controlled runbooks; API authorization model |
| ODR-014 | ADR 0009; preserved hosted routes/services/tables and compatibility tests; any UI still consuming frozen hosted surfaces |
| ODR-015 | Experiment 0.4/0.5 package facts in `backend/workflow_packages/production_workflows.py`; shared readiness/recovery in `backend/project_workspaces/workspace_cli.py`; recovery tests and 2026-08-14 progress evidence; no historical byte is an edit target |
| ODR-016 | Writing/Review/Revision tests under `backend/project_workspaces/tests/` and `backend/workflow_packages/tests/`; `docs/getting-started/OWNER_TEST_OBSERVATIONS.md`; owner-test instructions; future W1/R1/W2 contracts |

## Current disposition

All sixteen entries are accepted within their recorded scope. Ratification does
not authorize implementation. H2A may begin only after a separate Owner
instruction; S1 may draft shared contracts, but final Writing, Review, and
revision approval remains blocked by ODR-016.
