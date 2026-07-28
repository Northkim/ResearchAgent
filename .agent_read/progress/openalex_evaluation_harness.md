# Phase 9B-2A：OpenAlex Discovery Evaluation Harness and Retention Policy

日期：2026-07-28  
状态：**PASS**  
性质：evaluation infrastructure + synthetic validation；live pilot 未执行  
起始 baseline：`3d1e90a feat: validate supervised OpenAlex paper discovery`

## 1. 结论

ReAgent 已具备由人类评审 OpenAlex discovery candidate pool 的独立 evaluation
harness。它可生成 immutable candidate evidence、导出/导入 JSON/CSV human
review sheets、验证 adjudication、计算 deterministic retrieval/metadata/dedup/
operational/agreement metrics，并生成不含完整 abstract 的 evidence report。

该 harness 不属于 Agent Runtime lifecycle，不修改 Workflow Engine、Skill、
Domain 或 persistence semantics。它复用：

```text
versioned EvaluationTopic set
→ ResearchQuery / OpenAlex SearchPlan
→ existing PaperSearchProvider
→ existing ProviderOperationService + budget
→ evaluation-only append-only ProviderOperation journal
→ normalized PaperRecord
→ immutable ArtifactContentStorage manifests/checksums
→ human reviewer imports
→ human adjudication
→ pure EvaluationMetrics
→ deterministic evaluation report
```

系统没有生成 relevance labels，Codex 没有充当 reviewer/adjudicator。没有调用
Semantic Scholar、Crossref、real LLM、SourceContent/full text 或 PDF。

## 2. Git baseline gate

实施前：

- working tree clean；
- latest reviewed commit：
  `3d1e90a (HEAD/main/origin/main) feat: validate supervised OpenAlex paper discovery`；
- `.env` 命中 `.gitignore:39`，未 tracked；
- `runtime_data` 命中 `.gitignore:53`；
- tracked 环境文件只有 `.env.example` 和 `frontend/.env.example`；
- 没有 tracked live artifact path。

未 amend/rewrite baseline、未 `git clean`、未 reset、未 stage、未 commit。

## 3. Evaluation contracts

Pure package：`backend/research/evaluation/`。

Contracts：

- `EvaluationTopic`
- `EvaluationCandidate`
- `CandidateJudgment`
- `AdjudicatedJudgment`
- `EvaluationRun`
- `EvaluationMetricSummary`
- `MetricValue`

均为 frozen dataclass、JSON serializable、canonical SHA-256 capable。Candidate
identity hash 绑定 topic/candidate/PaperRecord/OpenAlex/search execution/provider/
adapter identity。Import 若 paper identity、metadata hash 或 execution ID 被改写
则拒绝。

Relevance labels：

- `HIGHLY_RELEVANT`
- `RELEVANT`
- `PARTIALLY_RELEVANT`
- `NOT_RELEVANT`
- `CANNOT_JUDGE`

Gain mapping `3/2/1/0` 是显式 ReAgent Class D policy；`CANNOT_JUDGE` 没有 gain，
不会被静默转成 0。

## 4. Topic set

Tracked source：
`evaluation/topics/openalex_v1.json`。

- ID/version：`reagent-openalex-engineering-evaluation@1.0.0`
- 12 topics；
- CS/AI、biomedical、social science、humanities、engineering、climate、
  interdisciplinary、Global South、Chinese/non-English；
- 包含 broad/narrow、terminology、abstract missingness、preprint/published
  manifestation 和 Unicode stress cases；
- 每题最多 20 candidates；
- topic itself 可 commit，live result 不可 commit。

这是 ReAgent engineering evaluation set，不是 universal benchmark。

## 5. Candidate pool

`CandidatePoolGenerator` 依赖 ports/services，不依赖 FastAPI、ORM 或 Runtime：

- `PaperSearchProvider`
- `ProviderOperationService`
- `ProviderExecutionPolicy`
- `ArtifactContentStorage`

每个 topic：

1. 生成 `ResearchQuery` 和 provider request fingerprint；
2. reserve budget 并 commit；
3. mark `RUNNING` 并 commit；
4. 调用 existing OpenAlex adapter；
5. settle success/failure 并 commit；
6. 只保留 normalized `EvaluationCandidate`；
7. 写 evaluation topic、SearchPlan/Execution/Statistics、candidate pool 和
   per-topic manifest；
8. 写 checksum、usage、operation ID/settled evidence；
9. top manifest 完成前检查 zero unsettled operations。

CLI 的 commit callback 写入 private mode-`0600`、append-only、checksum-chained
`provider_operations.journal.jsonl`。Reserve、RUNNING、settlement 是独立
`fsync` boundaries；restart 必须同时找到 journal 中同一 operation 的
`SUCCEEDED/SETTLED` 状态和 immutable topic receipt。Partial/tampered/stale
journal fail closed。

Journal concurrency 使用 POSIX `flock`，只验证当前 macOS/Linux
single-host supervised mode；不是 multi-host/production queue ledger。

Artifacts：

- `evaluation_manifest.json`
- per evaluation `provider_operations.journal.jsonl`（private audit，不是
  published artifact）
- per topic `evaluation_topic.json`
- per topic `search_plan.json`
- per topic `search_execution.json`
- per topic `search_statistics.json`
- per topic `candidates.json`
- per topic `topic_manifest.json`

Manifest 只含 relative storage keys。默认不保留 abstract preview；显式
`--include-abstract-preview` 最多 500 normalized chars，并受 retention policy
约束。Raw response body 不保留。

Resume：完整 manifest 存在时先验证所有 size/checksum 并重建 candidates，不调用
provider。Per-topic manifest 可跳过已经完成的 topic。若 operation 已 succeeded
但 immutable receipt 丢失，fail closed 而不是再次调用。Corrupted artifact
resume 拒绝。

## 6. Human review 与 adjudication

Export：

- JSON
- CSV

模板包含可读 topic title/query/research question、rank、title、year、authors、
venue、DOI、OpenAlex ID、
abstract availability、可选短 preview 和空 judgment fields。不会输出 key、DB
URL、absolute path、raw HTTP 或 provider diagnostics。

Import 验证：

- reviewer pseudonymous ID required；
- unknown candidate rejected；
- changed identity hash rejected；
- invalid/empty label rejected；
- duplicate `(candidate, reviewer)` rejected；
- partial sheet 可显式保留，`--require-complete` fail closed；
- input file checksum recorded；
- ranking score 不生成 label。

Adjudication 必须绑定至少两个 distinct reviewer judgment hashes。Unknown source
hash、candidate mismatch、duplicate candidate 或缺少 disagreement reason 均拒绝。

## 7. Metrics

Pure `EvaluationMetrics` 提供：

- Precision@5 / Precision@10；
- nDCG@10；
- pooled Recall@K（只有 supplied adjudicated denominator 才 available）；
- relevant-paper yield；
- judgment coverage；
- DOI/abstract/author/venue completeness；
- duplicate/unresolved/false-merge metrics；
- request/latency/retry/failure；
- manual-review burden；
- Cohen kappa。

Precision/nDCG 先按 topic 计算，summary 使用 per-topic median，并在
`per_topic_retrieval` 保留每题结果；不会把多个 topic 拼成一条全局 ranking。
每个 metric 包含 `available`、`value`、`sample_size`、`reason`。Zero candidates、
partial judgments、top-K `CANNOT_JUDGE`、invalid pooled denominator、reviewer
结构/sample 不足时返回 unavailable，而不是制造分母或 0。
Duplicate/false-merge evidence 未由 human adjudication 或明确计数提供时也返回
unavailable，不把缺失证据静默解释成零重复。

## 8. Report artifacts

`EvaluationReportGenerator` 生成：

- `topic_results.json`
- `metrics.json`
- `reviewer_agreement.json`
- `metadata_quality.json`
- `operational_metrics.json`
- `evaluation_report.md`

Candidate generator 已生成 required `evaluation_manifest.json`。Report 分开列出
measured results、reviewer judgments、proposed project thresholds、provider
contract facts、engineering inference 和 limitations。Markdown 不复制 full
abstract，不能自动 promote provider。

## 9. CLI

唯一 command interface：

```text
python -m backend.research.evaluation
```

Subcommands：

- `initialize`
- `generate`
- `export`
- `import`
- `adjudicate`
- `report`
- `status`
- `clean`

默认 root：`runtime_data/evaluations/openalex/`。Live `generate` 必须显式
`--live` 和 configured key，单次最多 3 topics。CLI 不打印 key。Cleanup 需要
`--confirm` exact evaluation ID，并拒绝 broad root。

当前 CLI 使用 configured isolated storage、existing
`ProviderOperationService` 和 evaluation-only journaled
`ProviderOperationRepository`；不新增 evaluation database/migration。Topic
receipt/top manifest + journal 共同实现 restart no-call resume。Production SQL
repository 的 FK 按设计要求真实 WorkflowRun；evaluation harness 不伪造 Runtime
lifecycle row。若未来需要 central SQL ProviderOperation queries，必须单独 review
evaluation persistence，不得复用既有 acceptance/project databases。

## 10. Retention policy

`docs/evidence/OPENALEX_DATA_RETENTION_POLICY.md` 提议：

- key/auth URL/raw response：never retained；
- normalized metadata/candidate pools：private ignored，30-day owner review；
- optional abstract preview：private ignored，14 days 或 adjudication 后较早者；
- full real abstract committed fixture：禁止；
- append-only ProviderOperation journal：private ignored、retained 30 days；
- pseudonymous judgments/adjudication：owner review 后可作为 evidence 保留；
- aggregate reports：不含 protected text 时可 owner-approved commit；
- cleanup 必须 exact evaluation ID、先保存 aggregate/checksum evidence；
- orphan bytes 不自动删除。

这是 proposed engineering policy，不是 legal advice；owner 尚未批准实际 live
evaluation retention。

## 11. Test evidence

Focused evaluation：

```text
conda run --no-capture-output -n reagent-dev \
  python -m pytest -q backend/research/tests/test_evaluation_*.py
```

- exit 0
- `22 passed in 0.23s`
- network：none
- database：none

Coverage includes immutable serialization/hash、topic loading、JSON/CSV round
trip、unknown/duplicate/invalid/altered judgment rejection、adjudication
consistency、per-topic Precision/nDCG/unavailable Recall、metadata/agreement、
CANNOT_JUDGE/zero/partial cases、deterministic no-abstract report、synthetic
OpenAlex mapping、reservation/settlement、budget pre-call block、checksum,
append-only journal restart/no-call、partial-journal rejection、corruption
rejection、raw/key leakage canary、CLI initialization/status 和 missing
`--live` rejection。

Resolved intermediate test-only evidence：

- first focused draft：`9 passed, 1 failed`，原因是 raw-response canary
  assertion 把合法 requested field name `abstract_inverted_index` 误判为 raw
  body；改为真实 body/content canary 后通过；
- late full-backend draft：`159 passed, 18 skipped, 1 failed`，原因是新增 journal
  mode assertion 放错 test scope 导致 `NameError`；只移动 assertion 后 final
  full suite 通过。

Full backend：

```text
conda run --no-capture-output -n reagent-dev python -m pytest -q backend
```

- exit 0
- `161 passed, 18 skipped in 1.05s`
- skips：既有 environment/PostgreSQL/live gates
- network：none
- database：none

Compile：

```text
conda run --no-capture-output -n reagent-dev python -m compileall -q backend
```

- exit 0
- no output

PostgreSQL regression：

```text
REAGENT_TEST_DATABASE_URL=<redacted isolated URL> \
  conda run --no-capture-output -n reagent-dev \
  python -m pytest -q backend/database/tests
```

- exit 0
- `14 passed in 0.91s`
- database：`reagent_9b2a_harness_test`
- Alembic：`current=head=20260721_0002`；`check` no drift

在 final design 前曾用一个临时 targeted test 尝试把 evaluation-only operation
直接写入 production SQL repository；命令 exit 1、`1 failed`，PostgreSQL
`fk_provider_operations_run_scope` 正确拒绝了没有真实 `WorkflowRun` 的 row。
这不是 production defect，而是证明 evaluation 不应伪造 Runtime lifecycle。
该临时 test file 已移除，final CLI 改用 journaled existing port；随后 focused、
full backend 和 PostgreSQL regressions 全部通过。

为该 probe 新建的 `reagent_9b2a_harness_test` 已迁移并保留供 owner inspection：
`8,820,415 bytes`，当前 `provider_operations=0`、`workflow_runs=0`。没有 drop。
Optional cleanup（未执行）：`dropdb reagent_9b2a_harness_test`。

没有新增 schema、migration 或 production SQL composition。  
Frontend：not run/not required；没有 frontend/API DTO/shared type change。  
Live pilot：**not executed**；本 prompt 没有单独授权 3-topic live pilot。

## 12. Files

Created：

- `backend/research/evaluation/__init__.py`
- `backend/research/evaluation/__main__.py`
- `backend/research/evaluation/contracts.py`
- `backend/research/evaluation/topics.py`
- `backend/research/evaluation/candidate_pool.py`
- `backend/research/evaluation/operation_journal.py`
- `backend/research/evaluation/judgments.py`
- `backend/research/evaluation/metrics.py`
- `backend/research/evaluation/report.py`
- `backend/research/evaluation/cli.py`
- `evaluation/topics/openalex_v1.json`
- four `backend/research/tests/test_evaluation_*.py` files
- three `docs/evidence/OPENALEX_*.md` files
- this progress report

Updated：

- `docs/evidence/SEARCH_EVALUATION_PROTOCOL.md`
- `docs/evidence/PAPER_SEARCH_EVIDENCE_REGISTER.md`
- `DEMO.md`
- `.agent_read/context.md`

No migration、dependency、environment template、API、frontend、workflow 或 Phase
9B-1 baseline source changed。

## 13. Remaining owner actions

1. 指定两名 independent reviewers 和一名 adjudicator；
2. 批准/修改 30-day metadata、14-day preview retention；
3. 决定是否允许 `--include-abstract-preview`；
4. 批准 proposed Precision/metadata/dedup/operations thresholds；
5. 批准第一批最多 3 topics；
6. 完成 judgment import、disagreement adjudication 和 result review；
7. 人工决定是否继续其余 9 topics。
8. 若继续 12-topic evaluation，批准跨 batch aggregation contract；当前 report
   unit 是单个最多 3-topic batch。

## 14. Exact next milestone

唯一建议：**Phase 9B-2B — bounded three-topic OpenAlex candidate-pool pilot +
two-human blind review and adjudication**。

Entry gates：

- owner 指定 reviewers/adjudicator；
- owner 接受或修改 retention；
- owner 选择 3 topics；
- `.env`/runtime_data ignore 和 key safety 再确认；
- explicit live authorization、zero-cost/free-credit policy 保持；
- no S2/Crossref/real LLM/full text。

该 pilot 只验证 harness 与产生初步 human evidence，不足以得出 universal
OpenAlex quality conclusion。只有 human-reviewed results 被 owner/architecture
review 后，才能决定是否扩展 12-topic evaluation；不得提前推荐 Semantic
Scholar、Crossref 或 real LLM。
