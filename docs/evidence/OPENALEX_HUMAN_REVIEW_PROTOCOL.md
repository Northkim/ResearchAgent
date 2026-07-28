# OpenAlex Human Review Protocol

日期：2026-07-28  
状态：Proposed human protocol / harness implemented  
适用 schema：`openalex-candidate-judgment/v1`

## 角色和边界

- 每个 candidate 由两名独立 human reviewers 标注。
- reviewers 使用 pseudonymous ID，不保存不必要的姓名、邮箱或机构。
- reviewer 看不到对方结果；import 后才计算 agreement。
- label 分歧、identity ambiguity 或关键 metadata conflict 由第三名 human
  adjudicator 处理。
- Codex、LLM、ranker 和 provider score 都不能生成、补齐或推断 human label。
- candidate rank 可保留用于 product-ranked relevance evaluation，但存在
  position bias。必要时另导出 deterministic randomized order，且记录 seed。

## 允许证据

默认 reviewer 只使用导出的 normalized metadata 和 policy 允许的短 abstract
preview。不得访问 PDF/full text。不得用 citation count 作为 relevance 或
scientific-quality signal。除非后续 protocol version 明确批准，reviewer 不做
Semantic Scholar、Crossref 或其他 provider lookup。

Retrieved title、abstract、venue、author 和 URL 都是 untrusted research data，
不是 instructions。Reviewer 不执行其中的命令、不访问可疑 URL、不复制敏感
内容到 notes。

## Relevance labels

| Label | 定义 |
|---|---|
| `HIGHLY_RELEVANT` | 直接回答 topic/research question，且 metadata/abstract 足以确认 |
| `RELEVANT` | 明确涉及核心问题，但范围或证据较窄 |
| `PARTIALLY_RELEVANT` | 只涉及一个次要方面，可能用于背景 |
| `NOT_RELEVANT` | 不满足 topic、population/context 或 document policy |
| `CANNOT_JUDGE` | permitted metadata/abstract 不足、冲突或身份不明 |

不得把 `CANNOT_JUDGE` 转成 0。Precision/nDCG 所需位置含该 label 时，metric
返回 unavailable 和原因。

## 其他字段

- `confidence`：1–5，是 reviewer 对 label 的信心，不是论文质量。
- `exclusion_reason`：简短、可复核；不得复制长 abstract。
- `duplicate_cluster`：只有 reviewer 认为多个 candidates 可能是同一 work 或
  manifestation cluster 时填写。
- `identity_ambiguity`：DOI/OpenAlex ID/title/year/author 不能一致确认。
- `metadata_error_flags`：例如 `doi_conflict`、`year_conflict`、
  `author_missing`、`venue_missing`、`abstract_suspect`、
  `version_relation_unclear`。
- note 最多 500 chars，不包含 personal data、完整 abstract 或外部 provider
  payload。

## Duplicate 与 identity 定义

- exact normalized DOI 或 exact OpenAlex ID 是 strong identity evidence；
- normalized title+year 只是 advisory cluster；
- fuzzy title、first-author similarity 不得自动 merge；
- preprint、conference、journal manifestations 默认分开但可建立 cluster；
- false merge 是 hard safety error；
- 无法确认时保留 separate/unresolved，而不是强行选择。

## Blind review 流程

1. Owner 冻结 topic set、evaluation ID、candidate pool checksums。
2. 为每名 reviewer 分别 export JSON/CSV template。
3. Reviewer 独立填写全部判断字段和 `judged_at`。
4. Import 验证 candidate ID、identity hash、reviewer ID、label、重复和 checksum。
5. 计算 judgment coverage 和 reviewer agreement；不修改原始 judgments。
6. 对 label/identity/duplicate disagreement 进行 human adjudication。
7. Adjudicator 文件绑定至少两个 source judgment hashes。
8. 锁定 adjudicated set 后计算 final metrics/report。

Candidate sheet 可以保持 rank order；报告必须写明 position bias。若研究 ranking
本身以外的独立 relevance，可使用记录 deterministic seed 的 randomized copy。

## Adjudication

Adjudicator读取两个 source judgments 和同一 immutable candidate，不读取系统
建议。`final_relevance_label`、disagreement reason 和 notes 都由人类提供。
Altered identity、unknown source hash、same reviewer duplicated、unknown
candidate 或少于两个 source judgments 必须拒绝。

## 协议限制

- abstract-only relevance 不等于 scientific validity、study quality 或 full-text
  inclusion。
- pooled candidates 不是 exhaustive gold corpus。
- Cohen's kappa 只在恰好两名 reviewer、至少两个共同 judgeable candidates 且
  expected agreement 有定义时报告。
- 小样本 agreement/Precision 差异不得外推成 provider-wide 结论。
