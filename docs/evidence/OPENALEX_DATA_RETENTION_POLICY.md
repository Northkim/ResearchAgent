# OpenAlex Data Retention Policy

日期：2026-07-28  
状态：Proposed engineering policy；owner/legal review required  
默认 ignored root：`runtime_data/evaluations/openalex/`

本文是工程风险控制，不是法律意见。OpenAlex dataset 的 CC0 描述不能自动替代
第三方 publication/abstract rights 判断。

## 数据分类

| 数据 | 默认处理 | 建议期限 | 可提交 Git |
|---|---|---:|---|
| API key / auth URL/header | 永不保存、打印、hash 或写入 manifest | 0 | 禁止 |
| raw HTTP response body | 不保留 | 0 | 禁止 |
| normalized metadata | isolated ignored evaluation storage | 30 天或 owner review 后较早者 | 默认禁止 |
| abstract/full abstract | 不进入 candidate pool；显式选择时只存短 preview，ignored/private | 14 天或 adjudication 后较早者 | 禁止 |
| SearchPlan/Execution/Statistics | immutable、sanitized、relative key/checksum | 30 天 | 仅 synthetic 可提交 |
| ProviderOperation audit | private append-only checksum-chain journal；保留 ID、status、usage、failure、hash 和安全 diagnostics | 30 天；必要证据可延长 | 禁止 |
| candidate pools | immutable、ignored、无 raw payload/label | 30 天 | 未单独批准时禁止 |
| human judgments | 去除真实个人身份，使用 pseudonymous ID | evaluation evidence 生命周期；建议 12 个月复审 | 可在 owner 审查后提交 |
| adjudication | 与 source judgment hashes 一起保存 | 同 judgments | 可在去标识/无 protected text 后提交 |
| evaluation reports/metrics | 不复制 full abstracts，只保留 counts/短 metadata | 可长期保留 | owner 审查后允许 |
| screenshots | 默认不需要；若生成不得含 key/full abstract | 30 天 | 默认禁止 |
| database rows | 只允许新建 isolated evaluation database | 30 天 | 不适用 |
| ignored Artifact content | relative immutable keys；未知 orphan 不自动删 | 30 天/显式 cleanup | 禁止 |
| committed fixtures | hand-authored synthetic only | 长期 | 允许 |

## Candidate preview policy

CLI 默认 `abstract_preview=null`。只有 owner 明确允许 temporary abstract
review 时才使用 `--include-abstract-preview`；preview 最大 500 normalized
characters，仍视为 abstract data、不得进入 Git 或最终 public report。完整
abstract 不写入 evaluation report。

## Retention trigger

任一条件达到即进入 owner review：

- candidate pool generation 完成后 30 天；
- adjudication/report 完成；
- provider terms/licensing 变化；
- credential/content leakage、rights complaint 或 identity incident；
- project 准备公开、商业分发或跨用户共享；
- evaluation abandoned。

Owner 必须决定：保留去标识 judgments/report，还是删除整个 isolated run。
未经 review 不自动延长。

## Cleanup 与 evidence preservation

Cleanup 是显式、单 run、不可恢复操作。先保存不含 protected text 的：

- evaluation ID/topic-set/provider/adapter/API snapshot；
- pool/judgment/report checksums；
- aggregate metrics、request/latency/retry/failure counts；
- deletion reason/date/actor。

然后只允许 target：

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  --root runtime_data/evaluations/openalex \
  clean <evaluation-id> --confirm <evaluation-id>
```

如果以后使用 dedicated evaluation database，cleanup command 必须明确列出
数据库全名并拒绝：

- `ProjectDB`
- `reagent_9a1_acceptance`
- `reagent_9a2_acceptance`
- `reagent_9b1_acceptance`
- `reagent_9b1_live_acceptance`

不得使用 wildcard、broad root、`git clean` 或全局 cache cleanup。Unknown
filesystem objects 可能是 PostgreSQL rollback 后的 orphan；先 inventory 和
checksum comparison，再由 owner 单独批准删除。

## Current implementation boundary

Phase 9B-2A CLI 使用 configured isolated root、existing
`ProviderOperationService` 和实现现有 `ProviderOperationRepository` port 的
evaluation-only append-only journal：
`<evaluation-id>/provider_operations.journal.jsonl`。每次 reserve、RUNNING、
settlement 都先写入、`fsync` 并形成 previous-checksum chain；truncated、tampered
或 concurrent stale journal fail closed。Journal mode `0600`，不保存 API key、
auth URL 或 raw response。

Per-topic immutable manifest 绑定 settled operation 与 usage；restart 同时验证
journal terminal state 和 artifact checksums，因此 completed resume 不重复
provider call。Production SQL ProviderOperation table 需要真实 WorkflowRun FK；
evaluation 不伪造 Runtime lifecycle record，因此未复用该 SQL table、未新增
schema/migration。未来若 owner 要求 central SQL queries，必须单独 review
evaluation persistence，不得复用产品/既有 acceptance database。

Journal 使用 POSIX `flock`/`fsync`，适用于当前 macOS/Linux supervised
environment；Windows、network filesystem 和 multi-host writers 未验证，不能
视为 production distributed ledger。

## Legal-policy uncertainty

- metadata、abstract、source URL 和第三方 work 的权利可能不同；
- provider index/runtime contract 会变化；
- pseudonymous reviewer ID 仍可能在外部上下文中被重新识别；
- commercial/public report 需要 owner/legal review；
- 本 policy 不能授权超出 OpenAlex、metadata+abstract-only、zero-cost supervised
scope 的处理。
