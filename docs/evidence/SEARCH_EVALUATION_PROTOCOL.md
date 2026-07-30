# ReAgent Search Evaluation Protocol

日期：2026-07-29；状态：**Harness implemented / automated silver contract
Proposed / no labels generated**。本协议评估 provider/architecture，不评估论文
科学质量，也不以截图作为证据。

## Phase 9B-2C-0 proposed supersession

For the current prototype, the working evaluation objective is proposed as:

> **Automated silver-label relevance evaluation with targeted human audit.**

This is not expert ground truth, scientific peer review, methodological-quality
assessment, definitive paper-quality ranking, or a systematic-review gold
standard. The original two-human blind protocol below remains the higher-rigor
expert-gold design and is **deferred**, not deleted or declared incorrect.
Existing blank reviewer A/B packets remain untouched.

No real judge, multilingual search, human label, automated label, or retrieval
metric was generated in Phase 9B-2C-0. ADR 0005 remains Proposed. Governing
proposed contracts:

- `AUTOMATED_RELEVANCE_RUBRIC.md`;
- `SILVER_LABEL_AGGREGATION_POLICY.md`;
- `HUMAN_AUDIT_PROTOCOL.md`;
- `MULTILINGUAL_SEARCH_PLAN.md`;
- `TWO_HUMAN_REVIEW_SUPERSESSION.md`.

## Phase 9B-2A implementation status

已实现 network-free infrastructure：immutable evaluation contracts、12-topic
versioned engineering set、existing `PaperSearchProvider` +
`ProviderOperationService` + `ArtifactContentStorage` candidate generator、
evaluation-only append-only/checksum-chained ProviderOperation journal、JSON/CSV
human review import/export、adjudication source-hash validation、
deterministic metrics、report artifacts 和单一 module CLI：
`python -m backend.research.evaluation`。

Retrieval metrics are calculated independently for each topic. Summary
Precision/nDCG values are medians of available per-topic values, and the report
retains the per-topic results; candidates from different topics are never
treated as one ranking.

具体执行依据：

- `OPENALEX_EVALUATION_TOPIC_SET.md`；
- `OPENALEX_HUMAN_REVIEW_PROTOCOL.md`；
- `OPENALEX_DATA_RETENTION_POLICY.md`。

Phase 9B-2A 没有执行 live pilot、没有 human judgments，也没有比较 layered
architecture。Semantic Scholar/Crossref 仍未授权或实现。

## Evaluation question

最终 provider promotion evaluation 应比较至少：

1. **primary-only**：OpenAlex discovery；
2. **layered**：只有未来单独批准并实现后，才可对同一 OpenAlex result 加
   selected/ambiguous verification/fallback。

层次方案不会产生额外 discovery recall，除非未来批准 query expansion；
本轮重点检验 identity、metadata、dedup、人工审查负担和 operational cost。

## Deferred expert-gold human-reviewed set

Proposed Class D default: 12 topics, four domain groups各 3：

- computer science/AI；
- biomedical/health；
- social science/humanities；
- climate/engineering/interdisciplinary。

Topic selection:

- owner 与 reviewer 预先冻结 topic、research question、synonym/Boolean plan、
  2018–2026 或适当 year window、language/document-type policy；
- 包含 3 个 non-English 或 Global South 相关题目、3 个容易混淆 preprint/
  journal version 的题目、3 个 abstract missingness 风险题目；
- 不用 provider 的现有 top result 反向挑题。

每个 topic 从两种 architecture 的 top-20 取 union，按 DOI/external IDs 做
conservative clustering；去除 provider/score 标识后随机排序。两名 reviewer
独立使用下列 labels：

- `HIGHLY_RELEVANT`（gain 3）；
- `RELEVANT`（gain 2）；
- `PARTIALLY_RELEVANT`（gain 1）；
- `NOT_RELEVANT`（gain 0）；
- `CANNOT_JUDGE`（无 gain，绝不转成 0）；
- identity cluster and version relation；
- title/year/authors/DOI/venue/abstract presence/correctness；
- inclusion decision + reason；
- uncertainty flag。

分歧由第三名 reviewer 或共同 adjudication；保存匿名 reviewer ID、guideline
version、timestamps，不保存不必要个人数据。

### Gold-pool limitation

这是 pooled relevance set，不是世界范围 exhaustive gold corpus；两个系统都
漏掉的 paper 不会进入 pool。因此 `Recall@K` 必须写作 “recall within pooled
candidate set”。小样本会有 domain/annotator variance，不得外推成 universal
provider superiority。

## Proposed automated silver set

The existing 40 reviewable candidates remain the bounded pilot input. The empty
Chinese topic remains coverage/normalization evidence and receives no fabricated
candidate.

Each candidate receives two pointwise judgments under separately versioned but
equivalent prompt structures. A limited deterministic set of neighboring pairs
receives mirrored-order pairwise consistency checks. Exact agreement with
confidence/evidence/warning requirements may create `AUTO_ACCEPTED` or
`AUTO_REJECTED`; every disagreement, partial label, cannot-judge state, low
confidence, missing evidence, pairwise conflict, non-English uncertainty, or
metadata warning becomes `NEEDS_HUMAN_REVIEW`.

All thresholds, call counts, pair selection, and audit sampling are proposed
**Class D ReAgent policy** and require owner approval.

## Metrics

### Retrieval

- Precision@5, Precision@10（relevance ≥2）；
- pooled Recall@10/20；
- nDCG@10（0–3 grades）；
- relevant-paper yield / request 和 per topic；
- unique relevant yield by provider/architecture。

这些是 literature-established IR metrics；没有 universal passing threshold。

### Automated silver relevance

Silver-only names prevent a gold-standard claim:

- Silver Precision@5;
- Silver Precision@10;
- Silver nDCG@10;
- Silver Relevant-paper Yield;
- Automated Judgment Agreement;
- Human-audit Agreement;
- Human Override Rate;
- NEEDS_HUMAN_REVIEW Rate;
- CANNOT_JUDGE Rate;
- Non-English Uncertainty Rate.

Reports must publish (1) raw-silver metrics, (2) human-audited-silver metrics
using audit overrides where available, (3) audit agreement/override, (4)
coverage and unavailable values, and (5) the explicit statement that expert-gold
labels do not exist. Required-review items without audit are unavailable, never
coerced to non-relevant.

### Metadata

- DOI resolution rate；
- normalized title/year agreement with adjudicated record；
- author completeness (ordered author recall where gold available)；
- abstract availability and abstract-integrity manual flag；
- venue completeness；
- provider conflict rate by field；
- version/retraction relationship visibility。

### Deduplication

- duplicate rate before normalization；
- duplicate rate after normalization；
- pairwise false merge rate（最重要 hard safety metric）；
- missed duplicate rate；
- unresolved-cluster rate；
- preprint/published false collapse count。

若 evaluation run 尚未导入可审计的 duplicate-pair/adjudication evidence，
duplicate/false-merge metric 必须返回 unavailable；不得把缺失 evidence 报告
为零。

### Engineering

- logical/physical request count；
- p50/p95 latency and total provider runtime；
- 429, timeout, retry and provider failure rates；
- ProviderOperation settled/unsettled count；
- actual/reported monetary cost；
- idempotent replay duplicate call/reservation count；
- cache/reuse hit rate；
- response/normalized artifact bytes。

### Product and evidence completeness

- candidates requiring manual identity review；
- approval rejection/change rate；
- reviewer relevance rating；
- search plan/execution/statistics/verification artifact completeness；
- percentage of reportable records with provider/version/timestamp/request hash；
- page reload/reconstruction completeness in later integration testing。

## Deferred expert-gold acceptance thresholds (Class D, owner approval required)

These are starting gates, not established standards:

| Metric | Proposed gate | Reason / revisit |
|---|---:|---|
| Precision@5 | ≥ 0.70 median topic | supervised review usefulness |
| Precision@10 | ≥ 0.60 median | broad discovery tradeoff |
| pooled Recall@20 | ≥ 0.85 | small candidate cap must retain pool |
| DOI resolution | ≥ 0.75 where adjudicated work has DOI | identity utility; domain-sensitive |
| false merge | **0** in evaluation set | fail-closed identity |
| unresolved clusters | ≤ 10% | manual burden |
| ProviderOperations unsettled | **0** | existing publication invariant |
| idempotent replay new calls/reservations | **0** | existing architecture invariant |
| total requests/run | ≤ approved cap (proposed 12) | supervised budget |
| monetary cost | 0 | owner policy |
| 429/provider failure | ≤1% operations in evaluation batch | operational signal; small N caveat |
| evidence artifact required fields | 100% | reproducibility contract |

Promotion rule: layered must not worsen retrieval metrics beyond sampling
uncertainty, must reduce identity/metadata unresolved rate or manual review burden,
and must remain inside request/legal/latency caps. If it adds no material value,
prefer OpenAlex-only until a stronger use case.

## Proposed silver execution design

1. Freeze candidate/topic checksums, schema/rubric/prompt/model/adapter identities,
   retention, and owner-approved limits.
2. Validate deterministic metadata without exposing rank/citation data.
3. Reserve and execute pointwise A/B operations; validate structured output,
   supporting spans, usage, identity, and settlement.
4. Execute only selected mirrored pairwise consistency operations.
5. Aggregate without letting a judge see another judge's result.
6. Audit all required exceptions plus a deterministic consensus sample and
   per-topic minimum.
7. Report raw-silver and audited-silver metrics separately. Keep untouched human
   packets and nonexistent expert-gold labels distinct.
8. Fail closed on cost/token/call excess, unavailable model, repeated schema
   failure, missing usage, or unresolved state.

The current authorized judge budget is USD 0.00. No execution may begin until
ADR 0005 and provider/model/cost/retention decisions are approved.

## Deferred expert-gold execution design

1. Freeze evaluation manifest, schemas, adapter versions, official-contract review
   date and owner-approved limits.
2. Run both architectures against the same SearchPlan timestamps as close as
   practical; record provider index time and acknowledge non-simultaneity.
3. Capture normalized outputs and response hashes; raw bodies follow retention
   policy and are not committed.
4. Blind and randomize pooled records.
5. Annotate independently, adjudicate, lock gold set.
6. Compute metrics with per-topic values；bootstrap confidence intervals 只在
   sample size 和 resampling assumptions 合理时加入，否则明确记录
   unavailable/sample-size limitation；never report only a global mean.
7. Perform failure injection separately for 429/timeout/5xx/malformed/pagination/
   contract drift; do not cause abusive live traffic.
8. Rerun idempotently and after application restart; assert zero duplicate
   provider operations.
9. Publish evaluation artifact/report including all failures and missingness.

## Re-evaluation triggers

- adapter/query/ranking/dedup version change；
- provider API/schema/terms/rate change；
- new domain or language；
- candidate cap or verification scope change；
- observed live false merge, DOI mismatch, >1% 429/failure, or abstract integrity
  incident；
- shift from abstract-only or future commercial/public distribution。
- judge provider/model/snapshot, prompt, rubric, schema, aggregation, audit, or
  translation change;
- audit override/uncertainty exceeds approved policy;
- expert/publication/systematic-review claim is planned.

## Phase 9B-2C-2 synthetic automated-silver path

The evaluation CLI adds `judge-synthetic`. It accepts only the committed,
source-marked synthetic fixture schema, runs fixture-driven pointwise A/B and
selected mirrored pairwise checks, records a separate zero-cost
ProviderOperation per logical call, aggregates under `TEST_POLICY_ONLY`, emits
an uncompleted human-audit queue, and calculates synthetic raw-silver metrics.
Replay reconstructs the immutable result and makes no Fake Judge call.

This path does not load the OpenAlex candidate manifests, does not call a
network, does not generate a `CandidateJudgment` or `HumanAuditResult`, and does
not calculate expert-gold metrics. Synthetic numbers demonstrate contract
behavior only; they do not estimate provider/model relevance quality.

## Phase 9B-2C-3A required real-Judge calibration

Before any real Judge may evaluate a retained OpenAlex candidate pool, Proposed
ADR 0006 requires a separately approved bounded calibration:

1. freeze a private ignored manifest with 12 real candidates: four from each of
   two English topics and four from one multilingual topic; include no titles or
   previews in committed documentation;
2. retain three synthetic canaries for adapter/schema/replay evidence, excluded
   from model-quality denominators;
3. collect blinded primary human-reference labels for all real cases and
   targeted independent secondary checks before revealing Judge output;
4. run frozen pointwise A/B for all 15 request candidates and three preselected
   real pairs in both orders;
5. validate schema, exact span containment, usage/request identity, cost,
   ProviderOperation settlement, and zero-call replay;
6. report human agreement, prompt stability, pairwise order consistency,
   multilingual differences, confidence behavior, and engineering metrics
   without statistical-significance or expert-gold claims;
7. apply Proposed Class D gates from
   `REAL_JUDGE_PASS_FAIL_GATES.md`.

Code acceptance, calibration acceptance, and permission to judge the full pool
are separate owner decisions. ADR 0006 authorizes none while Proposed. Current
hosted-preview permission and Judge budget remain absent, so execution is
blocked.

## Evidence basis

- PRISMA-S (peer reviewed) supports exact source/query/date/limits/dedup reporting:
  https://doi.org/10.1186/s13643-020-01542-z
- Academic search-system evaluation uses retrieval capability and coverage
  dimensions: https://pmc.ncbi.nlm.nih.gov/articles/PMC7079055/
- OpenScholar/ScholarQABench demonstrates multi-domain expert/human evaluation
  and citation-aware evaluation, while acknowledging small expert sets:
  https://www.nature.com/articles/s41586-025-10072-4
- OpenAlex comparison/abstract studies motivate field-level metadata checks:
  https://arxiv.org/abs/2401.16359 and https://arxiv.org/abs/2605.20168
- ARS/PaperQA2/OpenScholar are Class C design experience for provenance,
  multi-provider metadata and failure testing, not universal thresholds.
