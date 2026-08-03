# R3A Cloud API Proxy Current-State Inventory

Status: **AUDITED — DOCUMENTATION ONLY**

Date: 2026-08-03

Baseline: `592410e274b07ac6480f12419b45cd9b742ff838`

Governing decision: ADR 0009

## Audit conclusion

The repository does not implement a local-Harness-facing API Proxy. It does
contain provider-neutral contracts, a bounded OpenAlex adapter, durable hosted
provider-operation accounting, immutable content storage, fake providers and a
FastAPI composition root. Those are candidate building blocks, not an existing
proxy.

The only current server path that can call OpenAlex is part of Hosted Mode:

```text
POST /runs/{workflow_run_id}/resume (or an approval decision)
  -> ResumeWorkflowRunService / ApprovalDecisionService
  -> ExecutionDispatcher
  -> AgentRuntime
  -> SkillExecutor
  -> research.search_papers
  -> PaperSearchProvider / OpenAlexPaperSearchProvider
  -> later ranking, source processing and report-generation Skills
```

That path can choose and execute Workflow steps, rank papers, invoke synthetic
LLM or structured-generation providers, write hosted artifacts, checkpoints,
memory revisions and events, and compose a research report. It is therefore
`HOSTED_MODE_ONLY` and prohibited as the implementation route for the
teacher-aligned V1 proxy.

No authentication middleware, bearer-token validator, authenticated principal,
project ownership model or multi-user authorization service was found. Fields
such as `actor_user_id` and `permitted_approver_role` are request/domain data;
they are not proof of caller identity or authority.

## Classification vocabulary

- `REUSABLE_UNCHANGED_FOR_PROXY`: a narrow contract or mechanism can retain its
  current semantics behind the new boundary.
- `REUSABLE_ONLY_BEHIND_NEW_BOUNDARY`: useful implementation, but only when an
  explicit proxy use case prevents Hosted execution ownership.
- `REQUIRES_ADAPTATION`: useful shape, but its current identity, persistence or
  policy cannot represent local Package callers safely.
- `HOSTED_MODE_ONLY`: preserved optional/internal Hosted execution behavior.
- `DEFERRED`: retained, but outside the first proxy slice.
- `PROHIBITED_FOR_TEACHER_ALIGNED_V1`: must not be called or relabelled as the
  proxy.
- `OBSOLETE_OR_UNCLEAR`: cannot be treated as an approved V1 control.

## Exact component inventory

| Classification | Files/components | Current behavior and R3 implication |
|---|---|---|
| `REUSABLE_UNCHANGED_FOR_PROXY` | `backend/research/contracts/_serialization.py` | Stable UTF-8 canonical JSON, SHA-256 helpers and immutable JSON values are suitable for proxy contract identity. |
| `REUSABLE_UNCHANGED_FOR_PROXY` | `backend/research/ports/providers.py` — `ProviderIdentity`, `ProviderRequestContext`, `ProviderError`, `PaperSearchProvider`, `PaperSearchResult` | Provider SDKs stay behind ports; normalized results and safe failures do not expose raw SDK objects. Capability-facing envelopes still need a new API contract. |
| `REUSABLE_UNCHANGED_FOR_PROXY` | `backend/research/ports/artifact_storage.py`; `backend/research/adapters/local_artifact_storage.py` | Immutable byte storage, relative storage keys, checksum verification, traversal/symlink protection and restart-safe reads are reusable. Retention policy remains undecided. |
| `REUSABLE_UNCHANGED_FOR_PROXY` | `backend/research/contracts/models.py` — `ProviderIdentity`-related records, `ProviderUsage`, `ProviderReservation`, `ProviderFailureCategory`; `backend/research/services/budget.py` — `ProviderBudgetEvaluator` | Usage, reservation and fail-closed budget arithmetic are useful semantic primitives. A proxy-specific budget scope is still required. |
| `REUSABLE_ONLY_BEHIND_NEW_BOUNDARY` | `backend/research/adapters/openalex.py` | Fixed official base URL, no redirects, key injection inside the adapter, 15-second request cap, 2 MiB response cap, bounded retries, schema mapping and safe error details are useful. The adapter is currently selected by Hosted composition and its current query planning is not yet a local-Harness proxy contract. |
| `REUSABLE_ONLY_BEHIND_NEW_BOUNDARY` | `backend/research/adapters/fake_providers.py`; `backend/research/adapters/synthetic_grounded.py` | Network-free deterministic adapters are suitable for R3B contract/idempotency/restart testing. Fake LLM and structured-generation behaviors must not be exposed by the first proxy slice. |
| `REUSABLE_ONLY_BEHIND_NEW_BOUNDARY` | `backend/research/services/artifacts.py`; `backend/domain/models/artifact_metadata.py`; `backend/persistence/ports/artifact_repository.py`; `backend/database/repositories/artifact.py` | Immutable content plus metadata/checksum linkage is reusable if the owner permits response retention. Hosted run ownership must not be fabricated for proxy data. |
| `REUSABLE_ONLY_BEHIND_NEW_BOUNDARY` | `backend/api/app.py`; transport-level error mapping in `backend/application/errors.py` | FastAPI can host separate explicit proxy routes. Existing app wiring currently also exposes Hosted run/resume routes, so the proxy service graph must remain independent. |
| `REUSABLE_ONLY_BEHIND_NEW_BOUNDARY` | `backend/progress_reports/client.py` | Its standard-library CLI, explicit one-attempt upload, bounded timeout and “outcome unknown; reconcile before retry” pattern are a useful local-client precedent. It is not a proxy client and carries no authentication. |
| `REQUIRES_ADAPTATION` | `backend/research/contracts/models.py` — `ProviderOperation`, `ProviderBudget`, `ProviderOperationStatus`, `ProviderOperationKind`, `ProviderCategory` | The immutable lifecycle and usage concepts are useful, but `ProviderOperation` requires hosted `workflow_run_id`, `logical_step_id` and optional `step_run_id`; it lacks Package/Workflow-package/caller/capability/response identity. Existing statuses also lack a durable explicit client-unknown/reconciliation state. |
| `REQUIRES_ADAPTATION` | `backend/research/services/budget.py` — `ProviderOperationService`; `backend/persistence/ports/provider_operation_repository.py`; `backend/database/repositories/provider_operation.py`; `backend/persistence/models/provider_operation_record.py` | Reservation-before-call, idempotency conflict checking, settlement and optimistic versioning are valuable. Current lookup scope is project plus hosted idempotency key and lists by Workflow Run. A new proxy-owned model/port or approved additive adaptation is required. |
| `REQUIRES_ADAPTATION` | `backend/database/orm/models.py` — `ProviderOperationORM`; `backend/database/migrations/versions/20260721_0002_provider_operations.py` | The table has foreign keys to `workflow_runs`/`workflow_step_runs`. R3B must not fabricate Hosted runs to persist proxy calls and must qualify any additive mapping separately. |
| `REQUIRES_ADAPTATION` | `backend/research/services/execution_policy.py` | Existing fake/OpenAlex/grounded policies are scoped to Hosted Workflow Runs. Some caps are useful prior evidence, but Package capability, caller, operation and project budgets require owner approval. |
| `REQUIRES_ADAPTATION` | `backend/api/composition.py` | It safely reads an OpenAlex key server-side and adapter configuration hides the key from `repr`, but it wires providers into `AgentRuntime` Skills. A separate proxy-only service graph, fixed capability allowlist and approved credential source are required. |
| `REQUIRES_ADAPTATION` | `backend/workflow_packages/template.py` — `cloud/proxy.example.json` | The disabled, credential-free placeholder correctly records no key and `UNDECIDED_R3_NO_CREDENTIAL_PRESENT`. Later Package changes require their own authorized phase after the contract and authentication decision; R3A does not alter it. |
| `REQUIRES_ADAPTATION` | `backend/research/contracts/models.py` — `ResearchQuery`, `PaperRecord`, `SearchPlan`, `SearchExecution`, `SearchStatistics` | `ResearchQuery` and `PaperRecord` are strong candidate schemas for the first capability. `SearchPlan` currently includes provider-specific planning chosen in backend Skills/adapters; the proxy must forward a local request and record transport provenance without deciding research method. |
| `HOSTED_MODE_ONLY` | `backend/application/execution/dispatcher.py`; `backend/agent_runtime/runtime/agent_runtime.py`; `backend/workflow_engine/`; `backend/skill_system/runtime/skill_executor.py` | These schedule/execute/resume concrete hosted Workflows. The proxy request path must not import or call them. |
| `HOSTED_MODE_ONLY` | `backend/api/routers/runs.py`; `backend/api/routers/approvals.py`; Hosted service graph in `backend/api/dependencies.py` and `backend/api/composition.py` | `/runs/{id}/resume` and approval decisions can dispatch AgentRuntime. They are not authentication or proxy endpoints. |
| `HOSTED_MODE_ONLY` | `backend/research/skills.py`; `backend/research/grounded_skills.py` | Server Skills validate/construct queries, call providers, normalize/rank/select papers, retrieve sources, summarize/synthesize, invoke LLM/structured generation, compose reports and persist artifacts. These responsibilities remain local in teacher-aligned V1. |
| `HOSTED_MODE_ONLY` | `backend/application/services/research_outputs.py`; `backend/api/routers/artifacts.py`; `backend/api/schemas/research.py` | They expose Hosted run artifacts and provider usage. They do not represent a proxy operation requested by a local Package. |
| `HOSTED_MODE_ONLY` | Hosted `WorkflowRun`, `StepRun`, `ExecutionEvent`, checkpoint, memory-revision and approval models/repositories | These remain optional/internal Hosted state and must not become proxy operation or local task state by relabelling. |
| `DEFERRED` | `backend/research/adapters/anthropic_substrate.py`; `backend/research/ports/providers.py` — LLM and structured-generation ports | No default network wiring exists, but any LLM proxy capability would risk cloud research execution and requires a separate future owner decision. It is outside R3B/R3C’s first slice. |
| `DEFERRED` | `backend/research/evaluation/`; `docs/evidence/LLM_JUDGE_PROVIDER_MATRIX.md`; real-Judge and real-report evidence/policies | Evaluation/Judge/report-generation paths are preserved historical work, not initial V1 proxy capabilities. |
| `DEFERRED` | Semantic Scholar and Crossref roles described in ADR 0004 | They have no implemented adapters and require separate current terms, credential, schema and retention approval. |
| `PROHIBITED_FOR_TEACHER_ALIGNED_V1` | `ExecutionDispatcher -> AgentRuntime -> research Skills` as the implementation of proxy requests | This path executes and advances research, so it cannot sit behind a proxy endpoint. |
| `PROHIBITED_FOR_TEACHER_ALIGNED_V1` | `research.rank_papers`, `summarize_sources`, `synthesize_literature`, `generate_research_report`, grounded generation/composition Skills | The cloud must not decide relevance, synthesize findings, invoke a research LLM or write the research report. |
| `PROHIBITED_FOR_TEACHER_ALIGNED_V1` | User-controlled base URL/endpoint forwarding | No general-purpose HTTP proxy or arbitrary URL field is permitted. Adapter endpoints are fixed in server policy. |
| `OBSOLETE_OR_UNCLEAR` | Request-supplied `actor_user_id`, approval role fields and unrestricted project IDs as security controls | These fields are not backed by authenticated principals or ownership enforcement. They cannot authorize Package proxy calls. |
| `OBSOLETE_OR_UNCLEAR` | Historical hosted retention values as production proxy policy | The old evaluation policies are useful risk evidence but do not decide multi-user V1 retention. New owner approval is required. |

## Current policy and security evidence

- `OpenAlexConfiguration` accepts only the official fixed base URL, disables
  redirects, caps one response at 2 MiB, caps per-request time at 15 seconds,
  and permits at most two retries after the initial attempt.
- `HttpxOpenAlexTransport` deliberately avoids retaining credential-bearing
  request exceptions and retains only selected response headers.
- `ApplicationContainer.from_environment()` is the only production composition
  path that reads `REAGENT_OPENALEX_API_KEY`; no Package generator or local
  Progress Report client reads it.
- `.env.example` contains an empty variable placeholder, not a credential.
- `LocalFilesystemArtifactStorage` rejects absolute/traversal keys and symlink
  traversal and verifies immutable content.
- The Package proxy placeholder is disabled, offline, contains no credential,
  and records authentication as undecided.
- Progress Report security rejects raw-provider-response and secret-like data;
  a future proxy must not use Progress Reports to smuggle provider bodies or
  credentials.

These controls reduce implementation risk but do not provide caller
authentication, authorization, tenant isolation, request signing, revocation,
retention enforcement or a Package-scoped operation ledger.

## Boundary risks requiring explicit separation

1. Reusing `ApplicationServices` would instantiate `AgentRuntime` and
   `ExecutionDispatcher` in the same request graph. A proxy-only service graph
   must exclude those imports and capabilities.
2. Reusing the SQL `provider_operations` table unchanged would require a fake
   Hosted `WorkflowRun`, which violates the state-authority boundary.
3. Reusing `research.search_papers` would let the server build provider-specific
   search plans and would leave later server ranking/report steps reachable.
4. Treating `actor_user_id` as authentication would permit spoofing and
   cross-project calls.
5. Treating existing OpenAlex retryability as permission for client retries
   would duplicate ambiguous operations. Client reconciliation must be
   explicit.
6. Persisting raw provider bodies through generic artifacts without an owner
   policy could retain copyrighted, secret-bearing or malicious data.
7. Exposing Source Content, LLM or structured generation in the first slice
   would materially enlarge the proxy into research execution.

## Supporting tests, evaluation paths and governing documents

These additional files were inventoried as evidence or preserved historical
behavior. They are not proxy implementation:

| Classification | Exact paths | Relevance |
|---|---|---|
| `REUSABLE_ONLY_BEHIND_NEW_BOUNDARY` | `backend/research/tests/test_openalex_provider.py`, `backend/api/tests/test_openalex_composition.py`, `backend/database/tests/test_openalex_provider_operation_postgresql.py`, `backend/integration/tests/test_http_postgresql_openalex_contract.py` | Bounded adapter, secret-safe composition and persistence test patterns can inform fake/live proxy tests after adaptation. The integration path remains Hosted. |
| `DEFERRED` | `backend/integration/tests/test_http_postgresql_openalex_live.py` | Supervised Hosted live-provider acceptance; not usable as R3B and no live call is permitted before separately authorized R3C. |
| `DEFERRED` | `backend/research/evaluation/cli.py`, `operation_journal.py`, `candidate_pool.py`, `audit_queue.py`, `contracts.py`, `judgments.py`, `metrics.py`, `multilingual.py`, `topics.py` | Evaluation-only OpenAlex orchestration/journal/candidate and human-review substrate. The CLI can read the server-side OpenAlex environment variable, but it is not an authenticated Package proxy. |
| `HOSTED_MODE_ONLY` / `DEFERRED` | `backend/research/evaluation/judge_port.py`, `fake_judge.py`, `prompts.py`, `silver_aggregation.py`, `silver_contracts.py`, `silver_metrics.py`, `silver_orchestrator.py`, `report.py`, `synthetic_fixtures.py` | Automated Judge/evaluation/report logic stays outside the first proxy capability. |
| `REUSABLE_UNCHANGED_FOR_PROXY` as design evidence | `.agent_read/decisions/0003-real-research-provider-and-artifact-boundaries.md` | Accepts provider ports, durable operation reservation and immutable artifact-content boundaries; it does not decide auth/vendor/retention. |
| `REUSABLE_ONLY_BEHIND_NEW_BOUNDARY` as historical evidence | `.agent_read/decisions/0004-first-paper-search-provider.md`, `.agent_read/decisions/0005-automated-relevance-judge-and-multilingual-search.md` | Establish bounded OpenAlex and safe diagnostic prior art. Hosted method/limits do not automatically become proxy policy; real Judge remains deferred. |
| `HOSTED_MODE_ONLY` / `DEFERRED` as governance | `.agent_read/decisions/0006-bounded-real-judge-calibration.md`, `0007-first-real-grounded-literature-report.md`, `0008-bounded-real-grounded-report-acceptance.md` | Real Judge/report/Hosted activation is deferred by ADR 0009. |
| Governing boundary | `.agent_read/decisions/0009-teacher-aligned-initial-product-boundary.md`, `docs/architecture/CLOUD_PROGRESS_AND_API_PROXY_BOUNDARY.md`, `docs/architecture/EXISTING_COMPONENT_RECLASSIFICATION.md` | Cloud holds credentials/proxy metadata; local folder/Harness owns research and concrete task state. |
| Retention/risk evidence only | `docs/evidence/OPENALEX_DATA_RETENTION_POLICY.md`, `PROVIDER_FAILURE_MATRIX.md`, `PROVIDER_FIELD_MAPPING.md`, `MULTILINGUAL_SEARCH_FAILURE_ANALYSIS.md` | Supplies prior threat/failure/field analysis. Its supervised-evaluation retention durations are not approved production proxy policy. |
| `DEFERRED` policy evidence | `docs/evidence/LLM_JUDGE_PROVIDER_MATRIX.md`, `REAL_JUDGE_*`, `REAL_REPORT_*`, `REAL_GROUNDED_REPORT_*`, `CITATION_AND_REPORT_CONTRACT.md`, `GROUNDED_REPORT_INPUT_CONTRACT.md` | LLM/Judge/report provider, prompt, cost, data and acceptance material is outside `paper.search/v0.1` and teacher-aligned proxy execution. |

No repository-supported authentication model was discovered during the audit.
The empty OpenAlex key placeholder in `.env.example` is configuration
documentation, not a secret or caller-authentication mechanism. R3A did not read
`.env` or any real credential.

## Static inspection scope

R3A inspected imports, routes, composition, provider ports/adapters, provider
operation contracts/repositories/migration, budget and execution policy,
artifact storage, Package proxy placeholder, local client precedent, project
identity fields, and authentication-related symbols. This is static evidence;
it is not runtime proxy acceptance and does not claim any proxy endpoint exists.
