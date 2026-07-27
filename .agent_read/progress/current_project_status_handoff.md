# ReAgent 当前项目状态与交接报告

- 审查日期：2026-07-27
- 审查性质：READ-ONLY REVIEW AND DOCUMENTATION
- 仓库根目录：`/Volumes/tb/个人资料/暑研/UCInspire26/MetaResearchAgent/ResearchAgent`
- 产品依据：`docs/PROJECT_DEVELOPMENT_PLAN.md`
- 冻结架构合同：`.agent_read/progress/architecture_contract.md`
- 当前 Alembic 静态 head：`20260721_0002`
- 当前结论：`PASS_WITH_WARNINGS`

本报告以当前源码、Git 工作树、迁移、测试配置和本次实际执行结果为主，以 `.agent_read/progress/` 的历史记录为补充。历史记录与源码冲突时，以 ADR 本体和当前源码为准。本次没有修改 `.agent_read/context.md`；该文件含有按时间累积的旧叙述，例如 Phase 9A-0 段落仍说 ADR 0003 是 Proposed，但后续段落和 ADR 本体已经明确其限定范围于 2026-07-21 Accepted。这个时序矛盾不影响当前判断，因此未做非必要改写。

## 1. Executive Summary

ReAgent 的最终目标是一个基于 Web 的、可持久化的研究 Agent 平台：用户创建 research project，选择可复用 Workflow，启动长时间运行的 Agent，在中断或重启后恢复，通过 human approval 控制关键动作，并获得带 provenance 的可下载研究 artifacts。产品愿景来自 `docs/PROJECT_DEVELOPMENT_PLAN.md`，具体模块边界来自 `.agent_read/progress/architecture_contract.md` 和 ADR 0001。

当前实际建成的不是 production-ready research platform，而是一个有持久化生命周期、审批、事件时间线和真实 PostgreSQL 路径的 supervised full-stack demo，外加 Phase 9A-1 的 provider-independent research substrate。当前可演示的完整产品路径是 `guided-literature-review@1.0.0`：Next.js 创建 run，FastAPI 同步驱动 Runtime，fake paper search 完成后暂停审批，审批通过后 fake summary 完成，状态和事件保存在 PostgreSQL，浏览器 reload 后仍可读取。历史真实浏览器证据见 `.agent_read/progress/e2e_demo_integration.md`。

当前 research substrate 已实现：

- immutable research contracts；
- `PaperSearchProvider`、`SourceContentProvider`、`LLMProvider` 和 `ArtifactContentStorage` ports；
- deterministic synthetic providers；
- `LocalFilesystemArtifactStorage`；
- provider budget reservation/settlement；
- `provider_operations` PostgreSQL 表及 InMemory/SQL adapter；
- Engine-resolved approval inputs；
- fail-closed `ProvenanceValidator`。

这些能力主要位于 `backend/research/`、`backend/persistence/`、`backend/database/`、`backend/skill_system/` 和 `backend/workflow_engine/`。它们没有组成 `guided-literature-review@2.0.0`：仓库中不存在 v2 Workflow fixture/seed，不存在 v2 research Skills，不存在 artifact/provider-usage HTTP API，也不存在 report/artifact frontend route。`AgentRuntime._execute_step()` 当前只使用 `SkillResult.output_data`，没有 materialize `emitted_artifacts`，也没有结算 `provider_usage`。因此 Phase 9A-2 是 `NOT_STARTED`，不是 partial implementation。

实际当前阶段是：**Phase 9A-1.5 已完成并有历史 PostgreSQL 验收证据，等待进入 Phase 9A-2**。成熟度分类为：**supervised full-stack demo**。不能称为 deterministic research vertical slice，因为 v2 DAG 和报告/证据/artifact 用户路径尚不存在；不能称为 production-ready platform，因为 worker、authentication、multi-user isolation、real providers、production storage 和 operations 均未实现。

立即下一里程碑应且只能是：**Phase 9A-2 — Complete Deterministic Fake-Provider Guided Literature Review v2 Vertical Slice**。在开始编码前，应先保护当前未提交的 Phase 9A-1/1.5 工作，因为当前 Git HEAD 仍是 Phase 8B baseline。

## 2. Product Vision

最终产品应是一个 Web-based persistent research agent platform，用户可以：

1. 创建和管理 research projects；
2. 上传或引用 research materials；
3. 从版本化 catalog 选择 Workflow；
4. 启动 long-running execution；
5. 查看步骤、事件、错误、成本和恢复状态；
6. 在受保护动作前进行 human approval；
7. 在进程或机器重启后从 durable checkpoints 和 memory 恢复；
8. 阅读、下载和复用版本化 artifacts；
9. 从 report claim 追踪到 evidence、paper、citation 和 source；
10. 通过 immutable, semantic-versioned Skills 扩展能力；
11. 将 provider SDK、LLM、paper search、object storage 和 worker 作为 adapters 替换。

上述愿景在 `docs/PROJECT_DEVELOPMENT_PLAN.md`、`.agent_read/progress/architecture_contract.md` 和 `.agent_read/progress/real_research_vertical_slice_contract.md` 中定义。当前实现与愿景的差异如下：

| 产品方面 | 当前实现 |
|---|---|
| Research project | 只有 `project_id` 作为隔离字段；没有 Project/User aggregate、project CRUD 或 project switcher |
| Workflow selection | 有 persisted catalog list 和一个 hash-pinned v1 demo seed；没有一般 publication/admin lifecycle |
| Long-running execution | Runtime 可 checkpoint/recover，但 HTTP 通过 `SyncExecutionDispatcher` 同步执行；没有 durable worker |
| Memory | 有 project/run-scoped append-only working-memory revisions；没有 long-term semantic retrieval 或 pgvector |
| Human approval | 已持久化、fingerprint-bound、可 approve/reject/expire-on-access；没有 authentication/role enforcement |
| Artifacts | PostgreSQL metadata repository、local immutable byte storage 和 application gateway 已实现；未接入 Runtime/API/UI |
| Provenance | contracts 和纯 validator 已实现并有单元测试；未成为 v2 workflow completion gate |
| Skills | v1 fake Skills 已完整运行；research provider capability bundle 已实现；v2 research Skills 未实现 |
| Real providers | 未选择、未实现、未验证、无 SDK、无 credentials、无 live network |
| Web product | v1 workflow/run/approval 页面可用；无 report/artifact/project/auth 页面 |

## 3. Current Architecture

当前实际依赖流：

```text
Next.js App Router
  -> typed API client / TanStack React Query
  -> FastAPI routers + Pydantic DTOs
  -> framework-independent Application Services
  -> ExecutionDispatcher
  -> SyncExecutionDispatcher
  -> AgentRuntime
  -> Workflow Engine / Skill System
  -> Domain Core
  -> Persistence Ports / UnitOfWork
  -> InMemory adapters or SQLAlchemy adapters
  -> PostgreSQL

Research substrate side path:

Skill capability contracts / application gateways
  -> ProviderOperationService / ProvenanceValidator
  -> Provider ports / ArtifactContentStorage
  -> deterministic fake providers / LocalFilesystemArtifactStorage
```

### Domain Core

- 路径：`backend/domain/`
- 责任：定义 `Workflow`、`WorkflowStep`、`WorkflowRun`、`StepRun`、`AgentSession`、`Checkpoint`、`ArtifactMetadata`、`ApprovalRequest`，以及合法 lifecycle transitions。
- 关键抽象：`ExecutionState`、`ExecutionCoordinator`、status enums、checkpoint integrity hash、row version。
- 不得拥有：DAG scheduling、reference resolution、Skill invocation、HTTP、ORM、provider SDK、filesystem。
- 状态：fully implemented and regression-tested。Domain 只执行合法 mutation；Workflow Engine 决定节点 readiness 和完成/失败。

### Workflow Engine

- 路径：`backend/workflow_engine/`
- 责任：验证 immutable static DAG、确定一个 ready node、解析 `${inputs.*}` 与 `${nodes.*.outputs.*}`、计算 retry decision、approval decision 和 workflow completion。
- 关键抽象：`WorkflowDefinition`、`StepDefinition`、`RetryPolicy`、`ExecutionSnapshot`、`StepReady`、`WaitingApproval`、`RetryScheduled`、`WorkflowCompleted`、`WorkflowFailed`、`WorkflowExecutionCoordinator`。
- 不得拥有：Skill execution、persistence、user authorization、worker sleep/queue、HTTP。
- 状态：fully integrated。Phase 9A-1 已将 `WaitingApproval.resolved_inputs` 加入 decision，并由 Engine 做 reference resolution；当前仍是 sequential static DAG。

### Skill System

- 路径：`backend/skill_system/`
- 责任：immutable semantic-versioned Skill definitions、small internal schema validation、allow-listed registry、exact-version resolution、async execution 和 normalized result。
- 关键抽象：`SkillDefinition`、`SkillMetadata`、`SkillReference`、`SkillSchema`、`FieldSchema`、`SkillRegistry`、`SkillExecutor`、`SkillExecutionContext`、`SkillCapabilities`、`SkillResult`、`SkillExecutionOutput`。
- 不得拥有：Workflow state mutation、DAG scheduling、SQLAlchemy、FastAPI、provider client construction。
- 状态：v1 fake Skills fully integrated；research capability substrate implemented but not composed into v2 Skills。默认 deny-by-default，只有 definition 声明并由 composition grant 的 provider/artifact capability 才可用。

### Agent Runtime

- 路径：`backend/agent_runtime/`
- 责任：按 Engine decision 协调 Domain、Skill System、checkpoint、memory、approval、events 和 UoW commits。
- 关键抽象：`AgentRuntime.run()`、`AgentExecutionContext`、`RuntimeResult`、approval fingerprint helpers。
- 不得拥有：DAG policy、provider SDK、ORM、HTTP、worker implementation。
- 状态：fully integrated for v1 fake Skill outputs, approvals, events and PostgreSQL recovery。重要限制：`backend/agent_runtime/runtime/agent_runtime.py` 的 success path 只提交 `result.output_data`；`SkillResult.emitted_artifacts` 和 `provider_usage` 尚未 materialize/settle，因此 research substrate 还没有运行时纵向集成。

### Persistence

- 路径：`backend/persistence/`
- 责任：定义 framework-independent repositories 和 `UnitOfWork`，提供 transactional InMemory adapters。
- 关键抽象：`WorkflowRepository`、`CheckpointRepository`、`MemoryRepository`、`ArtifactRepository`、`ApprovalRepository`、`ExecutionEventStore`、`ProviderOperationRepository`、`UnitOfWork`。
- 不得拥有：HTTP DTO、provider SDK、workflow scheduling。
- 状态：implemented。InMemory adapter 提供 validation-before-apply、rollback、detached reconstruction、idempotency 和 optimistic concurrency。`ArtifactRepository` 只存 metadata。

### Execution Events

- 路径：`backend/execution_events/`
- 责任：append-only、project/run-scoped、ordered audit events。
- 关键抽象：`ExecutionEvent`、`EventPayload`、`ExecutionEventType`、`ExecutionEventStore`。
- 事件：`WORKFLOW_STARTED`、`STEP_STARTED`、`SKILL_EXECUTED`、`CHECKPOINT_CREATED`、`APPROVAL_REQUESTED`、`WORKFLOW_COMPLETED`、`WORKFLOW_FAILED`。
- 不得拥有：notification delivery、outbox consumer、Workflow mutation。
- 状态：fully integrated into Runtime transactions；不是 message outbox。

### Approval System

- 路径：`backend/domain/models/approval_request.py`、`backend/application/services/approvals.py`、Runtime 和 persistence adapters。
- 责任：durable `PENDING -> APPROVED|REJECTED|EXPIRED` lifecycle、action fingerprint、idempotent decision、resume/cancel。
- 不得拥有：身份认证、角色授权实现、主动 expiry scheduler。
- 状态：fully integrated for current trusted prototype。Phase 9A-1 fingerprint 包含 Engine-resolved inputs 和 pinned Skill versions，但 v2 candidate selection 尚未存在。

### PostgreSQL Adapter

- 路径：`backend/database/`
- 责任：SQLAlchemy ORM mappings、sync Session repositories、transaction ordering、psycopg3 engines、Alembic migrations。
- 关键抽象：`SQLAlchemyUnitOfWork`、各 `SQLAlchemy*Repository`、`WorkflowDefinitionORM` 到 `ProviderOperationORM`。
- 不得拥有：Domain/Workflow/Skill policy；ORM objects 不得越过 adapter boundary。
- 状态：implemented and historically verified on PostgreSQL 18.1。当前 ports 是 synchronous；AsyncEngine factory 仅为未来 composition 提供，不等于 async repository。

### Application Layer

- 路径：`backend/application/`
- 责任：commands、read views、use-case services、transaction boundary、dispatcher abstraction。
- 当前 services：create/get/list/resume/cancel run、list events、list/decide approvals、list workflows。
- 不得拥有：FastAPI/Pydantic、ORM、provider SDK。
- 状态：v1 fully integrated。没有 catalog-pinned v2 create service、artifact service routes、provider usage query 或 provider retry use case。

### API Layer

- 路径：`backend/api/`
- 责任：FastAPI routing、Pydantic DTO validation、request-scoped composition、error mapping。
- 不得拥有：business rules、ORM query、workflow scheduling。
- 状态：v1 fully integrated。只有 composition root 选择 SQL adapter；routes/schemas 不导入 SQLAlchemy。

### Frontend

- 路径：`frontend/`
- 责任：dashboard、workflow catalog、run ledger、event timeline、approval center。
- 关键抽象：App Router pages、`api/client.ts`、React Query hooks、typed transport types。
- 不得拥有：Workflow/approval/runtime business rules 或 backend Python imports。
- 状态：supervised v1 demo implemented。没有 v2 form、candidate paper preview、report renderer、citation viewer、artifact download。

### Research Contracts

- 路径：`backend/research/contracts/`
- 责任：immutable canonical JSON contracts 和 hashes。
- 包含：`ResearchQuery`、`PaperRecord`、`SourceContent`、`RankedPaper`、`CitationReference`、`EvidenceUnit`、`GroundedClaim`、`ResearchReport`、`ProviderUsage`、`ProviderBudget`、`ProviderOperation`、`ProvenanceManifest`。
- 不得拥有：network、ORM、FastAPI、filesystem。
- 状态：implemented and unit-tested；尚未作为 runnable v2 Workflow 的 Step I/O。

### Provider Operations

- 路径：`backend/research/services/budget.py`、`backend/persistence/ports/provider_operation_repository.py`、InMemory/SQL repositories、migration `20260721_0002`。
- 责任：pre-call reservation、idempotency、budget enforcement、running/success/failure/cancel settlement、unsettled recovery visibility。
- 不得拥有：provider-specific clients 或自动 Workflow mutation。
- 状态：persistence/lifecycle fully implemented and historically PostgreSQL-verified；未连接到完整 provider-call orchestration，也没有 HTTP usage view。

### Artifact Storage

- 路径：`backend/research/ports/artifact_storage.py`、`backend/research/adapters/local_artifact_storage.py`、`backend/research/services/artifacts.py`。
- 责任：immutable byte write/read/verify，relative storage keys，path traversal/symlink protection；application gateway 在写 bytes 后 stage `ArtifactMetadata`。
- 不得拥有：Workflow lifecycle、SQL transaction、authorization、public URL。
- 状态：implemented and unit-tested，但 not Runtime/API/UI integrated。默认设计 root 为 ignored `runtime_data/artifacts`，当前目录不存在。

### Provenance

- 路径：`backend/research/services/provenance.py`。
- 责任：fail-closed 检查 report label -> citation -> selected paper，以及 claim -> evidence -> source-content checksum；同时检查 versions、artifact checksum links、source scope 和 unsettled provider operations。
- 不得拥有：report generation、Domain transition、artifact publication。
- 状态：contract-level implemented and tested with fixtures；未成为实际 v2 terminal gate。

## 4. Architecture Decisions

### ADR 0001: Foundational application architecture

- 文件：`.agent_read/decisions/0001-foundational-architecture.md`
- 状态：`Accepted`
- 决定：使用 modular monolith + ports and adapters；one primary Agent Session per versioned static-DAG Workflow Run；FastAPI、PostgreSQL/SQLAlchemy/Alembic、Next.js；大内容通过 file/object-storage port；pgvector 延后。
- 后果：核心不依赖 HTTP、ORM、model vendor 或 queue；PostgreSQL 是 lifecycle/recovery authority；v1 sequential deterministic；API/worker 可分进程但共享 package/schema。
- 有意不决定：具体 LLM/provider、queue product、object store、auth provider、vector strategy、production deployment。

### ADR 0002: Use psycopg 3 with the frozen synchronous persistence ports

- 文件：`.agent_read/decisions/0002-psycopg3-and-synchronous-persistence-adapter.md`
- 状态：`Accepted`
- 决定：使用 psycopg3；当前 repository adapters 使用 SQLAlchemy synchronous `Session`；同时提供 AsyncEngine factory，但不创建第二套 async repository contract。
- 后果：Runtime 可直接使用 frozen sync UoW；未来若在 async API 高并发使用，必须增加 thread boundary 或单独评审 async contract。
- 有意不决定：不会自动把现有 ports 转成 async，也没有决定 worker/queue 或 event-loop isolation 方案。

### ADR 0003: Add real-provider operation and artifact-content boundaries

- 文件：`.agent_read/decisions/0003-real-research-provider-and-artifact-boundaries.md`
- 状态：`Accepted`，只限记录的 Phase 9A-1 additive scope。
- 决定：
  - `UnitOfWork` 增加 `ProviderOperationRepository`；
  - `WaitingApproval` 携带 Engine-resolved inputs；
  - artifact bytes 通过 `ArtifactContentStorage`；
  - provider SDK/client 只在 adapters/composition；
  - provider usage/budget state durable and auditable；
  - Skill context/result 增加 deny-by-default capability、artifact/usage envelope。
- 后果：支持 pre-call reservation、restart audit、local immutable content 和 selection-bound approval；filesystem 与 PostgreSQL 仍不能原子提交；没有 provider idempotency 时不能保证 exactly-once billing。
- 有意不决定：paper provider、LLM vendor/model、pricing、API key、live mode、S3、retention、Domain lifecycle、worker、auth。

### Proposed ADRs

当前没有状态为 `Proposed` 的 ADR 文件。`architecture_analysis.md` 是早期 proposal，不是 ADR；ADR 0003 在早期 Phase 9A-0 completion 文档中仍写 Proposed，但 ADR 本体和 Phase 9A-1/1.5 记录已将限定范围接受。未来 agent 不得把早期叙述当作当前 ADR status。

## 5. Phase-by-Phase History

| Phase | 目标 | 关键产出 | 验证证据 | 当前状态 | 未解决限制 |
|---|---|---|---|---|---|
| Phase 0: Architecture Definition | 定义系统形状、数据模型和 ports | `architecture_analysis.md` | documentation-only；未运行 production tests | `COMPLETED` | 当时所有技术选择仅为 proposal |
| Architecture Contract | 冻结 module ownership、lifecycle、storage 和 approval semantics | `architecture_contract.md`、ADR 0001 | documentation-only completion report | `COMPLETED` | provider、worker、auth、storage vendor 延后 |
| Phase 1: Domain Core | 纯 Domain lifecycle/checkpoint | `backend/domain/` | 历史 5 tests；后续回归包含在当前 suite | `COMPLETED` | 无 scheduling/I/O |
| Phase 2: Workflow Engine | deterministic static DAG decision engine | `backend/workflow_engine/` | 历史全套 17 passed | `COMPLETED` | sequential；无 loop/condition/dynamic graph |
| Phase 3: Skill System | versioned registry/executor/schema | `backend/skill_system/` | 历史全套 26 passed | `COMPLETED` | small schema subset；无 dynamic plugin |
| Phase 4: Agent Runtime | Engine/Skill/Domain execution loop | `backend/agent_runtime/` | 历史全套 32 passed | `COMPLETED` | 当时 in-memory；当前仍无 durable worker |
| Phase 5: Persistence Foundation | repositories/UoW/InMemory recovery | `backend/persistence/` | 历史 37 passed | `COMPLETED` | InMemory 仅测试用 |
| Phase 5.5: Events and Approval | append-only events + durable approval contracts | `backend/execution_events/`、Approval persistence | 历史 41 passed | `COMPLETED` | 当时未接 Runtime；Phase 7B 后已接入 |
| Phase 6: PostgreSQL | SQLAlchemy/psycopg/Alembic adapter | `backend/database/`、migration 0001 | 历史 fast 45；with PostgreSQL 52；migration replay/check | `COMPLETED` | sync ports；无 production ops |
| Phase 7A: Application and API | use cases 和 FastAPI 基础 | `backend/application/`、`backend/api/` | 历史 54 passed, 7 skipped；API 9 passed | `COMPLETED` | 当时无 events/approval auto-create |
| Phase 7B: Backend Product Readiness | Runtime events、approval lifecycle、queries、dispatcher | Runtime/Application/API updates | 历史 66 passed, 7 skipped | `COMPLETED` | inline sync execution、无 auth |
| Phase 8A: Frontend Vertical Slice | workflows/runs/events/approval UI | `frontend/` | 历史 4 files/4 tests，lint/build | `COMPLETED` | 当时无 real browser E2E；Phase 8B 后补 |
| Phase 8B: E2E Demo Integration | real Next.js/FastAPI/PostgreSQL/Chrome v1 demo | seed、Compose/Make、HTTP integration、Playwright | 历史 fast 67/8 skipped；full DB 75/0；Playwright 1 passed；Docker 未执行 | `COMPLETED_WITH_WARNINGS` | Docker/Compose runtime 未验证；仍是 fake summary |
| Phase 9A-0: Real Research Contract | 冻结 v2 product/contract/plan | `real_research_vertical_slice_contract.md` | documentation-only；没有 runtime tests | `COMPLETED_WITH_WARNINGS` | owner/provider decisions open；不代表实现 |
| Phase 9A-1: Research Contract Substrate | provider-independent contracts、storage、budget、provenance | `backend/research/`、UoW/Skill/Engine additions、migration 0002 | 历史 106 passed, 9 skipped；compile；SQL 未执行 | `COMPLETED_WITH_WARNINGS` | PostgreSQL gate 当时未跑；无 v2 workflow |
| Phase 9A-1.5: PostgreSQL Acceptance Gate | 接受 migration 0002 和 ProviderOperation SQL contract | SQL adapter tests、migration replay | 历史 13 PostgreSQL tests；full backend 123 passed, 0 skipped；two drift checks | `COMPLETED` | acceptance DB retained；frontend 未重跑 |
| Phase 9A-2 | deterministic fake-provider v2 end-to-end vertical slice | 当前无产出 | 源码无 v2 definition/Skills/API/UI；无 test evidence | `NOT_STARTED` | 是立即下一里程碑 |

Phase 9A-2 未被先前 prompt 自动执行。精确证据：

- `demo/workflows/` 只有 `guided_literature_review.v1.json`；
- `backend/demo/seed.py` 只允许 `1.0.0` 和固定 v1 hash；
- `register_fake_skills()` 只注册 `mock_paper_search@1.0.0`、`mock_summary@1.0.0`；
- API OpenAPI paths 没有 `/runs/from-catalog`、artifact 或 provider usage endpoints；
- `frontend/app/` 没有 report/artifact routes；
- Runtime 未处理 rich artifact/usage result；
- tests 没有完整 v2 fake flow。

## 6. Implemented Functional Capabilities

| Capability | 当前程度 | 说明 |
|---|---|---|
| Workflow definition/DAG validation | fully integrated | duplicate/missing dependency/cycle/kind/reference/retry/checkpoint validation |
| Deterministic scheduling | fully integrated | definition order + step ID fallback；one active node per run |
| Retry and recovery | integrated with warnings | retries create new attempts and checkpoints；delay 是 metadata，没有 `not_before` dispatcher |
| Checkpointing | fully integrated | append-only Domain checkpoints、hash verification、boundary records、restart reconstruction |
| Skill registration/execution | fully integrated for v1 | exact version、allow-list、schema validation、typed error |
| Research capability grants | contract-only substrate | deny-by-default provider/artifact capabilities；v2 Skills 未实现 |
| Approval pause/resume | fully integrated | durable request、fingerprint、approve/reject/expire-on-access、atomic resume/cancel |
| Event timelines | fully integrated | ordered contiguous audit stream exposed through API/UI |
| PostgreSQL persistence | fully integrated/historically verified | SQL UoW covers runs, steps, checkpoints, memory, artifacts metadata, approvals, events, provider operations |
| Optimistic concurrency | fully integrated | Domain row versions + repository persistence versions + SQLAlchemy mapper/version constraints |
| Idempotency | integrated | run creation、Step attempt、immutable checkpoint/artifact、approval decision、provider operation |
| Workflow catalog | integrated but restricted | lists persisted immutable definitions；只有 v1 admin seed，没有 general publication |
| Run create/list/detail/resume/cancel | fully integrated for inline definitions | API/UI available；no auth/project actor scope |
| Approval APIs/UI | fully integrated for prototype | no role authorization |
| Demo workflow | fully integrated | v1 only；fake paper titles + fake summary |
| Artifact metadata | implemented, not user-visible | repository/ORM/migration present；v1 Runtime 不产 artifact |
| Artifact content | adapter/gateway only | local immutable storage and verification tests；no Runtime/API/UI |
| Research contracts | contract-only | typed/canonical/immutable；not workflow outputs |
| Fake research providers | fake-only | direct adapter tests；not composed into v2 DAG |
| Provider budget reservation/settlement | persistence/service implemented | historical SQL acceptance；not used by a complete provider-call path |
| Provenance validation | pure contract-level | fail-closed fixture tests；not terminal workflow gate |
| Real provider capability | not implemented | no SDK/client/key/network/live test |

## 7. Current Workflows

### Seedable/catalog workflow: `guided-literature-review@1.0.0`

- Fixture：`demo/workflows/guided_literature_review.v1.json`
- Seeder：`backend/demo/seed.py`
- Canonical normalized definition hash：`2e58bc1702f0393230c7f0e76d64f4b35684b709abf0597352498d508f45457f`
- Raw JSON file byte hash 与 canonical hash 不同；系统以 normalized document hash 为准。
- Steps：
  1. `search` -> `mock_paper_search@1.0.0`
  2. `approve_sources` -> approval policy `project_reviewer`
  3. `summarize` -> `mock_summary@1.0.0`
- Input：required string `query`，demo default `persistent research agents`
- Output：`summary = ${nodes.summarize.outputs.summary}`
- Approval boundary：search 后、summary 前。v1 approval `input_mapping` 为空，因此不是 paper-record candidate preview。
- Provider status：fake Skill only；没有 PaperSearchProvider 或 LLMProvider 调用。
- API visibility：只有先通过 seed 或 run creation 将 definition 持久化后，`GET /workflows` 才可见；API 不自动 seed。
- Evidence：
  - backend/HTTP/PostgreSQL：历史 real integration passed；
  - browser：历史 Playwright real-stack 1 passed；
  - Docker：未验证。

### `guided-literature-review@2.0.0`

- 只存在于 `.agent_read/progress/real_research_vertical_slice_contract.md` 的 documentation contract。
- Proposed steps：`validate_query -> search_papers -> normalize_and_deduplicate -> rank_and_select -> approve_sources -> retrieve_source_content -> summarize_sources -> synthesize_findings -> generate_report -> persist_artifacts`。
- 当前没有 JSON/YAML definition、canonical published hash、seed、registered Skill implementations、catalog row、API/UI 或 E2E。
- 状态：`NOT_IMPLEMENTED`，不得作为 current workflow 描述。

### Test-local definitions

tests 中按场景即时构造 `linear`、`diamond`、`retry`、`approval`、`mock-literature-review`、`research-approval-binding`、`adapter-contract-workflow` 等 Workflow。它们用于 state/contract tests，不是 repository workflow assets，不可 seed，不通过 production API catalog 独立发布，因此不计为产品 workflow catalog。

## 8. Data and Persistence State

PostgreSQL 是 lifecycle、recovery、event、approval、artifact metadata 和 provider-operation 的 durable authority；对应代码在 `backend/database/`，schema authority 是 Alembic。

### Migrations and head

- `20260721_0001_initial_persistence.py`
- `20260721_0002_provider_operations.py`
- Static `alembic heads` 本次返回：`20260721_0002 (head)`

Head 下 11 个 application tables：

1. `workflow_definitions`
2. `workflow_runs`
3. `agent_sessions`
4. `workflow_step_runs`
5. `checkpoints`
6. `checkpoint_records`
7. `memory_revisions`
8. `artifacts`
9. `approval_requests`
10. `execution_events`
11. `provider_operations`

### `provider_operations`

该表由 migration 0002 创建，记录 project/run/logical step/optional StepRun、provider category/identity/adapter/model、idempotency key、request fingerprint、reservation、actual usage、failure、retry、timestamps、domain row version 和 persistence version。状态为 `RESERVED|RUNNING|SUCCEEDED|FAILED|CANCELLED`，settlement 为 `UNSETTLED|SETTLED|RELEASED`。历史 Phase 9A-1.5 在真实 PostgreSQL 上验证了 reservation、settlement、idempotency、optimistic race、rollback、foreign keys 和 unsettled provenance gate。

### Artifact metadata versus bytes

- `ArtifactRepository` / `artifacts`：metadata only，包括 relative `storage_ref`、checksum、media type、size、producer。
- `ArtifactContentStorage`：artifact bytes。
- `LocalFilesystemArtifactStorage`：注入 root，relative POSIX key，拒绝 absolute/`..`/backslash/symlink escape，temp write + fsync + checksum + immutable hard-link claim，同内容 replay idempotent。
- `ArtifactApplicationGateway`：先写 bytes，再 stage metadata；调用者负责 UoW commit。
- 当前没有 artifact HTTP endpoints，v1 demo 也不产出 artifact content。

Filesystem 与 PostgreSQL 不能原子提交：byte write 成功后若 DB transaction rollback，会留下 API 不可发现的 orphan；当前没有 orphan garbage collection。反方向若 metadata 指向缺失/损坏 bytes，`read_verified()` fail closed。这是已知 architecture limitation，不是 defect fix 已完成。

### Checkpoint、memory、events、approval

- Checkpoints append-only、sequence-ordered、parent-linked、SHA-256 integrity protected。
- `checkpoint_records` 可对同一个 Domain checkpoint 记录多个 Runtime boundaries。
- `memory_revisions` 是 project/run-scoped append-only working context，不是 long-term semantic memory。
- Events 是 run-scoped contiguous audit stream。
- Approval request 独立 optimistic version，fingerprint 绑定 action，持久化 resolver/reason/idempotency。

### Optimistic concurrency、idempotency、transaction

- Domain mutable entities 使用 `row_version`。
- Workflow aggregate、ApprovalRequest、ProviderOperation 另有 `persistence_version`。
- SQL UoW 在 one Session/transaction 中按 FK dependency order flush。
- Runtime commit 将 workflow state、checkpoints、memory、approval 和 events 放入同一 UoW transaction。
- Provider external I/O 和 filesystem content 不可能与 PostgreSQL transaction 原子化；provider call 通过 durable pre-call reservation 缩小风险。

### Known local databases（仅依据现有证据）

- `ProjectDB`：与 ReAgent 无关的用户数据库；**未经明确 owner approval，绝不能用于项目测试、migration、truncate、reset 或 drop**。
- `reagent_9a1_acceptance`：Phase 9A-1.5 创建的 isolated acceptance database；历史报告说保留在 `20260721_0002` head，包含一个 v1 deterministic workflow/run 作为验收证据。本次未连接或重新检查。
- `reagent_test`：Compose 设计会创建的 isolated integration-test DB；Docker 从未运行，不能据此断言当前存在。
- `reagent_acceptance`：environment audit 中仅是 owner-operated proposal；没有创建证据。
- 没有 Phase 9A-1.5 之后更晚的 acceptance database 证据。

## 9. API and Frontend Contract

本次通过 `app.openapi()["paths"]` 确认的 FastAPI endpoints：

### Health

- `GET /health`

### Workflows

- `GET /workflows`

### Runs

- `GET /runs`
- `POST /runs`
- `GET /runs/{workflow_run_id}`
- `GET /runs/{workflow_run_id}/events`
- `POST /runs/{workflow_run_id}/resume`
- `POST /runs/{workflow_run_id}/cancel`

### Approvals

- `GET /approvals`
- `POST /approvals/{approval_id}/approve`
- `POST /approvals/{approval_id}/reject`

### Artifacts

- 当前没有 endpoint。

### Provider usage

- 当前没有 endpoint。

`POST /runs/from-catalog`、`GET /runs/{id}/artifacts`、`GET /artifacts/{id}`、`GET /artifacts/{id}/content`、`GET /runs/{id}/provider-usage` 和 provider retry 均只在 Phase 9A-0 contract 中 proposed，源码中不存在。

### Frontend routes

- `/`
- `/workflows`
- `/runs/[id]`
- `/approvals`

没有 report page、artifact page、project page 或 auth page。

### Frontend integration

- `frontend/api/client.ts` 是唯一直接调用 `fetch` 的 product module，使用 typed methods 和 `ApiError`。
- TanStack React Query 负责 query/mutation/cache invalidation。
- Active run 和 events 每 3 秒 polling；pending approvals 每 5 秒 polling。
- `frontend/next.config.ts` 把 same-origin `/backend/:path*` rewrite 到 `REAGENT_API_URL`。
- 创建 run 是 `POST /runs` 后 `POST /runs/{id}/resume` 两次调用。
- mutation 使用固定 prototype identities，如 `prototype-user` 和 `prototype-reviewer`。
- 当前没有 streaming、SSE/WebSocket、offline behavior、report Markdown sanitization、artifact downloads 或 candidate-paper approval UI。

## 10. Testing Evidence

下表严格区分本次执行和历史证据。

| Command / test | Environment | Most recent known result | 新执行/历史 | Passed | Skipped | Database | 限制 |
|---|---|---|---|---:|---:|---|---|
| `pytest -q backend -rs` | `reagent-dev`, Python 3.11.15 | `109 passed, 14 skipped in 0.73s` | 本次 2026-07-27 | 109 | 14 | none | 13 SQL tests 因无 `REAGENT_TEST_DATABASE_URL` skip；1 destructive HTTP test 因无 E2E URL/reset opt-in skip |
| `python -m compileall -q backend` | `reagent-dev` | exit 0, no output | 本次 | n/a | n/a | none | 只验证 import/bytecode compilation |
| `alembic heads` | `reagent-dev` | `20260721_0002 (head)` | 本次 | n/a | n/a | none | static head discovery，不是 migration execution |
| `npm test` | local Node 25.2.1/npm 11.6.4 | 4 files, 5 tests passed | 本次 | 5 | 0 | none | component tests only |
| `npm run lint` | same | exit 0 | 本次 | n/a | n/a | none | no formal accessibility audit |
| `npm run build` | same, Next 16.2.10 | first sandbox attempt failed because Turbopack could not bind internal port；approved local rerun passed, generated 4 product routes + `_not-found` | 本次 | n/a | n/a | none | success required sandbox-external local execution |
| Focused persistence/research | `reagent-dev` | `47 passed` | historical Phase 9A-1.5 | 47 | 0 | none | contract tests only |
| PostgreSQL adapter suite | PostgreSQL 18.1, `reagent_9a1_acceptance` | `13 passed` | historical Phase 9A-1.5 | 13 | 0 | isolated DB | tests truncate only designated isolated schema |
| Full backend with all DB/E2E vars | PostgreSQL 18.1, same isolated DB | `123 passed, 0 skipped` | historical Phase 9A-1.5 | 123 | 0 | `reagent_9a1_acceptance` | destructive opt-in was explicit；not rerun now |
| Alembic upgrade/downgrade/check | PostgreSQL 18.1 | base -> head、head -> base、base -> head；two `alembic check` clean | historical Phase 9A-1.5 | n/a | 0 | `reagent_9a1_acceptance` | not rerun now |
| HTTP/PostgreSQL integration | FastAPI TestClient + SQL UoW | v1 create -> approval -> completion -> restart/no-op passed within full suite | historical Phase 8B/9A-1.5 | 1 scenario | 0 when enabled | isolated DB | only v1 fake summary |
| Playwright real-stack E2E | system Chrome + Next.js + FastAPI + PostgreSQL | `1 passed in 3.9s`；5 screenshots | historical Phase 8B | 1 | 0 | temporary isolated Phase 8B DB | not rerun now；not v2 |
| Compose YAML/shell syntax | Ruby YAML parser + `sh -n` | passed | historical Phase 8B | n/a | n/a | none | not equivalent to Docker Compose validation |
| `make demo-config-check` | Docker | failed: `docker: No such file or directory` | historical；本次也确认 docker command absent | 0 | n/a | none | image build/start/health/reset never run |

本次没有设置 `REAGENT_DATABASE_URL`、`REAGENT_TEST_DATABASE_URL`、`REAGENT_E2E_DATABASE_URL` 或 `REAGENT_ALLOW_DATABASE_RESET`，因此没有创建、reset 或修改数据库。

最强已验证 end-to-end path 是历史 Phase 8B：

```text
Next.js browser
-> FastAPI
-> Application Services
-> SyncExecutionDispatcher
-> AgentRuntime
-> Workflow Engine + fake Skills
-> SQLAlchemy UnitOfWork
-> PostgreSQL
-> Approval pause/approve
-> Completion
-> ordered events
-> application restart/browser reload
```

没有更晚的 research artifact/provenance browser path。

## 11. Environment and Dependency Management

### Python / Conda

- Canonical environment：`environment.yml`
- Conda env：`reagent-dev`
- Python：3.11.15
- Direct declarations：Python 3.11、pytest 8.4、SQLAlchemy 2、Alembic、psycopg 3、FastAPI、Pydantic 2、Uvicorn、httpx2。
- 本次版本：SQLAlchemy 2.0.51、Alembic 1.18.5、psycopg 3.3.4、FastAPI 0.139.2、Pydantic 2.13.4、Uvicorn 0.51.0。
- 没有 requirements.txt、pyproject dependency manifest 或 exact Python lock file。
- backend Dockerfile 直接从同一 `environment.yml` 创建 environment。

警告：当前 Conda env 同时装有 `httpx 0.28.1` 和 declared `httpx2 2.7.0`。历史说明 `httpx` 是旧环境 revision 遗留，没有用 `--prune` 清除；本次未修复。

### Node / npm / Playwright

- Local Node：25.2.1
- Local npm：11.6.4
- Docker Node：24.14.1
- `frontend/package.json`：Next 16.2.10、React 19.2.4、React Query 5.101.3、TypeScript 5、Tailwind 4、Vitest 4.1.10、Playwright 1.61.1。
- `frontend/package-lock.json`：lockfile v3，550 package records；npm resolution authority。
- 没有 `.nvmrc`、`engines` 或 `packageManager`，因此 local/Docker Node mismatch 未被工具强制。

警告：`npm ls --all --json` 本次仍返回 `ELSPROBLEMS`：5 个 optional WASM packages extraneous，且 hoisted `fsevents@2.3.3` 与 Playwright nested request 不一致。unit/lint/build 仍通过；本次没有运行 `npm ci` 或修复 dependency tree。

### Docker / Compose / PostgreSQL

- Dockerfiles 和 `compose.yaml` 已实现。
- Compose services：`db`、one-shot `migration`、one-shot `seed`、`backend`、`frontend`、profile-only `integration-test`。
- PostgreSQL image：`postgres:18.4-alpine3.23`；named volume：`reagent_postgres_data`。
- 本次环境仍没有 `docker` command；Docker runtime 状态完全未验证。
- Local historical acceptance 使用 Homebrew PostgreSQL 18.1，不等于 Compose PostgreSQL 18.4 验收。

### Environment variables

- Root `.env.example` 定义 Compose-only development placeholders。
- `REAGENT_DATABASE_URL` 供 API/migration/seed。
- `REAGENT_TEST_DATABASE_URL` 和 `REAGENT_E2E_DATABASE_URL` 必须指向 disposable isolated DB。
- `REAGENT_ALLOW_DATABASE_RESET=1` 是 destructive integration test 的显式 opt-in。
- `frontend/.env.example` / `REAGENT_API_URL` 控制 rewrite。
- Real provider env/key 尚未定义。

### Makefile and DEMO.md

`Makefile` 是 root lifecycle interface：demo configure/check/start/stop/reset/seed/status/logs，backend compile/test，frontend test/lint/build，integration 和 E2E。`DEMO.md` 描述 local Conda 和 Docker v1 workflow。注意 `DEMO.md` 的 “no artifact byte store” limitation 在 Phase 9A-1 之后已过时：byte store substrate 现已存在，但仍未接 demo/API/UI。

## 12. Repository and File Structure

```text
ResearchAgent/
├── .agent_read/
│   ├── AGENT.md
│   ├── context.md
│   ├── decisions/
│   └── progress/
├── backend/
│   ├── domain/
│   ├── workflow_engine/
│   ├── skill_system/
│   ├── agent_runtime/
│   ├── persistence/
│   ├── database/
│   │   └── migrations/versions/
│   ├── execution_events/
│   ├── application/
│   ├── api/
│   ├── demo/
│   ├── integration/
│   └── research/
├── demo/
│   ├── workflows/
│   └── postgres/
├── docker/
├── frontend/
│   ├── app/
│   ├── api/
│   ├── components/
│   ├── types/
│   └── tests/
├── docs/
├── runtime_data/        # intended ignored runtime root; currently absent
├── alembic.ini
├── environment.yml
├── compose.yaml
├── Makefile
└── DEMO.md
```

- `.agent_read`：跨会话 durable handoff/ADR/progress。23 个现有文件 tracked；6 个 Phase 9 文档和本报告是 untracked。
- `backend`：modular-monolith backend，当前实际布局不是最初合同建议的 `backend/src/reagent/`。
- `frontend`：独立 Next.js consumer。
- `demo`：唯一 seedable v1 Workflow 和 Compose test DB init。
- `docker`：backend/frontend images。
- `runtime_data`：ignored runtime output；`LocalFilesystemArtifactStorage` 默认设计使用 `runtime_data/artifacts`，当前不存在。
- `migrations`：`backend/database/migrations/versions/`。
- `tests`：各模块 colocated tests，另有 `backend/integration/tests/` 和 `frontend/tests/e2e/`。

Generated/ignored：

- `.pytest_cache/`
- Python `__pycache__/`、`*.pyc`
- `frontend/node_modules/`
- `frontend/.next/`
- `frontend/playwright-report/`
- `frontend/test-results/`
- `frontend/next-env.d.ts`
- local `.env*`（`.env.example` 除外）
- `/runtime_data/`、`/uploads/`、`/generated_artifacts/`

这些 generated files 可再生，但历史 Playwright screenshots/reports 也是验收证据；不得在未备份/确认前执行 broad clean。

### Git safety snapshot

- `git status --short`：31 个 tracked modified files；32 个 untracked files（展开目录计数，包含本报告）。
- `git log --oneline --decorate -n 10` 实际只有：
  - `469beeb (HEAD -> main, origin/main, origin/HEAD) demo version`
  - `cb598d7 Initial commit`
- `git ls-files | wc -l`：248。
- `.agent_read` 不是整体 ignored；HEAD 中有 23 个 tracked files。当前 ADR 0003、5 个 Phase 9 progress reports 和本报告仍 untracked。
- ignored generated state 包括上述 Python/frontend caches、reports 和 dependency/build trees；其中 Playwright output 可能仍含历史人工验收证据。
- `469beeb` 是适合 Phase 8B 的 baseline，但不是 Phase 9A-1/1.5 的 current baseline。未提交 source、migration、ADR 和 acceptance reports 存在被 `git clean`、reset 或错误 checkout 丢失的风险；在继续编码前必须先由 owner 审查并保护。

## 13. Current Limitations and Risks

### Architecture and Runtime

| 风险 | 分级 | 说明 |
|---|---|---|
| `SyncExecutionDispatcher` 在 HTTP request 内执行 | blocking next production milestone；对 Phase 9A-2 non-blocking | fake bounded demo 可用，real long run/traffic 不可用 |
| 无 durable worker/queue/lease/claim/fencing | deferred production concern | crash/retry timing/parallel execution 无调度基础 |
| retry delay 不被 clock/dispatcher 强制 | non-blocking warning for fake milestone | 下一次显式 resume 可立即继续 |
| sync repositories 在 async route 中调用 | deferred production concern | 高并发会阻塞 event loop |
| Runtime 忽略 rich artifact/usage results | **blocking Phase 9A-2** | v2 artifact 和 provider-operation 无法贯通 |
| static sequential DAG only | non-blocking warning | v2 contract 本身是 sequential，故不阻塞下一里程碑 |
| events 不是 outbox | deferred production concern | 无 notification delivery/consumer dedup |

### Product

| 风险 | 分级 | 说明 |
|---|---|---|
| 无 authentication/authorization/role enforcement | non-blocking for trusted fake milestone；blocking shared deployment | fixed prototype identities |
| 无 Project/User persistence 和 multi-user isolation | deferred production concern | 仅字段级 `project_id` |
| 无 general workflow publication/admin | non-blocking warning | 当前 seed 只允许一个 v1 hash |
| artifact lifecycle 无 retention/delete/orphan cleanup | non-blocking fake milestone warning；deferred production concern | local bytes 可 orphan |
| 无 artifact/report UI | **blocking Phase 9A-2** | 必须完成最小 report/artifact experience |

### Research Capability

| 风险 | 分级 | 说明 |
|---|---|---|
| v2 Workflow/Skills 未实现 | **blocking Phase 9A-2** | 当前最核心缺口 |
| fake providers 只做 direct contract tests | **blocking Phase 9A-2** | 未被 Skill/Runtime 调用 |
| 未选 first paper provider / fallback | non-blocking for Phase 9A-2；blocks real adapter |
| 未选 LLM provider/model/key/cost | non-blocking for Phase 9A-2；blocks live LLM |
| source scope/retention/excerpt policy 未定 | non-blocking for synthetic fake；blocks real content |
| provenance validator 未接 terminal completion | **blocking Phase 9A-2** | 当前只有 fixtures |
| 无 live provider verification | deferred until deterministic v2 passes | 不得提前做 real integration |

### Operations

| 风险 | 分级 | 说明 |
|---|---|---|
| Docker/Compose 未执行 | non-blocking for local Phase 9A-2；blocking clean-machine acceptance | 当前 docker unavailable |
| 无 cloud deployment/TLS/secret manager/backups | deferred production concern | prototype only |
| 无 monitoring/tracing/alerts | deferred production concern | 只有 audit events |
| 无 retention/orphan cleanup | deferred production concern | filesystem/DB atomicity limitation |
| Playwright 当前只覆盖 v1 Chrome | **blocking v2 browser gate** | 新 fake research E2E 必须增加 |

### Environment and Git

| 风险 | 分级 | 说明 |
|---|---|---|
| httpx/httpx2 drift | non-blocking warning |
| local Node 25 vs Docker Node 24 | non-blocking warning；Docker acceptance risk |
| optional `node_modules` drift | non-blocking warning；clean reproducibility risk |
| 无 exact Python lock | deferred CI/production concern |
| 当前 31 tracked modifications + 32 untracked files（含本报告） | **blocking safe continuation** | Phase 9A-1/1.5 工作可能被 clean/reset 删除 |
| HEAD 只有 Phase 8B baseline | **blocking appropriate current-phase baseline** | 当前 phase 无 Git commit |
| retained `reagent_9a1_acceptance` | non-blocking warning | 必须只按 isolated test DB 管理 |

## 14. Open Owner Decisions

| 决策 | 当前推荐 | Alternatives | 是否阻塞立即下一里程碑 |
|---|---|---|---|
| First Paper Search Provider | 暂不选择；v2 fake 完成后，按当时官方文档验证 OpenAlex | Semantic Scholar；Crossref enrichment | 否；阻塞 real adapter |
| Fallback Paper Search Provider | 条件推荐 Semantic Scholar | Crossref 或无自动 fallback | 否 |
| First LLM Provider/model | 暂不选择；v2 fake 后再按官方文档选择 structured-output model | Anthropic；explicit local model | 否；阻塞 live LLM |
| API key availability | composition-injected secret，绝不进入 Workflow/checkpoint/artifact | managed secret store later | 否；阻塞 live tests |
| Cost cap per real run | real mode 默认 disabled；owner 明确 low decimal cap 后开启 | 更低/更高显式 cap | 否；阻塞 real mode |
| Source scope | abstract-first；只有明确允许才使用 full text | metadata+abstract only | 否；阻塞 real source policy |
| Artifact retention | user artifacts 随 run；source content 最短 retention | fixed days；manual deletion | fake 可用 synthetic data，不阻塞；real data 阻塞 |
| Citation style | deterministic numeric `[P1]` | author-year；CSL later | 应在 Phase 9A-2 开始时冻结；否则阻塞 report output contract |
| Recorded fixtures | synthetic fixtures first；real responses 必须 legal/terms review 后 sanitized | no real fixtures | 不阻塞 fake；阻塞 recorded-provider coverage |
| Source excerpt policy | fake 使用 synthetic excerpts；real 只允许短、policy-gated excerpts | summaries only | 不阻塞 fake；阻塞 real evidence retention |
| Authentication timing | Phase 9A-2 后、共享/公网部署前 | 与 worker 一并推进 | 否 |
| Durable worker timing | deterministic v2 完成后、real long run/team-hosted 前 | 先实现 worker，但价值较低 | 否 |
| Docker remediation timing | 作为并行/后续 environment acceptance，不阻塞 local fake v2 | 强制先修 Docker | 否 |
| Git baseline timing | **立即审查并保护 Phase 9A-1/1.5 工作** | commit、patch bundle、受控备份 | **是，阻塞安全编码** |

本报告不更新 provider 推荐为“当前可用事实”。Phase 9A-0 没有查官方 provider 文档；在进入 real adapter milestone 时必须重新验证官方 API、auth、pricing、rate limits、model availability、terms 和 data handling。

## 15. Immediate Next Milestone

### Recommendation

**Phase 9A-2 — Complete Deterministic Fake-Provider Guided Literature Review v2 Vertical Slice**

### Goal

用 deterministic synthetic data 把现有 research substrate 贯通为一个真正可运行、可审批、可下载、可 reload 的 v2 literature-review 产品路径，且零真实 provider、零 credential、零 network、零成本。

### Entry conditions

1. Owner 审查并保护当前未提交的 Phase 9A-1/1.5 changes；不得在现状上 `git clean`/`reset`。
2. 保持 ADR 0001–0003 accepted boundaries。
3. PostgreSQL entry gate 已由 Phase 9A-1.5 历史证据满足；后续测试必须使用明确 isolated DB，绝不使用 `ProjectDB`。
4. 使用 `reagent-dev` 和现有 frontend lock；不添加 dependency，除非 Phase 9A-2 经明确评审不可避免。

### Scope

- publish immutable hash-pinned `guided-literature-review@2.0.0`；
- 实现 contract 中全部 research Skills，使用 existing fake providers；
- 每个 fake provider call 执行 durable reservation -> running -> settlement；
- Runtime/application materialize all planned artifact bytes and metadata；
- provenance validation 在 completion 前 fail closed；
- catalog-pinned run creation、artifact list/metadata/content、provider usage API；
- v2 input form、candidate selection approval preview、report/citations/artifact UI；
- InMemory、PostgreSQL、HTTP 和 real-browser fake-provider acceptance；
- exact output/checksum/event/idempotency/reload assertions。

### Exclusions

- no real paper provider；
- no real LLM/provider SDK；
- no API key/network/live tests；
- no worker queue/lease；
- no authentication redesign；
- no S3；
- no Docker remediation；
- no dynamic DAG/parallel/multi-agent；
- no production retention system。

### Completion gates

1. v2 workflow/Skill references all immutable and seed-validated；
2. default fast backend suite green；
3. migration/check/provider-operation SQL contracts green on isolated PostgreSQL；
4. full fake v2 HTTP/PostgreSQL run passes：

   `topic -> search -> normalize -> rank -> approval -> retrieve -> summarize -> synthesize -> report -> artifacts -> completion`

5. every provider operation settled, no duplicate logical call；
6. report citations/claims/evidence/source hashes pass `ProvenanceValidator`；
7. artifact metadata/content checksums match after application reconstruction；
8. artifact/report endpoints never expose absolute paths；
9. frontend shows exact candidates, source scope, report, citations, artifacts and usage；
10. Playwright uses real Next.js/FastAPI/PostgreSQL/local artifact storage, no HTTP mocks，reload 后 artifact IDs/checksums 不变；
11. existing v1 demo/regression remains green；
12. `.agent_read/context.md` 和 milestone progress report 更新，必要 ADR 单独记录。

### Why this is the highest-value next step

Phase 9A-1/1.5 已经把高风险 contracts、budget ledger、storage 和 provenance validator 分别实现并验证，但没有产品价值闭环。直接做 real provider 会把网络、费用、schema drift 和数据权利问题叠加在尚未证明的 integration 上。Phase 9A-2 能以 deterministic data 验证所有新边界，形成唯一合理的 real-provider entry gate。

## 16. Exact Continuation Instructions

### 1. Files that must be read first

按顺序：

1. `docs/PROJECT_DEVELOPMENT_PLAN.md`
2. `.agent_read/AGENT.md`
3. `.agent_read/context.md`
4. `.agent_read/progress/current_project_status_handoff.md`
5. `.agent_read/progress/architecture_contract.md`
6. `.agent_read/decisions/0001-foundational-architecture.md`
7. `.agent_read/decisions/0002-psycopg3-and-synchronous-persistence-adapter.md`
8. `.agent_read/decisions/0003-real-research-provider-and-artifact-boundaries.md`
9. `.agent_read/progress/real_research_vertical_slice_contract.md`
10. `.agent_read/progress/real_research_contract_substrate.md`
11. `.agent_read/progress/postgresql_real_research_substrate_acceptance.md`
12. 当前 Git diff/status 和所有 `backend/research/`、Runtime、UoW、migration 0002、API、frontend source。

### 2. Frozen architecture boundaries

- Domain owns legal lifecycle only。
- Workflow Engine owns DAG scheduling、reference resolution、retry/approval/completion decisions。
- Skill System owns exact-version capability execution/schema validation。
- Runtime owns orchestration、events、checkpoint/memory/approval transactional coordination。
- Application owns use cases and transaction boundaries。
- API owns transport mapping only。
- ORM/provider SDK/concrete storage remain adapters/composition。
- PostgreSQL is lifecycle authority；artifact bytes stay behind `ArtifactContentStorage`。
- Frontend consumes HTTP only。
- 不得把 provider client、SQLAlchemy、FastAPI 或 filesystem adapter import 进 research Skills/core。

### 3. Database safety rules

- `ProjectDB` 永远不得用于 ReAgent test/migration/reset。
- 只使用名称和 URL 明确的 isolated disposable DB。
- destructive test 必须同时有 isolated `REAGENT_E2E_DATABASE_URL` 和 `REAGENT_ALLOW_DATABASE_RESET=1`。
- 运行前确认目标 database name；不要依赖模糊 env 或 shell default。
- 不要 drop `reagent_9a1_acceptance`；除非 owner 明确授权并确认不再需要证据。
- Alembic 是 schema authority；application 不得 `create_all()`。

### 4. Environment rules

- Python command 通过 `conda run --no-capture-output -n reagent-dev ...`。
- 不安装 dependency，不清理 Conda/npm cache，不运行 `npm ci`，除非 owner 另行授权。
- 保留已知 httpx/httpx2、Node/Docker Node 和 node_modules warnings；不要在 Phase 9A-2 顺手 remediation。
- Docker 当前不可用，不要把 Docker remediation 混入 milestone。
- Real provider mode 保持 disabled；不要创建 secrets/env key。

### 5. Git safety rules

- 当前 HEAD：`469beeb demo version`；当前工作树有 31 tracked modifications 和 32 untracked files（含本报告）。
- Phase 9A-1/1.5 source、migration、ADR/progress 多数未提交。
- 开始前运行 `git status --short`、`git status --ignored --short`、`git diff --stat`。
- 不得 `git clean`、`git reset --hard`、`git checkout --`、删除 untracked research files 或覆盖 user changes。
- 不得自行提交，除非 owner 明确要求；如果 owner 要建立 baseline，应先确认 exact scope。
- `.agent_read` 可 track，但当前只有早期 23 个文件在 HEAD；Phase 9 文档和本报告需要保护。

### 6. What must not be implemented yet

- real OpenAlex/Semantic Scholar/Crossref adapter；
- real OpenAI/Anthropic/local model adapter；
- credentials、live network、billable test；
- durable worker/Redis/queue；
- auth/multi-tenant redesign；
- S3/object storage；
- Docker remediation；
- dynamic graph/condition/loop/parallel/multi-agent；
- full-text scraping/paywall bypass；
- production retention/deletion system；
- general workflow editor/publication redesign。

### 7. Evidence required at completion

返回：

1. exact files changed；
2. v2 workflow ID/version/canonical hash/step/Skill table；
3. architectural boundary statement；
4. backend fast test command/result/skips；
5. compile result；
6. isolated PostgreSQL DB name（redact password）；
7. Alembic heads/current/check and migration replay evidence；
8. SQL provider-operation tests and full backend result；
9. exact HTTP fake v2 flow result；
10. artifact list、IDs、checksums、content verification；
11. provider operation reservation/settlement/idempotency evidence；
12. provenance validation result and deliberate negative test；
13. frontend unit/lint/build；
14. Playwright real-stack result、screenshots、reload identity checks；
15. confirmation that no real provider/SDK/key/network was used；
16. final `git status --short`；
17. updated `.agent_read/context.md` and new milestone progress report。

## 17. 可直接复制到新对话的项目上下文

ReAgent 是一个面向长期研究任务的 Web-based persistent research agent platform。最终产品不是聊天机器人，而是允许用户创建 research project、上传材料、选择版本化 Workflow、启动长时间运行的 Agent、观察进度、处理 human approval、在重启后从 checkpoint/memory 恢复，并获得带 citation、evidence 和 provenance 的版本化 research artifacts。产品来源是 `docs/PROJECT_DEVELOPMENT_PLAN.md`；冻结架构是 `.agent_read/progress/architecture_contract.md` 和 ADR 0001–0003。

当前后端采用 modular monolith + ports/adapters。依赖方向是：Next.js -> FastAPI -> Application Services -> ExecutionDispatcher -> AgentRuntime -> Workflow Engine / Skill System -> Domain -> Persistence Ports / UnitOfWork -> SQLAlchemy/PostgreSQL；artifact bytes 单独通过 `ArtifactContentStorage`。Domain 只拥有合法 lifecycle；Workflow Engine 拥有 static DAG scheduling、reference resolution、retry/approval/completion decisions；Skill System 拥有 exact-version capability execution；Runtime 负责 orchestration、checkpoints、memory、events、approval 和 UoW commit；Application 负责 use cases；API 只做 transport；ORM、provider SDK 和 concrete storage 只能在 adapters/composition。

Phase 0/Architecture Contract、Domain Core、Workflow Engine、Skill System、Agent Runtime、Persistence Foundation、Events/Approval、PostgreSQL、Application/API、Frontend 和 Phase 8B supervised E2E demo 均已完成。当前可验证产品是 `guided-literature-review@1.0.0`：`search` 使用 `mock_paper_search@1.0.0`，随后 `approve_sources` 暂停，审批后 `summarize` 使用 `mock_summary@1.0.0`，最终 summary、events 和状态保存在 PostgreSQL。历史 Phase 8B 使用真实 Next.js、FastAPI、PostgreSQL 和 system Chrome 完成 create -> approval -> completion -> reload；Docker/Compose 从未运行成功。

Phase 9A-0 只冻结了 `guided-literature-review@2.0.0` 的 contract，不是实现。Phase 9A-1 已实现 provider-independent research substrate：immutable `ResearchQuery`、`PaperRecord`、`SourceContent`、`RankedPaper`、`CitationReference`、`EvidenceUnit`、`GroundedClaim`、`ResearchReport`、`ProviderUsage`、`ProviderOperation` 和 `ProvenanceManifest`；`PaperSearchProvider`、`SourceContentProvider`、`LLMProvider`、`ArtifactContentStorage` ports；deterministic synthetic providers；`LocalFilesystemArtifactStorage`；`ProviderOperationService`；Engine-resolved approval inputs；deny-by-default Skill capabilities；fail-closed `ProvenanceValidator`。Alembic `20260721_0002` 增加 `provider_operations`。Phase 9A-1.5 在 isolated PostgreSQL 18.1 database `reagent_9a1_acceptance` 上历史验证 migration replay、SQL adapter、budget settlement、optimistic concurrency、rollback、foreign keys 和 provenance unsettled gate，完整 backend 当时 `123 passed, 0 skipped`。

当前实际阶段是“Phase 9A-1.5 completed，等待 Phase 9A-2”。Phase 9A-2 尚未开始：仓库只有 v1 Workflow fixture/seed；没有 v2 Workflow、没有 research Skills、没有 artifact/provider-usage APIs、没有 report/artifact frontend routes；Runtime 也没有处理 `SkillResult.emitted_artifacts` 和 `provider_usage`。因此项目成熟度只能称为 supervised full-stack demo，不能称为 deterministic research vertical slice 或 production-ready platform。

立即下一里程碑必须是 Phase 9A-2 Complete Deterministic Fake-Provider Guided Literature Review v2 Vertical Slice。目标是用零网络、零 credential、零真实 provider、零成本的 synthetic providers，完成 topic -> search -> normalize -> rank -> candidate approval -> abstract retrieval -> structured summaries -> synthesis -> grounded report -> immutable artifacts -> API read/download -> frontend report/citations -> reload persistence。每个 fake provider call 必须先 durable reserve budget，再 running/settle；所有 citation、claim、evidence、source hash 和 artifact checksum 必须通过 `ProvenanceValidator`；Playwright 必须走真实 Next.js/FastAPI/PostgreSQL/local artifact storage，不能 mock HTTP。完成 deterministic v2 前，不得做 real provider integration。

Open owner decisions 包括 first paper provider、fallback、first LLM/model、API key、real-run cost cap、abstract/full-text scope、retention、source excerpt、recorded fixtures、citation style、authentication、durable worker 和 Docker remediation。这些不阻塞 fake Phase 9A-2，但阻塞后续 real provider 或 shared production use。进入 real adapter milestone 时必须重新查当前官方文档，不能沿用未验证的旧推荐。

数据库安全：`ProjectDB` 是无关用户数据库，绝不能用于 ReAgent migration/test/reset/drop。只允许明确命名的 isolated disposable DB；destructive HTTP test 需要 isolated `REAGENT_E2E_DATABASE_URL` 和 `REAGENT_ALLOW_DATABASE_RESET=1`。`reagent_9a1_acceptance` 是历史保留验收 DB，不得擅自删除。环境使用 Conda `reagent-dev` 和 `environment.yml`；不要安装依赖或顺手清理已知 httpx/httpx2、Node 25 vs Docker Node 24、node_modules optional drift。Docker 当前不可用。

Git 当前非常重要：HEAD `469beeb demo version` 只代表 Phase 8B；Phase 9A-1/1.5 有大量 tracked modifications 和 untracked files，尚无 current-phase baseline。开始任何编码前必须 `git status`/`git diff`，保护这些文件；不得 `git clean`、`git reset --hard`、checkout 丢弃或删除 untracked research/migration/ADR/progress。是否 commit 必须由 owner 明确授权。

项目协作方式是 ChatGPT Web planning + Codex CLI execution：ChatGPT Web 用于 milestone scope、owner decisions 和 architecture review；Codex CLI 按仓库真实状态实现、测试并返回精确证据。每个 milestone 完成后，Codex 必须更新 `.agent_read/context.md`，新增/更新 `.agent_read/progress/` 报告；只有明确接受的 consequential decision 才写 ADR。下一 agent 首先阅读 `docs/PROJECT_DEVELOPMENT_PLAN.md`、`.agent_read/AGENT.md`、`.agent_read/context.md`、本 handoff、architecture contract、ADR 0001–0003、Phase 9A contract/substrate/acceptance reports，然后再看 Git diff 和源码。
