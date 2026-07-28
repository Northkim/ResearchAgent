# Phase 9B-1 Live Acceptance：Supervised Real OpenAlex Discovery

日期：2026-07-28  
状态：**PASS**

## 1. 结论

ReAgent 已通过首个真实 Paper Search Provider 的 supervised acceptance。
实际验证路径为：

```text
OpenAlex /rate-limit + /works
→ OpenAlexPaperSearchProvider
→ normalized PaperRecord
→ deterministic normalization/ranking
→ exact approval
→ FakeSourceContentProvider
→ FakeLLMProvider
→ report/provenance publication gate
→ PostgreSQL + LocalFilesystemArtifactStorage
→ application reconstruction
→ completed resume without another provider operation
```

本阶段没有调用 Semantic Scholar、Crossref、PDF/full text、真实
SourceContent provider 或真实 LLM。`guided-literature-review@2.0.0`、migrations
0001/0002、Domain/Workflow Engine/Skill System/Runtime/persistence ownership 均
未修改。

技术 approval 只验证 exact candidate-set fingerprint 和 lifecycle；不代表
人工对论文相关性或科学质量的认可。

## 2. Credential 与 Git safety

- OpenAlex API key：**configured and redacted**；
- `.env`：`.gitignore:39` 命中、未被 Git 跟踪；
- `.env.example`：只保留空 placeholder；
- key 未输出、未进入命令参数、URL、pytest output、events、diagnostics、
  artifacts、documentation 或 Git；
- live request 前发现 `httpx` request exception 会保留 credential-bearing
  Request URL。适配器已做最小修复：离开原始 HTTP exception handler 后才抛出
  normalized `ProviderError`，不保留 `__cause__`/`__context__`；
- synthetic secret canary test 验证 normalized exception 不保留凭据；
- 最终 audit 扫描 Git tracked files、`.agent_read`、acceptance artifacts、
  pytest/browser diagnostic directories、execution events、approval/provider
  diagnostics、artifact metadata 和相关数据库 rows，结果全部
  `leakage=no`。

Phase 开始时既有 Phase 9B-1 变更已 staged；本阶段没有执行 `git add`、
`git clean`、reset 或 commit。live remediation 保持为 unstaged changes。

## 3. Official OpenAlex contract recheck

统一访问日期：2026-07-28。没有发现相对 2026-07-27 evidence register 的
material contract drift。

| Official source | 当前事实 | Acceptance impact |
|---|---|---|
| [Authentication & Pricing](https://developers.openalex.org/api-reference/authentication) | `https://api.openalex.org`；query `api_key`；no-key `$0.10/day`、free key `$1/day`；search `$1/1000 calls`；`meta.cost_usd`；100 requests/s；429；exponential backoff | ReAgent 要求 free key，先作 `/rate-limit` free-credit preflight；out-of-pocket budget 仍为 0 |
| [Rate limit status](https://developers.openalex.org/api-reference/rate-limits/check-rate-limit-status) | `/rate-limit` 要求 key，返回 daily remaining 和 endpoint search cost；response body 可包含 key field | adapter 只读取 rate-limit 数值，不保留 raw payload；leak audit 通过 |
| [List Works](https://developers.openalex.org/api-reference/works/list-works) | `GET /works`、`meta + results`、selected Work fields | 当前 root/meta/results/field validation 继续匹配 |
| [Search](https://developers.openalex.org/guides/searching) | full-text keyword search 与 Boolean operators | live failure 证明 whole-topic exact phrase recall 过窄；修复为 escaped term-level Boolean `AND` |
| [Pagination](https://developers.openalex.org/guides/page-through-results) | cursor paging；`per_page<=100` | 本次固定 `cursor=*`、one page、20 candidates |
| [Error handling](https://developers.openalex.org/api-reference/errors) | 400/403/429/5xx 和 bounded backoff guidance | 当前 normalized category/retry policy 保持有效 |
| [CC0/pricing](https://help.openalex.org/hc/en-us/articles/24397762024087-Pricing), [citation](https://help.openalex.org/hc/en-us/articles/28761511652247-How-can-I-cite-OpenAlex), [Terms](https://openalex.org/OpenAlex_termsofservice.pdf) | dataset 描述为 CC0；请求引用 OpenAlex；第三方 publication rights/completeness 仍有限制 | normalized private retention、OpenAlex attribution、raw response off；abstract rights 仍为风险 |

## 4. Isolated database 与 storage

- PostgreSQL host/port/owner：`localhost:5432` / `lifengguang`；
- database inventory 先确认目标不存在；
- 唯一新建数据库：`reagent_9b1_live_acceptance`；
- base → `20260721_0001` → `20260721_0002` 成功；
- `alembic current`：`20260721_0002 (head)`；
- `alembic heads`：`20260721_0002 (head)`；
- `alembic check`：`No new upgrade operations detected`；
- retained database size：`15 MB` (`15759039` bytes)；
- repository-relative artifact root：
  `runtime_data/acceptance/openalex-live/run.0wOip3`；
- root retained size：`564 KiB`，37 files（含 regression、failed-attempt 和
  final acceptance evidence）；
- final completed live run：
  `run_65844bc9c65443f5b52a27c03b920dea`。

`ProjectDB`、`reagent_9a1_acceptance`、`reagent_9a2_acceptance`、
`reagent_9b1_acceptance` 没有被连接、reset、migrate、truncate 或删除。

## 5. Live attempts、defects 与 remediation

Owner limits 内共使用 3/3 Works discovery calls、6/12 total OpenAlex calls
（每次一项 `/rate-limit` + 一项 `/works`）、0 retries。每个 Works response
报告 `$0.001` provider credit，共 `$0.003` free credit；preflight 确认免费余额
足够，没有使用 owner prepaid/paid amount，ReAgent
`estimated_cost_minor_units=0`。

### Attempt 1

- live provider operation：`SUCCEEDED/SETTLED`，2 requests，0 retries；
- whole-topic exact phrase 只返回 2 records；
- workflow 按设计以 `INSUFFICIENT_DISCOVERY_PAPERS` fail closed；
- verified defect：broad topic 被错误表达为完整 exact phrase；
- remediation：topic 以 whitespace terms 分解，各 term 保持 escaped quoted
  data，再用显式 Boolean `AND` 连接；year/abstract filter、pagination、sort、
  budget 不变。

### Attempt 2

- live provider operation：`SUCCEEDED/SETTLED`，2 requests，0 retries；
- 返回并 normalize 20 records；
- `rank_and_select` 在第 14 条以后产生 negative relevance score，违反
  `RankedPaper [0,1]` contract；workflow 在 approval 前以
  `SKILL_EXECUTION_ERROR` fail closed；
- verified defect：原 three-paper fake fixture 没有覆盖 full 20-candidate page；
- remediation：deterministic score clamp 至 `0.0`，并新增 20-candidate
  regression；同时移除 real approval explanation 中不准确的 “synthetic”
  wording。

### Attempt 3 — final

- targeted pytest：`1 passed in 8.97s`；
- OpenAlex operation latency：`1772 ms`；
- 2 requests，0 retries；
- `WAITING_FOR_APPROVAL`、exact approval、completion、reconstruction、
  completed resume 全部通过。

## 6. Candidate evidence

Final SearchPlan：

- topic：`persistent research agents`；
- years：2020–2026；
- content：metadata + abstract only；
- one cursor page；
- maximum candidates：20；
- selected：3；
- identity：`discovery_only_unverified`；
- citation count 不请求、不参与 ReAgent rank。

Final completeness：

| Metric | Count |
|---|---:|
| provider-reported matching index count | 468877 |
| page records received | 20 |
| adapter records normalized | 20 |
| records rejected | 0 |
| with abstract | 20 |
| with DOI | 20 |
| with authors | 20 |
| with publication year | 20 |
| with venue | 19 |
| surviving workflow normalization | 20 |
| selected | 3 |
| duplicate DOI | 0 |
| duplicate OpenAlex ID | 0 |
| advisory title/year clusters | 0 |

Selected technical candidate set：

| OpenAlex ID | Title | Year | DOI | Abstract |
|---|---|---:|---|---|
| `W4362515116` | A Survey of Large Language Models | 2026 | `10.1007/s11704-026-60308-3` | available |
| `W4412505619` | AI Agents vs. Agentic AI: A Conceptual Taxonomy, Applications and Challenges | 2025 | `10.70777/si.v2i3.15161` | available |
| `W4393065402` | A survey on large language model based autonomous agents | 2024 | `10.1007/s11704-024-40231-1` | available |

没有在本报告中复制 abstract。选择结果只证明 pipeline 可执行；当前
deterministic recency/title ranking 未经人工 relevance evaluation。

## 7. Approval、provenance 与 ProviderOperation

- approval count/status：1 / `APPROVED`；
- approval 绑定 exact selected IDs、selected artifact checksum、query hash、
  project/run/workflow/step、ranker、pinned Skills、role 与 expiry；
- final run operations：9；
  - OpenAlex search：1；
  - FakeSourceContent retrieve：3；
  - FakeLLM structured/text：5；
- final run statuses：9 `SUCCEEDED/SETTLED`；
- final run RESERVED/RUNNING：0；
- final run UNSETTLED：0；
- entire retained database：28 operations，全部 `SUCCEEDED/SETTLED`，
  RESERVED/RUNNING/UNSETTLED 为 0；
- final OpenAlex request/retry：2 / 0；
- final OpenAlex ReAgent monetary usage：0 minor units；
- diagnostic metadata keys：empty for final success；无 key/URL/raw body；
- application reconstruction 后 run/artifact/operation/event IDs 不变；
- completed resume 没有新增 operation、reservation、artifact 或 event。

Publication gate：

- `publishable=true`；
- `abstract_only=true`；
- selected papers：3；
- SourceContents：3；
- EvidenceUnits：3；
- GroundedClaims：4；
- citations：3；
- validator：`provenance-validator/v1`；
- `all_provider_operations_settled=true`；
- estimated cost：0 minor units。

## 8. Artifact evidence

所有 11 个 final artifacts：

- 在 PostgreSQL 有 metadata；
- storage key 均为 relative immutable
  `runs/<opaque-run>/artifact_<opaque>/v1/<logical-file>`；
- API/metadata 不暴露 root absolute path；
- reconstruction 后通过 size + SHA-256 verification；
- `artifact_checksum_reload_verified=11`。

| Logical artifact | Kind | Media type | SHA-256 |
|---|---|---|---|
| `search_plan.json` | `search_plan` | `application/json` | `sha256:49c597713798e15d30ce798a075c0db3e1aa70b5d1f25b97cfabc6b94012b464` |
| `search_execution.json` | `search_execution` | `application/json` | `sha256:62a3d9d3490d54c5a21b2f5505dbe0a1170bf8b9b9097a3830b30eafe4dfa5e8` |
| `search_statistics.json` | `search_statistics` | `application/json` | `sha256:2056d72b76918ea9358f18f2931db5705e68131029f64eb3a59494c2bfca899d` |
| `papers.json` | `candidate_papers` | `application/json` | `sha256:26b3c112dbae809d35bea7b4411a5b10d71c069968b02d866bff47ccac950a7d` |
| `selected_papers.json` | `selected_papers` | `application/json` | `sha256:b2b1bfccfc9a994fb80e41f9779dae5efb1c57ced9511f3ce8082c6c81704a87` |
| `source_content.json` | `source_content` | `application/json` | `sha256:9d58fcb407941b544a9237f79c3989267d31e32bd596d22f0d0103d278532353` |
| `paper_summaries.json` | `paper_summaries` | `application/json` | `sha256:18f54943b14ca408cd650fafb1e20ea9a91cbca69b26243a6653076a6fc2f90a` |
| `evidence.json` | `evidence` | `application/json` | `sha256:00a7b103f548663f6ef4153a9e131f3b07f0bb114df8c60c5dbdad66598df905` |
| `report.md` | `research_report` | `text/markdown; charset=utf-8` | `sha256:ed828259180bc17a6aeb571543856600679d8131f9a895f41134bf60c8c15aea` |
| `provenance.json` | `provenance` | `application/json` | `sha256:391b343c19b90dd0f6863d5ca87f0ba2a3b61f444d1265c5608fa4fa43964cc8` |
| `usage.json` | `provider_usage` | `application/json` | `sha256:31e72e1c6a9e47242841d22986a9b7fd59c86b31f97be9215121e88e48c4c23e` |

未生成或保留 raw response artifact。`raw_metadata_hash` 仅是 normalized selected
Work mapping 的 canonical hash。

## 9. Validation evidence

| Command/scope | Exit | Result |
|---|---:|---|
| `python -m pytest -q backend/integration/tests/test_http_postgresql_openalex_live.py` final opt-in live | 0 | `1 passed in 8.97s` |
| same live test attempt 1 | 1 | fail closed：2 candidates / `INSUFFICIENT_DISCOVERY_PAPERS` |
| same live test attempt 2 | 1 | fail closed：20-candidate rank score contract defect |
| PostgreSQL-enabled full backend suite against only live acceptance DB; live gate disabled | 0 | `155 passed, 1 skipped in 3.44s`；skip 为 live test |
| affected adapter + research Skill tests after final remediation | 0 | `24 passed in 0.35s` |
| final network-free `python -m pytest -q backend` | 0 | `139 passed, 18 skipped in 0.88s`；DB/live gates 未设置 |
| `python -m compileall -q backend` | 0 | pass / no output |
| `alembic upgrade head` | 0 | base → `20260721_0002` |
| `alembic current` | 0 | `20260721_0002 (head)` |
| `alembic heads` | 0 | `20260721_0002 (head)` |
| `alembic check` | 0 | no drift |
| 11-artifact reconstruction/checksum verifier | 0 | 11 verified |
| redacted secret leakage audit | 0 | tracked/generated/diagnostic/database all no |

One parallel final Alembic check request timed out in the tool approval layer
before process creation；the same commands were rerun sequentially and passed。

Frontend unit/lint/build and browser Playwright were not executed：本阶段没有
frontend/API DTO/source change，browser acceptance 是 optional。

## 10. Source changes required by live evidence

Verified remediation files：

- `backend/research/adapters/openalex.py`
  - discard credential-bearing raw HTTP exception context；
  - replace whole-topic exact phrase with escaped Boolean term conjunction。
- `backend/research/tests/test_openalex_provider.py`
  - secret exception-retention canary；
  - updated deterministic query identity assertion。
- `backend/research/skills.py`
  - clamp rank score to `[0,1]` for a full 20-candidate page；
  - provider-neutral ranking explanation。
- `backend/research/tests/test_research_skills.py`
  - full 20-candidate rank regression。

No migration、dependency、workflow、Domain、Workflow Engine、Runtime、
persistence port、API DTO 或 frontend source changed。

## 11. Retention、cleanup 与 processes

Retained until owner review：

- database：`reagent_9b1_live_acceptance`；
- artifact root：
  `runtime_data/acceptance/openalex-live/run.0wOip3`。

未执行 cleanup。仅 owner review 后可选：

```bash
dropdb reagent_9b1_live_acceptance
rm -rf -- runtime_data/acceptance/openalex-live/run.0wOip3
```

Final process audit：

- port 3000：free；
- port 8000：free；
- pytest processes：none；
- no Uvicorn/Next.js/Playwright stack was started；
- Homebrew PostgreSQL service unchanged。

## 12. Remaining risks 与 next milestone

- OpenAlex metadata relevance、field semantics、venue missingness 和 dynamic
  index；
- abstract rights、integrity 和 completeness；
- 尚无 Semantic Scholar/Crossref independent identity verification；
- three selected results 显示 deterministic ranking 仍需人类 relevance
  evaluation，不能视为科学 endorsement；
- provider contract/credit/terms drift；
- synchronous inline HTTP，无 durable worker/lease；
- 无 authentication/multi-user isolation；
- filesystem/PostgreSQL non-atomicity、无 retention/orphan sweeper；
- Docker 未验证；Python exact lock/httpx naming drift 警告保留。

唯一建议下一里程碑：

**Phase 9B-2：Human-reviewed OpenAlex discovery evaluation and retention
review**。

使用 `docs/evidence/SEARCH_EVALUATION_PROTOCOL.md` 的小型、多主题、人工 pooled
evaluation，评估 Precision@K、relevant-paper yield、metadata completeness、
dedup/false merge、request/latency 和 selection review burden；同时 owner
确认 real abstract retention/cleanup policy。该阶段不应同时实现 S2、
Crossref 或真实 LLM。只有 evaluation 证明 OpenAlex-only 的具体 identity/
metadata gap 后，才进入独立的 verification-provider approval。
