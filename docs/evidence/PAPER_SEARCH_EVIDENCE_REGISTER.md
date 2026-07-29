# ReAgent Paper Search Evidence Register

更新日期与统一访问日期：2026-07-27  
阶段：Phase 9B-1（OpenAlex adapter；official contract reverified）
结论状态：ADR 0004 **Accepted with limited scope**；仅 OpenAlex discovery
已获实现授权，Semantic Scholar/Crossref 仍是 future candidates。

## 证据标准与研究问题

- **Class A — Official Contract**：当前官方 API、schema、认证、限流、条款、许可和状态页面。实现时的合同事实以此为准。
- **Class B — Primary / Peer-reviewed Research**：平台论文、覆盖与质量研究、PRISMA-S、检索与引用评估。
- **Class C — Mature Open-source Experience**：Academic Research Skills（ARS）、PaperQA2、OpenScholar 的成熟实现经验。
- **Class D — ReAgent Engineering Decision**：限额、超时、重试、分层顺序、阈值等项目政策；必须显式标注。

对 14 个研究问题的回答如下：

1. 广泛发现需要跨学科覆盖、可表达的 keyword/filter、稳定分页、可记录排序、可接受的许可和可控成本；不能只看记录总量。
2. 身份验证需要稳定 native/external IDs、DOI 精确查询、批量/低请求获取及可解释的冲突字段。
3. canonical DOI metadata 应优先来自该 DOI registration agency 的注册元数据；Crossref 只对 Crossref DOI 是权威 fallback，不覆盖所有 DOI agency。
4. 单一 provider 可完成低风险 demo，但不足以同时给出广覆盖、独立身份交叉核验和 DOI 注册元数据回退。
5. 分层策略可揭示 missingness、ID mismatch 和 provider disagreement；它不自动证明 scientific quality。
6. 代价是更多请求、延迟、许可/归因面、冲突合并逻辑、故障状态和测试矩阵。
7. 当前 `PaperRecord` 必需/核心字段为 internal/provider ID、title、authors、provider、retrieval time、raw hash；abstract/year/venue/URL/DOI 可缺失，详见 `PROVIDER_FIELD_MAPPING.md`。
8. language、document type、OA、citation count、provider update timestamp、external IDs 是有价值的 enrichment，但当前 contract 尚未承载。
9. abstract、language、document type、venue、citation count 和 provider-inferred topics 的 missingness/语义差异过大，不得作为未经确认的 hard gate；citation count 不得作为 quality score。
10. primary discovery 的 invalid/auth/contract drift、不可完成的 pagination，以及无法满足最小候选数必须阻断。
11. selected-paper enrichment 和 DOI fallback 失败可在身份无歧义时降级；歧义或 DOI mismatch 必须 pause/fail closed。
12. 可安全长期保留的是请求参数、provider/version、时间、计数、normalized minimum metadata、checksums 和来源 URL；abstract/raw payload/fixtures 需 owner 的许可与 retention 决策。
13. 应用 human-reviewed pooled set 比较 primary-only 与 layered，量化 retrieval、metadata、dedup、engineering 和 product 指标。
14. OpenAlex 的 discovery fit、S2 的 enrichment fit、Crossref 的 DOI role 有证据支持；具体调用上限、超时、保留期、API key、公开归因位置仍是 owner policy。

## Provider snapshot

| Provider | 官方组织/目的 | 当前 access contract | 强项 | 关键限制 |
|---|---|---|---|---|
| OpenAlex | OurResearch；开放 scholarly graph | `https://api.openalex.org`；当前 Authentication 页面记录 no-key `$0.10/day`、free key `$1/day`；ReAgent live mode 要求 key 以先调用 `/rate-limit` 作 free-credit preflight；search/list 按 action 计费，100 RPS/credit exhaustion 触发 429 | 跨学科 discovery、filter/search/cursor、稳定 OpenAlex ID、DOI/PMID 等 external IDs、CC0 dataset | abstract 可能缺失或有质量问题；index 会更新；第三方 publication 权利不由 OpenAlex 保证 |
| Semantic Scholar Academic Graph | Allen Institute for AI；scientific discovery graph | `https://api.semanticscholar.org/graph/v1`；多数 endpoint 可匿名，官方产品页记录 anonymous shared pool；API key 用 `x-api-key`，初始 key 限额较低且可变 | S2 paper/corpus IDs、DOI/external IDs、abstract、citation graph、batch paper lookup，适合 selected-item verification | API 与 S2 Data/third-party content 各有许可；at-will/change risk；commercial/retention 需审查，不宜作为默认可自由再分发数据 |
| Crossref REST | Crossref member-governed DOI infrastructure | `https://api.crossref.org`；无需注册；`mailto` 进入 polite pool；2025-12-01 起 public/polite 有公开 request/concurrency limits | Crossref DOI 的 canonical deposited metadata、更新/更正关系、稳定 DOI、开放元数据检索 | 不是所有 DOI 的 registration agency；member-deposited 字段不齐；abstract 可能受版权；topic discovery/relevance 不是其首要用途 |

## Provider dossiers

### OpenAlex

**Identity/governance and maturity.** OpenAlex is operated by the nonprofit
OurResearch as an open catalog and successor-oriented alternative to closed
scholarly graphs. It publishes a REST API, OpenAPI specification, downloadable
snapshot, deprecation page and quarterly/free snapshot schedule. These are
sustainability signals, not an uptime or non-change guarantee; its ToS permits
changes and disclaims completeness.

**Access.** Current base URL is `https://api.openalex.org`. Current official
documentation says a free `api_key` is required for normal scale and receives
`$1/day` free credit; unauthenticated access has `$0.10/day`. Current action
prices distinguish singleton, list/filter, search and content. The documented
ceiling is 100 requests/s, with 429 for rate/credit exhaustion and
`X-RateLimit-*`/credit headers. `per_page` max is 100, basic paging is limited to
10,000 and cursor paging is available; OR filters and bulk DOI filters are
bounded. These numbers are Class A facts as of access date, not hardcoded
ReAgent budgets.

**Metadata.** Works expose OpenAlex ID, DOI/other IDs, title, authorships,
abstract inverted index, publication year/date, type/language, primary/source
locations, OA state, citation count, topics, updated date and retraction-related
flags. Field presence is not guaranteed. Abstract reconstruction and third-party
rights require special handling.

**Search.** Keyword/full-text search, exact ID/DOI singleton, filter, range/OR/
NOT, sort, semantic search, field selection, grouping and cursor pagination are
documented. Search ranking is provider-controlled and mutable; exact queries,
sort and timestamp must be retained.

**Reliability.** Official docs expose 429/rate headers and backoff guidance.
Malformed/schema/pagination cases still require ReAgent validation. ToS says the
service/data are as-is and may be incomplete; no SLA was found for the free API.

**Legal/policy.** The complete dataset is advertised CC0 and research citation is
requested. The ToS warns that referenced publications/external-platform content
may have separate rights and restrictions. Engineering policy therefore
separates metadata from abstract/publication content and retains field-level
provenance.

**Independent evidence.** Culbert et al. report comparable reference coverage on
a cleaned shared recent-publication subset but mixed metadata, including fewer
abstracts. Kim et al. (2026 preprint) report abstract integrity defects in a
sample. These limit provider marketing claims and justify independent
verification.

### Semantic Scholar Academic Graph

**Identity/governance and maturity.** Semantic Scholar is an AI2 scientific
discovery platform with Graph API 1.0, paper/author/citation graph endpoints,
dataset releases, tutorial and public status page. The API license permits AI2
to change features and describes at-will access, with notice language for full
sunset; this is a real operational risk.

**Access.** Base is `https://api.semanticscholar.org/graph/v1`. The current
official product page says most endpoints are publicly accessible without a key,
but anonymous traffic shares a 1,000 requests/s pool and may be further
throttled; issued keys use the case-sensitive `x-api-key` header and the
introductory rate is described as 1 request/s. Certain endpoints require a key.
These are service-wide/account-dependent facts to recheck; ReAgent must learn
effective limits from the issued key and responses. Paper relevance search uses
offset/limit; bulk search provides a continuation token; paper batch lookup is
available.

**Metadata.** Selectable fields include `paperId`, `corpusId`, external IDs,
title, authors/author IDs, abstract, year/publication date, venue/journal,
publication types, URL/OA PDF signal, citation/reference counts and graph
relations. Language/provider-updated time are not reliable common core fields.

**Search.** Relevance search, title/bulk search, exact paper lookup by S2/native
external identifiers, filters for year/publication type/OA/min citation and
batch paper retrieval are documented. Boolean and ranking semantics are not
equivalent to OpenAlex/Crossref and must not be translated silently. Citation
count remains advisory.

**Reliability.** Official API specs list endpoint response contracts; the status
page exposes availability/error-rate incidents. No stable universal retry
schedule or guaranteed per-key quota was found, so timeout/retry values are
Class D and 429/5xx handling is bounded.

**Legal/policy.** The API license is limited, terminable and non-sublicensable;
S2 Data and underlying third-party content may have additional licenses.
Public-display/marks/link and commercial-use implications require review.
Consequently S2 is proposed only for selected-item verification with minimum
retention, not bulk local redistribution.

**Independent evidence.** The Semantic Scholar Open Data Platform and S2ORC
papers describe large-scale multi-source graph construction and entity
resolution, but they are platform authors’ primary reports, not independent
guarantees of every API field. PaperQA2 provides Class C evidence for using S2
alongside Crossref.

### Crossref REST

**Identity/governance and maturity.** Crossref is member-governed DOI
infrastructure with a public REST API operating since 2013, documentation,
status page, annual public data file and commercial Metadata Plus option. Member
deposit is a governance strength for Crossref DOI metadata but also causes
field-level missingness.

**Access.** Base URL is `https://api.crossref.org`; no signup/key is required.
An approved `mailto` selects the polite pool. Effective 2025-12-01, the official
limits are: public single record 5 requests/s with concurrency 1 and list 1/1;
polite single DOI 10/3 and list 3/3. Cursor-based pagination, rows, filters,
select/query parameters and single DOI endpoints are documented. Crossref
recommends status checking and caching.

**Metadata.** Records include DOI, title, authors/ORCID, issued/published/created/
deposited/indexed dates, container title, type, URL, language when deposited,
license/link, abstract when deposited, citation count, relations/updates and
publisher/member data. These values describe deposits and do not guarantee
completeness or identical semantics to discovery graphs.

**Search.** `/works/{doi}` is the exact fallback; `/works` supports bibliographic,
title/author/container queries, date/presence filters, sort, facets and cursor
retrieval. It can discover records but relevance-ranked broad topic discovery is
not its best-evidenced role. `/works/{doi}/agency` prevents treating all DOIs as
Crossref DOIs.

**Reliability.** Current official material documents rate/concurrency behavior,
HTTP status checking, caching and a status page. Complex list queries receive
stricter limits. ReAgent still needs duplicate-cursor/page, malformed schema and
partial-response guards.

**Legal/policy.** Crossref says almost none of its metadata is copyrighted and it
may generally be used for any purpose, while explicitly warning that some
abstracts may be copyrighted by publishers/authors. The site content license
does not automatically license every deposited abstract. Raw/abstract retention
therefore remains owner-controlled.

**Independent evidence.** Crossref’s canonical role follows from DOI registry/
deposit governance, not proof that every deposited field is accurate. Multi-
database and scholarly-graph studies show provider overlap/missingness and
support using it as fallback rather than sole relevance source.

### Optional/domain-specific providers

arXiv, PubMed/NCBI, Europe PMC and CORE can be valuable for specific preprint,
biomedical or open-access domains. They were **deferred**, not scored into the
domain-general V1 choice: adding one now would widen query taxonomy, legal
review, test corpus and failure surface without evidence that it improves the
first general supervised milestone. The evaluation protocol is the revisit
mechanism.

## Weighted provider decision matrix

评分 1（弱/高风险）到 5（强/低风险），加权总分为 `Σ(weight × score) / 100`。评分是 Class D 的比较工具，不是外部事实。

| Driver | Weight | 权重依据 | OpenAlex | Semantic Scholar | Crossref |
|---|---:|---|---:|---:|---:|
| broad discovery coverage | 15 | V1 首要任务；B 支持 coverage 对 recall 的影响，权重为 D | 5 | 4 | 3 |
| metadata completeness | 7 | `PaperRecord` 构造需要；B+D | 4 | 4 | 4 |
| abstract availability | 5 | 当前 abstract-only workflow；B+D | 3 | 5 | 2 |
| DOI coverage | 5 | identity anchor；A+B+D | 4 | 4 | 5 |
| identifier stability | 5 | replay/merge/provenance；A+D | 5 | 5 | 5 |
| search quality | 10 | discovery relevance；A+B+D | 4 | 4 | 3 |
| filtering | 5 | year/type/language planning；A+D | 5 | 4 | 4 |
| batch efficiency | 3 | low request budget；A+D | 5 | 4 | 4 |
| reproducibility | 7 | recorded search contract；B+D | 5 | 4 | 5 |
| licensing | 9 | future commercial risk；A+D | 5 | 2 | 5 |
| attribution burden | 2 | UI/report requirement；A+D | 4 | 2 | 5 |
| retention compatibility | 5 | artifacts/fixtures；A+D | 5 | 2 | 4 |
| rate-limit suitability | 5 | supervised low volume；A+D | 4 | 3 | 5 |
| error transparency | 3 | normalized failure policy；A+D | 4 | 3 | 4 |
| integration complexity | 4 | additive adapter goal；C+D | 3 | 3 | 3 |
| fallback suitability | 3 | layered reliability；C+D | 3 | 4 | 5 |
| testability | 4 | fixtures/replay；C+D | 4 | 4 | 5 |
| operational risk | 3 | change/availability/legal surface；A+D | 4 | 3 | 5 |
| **weighted total** | **100** |  | **4.37** | **3.63** | **4.04** |

总分不能替代 role fit：Crossref 的高许可/稳定性分不让它成为最好的 topic discovery engine；S2 的许可风险不否定其对少量 selected papers 的 verification 价值。

### Architecture alternatives

| Alternative | 请求/延迟估计（D） | 优点 | 缺点与 failure mode | V1 适用性 |
|---|---|---|---|---|
| A. OpenAlex only | 1–3 discovery calls；最低延迟 | 最小实现、开放、广覆盖、易重放 | 无独立交叉核验；OpenAlex missing/error 直接阻断；DOI deposit conflict 不被发现 | 可作第一 adapter milestone；不足以成为最终 verification architecture |
| B. Semantic Scholar only | 1–3 search calls；低延迟 | abstract/citation/external ID 丰富 | API/data license 与 future commercial use 风险更高；shared anonymous throttle；单源冲突仍存在 | 不推荐作为 primary V1 |
| C. Layered：OpenAlex → S2 → Crossref | 1–3 + 最多 5 + 最多 3；预计增加数秒到几十秒 | discovery、independent verification、registry fallback 分责；冲突可见 | 最复杂；许可/归因/重试更多；provider disagreement 需 pause/fail policy | **Proposed target architecture**，但分阶段实施 |
| D. OpenAlex + Crossref | 1–3 + 最多 3 | 避开 S2 许可面，DOI metadata 稳定 | 没有 S2 identity/citation graph enrichment；无 DOI 的歧义更难处理 | 若 owner 不批准 S2 条款时的可行 fallback |

## Decision PS-001: Primary discovery provider

Status: **Accepted for OpenAlex-only Phase 9B-1 scope**
Evidence classes: A / B / C / D  
Last verified: 2026-07-28
Candidate decision: OpenAlex 作为 ReAgent V1 primary discovery；第一实施里程碑只替换 `PaperSearchProvider` boundary。

Sources:
1. OpenAlex, “Overview / Authentication & Pricing / Search / OpenAPI”, official docs, Class A, live documentation, accessed 2026-07-27: https://developers.openalex.org/
2. OpenAlex Terms of Service, OurResearch, Class A, accessed 2026-07-27: https://openalex.org/OpenAlex_termsofservice.pdf
3. Priem et al., “OpenAlex: A fully-open index…”, arXiv platform paper, Class B (preprint), 2022, accessed 2026-07-27: https://arxiv.org/abs/2205.01833
4. Culbert et al., “Reference Coverage Analysis of OpenAlex compared to Web of Science and Scopus”, Class B (preprint/current study), 2024, accessed 2026-07-27: https://arxiv.org/abs/2401.16359
5. Kim et al., “One in Eight OpenAlex Abstracts Has Integrity Issues”, Class B (preprint), 2026, accessed 2026-07-27: https://arxiv.org/abs/2605.20168

What the evidence supports:
- Broad, open, filterable discovery with stable IDs, DOI lookup, cursor pagination and reproducible request recording.
- On shared recent publications, reference coverage can be comparable to Scopus/WoS, while abstract completeness is mixed.

What the evidence does not support:
- Perfect coverage, unbiased ranking, error-free abstracts, exact rerun result equality, or systematic-review compliance.

Known conflicts:
- Older docs/skills describe an email “polite pool”; the current OpenAlex contract is API-key and credit based. Current official docs control.
- OpenAlex markets broad/inclusive coverage; independent studies show field/language/metadata variation. Provider claims are not treated as independent validation.

ReAgent inference:
- OpenAlex best matches current broad-discovery port, but adapter output must expose missingness and record exact request/pagination/sort.

Alternatives: S2 primary; Crossref search; domain-specific providers.  
Risk: API pricing/contract changes, abstract quality, dynamic index.  
Revisit trigger: evaluation shows lower Recall@K/relevance than S2, license changes, or >5% blocking contract/malformed response rate.  
Owner approval required: **Yes**.

## Phase 9B-1 official OpenAlex contract re-verification

Access date: **2026-07-27**. These Class A sources are the implementation source
of truth for `backend/research/adapters/openalex.py`.

| Official source | Current fact used | Implementation impact / limitation |
|---|---|---|
| OpenAlex, [Authentication & Pricing](https://developers.openalex.org/api-reference/authentication) | base `https://api.openalex.org`; `api_key` query parameter; no-key free daily usage `$0.10`, free key `$1`; search `$1/1000` calls; `/rate-limit`; `meta.cost_usd`; `X-RateLimit-*`; 100 requests/s; `per_page<=100`; basic paging 10,000; exponential backoff guidance | ReAgent injects, never logs/stores, the key; supervised mode requires a key so `/rate-limit` can prove remaining free credit before search; one search page, max 20; actual provider credit recorded as a decimal string while out-of-pocket `estimated_cost_minor_units=0`. Pricing/credits can drift and must be rechecked. |
| OpenAlex, [Works](https://developers.openalex.org/api-reference/works) and [List Works](https://developers.openalex.org/api-reference/works/list-works) | Work fields include `id`, `doi`, `display_name/title`, `authorships`, `abstract_inverted_index`, publication fields, primary location, language/type; list response has `meta` + `results` | Adapter selects only required root fields, validates root/meta/results and maps optional missingness explicitly. Abstracts are reconstructed from the inverted index and remain third-party untrusted content. |
| OpenAlex, [Search](https://developers.openalex.org/guides/searching) | `search` searches title/abstract/fulltext; Boolean operators are supported; default results include provider `relevance_score` and citation count influences it | Exact query is recorded. ReAgent performs its existing deterministic rank afterward and does not use citation count as a quality score. OpenAlex relevance is discovery ordering, not evidence of scientific quality. |
| OpenAlex, [Page through Results](https://developers.openalex.org/guides/page-through-results) | `cursor=*`, then exact `next_cursor`; `per_page` 1–100 | Phase 9B-1 deliberately requests one cursor page because max candidates is 20. `complete` means the requested bounded plan was fulfilled, never an exhaustive result corpus. |
| OpenAlex, [Select Fields](https://developers.openalex.org/guides/selecting-fields) | `select` supports top-level fields only | Requested-field identity is pinned in `ProviderOperation`; nested field selection is not attempted. |
| OpenAlex, [Error Handling](https://developers.openalex.org/api-reference/errors) | 400 bad request, 403 rate exceeded, 404 not found, 429 daily limit, 500 transient; exponential backoff for transient failures | 400 is non-retryable invalid query; official 403 and 429 normalize to rate limit; 5xx/timeouts/network retry at most twice after initial call. Diagnostics exclude bodies, URLs and credentials. |
| OpenAlex, [Check rate limit status](https://developers.openalex.org/api-reference/rate-limits/check-rate-limit-status) | `/rate-limit` requires an API key and exposes daily remaining and endpoint cost | This resolves the zero-out-of-pocket policy: live composition requires a key and blocks before `/works` if free daily remaining credit cannot cover search. Prepaid balance is never needed. |
| OpenAlex, [Pricing / CC0](https://help.openalex.org/hc/en-us/articles/24397762024087-Pricing), [About us](https://help.openalex.org/hc/en-us/articles/24396686889751-About-us), [citation guidance](https://help.openalex.org/hc/en-us/articles/28761511652247-How-can-I-cite-OpenAlex), and [Terms](https://openalex.org/OpenAlex_termsofservice.pdf) | OpenAlex describes its dataset as CC0 and asks users to cite the OpenAlex paper; Terms preserve risks for linked publications/third-party material and disclaim completeness | Report displays OpenAlex attribution; normalized metadata, IDs, hashes and plan/execution evidence may persist privately. Raw responses and real abstracts are not committed. Abstract/publication rights are not inferred from dataset-level CC0. This is engineering risk assessment, not legal advice. |

### Conflicts with Phase 9B-0 evidence

1. Phase 9B-0 recorded unauthenticated allowance as `$0.01/day`; current official
   Authentication & Pricing says `$0.10/day`. The current value controls and the
   earlier value is retained here as a documented drift conflict.
2. The OpenAlex help-center pricing page still presents an older “100k/day,
   max 10/second” style table, while the current developer Authentication page
   uses credit-based pricing and a 100 requests/s ceiling. The developer
   contract controls adapter behavior; the conflict is a provider-drift risk.
3. The general authentication page permits no-key trial usage, but the official
   `/rate-limit` reference requires a key. ReAgent therefore makes the stricter
   project decision to require a free key for supervised live mode so monetary
   budget can fail closed before the billable search.

### Phase 9B-1 Class D decisions

- One cursor page / maximum 20 candidates / maximum 3 discovery attempts.
- One free-credit preflight plus up to three Works attempts reserves four
  request units; the full workflow hard cap remains 12.
- 15-second request timeout, exponential delays 1/2 seconds (or bounded
  `Retry-After`), 90-second provider-operation deadline.
- Exact DOI then exact OpenAlex ID automatically deduplicate; normalized
  title+year is advisory only; fuzzy/version merging is prohibited.
- Full response bodies are not retained; selected raw-record canonical hashes
  are retained. Live artifacts remain ignored and require owner-approved cleanup.

These are ReAgent policies, not OpenAlex recommendations. Revisit when official
contracts drift, live smoke reveals incompatible behavior, or evaluation begins.

## Decision PV-001: Verification and enrichment provider

Status: **Proposed**
Evidence classes: A / B / C / D
Last verified: 2026-07-27  
Candidate decision: S2 verification runs only on selected papers and identity-ambiguous ranked candidates, not every discovery result.

Sources:
1. Semantic Scholar Academic Graph API docs/product/tutorial, AI2, Class A, accessed 2026-07-27: https://api.semanticscholar.org/api-docs
2. Semantic Scholar API License Agreement, AI2, Class A, updated 2023-05-17, accessed 2026-07-27: https://www.semanticscholar.org/product/api/license
3. Kinney et al., “The Semantic Scholar Open Data Platform”, Class B (preprint), 2023, accessed 2026-07-27: https://arxiv.org/abs/2301.10140
4. PaperQA2 repository, Class C, accessed 2026-07-27: https://github.com/Future-House/paper-qa
5. ARS S2 protocol/verification workflow, Class C, commit `e624c5a0682176415b97db4dc3b53a3ec2b556da`, accessed 2026-07-27: https://github.com/Imbad0202/academic-research-skills

What the evidence supports:
- DOI/external-ID paper lookup, stable S2 IDs, selected-paper batch retrieval, and independent metadata comparison.
- Mature systems use multiple metadata providers for enrichment and retraction/citation-related checks.

What the evidence does not support:
- That S2 is authoritative over DOI registries, that its citation count is a quality score, or that all S2 data can be retained/redistributed commercially.

Known conflicts:
- ARS says unauthenticated 1 RPS/authenticated 10 RPS; the current S2 product page describes a shared anonymous pool and introductory key limits. Official current contract controls and limits must be discovered at runtime/configuration review.

ReAgent inference:
- Verification of selected (3–5) items gives most identity value with bounded request/legal surface.

Alternatives:
- all 20 discovered: up to 20 lookups (or batch), maximum validation but unnecessary exposure;
- top 10 ranked: moderate;
- DOI-bearing only: cheap but misses non-DOI ambiguity;
- ambiguous only: lowest calls but less independent audit.

Risk: API terms and underlying data licenses; key availability; service at-will/change.  
Revisit trigger: legal review rejects data use, selected-paper mismatch rate is negligible, or batch endpoint contract changes.  
Owner approval required: **Yes**.

## Decision PS-002: DOI fallback

Status: **Proposed**  
Evidence classes: A / C / D  
Last verified: 2026-07-27  
Candidate decision: Crossref `/works/{doi}` only for DOI-bearing records whose DOI is registered by Crossref and whose core metadata is missing/conflicting.

Sources:
1. Crossref REST API documentation, Class A, accessed 2026-07-27: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
2. Crossref 2025 rate-limit update, Class A, effective 2025-12-01, accessed 2026-07-27: https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/
3. Crossref REST filters, Class A, accessed 2026-07-27: https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/
4. PaperQA2 metadata behavior, Class C, accessed 2026-07-27: https://github.com/Future-House/paper-qa

What the evidence supports:
- No-signup DOI lookup, member-deposited metadata, updates/relations, polite-pool `mailto`, caching, current public/polite limits.

What the evidence does not support:
- Crossref as authority for DataCite/other-agency DOI records, full abstract availability, or broad semantic discovery.

Known conflicts: older Crossref rate-limit values are superseded by the official 2025-12-01 limits.  
ReAgent inference: query `/works/{doi}/agency` or handle non-Crossref DOI as unresolved/future DataCite, never assume.  
Alternatives: no DOI fallback; DataCite future adapter; OpenAlex-only.  
Risk: deposited metadata missingness and copyright in abstracts.  
Revisit trigger: non-Crossref DOI unresolved rate exceeds proposed 5%, or evaluation needs DataCite.  
Owner approval required: **Yes**.

## Decision PD-001: Deterministic identity and deduplication

Status: **Proposed**  
Evidence classes: A / B / C / D  
Last verified: 2026-07-27  
Candidate decision:

1. Normalize DOI by trim, remove `doi:`/resolver prefix, Unicode NFC, lowercase ASCII DOI, validate `10.<registrant>/<suffix>`; an exact DOI match is an identity candidate, then title/year sanity-check.
2. Exact known external-ID crosswalk (S2 CorpusID/paperId, PMID, arXiv ID) can join records only when namespace matches.
3. Exact provider-native ID is authoritative only inside the same provider/version namespace.
4. Unicode-NFKC + casefold + HTML entity decode + whitespace/punctuation normalization of title with exact year creates a **candidate cluster**, not an automatic merge when collisions exist.
5. Title similarity + normalized first author + year is advisory/manual only.
6. Ambiguous/unresolved records remain separate and visible.

Author normalization retains display order, separates identifiers from names, applies Unicode NFKC/casefold for comparison, and never assumes name equality means person equality. Preprint/published and conference/journal versions remain distinct but may carry a `related_version` cluster unless exact DOI/provider relationship proves same manifestation. False-positive protection has priority over reducing duplicate count.

Sources:
1. DOI Handbook, International DOI Foundation, Class A, accessed 2026-07-27: https://www.doi.org/doi-handbook/HTML/
2. Crossref REST/agency endpoints, Class A, accessed 2026-07-27: https://www.crossref.org/documentation/retrieve-metadata/rest-api/
3. S2ORC/Open Data Platform entity resolution papers, Class B, accessed 2026-07-27: https://aclanthology.org/2020.acl-main.447/ and https://arxiv.org/abs/2301.10140
4. ARS bibliography/source-verification agents, Class C, accessed 2026-07-27.

What the evidence supports: persistent IDs before fuzzy matching; conservative unresolved handling; transparent version relations.  
What it does not support: a universal title-similarity threshold.  
Known conflicts: provider DOI/title/year can disagree or refer to different manifestations.  
ReAgent inference: no fuzzy automatic merge in first live milestone.  
Alternatives: aggressive fuzzy merge; DOI-only dedup; manual-only dedup.  
Risk: residual duplicates versus false merge; proposed policy prefers residual duplicates.  
Revisit trigger: human-reviewed evaluation produces >1% false merges or >10% unresolved duplicate clusters.  
Owner approval required: **Yes**.

## Decision PS-003: Search methodology and reproducibility

Status: **Proposed**  
Evidence classes: B / C / D  
Last verified: 2026-07-27  
Candidate decision: add versioned `SearchPlan` and execution artifacts; call the output a documented guided literature search, not a systematic review.

Sources:
1. Rethlefsen et al., PRISMA-S, *Systematic Reviews* 10:39, peer reviewed, Class B, 2021, accessed 2026-07-27: https://doi.org/10.1186/s13643-020-01542-z
2. Gusenbauer & Haddaway, academic search-system retrieval evaluation, peer reviewed, Class B, 2020, accessed 2026-07-27: https://pmc.ncbi.nlm.nih.gov/articles/PMC7079055/
3. Bramer et al., database combinations study, peer reviewed, Class B, 2017, accessed 2026-07-27: https://pmc.ncbi.nlm.nih.gov/articles/PMC5718002/
4. ARS Search Strategy Framework, Class C, accessed 2026-07-27.

What the evidence supports: exact databases/platforms, complete query strings, limits, dates, dedup and record accounting should be recorded; multi-source searches can increase recall.  
What it does not support: systematic-review compliance from four JSON artifacts or one provider.  
Known conflicts: provider indices/ranking change, so identical historical results cannot be guaranteed.  
ReAgent inference: reproducibility means reproducible request/procedure plus immutable captured result hash, not promise of identical future provider output.  
Alternatives: retain only query string; full PRISMA workflow.  
Risk: users overinterpret “PRISMA-style” counts.  
Revisit trigger: product claims systematic review or adds protocol registration/full screening.  
Owner approval required: **No** for principle; **Yes** for policy fields/retention.

### Proposed SearchPlan contract (additive, not implemented)

Required fields:

```text
schema_version, plan_id, topic, research_question?, keywords, synonyms,
provider_queries[{provider, exact_query, boolean_expression, field_scope}],
year_range, language?, document_types?, inclusion_criteria, exclusion_criteria,
requested_max_results, providers, generated_at, approved_at?,
adapter_versions, api_contract_versions?, pagination_policy, sort_policy,
user_corpus_policy, search_expansion_policy
```

Artifacts:

- `search_plan.json`: immutable intent and exact provider query.
- `search_execution.json`: request fingerprints, operation IDs, timestamps, pages/cursors (hashed or sanitized), status/warnings and response hashes.
- `search_statistics.json`: identified, deduplicated, screened, selected, excluded and failure counts; “PRISMA-style accounting”, not compliance.
- `provider_verification.json`: per-paper identity evidence, compared fields, conflicts, decision and verifier version.

## Decision PB-001: Supervised V1 budget

Status: **Proposed**  
Evidence classes: A / D  
Last verified: 2026-07-27  
Candidate decision:

| Limit | Proposed value | Type / rationale |
|---|---:|---|
| discovery requests | 3 | D; initial + at most two pages/retries accounting must remain distinct |
| discovery pages | 2 | D; 20 candidates fit well below provider maxima |
| candidates | 20 | D; reviewability |
| verification logical lookups | 5 | D; selected/ambiguous only, prefer official batch |
| DOI fallbacks | 3 | D |
| total live requests | 12 | owner hard cap; retries count |
| selected papers | 3–5 | existing workflow minimum + D maximum |
| request timeout | 15 s | D, not provider mandate |
| retry | max 2 retries after initial | D; only 429/timeout/5xx/network, honor `Retry-After`, exponential full jitter capped at 20 s |
| total provider runtime | 90 s | D |
| monetary cost | **0** | owner must approve any non-zero budget |
| retained raw-response bytes | 2 MiB/run maximum | D; default raw body retention off |

Provider-imposed facts remain configuration/response-header inputs and may be stricter. Reservation occurs before every call through existing `ProviderOperationService`; actual usage/cost settles after success/failure, retry is a new operation attempt or auditable child according to the existing idempotency contract, and replay may not reserve twice.

Sources: current OpenAlex authentication/pricing docs; S2 product/API docs; Crossref current rate-limit announcement (all Class A).  
What the evidence does not support: these exact ReAgent limits as standards.  
Alternatives: 1/5/10 discovery pages; all-candidate verification; nonzero credit.  
Risk: insufficient recall in small cap.  
Revisit trigger: evaluation yield/Recall@K fails or 429 rate >1%.  
Owner approval required: **Yes**.

## Decision PL-001: Attribution, licensing and retention

Status: **Proposed**  
Evidence classes: A / C / D  
Last verified: 2026-07-27  
Candidate decision: minimum normalized metadata + provenance by default; no provider raw payload or real abstract in committed fixtures; private, time-bounded live artifacts only after owner approval.

| Item | Official fact / engineering assessment | Proposed ReAgent policy |
|---|---|---|
| OpenAlex | dataset advertised CC0; research citation requested; ToS disclaims rights in third-party publications | show “Metadata: OpenAlex” + source URL/provider version; normalized metadata may persist; treat abstract separately |
| S2 | API license is limited/terminable; S2 Data and third-party content have separate licenses; public display may carry marks/links requirements | selected-only use; preserve S2 URL/identity/license marker; no redistribution/raw fixtures; commercial use needs review/possible expanded permission |
| Crossref | metadata generally reusable; abstracts may be copyrighted; polite pool uses contact email | identify client with approved `mailto`; store DOI/core metadata/source URL; strip JATS safely; do not assume abstract redistribution |
| ARS | repository license CC BY-NC 4.0 | cite methodology; independently implement ideas; do not vendor/copy prompts, templates or code into a future commercial product |
| raw responses | licenses and personal/free-text fields vary | default no raw body retention; keep hash, status, headers allowlist, field-level provenance; optional encrypted/private 30-day retention requires owner |
| fixtures | real abstracts may be copyrighted and terms may restrict redistribution | synthetic/hand-authored fixtures only by default; live contract tests use ephemeral responses |
| public report | provider/source attribution should survive | provider names, source URLs, query timestamp and abstract-only disclosure in report/provenance |

This is an engineering risk assessment, **not legal advice**.

Sources:
1. OpenAlex docs and ToS, Class A.
2. Semantic Scholar API License, Class A.
3. Crossref REST docs, Class A.
4. Academic Research Skills LICENSE, CC BY-NC 4.0, Class C, accessed 2026-07-27: https://github.com/Imbad0202/academic-research-skills/blob/main/LICENSE

What the evidence does not support: legal certainty or a single license covering provider-sourced abstracts.  
Known conflicts: OpenAlex CC0 dataset messaging coexists with ToS warnings about external-platform publication rights; use conservative field-level handling.  
Alternatives: retain all raw payloads; retain normalized-only forever; ephemeral-only.  
Risk: commercial incompatibility or inability to reproduce exact payload.  
Revisit trigger: commercial launch, public fixture publication, provider term change, legal review.  
Owner approval required: **Yes**.

## Decision PE-001: Evaluation before promotion

Status: **Proposed**
Evidence classes: B / C / D
Last verified: 2026-07-28
Candidate decision: execute `SEARCH_EVALUATION_PROTOCOL.md` comparing OpenAlex-only and layered architecture before production default.

Sources:
1. PRISMA-S, Class B.
2. OpenScholar / ScholarQABench, Nature 2026, Class B, accessed 2026-07-27: https://www.nature.com/articles/s41586-025-10072-4
3. PaperQA2 / LitQA2, Class B/C, accessed 2026-07-27: https://arxiv.org/abs/2409.13740
4. OpenAlex coverage/abstract-quality studies above, Class B.

What the evidence supports: multi-domain human review, retrieval and citation/metadata metrics, explicit evaluator protocol.  
What it does not support: universal acceptance thresholds or screenshot-only validation.  
ReAgent inference: begin with 12 topics across four domain groups, pool top-20 from both architectures, blinded relevance labels and adjudication.  
Alternatives: 6-topic smoke set; 30-topic stronger set.  
Risk: small-set variance and pool incompleteness.  
Revisit trigger: new domain, ranking change, provider contract/adapter version change.  
Owner approval required: **Yes** for set size and thresholds.

Phase 9B-2A implementation note（2026-07-28）：evaluation harness、12-topic
engineering set、human review import/export、adjudication validation、pure
metrics、report generator 和 retention policy 已实现并通过 synthetic
network-free tests。**没有执行 live pilot、没有生成 human labels、没有完成
PE-001 evaluation，也没有实现 layered architecture。** 因此 PE-001 仍为
Proposed；owner 仍需批准 reviewers、retention 和 thresholds。

## Decision PL-002: OpenAlex evaluation retention

Status: **Proposed**
Evidence classes: A / B / D
Last verified: 2026-07-28
Candidate decision: raw response/key never retained；normalized live pools and
optional short abstract previews remain private/ignored；default 30-day pool
review window and 14-day abstract-preview limit；pseudonymous judgments and
no-abstract aggregate reports may be retained after owner review。

Sources:
1. OpenAlex Terms and CC0/pricing/citation sources already registered above
   (Class A).
2. PRISMA-S reporting evidence (Class B).
3. `docs/evidence/OPENALEX_DATA_RETENTION_POLICY.md` (Class D policy).

What the evidence supports: minimum-data collection、query/result accounting、
provider attribution 和不把 dataset license 推断为第三方 abstract rights。
What it does not support: legal certainty、universal retention duration 或公开
redistribution rights。
ReAgent inference: candidate pool 30 days、abstract preview 14 days、
raw-response off、private checksum-chained ProviderOperation journal、explicit
scoped cleanup。
Alternatives: ephemeral-only；owner-approved longer private retention。
Risk: protected-text retention、dynamic-index reproducibility loss、orphan
filesystem bytes。
Revisit trigger: owner/legal review、public/commercial distribution、provider
term change、rights incident。
Owner approval required: **Yes**。

Phase 9B-2B-1 pilot note（2026-07-28）：owner approved the 30-day normalized
pool/journal and 14-day abstract-preview policy for one bounded three-topic
pilot. `cs-machine-unlearning` and `social-algorithmic-management` each produced
20 normalized candidates. `nonenglish-chinese-digital-humanities` returned one
provider record that was rejected by the existing safe field-length validation,
so its normalized pool is empty. Six requests, zero retries and `$0.003` free
provider credit were recorded; all three operations settled. Two blank
pseudonymous review packets were generated. **No human labels, relevance
metrics, adjudication or provider-quality conclusion exists**, so PE-001
remains Proposed and provider promotion is not authorized.

## Decision PE-002: Automated silver relevance and multilingual expansion

Status: **Proposed**
Evidence classes: A / B / C / D
Last verified: 2026-07-29

Candidate decision: replace full two-human review for the current prototype with
**automated silver-label relevance evaluation with targeted human audit**, while
retaining the two-human method and packets for future expert-gold work. Add an
explicit, versioned multilingual SearchPlan in a separate later milestone.

Evidence:

1. Official OpenAI, Anthropic, gpt-oss, and vLLM contracts are registered with
   source title/URL/date/claim/limitation in
   `LLM_JUDGE_PROVIDER_MATRIX.md` (Class A/C).
2. Primary relevance/judge research on pointwise/pairwise ranking, position
   bias, prompt sensitivity, multilingual variance, self-preference, and
   human/LLM disagreement is registered in
   `AUTOMATED_RELEVANCE_JUDGE_EVIDENCE.md` (Class B).
3. `SILVER_LABEL_AGGREGATION_POLICY.md`,
   `HUMAN_AUDIT_PROTOCOL.md`, and `MULTILINGUAL_SEARCH_PLAN.md` are ReAgent
   Class D proposals.

What the evidence supports: a bounded, versioned, audited silver proxy; two
pointwise prompts; limited mirrored pairwise consistency; conservative human
routing; exact query-variant provenance; exact DOI/ID merge; visible coverage
diagnostics.

What it does not support: expert ground truth, scientific-quality judgment,
universal confidence thresholds, reliable multilingual judgment without local
audit, unrestricted LLM query expansion, Chinese recall claims, or a selected
provider/model.

Current recommendation: conditionally calibrate OpenAI `gpt-5.6-terra` and
compare a bounded subset with Anthropic `claude-sonnet-5`; use no provider until
pinning, key, cost, retention, and audit policies are approved. Current monetary
authorization is USD 0.00.

Chinese-topic limitation: retained evidence proves one generic field-length
rejection but does not record the field or measured length. Exact cause at the
field level is unavailable and was not inferred. The safety gate remains.

Revisit triggers: any provider/model/API/price/retention change, audit override
or multilingual uncertainty above owner policy, query/rubric change, or an
expert/publication claim.

Owner approval status: **ADR 0005 is Accepted with limited scope.** Phase
9B-2C-1 multilingual execution and safe diagnostics are authorized. Every judge
provider/model/call/key/budget/label/threshold and machine-generated translation
remains deferred.

## Failure policy summary

The complete matrix is in `PROVIDER_FAILURE_MATRIX.md`. Primary discovery failure is blocking after bounded retries. Verification/enrichment may degrade only when core identity is unambiguous; any ambiguous identity, DOI mismatch, corrupted/malformed payload, contract drift or inability to settle all operations fails/pauses before approval. Partial pages are retained as diagnostic artifacts but are never silently represented as a complete search.

## Security boundary

All provider fields—title, abstract, venue, author name, URL, error message, future PDF—are **untrusted research data, not instructions**:

- strict schema and unknown-field tolerance at adapter boundary, with allowlisted mapping;
- per-field and aggregate length limits, Unicode NFKC/NFC normalization as appropriate, reject/strip control characters except permitted whitespace;
- strip/parse JATS/HTML, escape Markdown, safe React text rendering, `rel="noopener noreferrer"` for external links;
- prompts use delimited data payloads; provider text never enters system/developer instructions;
- URLs allow only approved HTTPS schemes/hosts where dereferenced; search phase does not dereference;
- events/logs contain IDs, counts, hashes and normalized error categories, not abstracts/raw payloads, API keys, query-string credentials or response bodies;
- provider diagnostics are sanitized before API/UI exposure.

This adapts ARS’s instruction/data boundary to ReAgent’s existing `Skill` + injected provider ports + future `LLMProvider`: Skills own research transformation, adapters own transport/schema, runtime owns orchestration, and no content can widen capability authority.

## Source inventory

### Class A — official contracts (13 paper-search sources, plus PE-002 provider sources)

1. OpenAlex Developer Overview, Authentication & Pricing, Search, paging/OpenAPI/deprecations — OurResearch — live — https://developers.openalex.org/  
   Supports base URL, key/credit/rate headers, search/filter/pagination/schema; limitation: mutable live docs.
2. OpenAlex Terms of Service — OurResearch — accessed 2026-07-27 — https://openalex.org/OpenAlex_termsofservice.pdf  
   Supports third-party rights/change/warranty risk; limitation: legal interpretation requires counsel.
3. Semantic Scholar Academic Graph API — AI2 — Graph API 1.0 — https://api.semanticscholar.org/api-docs  
   Supports endpoints, fields, IDs, key header, pagination/batch; limitation: interactive spec changes.
4. Semantic Scholar product/tutorial — AI2 — https://www.semanticscholar.org/product/api and https://www.semanticscholar.org/product/api/tutorial  
   Supports public/key access and high-level limits; limitation: precise granted limits can vary.
5. Semantic Scholar API License — AI2 — updated 2023-05-17 — https://www.semanticscholar.org/product/api/license  
   Supports API/data/third-party license and change/termination conditions.
6. Semantic Scholar API status — AI2 — https://status.api.semanticscholar.org/  
   Supports operational status/5xx monitoring; not an SLA.
7. Crossref REST API docs — Crossref — https://www.crossref.org/documentation/retrieve-metadata/rest-api/  
   Supports endpoints, no signup, metadata/abstract caveat.
8. Crossref rate-limit update — Crossref — 2025-11-05/effective 2025-12-01 — https://www.crossref.org/blog/announcing-changes-to-rest-api-rate-limits/  
   Supports public/polite current limits, caching and mailto.
9. Crossref REST filters — Crossref — https://www.crossref.org/documentation/retrieve-metadata/rest-api/rest-api-filters/  
   Supports date/presence filters and update timestamps.
10. DOI Handbook — International DOI Foundation — https://www.doi.org/doi-handbook/HTML/  
    Supports DOI persistence/identity concepts; not a metadata-merge algorithm.
11. PRISMA-S official listing — PRISMA/EQUATOR — https://www.prisma-statement.org/prisma-search  
    Supports 16-item reporting checklist; not provider selection.
12. ARS upstream LICENSE — repository owner — CC BY-NC 4.0 — https://github.com/Imbad0202/academic-research-skills/blob/main/LICENSE
13. ARS-Codex LICENSE/manifest — repository owner — CC BY-NC 4.0 — https://github.com/Imbad0202/academic-research-skills-codex

PE-002 dynamic judge-provider sources are maintained in
`LLM_JUDGE_PROVIDER_MATRIX.md`; its access date is 2026-07-29. That matrix is the
authoritative detail register to avoid duplicating mutable model/pricing/
retention facts here.

### Class B — primary/peer-reviewed research (paper-search set plus PE-002 judge research)

1. Priem et al. 2022 OpenAlex platform paper (preprint).
2. Culbert et al. 2024 OpenAlex reference coverage (preprint).
3. Kim et al. 2026 OpenAlex abstract integrity (preprint).
4. Kinney et al. 2023 Semantic Scholar Open Data Platform (preprint).
5. Lo et al. 2020 S2ORC, ACL peer reviewed — https://aclanthology.org/2020.acl-main.447/
6. Rethlefsen et al. 2021 PRISMA-S, peer reviewed.
7. Gusenbauer & Haddaway 2020 search-system evaluation, peer reviewed.
8. Bramer et al. 2017 database combinations, peer reviewed.
9. Asai et al. OpenScholar, Nature 2026, peer reviewed.

PE-002 primary judge/relevance research is maintained in
`AUTOMATED_RELEVANCE_JUDGE_EVIDENCE.md`, including Faggioli et al., Sun et al.,
Qin et al., Zheng et al., Shi et al., Liu et al., Fu and Liu, Karpinska et al.,
and Hashemi et al., with claim and limitation.

### Class C — mature open-source experience (4 systems/repositories)

1. ARS upstream, commit `e624c5a0682176415b97db4dc3b53a3ec2b556da`, plugin `3.19.0`, deep-research `2.11.0`, CC BY-NC 4.0.
2. ARS-Codex, commit `f8d6b061efe98564a3f554c917fce66dcef6ca54`, adapter `0.1.22`, vendored upstream commit `828ef3b613b0e8b91830da3328a1e33d4eb5ab4c`, CC BY-NC 4.0.
3. PaperQA2 official repository, metadata from Crossref/S2 and evidence-context/citation pipeline.
4. OpenScholar official repository, Apache-2.0 code, retrieval/reranking/citation/evaluation pattern.

### Class D

All matrix weights/scores, request/time/size caps, selected-only verification, merge conservatism, artifact set and proposed thresholds are ReAgent decisions. They require owner approval where marked and must be revalidated against current official contracts immediately before implementation.

### PE-003 — Phase 9B-2C-1 implementation evidence

Evidence date: 2026-07-29. Evidence class: **Class D engineering
implementation and network-free verification**.

- ADR 0005 was accepted only for explicit multilingual variants, exact merge,
  provenance, and safe diagnostics; judge/provider/model recommendations remain
  unaccepted.
- `reagent-query-variant/v1` and
  `reagent-multilingual-search-plan/v1` use canonical JSON and stable SHA-256.
- Four owner-approved manual Chinese/English variants are versioned in
  `evaluation/topics/openalex_chinese_multilingual_v1.json`; no LLM or machine
  translation produced them.
- Every variant owns a separate ProviderOperation and result evidence envelope.
- Exact DOI then exact OpenAlex ID are the only automatic merge identities.
  Title/year is advisory and fuzzy automatic merge is prohibited.
- Future length rejection evidence records field, normalized length, configured
  limit, SHA-256 and an at-most-80-character safe preview. Historical evidence
  is not backfilled.
- Network-free focused verification is recorded in
  `.agent_read/progress/multilingual_search_and_safe_diagnostics.md`.

These are project implementation facts, not evidence that multilingual recall or
scientific relevance improved.

### PE-004 — Phase 9B-2C-2 synthetic Judge substrate

- **Class D implementation evidence, 2026-07-29:** immutable automated request,
  judgment, mirrored pairwise, consensus, audit request/result/queue, and silver
  metric contracts are implemented under `backend/research/evaluation/`.
- The provider-independent port has one fixture-driven Fake adapter. It uses no
  network, credentials, model server, or text heuristic. Its ProviderUsage is
  fixed and zero cost.
- The evaluation-private artifact storage, append-only operation journal, and
  ProviderOperationService are reused. Every attempted A/B/pairwise call settles;
  completed replay makes no Judge call.
- The committed fixture set contains only invented titles/previews with an
  enforced synthetic source marker. It does not contain OpenAlex candidate
  content or relevance labels for a real record.
- Confidence `0.80`, 10% topic-stratified sampling, and cap 20 are
  `TEST_POLICY_ONLY`, not an update to the limited acceptance of ADR 0005.
- Evidence and exact regression results are recorded in
  `.agent_read/progress/fake_relevance_judge_substrate.md`.

## Owner decisions

| Decision | Recommendation | Alternatives | Consequence / blocker |
|---|---|---|---|
| primary discovery | OpenAlex | S2; OpenAlex+Crossref only | **blocks implementation** |
| verification | S2 selected/ambiguous only | none; all/top-10/ambiguous-only | blocks layered milestone, not an OpenAlex-only adapter spike |
| DOI fallback | Crossref agency-aware | none; future DataCite | blocks layered milestone |
| OpenAlex/S2 API key | obtain scoped server-side keys; never expose | anonymous where allowed | OpenAlex key **blocks live run**; S2 key may block reliable verification |
| live request cap | 12 total | 6 / 20 | **blocks live acceptance** |
| monetary cost | 0 | explicit nonzero owner cap | **blocks live acceptance** |
| abstract retention | private, 30 days, no public redistribution | ephemeral / longer after legal review | **blocks storing real abstracts** |
| raw response retention | off; hashes + normalized data only | encrypted 7/30 days | non-blocking if off |
| fixture policy | synthetic/hand-authored only | approved redacted/recorded real fixture | **blocks recorded live fixtures** |
| attribution placement | report provenance + artifact metadata + UI source links | footer only | blocks public UI acceptance |
| Crossref contact | owner-approved monitored email | public pool/no polite pool | blocks polite-pool use |
| real metadata in acceptance DB | isolated DB, private, 30-day TTL | ephemeral/no persist | **blocks live acceptance** |
| live artifact retention | isolated/private, 30-day TTL | delete immediately / longer | **blocks live acceptance** |
| evaluation set size | 12 topics × pooled top-20 | 6 smoke / 30 stronger | blocks architecture promotion, not adapter implementation |
| abstract-only V1 | remain abstract-only | metadata-only / full text | **blocks workflow scope if changed** |
| verification scope | selected + ambiguous | all / selected-only / DOI-only | blocks layered DAG finalization |
| automated silver objective | approve with targeted audit and no-gold language | full two-human now | **blocks judge substrate** |
| judge provider/model | calibrate `gpt-5.6-terra`; compare `claude-sonnet-5` | Anthropic primary; local | **blocks judge substrate** |
| judge key / monetary cap | scoped key; at most USD 1.00 proposed after approval | USD 0 / defer | **blocks any real judge call** |
| judge calls / threshold | 2 pointwise + 10 mirrored pairwise total; 0.80 proposed | lower/higher | **blocks aggregation implementation** |
| human audit | all exceptions + 10% deterministic consensus, cap 20 | 5% / 20% | **blocks audit implementation** |
| non-English / partial cases | audit all initially | allow automated consensus | **blocks aggregation implementation** |
| machine translation | off until separate provenance/retention approval | manual or approved machine translation | blocks translated execution |
| Chinese variants | four manual V1 variants approved for Phase 9B-2C-1 | original only / publish a new revised version | accepted; any text change requires a new immutable version |
| expert gold / packets | defer expert gold; retain blank packets until cleanup | execute now / cancel | blocks supersession decision; packets unchanged |
