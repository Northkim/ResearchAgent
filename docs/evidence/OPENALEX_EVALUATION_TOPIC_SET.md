# OpenAlex Evaluation Topic Set

日期：2026-07-28  
状态：Implemented / ReAgent engineering evaluation set  
机器可读定义：`evaluation/topics/openalex_v1.json`  
Topic-set ID/version：`reagent-openalex-engineering-evaluation@1.0.0`

## 目的

该集合用于让人类 reviewer 检查 OpenAlex discovery 的候选相关性、metadata
完整性、identity ambiguity、deduplication 和 operational behavior。它不是
universal benchmark，不代表所有学科、语言、地区或检索方法，也不构成
systematic-review compliance。

Topic 在 provider execution 之前冻结；live candidate、abstract、judgment 和
report 不写入该 tracked JSON。Topic-set canonical hash 进入 evaluation
configuration/manifest，任何题目、日期、关键词或 policy 变化都必须发布新
version。

## 选择标准

12 个 topic 覆盖：

| Topic ID | 主要领域 | 主要压力点 |
|---|---|---|
| `cs-persistent-agents` | CS/AI | broad query、terminology ambiguity、fast-moving |
| `cs-machine-unlearning` | CS/privacy | narrow phrase、preprint/published versions |
| `biomed-microbiome-immunotherapy` | biomedical | high volume、study-type ambiguity |
| `biomed-long-covid-cognition` | clinical/public health | evolving terminology、abstract-only design |
| `social-algorithmic-management` | social science | interdisciplinary terminology |
| `humanities-digital-archives` | humanities | book/chapter coverage、abstract missingness |
| `engineering-battery-thermal-runaway` | engineering | specialized vocabulary、venue metadata |
| `climate-urban-heat-equity` | climate/planning | interdisciplinary、distributional equity |
| `interdisciplinary-science-of-team-science` | science of science | generic teamwork collision |
| `global-south-smallholder-climate` | agriculture/development | Global South、multilingual/geographic bias |
| `nonenglish-chinese-digital-humanities` | Chinese digital humanities | Unicode、non-English、abstract missingness |
| `ambiguity-foundation-model` | CS/AI | cross-domain term collision、version ambiguity |

每个 topic 记录 natural-language topic、research question、keywords、inclusive
year range、language/document-type policy、discipline、difficulty tags、selection
rationale 和预期 ambiguity。`maximum_candidates=20` 是 ReAgent Class D
工程上限，不是 OpenAlex 推荐值。

## 已知偏差与限制

- 12 topics 样本很小，且由 ReAgent owner/reviewer 面向产品风险选择。
- 学科覆盖不等于数据库 coverage 的统计代表性。
- non-English/Global South 只有少量 stress topics，不能估计整体区域偏差。
- OpenAlex index 随时间变化；同一 query 未来不保证相同候选。
- top-20 pool 无法观察 provider 未返回的 relevant papers。
- abstract-only review 对 abstract 缺失、错误或过短记录只能标
  `CANNOT_JUDGE`，不能推断 full-paper quality。
- topic 中出现医学/公共卫生领域不意味着系统提供医学建议；这里只评价文献
  discovery metadata。

## 批次与扩展规则

单次 supervised live pilot 最多 3 topics、每题一页/20 candidates。完整 12-topic
evaluation 必须分成 owner-approved batches，保存各自 query time、adapter/API
snapshot 和 pool checksum，再统一人工 review。不得为了改善结果在 execution
后修改 topic/query。

Phase 9B-2A CLI/report 以一个最多 3-topic batch 为 evaluation unit；尚未提供
跨 batch aggregate command。是否扩展到 12 topics 及如何冻结跨 batch aggregation
必须在三题 pilot review 后由 owner 决定，不能把多个不同时间的 batch 静默当成
simultaneous search。

以下变化要求 topic-set 新版本：

- 增删 topic；
- 修改 query、keywords、year/language/document-type policy；
- 改变 candidate cap 或 provider；
- 改变 primary evaluation question；
- 引入新的 domain/language；
- 发现 topic 含敏感、不安全或不可合法保留的数据。

扩展时优先补充当前 evidence 暴露的空白，不按 provider top result 反向挑题。
