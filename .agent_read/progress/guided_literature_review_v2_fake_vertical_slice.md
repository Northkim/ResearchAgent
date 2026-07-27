# Phase 9A-2：Deterministic Fake-Provider Guided Literature Review v2

日期：2026-07-27  
状态：**COMPLETED / PASS**

## 1. 目标与结论

本阶段把 Phase 9A-1/1.5 的 provider-independent research substrate 连接成
一个真实可见、可暂停审批、可恢复读取的完整垂直切片。执行中没有真实网络、
API key、provider SDK、真实论文 API 或真实 LLM；paper metadata、abstract、
summary 和 finding 均为 deterministic synthetic fixture。

真实执行路径：

```text
Next.js
→ FastAPI
→ Application Services / SyncExecutionDispatcher
→ AgentRuntime
→ Workflow Engine
→ versioned Research Skills
→ deterministic Fake Providers
→ durable ProviderOperationService
→ SQLAlchemy / PostgreSQL
→ LocalFilesystemArtifactStorage
→ ProvenanceValidator publication gate
→ report/artifact UI
→ reload
```

没有修改 Domain lifecycle、Workflow Engine decision ownership、Skill System
execution ownership、Agent Runtime orchestration ownership或 persistence port
semantics；没有新增 migration，Alembic head 仍为 `20260721_0002`。ADR 0003
覆盖此次 additive wiring，因此没有新增 ADR。

## 2. Workflow definition

- ID/version：`guided-literature-review@2.0.0`
- fixture：`demo/workflows/guided_literature_review.v2.json`
- canonical SHA-256：
  `af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`
- source scope：`abstract_only`
- minimum selected papers：`3`
- live-provider budget：`0`

DAG 与 Skill references：

1. `validate_query` → `research.validate_research_query@1.0.0`
2. `search_papers` → `research.search_papers@1.0.0`
3. `normalize_and_deduplicate` → `research.normalize_paper_metadata@1.0.0`
4. `rank_and_select` → `research.rank_papers@1.0.0`
5. `approve_sources` → approval policy `project_reviewer`
6. `retrieve_source_content` → `research.retrieve_source_content@1.0.0`
7. `summarize_sources` → `research.summarize_papers@1.0.0`
8. `synthesize_findings` → `research.synthesize_literature@1.0.0`
9. `generate_report` → `research.generate_research_report@1.0.0`
10. `persist_artifacts` → `research.persist_research_artifacts@1.0.0`

Skill steps 都有固定 timeout、retry metadata 与 `after_success` checkpoint。
`backend/demo/seed.py` 保留 v1 并增加 v2；相同 definition 重复 seed 返回
unchanged，相同 ID/version 不同内容拒绝覆盖。seed 前验证 DAG、Skill
reference、required input schemas 和 capability registration。

## 3. Research Skills 与 provider lifecycle

实现位于 `backend/research/skills.py`。Skills 只使用
`SkillExecutionContext.capabilities`，不实例化 adapter、不读取环境变量，也不
导入 FastAPI、SQLAlchemy 或 ORM。

每次 fake provider invocation 都执行：

```text
reserve budget → commit
→ mark RUNNING → commit
→ invoke injected fake provider
→ settle actual zero-cost usage → commit
```

完整运行产生 9 个 ProviderOperations：1 search、3 abstract retrieval、3
grounded summaries、1 cross-paper synthesis、1 Markdown generation。全部为
`SUCCEEDED / SETTLED`，token/cost 为 0，`is_live_provider=false`。完成 run
再次 resume 不增加 Skill execution、event、artifact 或 reservation。

## 4. Exact approval binding

`approve_sources` 的 Engine-resolved inputs 包含 `query_hash`、exact
`selected_paper_ids`、selected PaperRecords、`selected_papers_artifact`
（ID/checksum/media type/size）、`ranker_version`、UI preview 和
`source_scope=abstract_only`。

Runtime canonical fingerprint 另外绑定 project ID、run ID、workflow
ID/version、approval step/StepRun/attempt、policy/role、expiry 和全部 pinned
Skill versions。`ApprovalDecisionService` approve 前读取 artifact metadata 和
bytes，并验证 bound checksum、paper IDs 与 preview。artifact corruption、
metadata mutation、paper-ID mutation 或 fingerprint mutation均 fail closed；
router 不包含 selection logic。

## 5. Artifacts 与 storage

- port：`ArtifactContentStorage`
- adapter：`LocalFilesystemArtifactStorage`
- 默认 root：`runtime_data/artifacts`
- acceptance roots：`/private/tmp/reagent_9a2_smoke.zysdSX`、
  `/private/tmp/reagent_9a2_browser.tDgk1W`

storage keys 全部 relative、immutable；API/events/frontend 不暴露
`storage_ref` 或绝对路径。write 后执行 checksum/size verification，Runtime
通过 `UnitOfWork.artifacts` 保存 metadata。

| logical name | kind | media type |
|---|---|---|
| `papers.json` | `candidate_papers` | `application/json` |
| `selected_papers.json` | `selected_papers` | `application/json` |
| `source_content.json` | `source_content` | `application/json` |
| `paper_summaries.json` | `paper_summaries` | `application/json` |
| `evidence.json` | `evidence` | `application/json` |
| `report.md` | `research_report` | `text/markdown; charset=utf-8` |
| `provenance.json` | `provenance` | `application/json` |
| `usage.json` | `provider_usage` | `application/json` |

最近 browser run `run_4b5324e25ac34f4ca22adbbeab7699af`：

- `papers.json`: `sha256:fe3b1714dfe3e84469b5af5fdf441cf62bc9ca80950ad855c2d0dba098101d29`
- `selected_papers.json`: `sha256:9e39e9442d4e1833b546a0c85f49f571175ed831213ed8f4f1cfccf3ef29d58d`
- `source_content.json`: `sha256:2e3faeb9d74c73585c478a0f40374cb34ca31e5c0b0011b5d7c5c95db9e88793`
- `paper_summaries.json`: `sha256:2cc26a56184ae8f2ab75dd929ebec77b49a8ba3c2b9c827fff07fbb39f5d22aa`
- `evidence.json`: `sha256:6aed52ad450df366da40fe1288ab9f19bc3d3eecebbaa43921ef1e9561130ce0`
- `report.md`: `sha256:74588045153915ceba300a4e7e849deb942a40d661577de2c69b7339655b2dd5`
- `provenance.json`: `sha256:e1e9e35c9d22f0656f7519ab4692aee46240ebea3fb88602591285ea8faaa155`
- `usage.json`: `sha256:dfdb93caab24173daab05ea72245b09a3e2f3f23ca48b78db33668e454b6d39a`

filesystem 与 PostgreSQL 无共同 transaction；immutable writes 使相同内容 retry
安全，但 DB rollback 后可保留 orphan bytes，系统不会静默删除未知文件。

## 6. Provenance publication gate

成功报告含 3 approved papers、3 abstract-only SourceContents、3 citations
`[P1]`–`[P3]`、3 EvidenceUnits 和 4 GroundedClaims（3 source statements +
1 cross-source synthesis）。gate 验证 minimum paper count、DOI uniqueness、
citations、claim/evidence 双向链接、SourceContent checksum、abstract scope、
workflow/Skill/prompt/provider/model versions、report/provenance links 和 settled
operations。

合法 manifest 为 `publishable=true`；fast test 把 selected count 改为 2 时得到
`PROVENANCE_VALIDATION_FAILED / INSUFFICIENT_SELECTED_PAPERS`，报告不发布。

## 7. Application、API 与 frontend

新增 application services：catalog-pinned run creation、run artifact list、
artifact metadata/content、provider usage。新增 API：

- `POST /runs/from-catalog`
- `GET /runs/{run_id}/artifacts`
- `GET /runs/{run_id}/provider-usage`
- `GET /artifacts/{artifact_id}`
- `GET /artifacts/{artifact_id}/content`

DTOs forbid unknown fields。content 使用正确 media type、ETag、`nosniff` 和 safe
Content-Disposition；missing 为 404，corruption 为 409；routes 不访问 ORM/
filesystem。

frontend 保持 `Pages → React Query hooks → typed API client → FastAPI`，没有
component direct fetch。增加 v2 input、candidate preview、report viewer、
citations、artifact/download、zero-cost usage、abstract-only notice、query states、
reload 和 mobile layout。

## 8. PostgreSQL 与 validation evidence

- database：`reagent_9a2_acceptance`
- retained size：`10214 kB`（最终读取）
- head：`20260721_0002`
- `ProjectDB`：未使用、未修改
- `reagent_9a1_acceptance`：未修改

完整 backend 命令使用 `reagent-dev`，同时显式设置 isolated PostgreSQL test、
E2E 和 9A-2 variables。结果：`130 passed, 0 skipped`，exit 0。

其他结果：

- compileall：exit 0
- frontend Vitest：`5 passed`，exit 0
- frontend ESLint：exit 0
- Next.js production build：exit 0
- targeted PostgreSQL/HTTP/filesystem v2：`1 passed`
- targeted Playwright v2 real stack：`1 passed`
- complete Playwright real stack：`2 passed`

Playwright 没有 mock HTTP；使用 real Next.js、FastAPI、PostgreSQL 和 filesystem。
HTML report 在 `frontend/playwright-report/index.html`，success attachments 含
workflow input、candidate approval、completed report、artifact/provenance ledger；
失败时保留 screenshot/trace/video。v2 最终经过 reload 与 390px mobile check。

最终数据库在完整 suite 重建后保留 1 个 completed v2 acceptance run 和 9 个
`SUCCEEDED/SETTLED` operations；smoke artifact root 为 `264K`，browser root 为
`312K`。

## 9. Cleanup state 与限制

保留 database 和上述两个 artifact roots；未执行 destructive cleanup。仅在 owner
明确丢弃 acceptance evidence 后可选：

```bash
dropdb reagent_9a2_acceptance
rm -rf /private/tmp/reagent_9a2_smoke.zysdSX
rm -rf /private/tmp/reagent_9a2_browser.tDgk1W
```

限制：fake evidence 不是科学证据；真实 provider/fallback/credentials/rate/terms
未验证；filesystem/PostgreSQL non-atomic；无 auth/multi-user isolation；同步 HTTP
execution；无 durable worker/lease/queue；无 retention/orphan sweeper；Docker
本阶段未修复或执行；Python 无 exact lock，Node/Docker 与 optional-dependency
drift 警告延续。

## 10. 下一里程碑

唯一建议：**supervised first real Paper Search Provider decision and adapter
verification**，不同时引入真实 LLM。

进入条件：owner 选择 primary/fallback provider，明确 key、per-run request/cost
cap、metadata+abstract policy、recorded fixtures、excerpt/retention/citation policy，
并查阅当前官方 API/rate/terms/attribution/error semantics。fake v2 regression、
provenance gate 和 zero-network fast tests 必须保持。真实 LLM、authentication、
worker、Docker remediation、S3 和 retention sweeper 继续延后。
