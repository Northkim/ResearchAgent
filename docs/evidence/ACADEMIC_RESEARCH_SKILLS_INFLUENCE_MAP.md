# Academic Research Skills 对 ReAgent 的影响映射

日期/访问日期：2026-07-27  
用途：Phase 9B-0 methodology evidence review；**ARS 不是 Paper Search API，也不是 ReAgent 的可直接 vendor 依赖。**

## Reviewed revisions and files

### Claude Code repository

- Repository: https://github.com/Imbad0202/academic-research-skills
- current `main` commit: `e624c5a0682176415b97db4dc3b53a3ec2b556da`
- plugin version: `3.19.0`
- `deep-research` workflow metadata version: `2.11.0`（last updated 2026-07-11）
- license: CC BY-NC 4.0
- reviewed: `.claude-plugin/plugin.json`, `deep-research/SKILL.md`,
  `deep-research/agents/bibliography_agent.md`,
  `deep-research/agents/source_verification_agent.md`,
  `deep-research/references/`（尤其 `semantic_scholar_api_protocol.md`）,
  `docs/ARCHITECTURE.md`, shared handoff/provenance/degradation references,
  `LICENSE`, repository tree/README/commit history.

### Codex adapter repository

- Repository: https://github.com/Imbad0202/academic-research-skills-codex
- current `main` commit: `f8d6b061efe98564a3f554c917fce66dcef6ca54`
- adapter version: `0.1.22`
- vendored upstream commit: `828ef3b613b0e8b91830da3328a1e33d4eb5ab4c`（upstream v3.19.0；落后于上列 upstream current main）
- license: CC BY-NC 4.0
- reviewed: `skills/academic-research-suite/SKILL.md`,
  `skills/academic-research-suite/ars/deep-research/WORKFLOW.md`,
  Codex Runtime Mapping, `manifest.json`, `codex/README.md`, version/upstream
  metadata, licensing/vendoring说明。

## Influence matrix

| ARS pattern | ReAgent classification | 应用方式与理由 |
|---|---|---|
| execution 前定义 search strategy | **Adopt directly as a ReAgent principle** | 先冻结 `search_plan.json`，再创建 provider operations；减少事后改写方法 |
| 记录 databases/platforms 和 exact queries | **Adapt to existing ReAgent contracts** | provider list、query、adapter/API version、timestamp 进入 SearchPlan/Execution artifacts |
| Boolean query planning | **Adapt** | `ResearchQuery` 目前只有 topic/keywords；未来 additive `SearchPlan.provider_queries` 保存 provider-specific expression，不假装各 provider Boolean 语义相同 |
| date/language/document-type filters | **Adapt** | date 可映射；language/type 只作 best-effort filter，并记录 provider semantics/missingness |
| inclusion/exclusion criteria | **Adopt principle** | 当前 `ResearchQuery` 已承载；筛选结果必须给 reason code |
| two-pass screening | **Adapt** | V1 metadata/abstract first pass + exact selected-set human approval；不宣称 full-text second pass |
| DOI/S2 ID resolution | **Adapt** | ID evidence进入 `provider_verification.json`；persistent IDs优先，fuzzy 仅 advisory |
| deterministic deduplication | **Adopt principle** | DOI/external/provider ID 分层，ambiguous 保留，绝不 silent fuzzy merge |
| graceful degradation | **Adapt** | enrichment 可降级，primary discovery/ambiguous identity/provenance 不可降级；所有 degradation 显式 artifact/event |
| PRISMA-style accounting | **Adapt** | 保存 identified/deduped/screened/selected/excluded/failure counts；名称必须说明“不等于 PRISMA compliance” |
| external content is data, not instructions | **Adopt directly as a security principle** | schema/length/control-char/HTML sanitization；不把 title/abstract/error 放入 system instructions |
| human confirmation checkpoints | **Adopt** | 复用 ReAgent `WaitingApproval`、fingerprint、selected artifact checksum，不引入 ARS 自有交互层 |
| provenance and citation verification | **Adapt** | 复用 `GroundedClaim → EvidenceUnit → SourceContent → PaperRecord → CitationReference` gate |
| phase ownership boundaries | **Adopt** | adapter=transport/schema；Skill=research logic；Runtime=orchestration；Application/API/UI不拥有 merge/selection |
| corpus-first/search-fills-gap | **Defer** | ReAgent 没有 upload/corpus management；未来 project corpus 存在时再加入 SearchPlan policy |
| distributional-skew advisory | **Adapt** | provider/topic/language/year distribution 作为 advisory artifact；不做自动 bias correction |
| claim-faithfulness gate | **Adopt principle** | current provenance gate已有基础；未来 real abstract仍 fail closed |
| full 13-agent orchestration | **Reject for V1** | 超出 sequential Workflow/Skill model，增加 ownership/成本，和首个 search adapter无关 |
| full research-to-paper pipeline | **Reject for V1** | ReAgent 当前目标是 supervised guided literature review，不是自动投稿论文 |
| Claude hooks/slash commands | **Not applicable** | runtime-specific，不属于 ReAgent product contract |
| model-specific routing/cross-model verification | **Defer** | Phase 9B-0 明确不选择 LLM；不得由 search provider ADR 偷带决定 |
| direct vendoring of prompts/templates/code | **Reject** | CC BY-NC 与未来 commercial product 存在兼容风险；不需要复制表达即可实现工程原则 |

## Material methodology findings

1. **Plan before transport**：ARS 的重要贡献不是某个 API，而是把 database/query/filter/inclusion/exclusion 作为 execution input。ReAgent 应把它做成不可变 artifact 和 approval/replay evidence。
2. **Two-pass and conservative identity**：先用便宜 metadata 形成候选，再对少量候选做 ID/来源核验；无法确认时保留 unresolved，而不是凭 title 猜测。
3. **Graceful degradation has authority**：降级应有触发条件、终局影响和消费者；“provider unavailable”不能被系统悄悄修成 PASS。
4. **Phase ownership**：bibliography/source verification/synthesis 是不同判断阶段。ReAgent 应用 Workflow steps/Skills 表达这些边界，不需要复制 agent 数量。
5. **Search accounting and caveats**：记录每阶段数量、query、database 和日期；provider index 的动态性必须诚实披露。
6. **Instruction/data boundary**：外部研究材料是 untrusted payload；这与 ReAgent 的 capability injection 和 LLM provider boundary 完全兼容。

## Contract conflicts discovered

- ARS 的 `semantic_scholar_api_protocol.md` 记录 fixed unauthenticated/authenticated limits；当前 S2 官方产品/API 页面描述的是 shared anonymous pool、API-key-specific limits。该文件只能是历史 Class C 经验，不能作为 Class A 实现合同。
- ARS/Codex 的 vendored upstream commit不是 upstream current main；引用必须同时写 adapter commit、vendored commit、版本，不能说“reviewed latest upstream”。
- ARS 中的 provider fallback 和 retry 数字属于其项目政策；ReAgent 只能参考结构，不能把数值当 provider 标准。

## Licensing engineering risk assessment

ARS 与 Codex adapter 均标示 CC BY-NC 4.0。以下不是法律意见：

- **可引用**：repository、commit、version、license、公开方法描述和我们观察到的设计模式；需清楚 attribution。
- **可独立重实现**：search-before-execution、two-pass screening、graceful degradation、provenance、instruction/data separation 等抽象原则；实现、命名、schema、文案应由 ReAgent 独立产生。
- **适配有条件**：如果翻译/改写具体 prompt、template、schema 表达或代码，可能构成 adaptation，需满足 attribution 与 NonCommercial 限制。
- **不应复制**：substantial prompts、agent role files、templates、code、hook recipes、完整 handoff schema；它们可能使未来 commercial distribution 不兼容或法律状态不清。
- **默认策略**：methodological inspiration + attribution + clean independent implementation。若未来需要 vendor，先由 owner/法律审查并单独决策。

## Mature implementation comparison

| External system | Evidence type | 值得采用 | Defer | Reject | 原因 |
|---|---|---|---|---|---|
| ARS | Class C methodology | strategy-first、two-pass、graceful degradation、human gates、provenance/security boundary | corpus-first、distribution audits深化 | prompts/13-agent wholesale | 方法成熟，但许可/运行时/规模不适合作为依赖 |
| PaperQA2 | Class B paper + C repo | Crossref+S2 metadata、evidence contexts、citation checks、cache/replay思路 | full-text/PDF index、agentic QA | architecture wholesale | 证明 multi-provider/evidence pipeline 是成熟 pattern，但范围远大于 V1 |
| OpenScholar | peer-reviewed Class B + C repo | retrieval/reranking/cited generation分层、multi-domain human evaluation | 45M-paper datastore、self-feedback LM | 本地复制大型 index/model | evaluation discipline强；基础设施不适合首个 adapter |
| PRISMA-S | peer-reviewed/official Class B | exact sources/queries/dates/limits/dedup/accounting | full systematic-review process | “有 JSON 就合规”的产品声称 | 它是 reporting extension，不是 provider API 或自动认证 |

## ReAgent boundary mapping

```text
ARS search strategy
  → proposed SearchPlan artifact (Application input, immutable)
ARS bibliography transport
  → PaperSearchProvider adapter (transport/schema only)
ARS screening / verification
  → versioned Research Skills
ARS human checkpoint
  → existing ApprovalRequest + fingerprint
ARS handoff/provenance
  → existing research artifacts + ProvenanceValidator
ARS degradation registry
  → ProviderOperation + normalized failure + execution metadata
```

不会引入 Claude-specific hook/command、agent team 或 prompts；不会让 API route/
frontend 承担 query planning、dedup、verification 或 provenance 判断。

