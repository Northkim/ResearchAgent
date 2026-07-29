# OpenAlex Three-topic Pilot Selection

- **Phase:** 9B-2B-1
- **Date:** 2026-07-28
- **Evaluation ID:** `openalex-three-topic-pilot-v1`
- **Topic set:** `reagent-openalex-engineering-evaluation@1.0.0`
- **Status before live execution:** SELECTED / NOT YET EXECUTED

本选择只用于验证三类已知检索风险和 blind-review packet 流程，不代表全部学科，
也不能用于推断 OpenAlex 的总体 scientific quality。

## Selected topics

### `cs-machine-unlearning`

- exact topic text: `verifiable machine unlearning`
- discipline: computer science / privacy
- difficulty tags: `narrow_query`, `preprint_published_ambiguity`
- rationale: 作为 narrow and technically precise CS/AI query，检验专业术语、
  verification 语义以及 preprint/published manifestation 分离。
- expected risk: certified removal、empirical forgetting 与一般 data deletion
  可能混合；同一研究的不同 manifestation 可能形成 advisory duplicate cluster。

### `social-algorithmic-management`

- exact topic text: `algorithmic management worker autonomy`
- discipline: social science / labor studies
- difficulty tags: `interdisciplinary`, `terminology_ambiguity`
- rationale: 检验 management、sociology、information systems 与 labor studies
  交叉语境中的术语碰撞。
- expected risk: workforce scheduling、general automation、platform labor 与传统
  workplace 研究可能混入同一 candidate pool。

### `nonenglish-chinese-digital-humanities`

- exact topic text: `中国 数字人文 文本分析`
- discipline: digital humanities / Chinese studies
- difficulty tags: `non_english`, `abstract_missingness`, `unicode`
- rationale: 检验 Unicode query、Chinese/bilingual metadata、non-English coverage
  与 abstract missingness 风险。
- expected risk: commentary 与 applied text analysis 混合、翻译标题与原始标题
  不一致、venue/abstract metadata 缺失。

## Why the combination is useful

三项分别覆盖 narrow technical precision、interdisciplinary terminology ambiguity
以及 non-English metadata-coverage risk。组合能够验证 harness 在明显不同的 query
形态和 metadata missingness 条件下仍保持相同的预算、manifest、review export 和
human-only judgment 边界。

## Deferred topics

其余九项全部延后到 owner 审阅三-topic pilot、retention state 和人类 judgment
流程之后：

- `cs-persistent-agents`
- `biomed-microbiome-immunotherapy`
- `biomed-long-covid-cognition`
- `humanities-digital-archives`
- `engineering-battery-thermal-runaway`
- `climate-urban-heat-equity`
- `interdisciplinary-science-of-team-science`
- `global-south-smallholder-climate`
- `ambiguity-foundation-model`

延后理由是本阶段授权最多三个 live topics；扩大到完整 12-topic set 需要独立 owner
决定，且本阶段不得根据三个 topic 得出 provider-quality 结论。
