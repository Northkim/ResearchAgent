# Phase 9B-1：Supervised OpenAlex Paper Search Adapter

日期：2026-07-27  
状态：**PASS_WITH_WARNINGS（code-complete；live provider 未执行）**

## 1. 结论

ReAgent 已在现有 `PaperSearchProvider` boundary 后新增
`OpenAlexPaperSearchProvider`，但默认仍是 network-free
`FakePaperSearchProvider`。`guided-literature-review@2.0.0` 的 immutable
definition、version 和 canonical hash 均未修改；composition 选择 discovery
adapter。OpenAlex 结果继续走现有 normalization/ranking、exact approval、
Fake SourceContent、Fake LLM、provenance publication gate、PostgreSQL 和
LocalFilesystemArtifactStorage。

本阶段没有 owner-supplied OpenAlex key、narrow live query 或 real-data
retention 授权，因此 **live OpenAlex smoke/full path 未执行**。代码、synthetic
contract tests、真实 PostgreSQL/HTTP/Runtime/artifact recovery 路径均已验证。
不能把 OpenAlex-shaped synthetic response 的成功描述成 live API 成功。

## 2. ADR 0004 acceptance scope

`.agent_read/decisions/0004-first-paper-search-provider.md` 已由 `Proposed`
改为 `Accepted`，接受范围仅为：

- OpenAlex：首个 primary discovery provider；
- Semantic Scholar：future verification/enrichment candidate only；
- Crossref：future DOI metadata fallback candidate only；
- V1 metadata + abstract only；
- monetary budget 0、low-volume、supervised、explicit opt-in；
- real responses/abstracts/credentials/live artifacts 不得提交 Git。

没有接受或实现 Semantic Scholar、Crossref、real SourceContent、real LLM、
full text/PDF、worker、authentication、Docker remediation。没有新 ADR。

## 3. Official OpenAlex contract re-verification

统一访问日期：2026-07-27。实现 source of truth 与影响：

| Official source | 当前事实 | 实现影响 |
|---|---|---|
| [Authentication & Pricing](https://developers.openalex.org/api-reference/authentication) | base `https://api.openalex.org`；query `api_key`；no-key `$0.10/day`、free key `$1/day`；search `$1/1000 calls`；`meta.cost_usd` 和 `X-RateLimit-*`；100 requests/s；`per_page<=100` | live composition 必须显式 opt-in；key 仅注入 transport；max 20 / one page；provider credit 与 ReAgent whole-minor-unit monetary budget 分开记录 |
| [Rate limit status](https://developers.openalex.org/api-reference/rate-limits/check-rate-limit-status) | `/rate-limit` 要求 key，返回 daily remaining 和 endpoint cost | ReAgent live mode 要求 free key；在 `/works` 前 fail-closed，确认 daily free credit 足够，避免 prepaid/out-of-pocket usage |
| [Works / List Works](https://developers.openalex.org/api-reference/works) | `id`, `doi`, `display_name`, `authorships`, `abstract_inverted_index`, publication/location/language/type 等；list 为 `meta + results` | root/meta/results/field validation；abstract inverted-index reconstruction；missingness 显式 |
| [Search](https://developers.openalex.org/guides/searching) | `search` 覆盖 title/abstract/fulltext；支持 Boolean；provider relevance 同时受 citation count 影响 | 记录 exact query；citation count 不请求、不作 quality score；后续仍用 ReAgent deterministic rank |
| [Pagination](https://developers.openalex.org/guides/page-through-results) | `cursor=*` 与 `next_cursor`；1–100 per page | 当前 max 20，仅一个 cursor page；`complete` 表示 bounded plan fulfilled，不表示 exhaustive corpus |
| [Select fields](https://developers.openalex.org/guides/selecting-fields) | `select` 只支持 top-level fields | request identity 固定 top-level field list |
| [Error handling](https://developers.openalex.org/api-reference/errors) | 当前文档把 400 作为 bad request、403 作为 rate exceeded、429 作为 daily limit、5xx transient；建议 exponential backoff | 403/429 → `PROVIDER_RATE_LIMIT`；5xx/timeout/network bounded retry；response body 不进入 diagnostics |
| [CC0/pricing](https://help.openalex.org/hc/en-us/articles/24397762024087-Pricing), [citation](https://help.openalex.org/hc/en-us/articles/28761511652247-How-can-I-cite-OpenAlex), [Terms](https://openalex.org/OpenAlex_termsofservice.pdf) | dataset 描述为 CC0，官方请求引用 OpenAlex paper；外链 publication/third-party rights 和 completeness 仍有风险 | report 显示 OpenAlex attribution；normalized metadata 可私有保存；raw response/real fixture 不保留；abstract rights 不从 dataset CC0 推断 |

与 9B-0 的 conflict：

1. 旧 evidence 写 no-key `$0.01/day`；当前 official page 是 `$0.10/day`。
2. help-center pricing 仍显示旧式 “100k/day / 10 per second”，developer
   contract 已改为 credits/100 requests per second；implementation 采用后者。
3. general auth 允许 no-key trial，但 `/rate-limit` reference 要求 key；
   ReAgent 为 zero-out-of-pocket fail-closed 采用更严格的 key requirement。

这些变化已记录在
`docs/evidence/PAPER_SEARCH_EVIDENCE_REGISTER.md`。

## 4. Adapter architecture

主要实现：

- `backend/research/adapters/openalex.py`
  - `OpenAlexConfiguration`：base URL、15 s timeout、最多两次 retry、max 3
    discovery attempts、max 20 discovery candidates、selected-paper input cap
    5、2 MiB response cap；
  - `OpenAlexTransport` / `HttpxOpenAlexTransport`：已有 `httpx 0.28.1`，
    未新增 SDK/dependency；
  - `OpenAlexPaperSearchProvider`：`openalex@1.0.0`,
    endpoint identity `GET /works?search=`,
    contract snapshot `openalex-works-api/2026-07-27`。
- `backend/research/contracts/models.py`
  - `SearchPlan` / `SearchExecution` / `SearchStatistics` v1；
  - SearchPlan fingerprint 排除 execution timestamp，但绑定 exact query、
    filters/policies/provider/adapter/contract/page/sort/field set。
- `backend/research/ports/providers.py`
  - `PaperSearchResult` optional all-or-none search evidence；
  - additive credential-free `PaperSearchProvider.request_identity()`，使
    `ProviderOperation.request_fingerprint` 包含 SearchPlan fingerprint、
    query/filters/cursor/field set/adapter。
- `backend/research/services/execution_policy.py`
  - composition-owned `ProviderExecutionPolicy`；
  - fake default；OpenAlex supervised policy reserve 4 request units、full
    workflow max 12、max cost 0、deadline 90 s。
- `backend/api/composition.py`
  - `REAGENT_PAPER_SEARCH_PROVIDER=fake|openalex`；
  - fake 是 default；
  - openalex 还必须有
    `REAGENT_OPENALEX_LIVE_ENABLED=true` 和
    `REAGENT_OPENALEX_API_KEY`；
  - adapter 本身不读 environment。

执行路径：

```text
FastAPI/ApplicationContainer
→ AgentRuntime
→ research.search_papers Skill
→ ProviderOperation reserve + commit + RUNNING + commit
→ OpenAlexPaperSearchProvider
→ /rate-limit free-credit preflight
→ /works?search= one bounded cursor page
→ validated PaperRecord + Search evidence
→ ProviderOperation settlement + commit
→ existing normalize/rank/approval
→ FakeSourceContent + FakeLLM
→ provenance publication gate
→ PostgreSQL metadata + LocalFilesystemArtifactStorage bytes
```

Adapter 不更新 `WorkflowRun`、不创建 approval、不 ranking、不访问 ORM/
FastAPI/ArtifactRepository、不读 environment、不 fallback。

## 5. Field, identity and security mapping

当前 `PaperRecord` mapping：

- internal ID：normalized DOI，否则 namespaced OpenAlex ID；
- provider ID：validated `W…`；
- title：`display_name`，NFC/control cleanup，max 500；
- authors：最多 100 个 `authorships[].author`，可选 `A…`/ORCID；
- abstract：`abstract_inverted_index` 严格重建，max 10,000 positions /
  50,000 chars；
- year：valid integer 1000–2100；
- venue：`primary_location.source.display_name`；
- DOI：现有 `normalize_doi`；
- source URL：canonical `https://openalex.org/W…`；
- retrieval time：injected aware clock；
- raw metadata hash：selected Work mapping canonical SHA-256；
- limitations：always `identity_unverified_discovery_only` + missingness。

Missing abstract/DOI/author/venue/year 不伪造；abstract-less record 会在现有
normalization step 排除，少于三个则 fail closed。Required ID/title 或 malformed
abstract schema 拒绝该 record。

Dedup：

1. exact normalized DOI；
2. exact OpenAlex ID；
3. normalized title+year 只计 advisory cluster；
4. fuzzy merge、preprint/journal collapse、citation-count ranking 均未实现。

所有 title/abstract/author/venue/URL/ID/error 都按 untrusted data 处理；
provider content 不进入 system instruction；HTML 不新增 unsafe renderer；
event/public diagnostics 不含 raw content、URL、header、key；configuration
`repr` 隐藏 key。

## 6. Search evidence artifacts

OpenAlex path 在 approval 前新增：

- `search_plan.json` (`application/json`)；
- `search_execution.json` (`application/json`)；
- `search_statistics.json` (`application/json`)。

均使用现有 immutable relative storage key、checksum verification、Runtime
artifact metadata persistence。Search execution 记录 actual request/retry count、
bounded completeness、provider-reported decimal credit cost 和
`discovery_only_unverified`，不记录 raw response/key。完整 OpenAlex-shaped
contract path 共 11 artifacts；fake v2 仍为原 8 artifacts。

Filesystem/PostgreSQL 仍不能共享 atomic transaction；immutable retries 可复用
identical bytes，但 DB rollback 后可能留下 orphan bytes。系统不会静默删除。

## 7. Failure and budget behavior

- invalid query / 401 / malformed/schema/oversize/free-credit insufficient：
  non-retry or fail closed；
- official 403/429、5xx、timeout/network：initial + max 2 retries；
- delay：1 s、2 s，合法 `Retry-After` 最多 15 s；
- one page 结果不足标 `complete=false`，minimum-paper gate 阻止虚假完成；
- no silent provider substitution / fabricated records；
- request reservation 在 call 前 durable commit；RUNNING 在 invocation 前
  durable commit；
- successful usage settles actual count/retries/latency/zero whole-minor cost；
- post-call failure safe usage 进入 failed settlement；
- replay 遇到同 idempotency key 的 succeeded operation 时不调用 provider，
  要求 Runtime 复用 persisted Skill checkpoint；
- all operations terminal/settled 后 publication gate 才允许 report。

`ProviderOperation.retry_count` 现在与 settled `ProviderUsage.retry_count`
一致；数据库 schema/persistence semantics 未改变，无 migration。

## 8. Workflow/downstream compatibility

`demo/workflows/guided_literature_review.v2.json` 未修改，workflow ID/version/
hash 不变。Provider selection 属 composition，不属于 router/workflow mutation。
fake provider mode 仍 deterministic、network-free，回归测试保留原 8-artifact
path。

为避免 live report 误称 real metadata 为 synthetic，本阶段仅在
`source_provider` 非 synthetic 时采用：

- deterministic abstract extract，而非捏造 paper claim；
- 明确写 OpenAlex discovery identity unverified；
- 明确写 SourceContent 和 LLM 仍为 deterministic fakes；
- OpenAlex attribution；
- real metadata retrieval timestamp 作为 generated-at evidence。

Synthetic fake path 保留原 synthetic wording和行为。

## 9. Validation evidence

### Newly executed

| Command | Exit | Result | Network/DB |
|---|---:|---|---|
| `conda run --no-capture-output -n reagent-dev python -m pytest -q backend` | 0 | `137 passed, 18 skipped in 1.04s` | network-free；18 skips 为 environment/live gates |
| `conda run --no-capture-output -n reagent-dev python -m compileall -q backend` | 0 | no output | no DB/network |
| `conda run --no-capture-output -n reagent-dev alembic heads` | 0 | `20260721_0002 (head)` | no migration added |
| isolated PG command over `backend/database/tests`, fake-v2 HTTP regression, and `test_http_postgresql_openalex_contract.py` | 0 | `16 passed in 3.82s`, zero skips | `reagent_9b1_acceptance`; no network |
| `test_http_postgresql_openalex_contract.py` targeted | 0 | `1 passed in 2.23s` | real FastAPI/Runtime/PostgreSQL/filesystem; synthetic OpenAlex-shaped transport |
| `test_http_postgresql_openalex_live.py` | not run | live test not executed | requires explicit owner key/query/retention |

One earlier direct `pytest` invocation of the new integration module failed
collection because the repository root was not on `sys.path`; the corrected
`python -m pytest` invocation passed. One initial PostgreSQL unit scenario
failed its FK because it had not seeded a `WorkflowRun`; the test was corrected
to use the existing contract execution fixture and then passed. Neither failure
was represented as a passing product result.

The final PostgreSQL rerun first exited 1 because the restricted command
sandbox denied access to the local PostgreSQL Unix socket (`Operation not
permitted`); the identical command was then explicitly approved for that local
socket and passed `16/16`. This was an execution-environment denial, not a
database assertion failure.

Frontend unit/lint/build were not run: no HTTP DTO/shared frontend type/route/
component visible behavior changed. No Playwright run was required or claimed.

### PostgreSQL acceptance state

- database: `reagent_9b1_acceptance` (new; never ProjectDB)；
- revision: `20260721_0002`；
- retained size: `10325 kB`；
- final retained operations: 18, all `SUCCEEDED/SETTLED`:
  one network-free OpenAlex-shaped live-marked operation plus fake-v2/downstream
  operations from two contract paths；
- artifact root: `/tmp/reagent_9b1_pg_artifacts.Xo4fgn`；
- `ProjectDB`, `reagent_9a1_acceptance`, `reagent_9a2_acceptance` were not used
  or modified；
- no real OpenAlex response/abstract/credential is present: all accepted payloads
  were hand-authored synthetic shapes.

Optional cleanup, not executed:

```bash
dropdb reagent_9b1_acceptance
rm -rf /tmp/reagent_9b1_pg_artifacts.Xo4fgn
```

## 10. Files and frozen boundaries

No migration, dependency file, frontend source, workflow fixture or API DTO was
changed. Existing ownership remains:

- Domain lifecycle legality；
- Workflow Engine decisions；
- Skill System capability/execution；
- Runtime orchestration；
- provider adapter protocol translation；
- ProviderOperation audit/budget/idempotency；
- persistence adapter storage mapping；
- Application use cases；
- API transport。

Additive contract changes are Search evidence contracts,
credential-free request identity and composition-owned provider execution
policy. No persistence port semantics or migrations 0001/0002 changed.

## 11. Remaining risks

- **Blocking supervised live acceptance:** no owner-authorized API key, narrow
  query or real-data retention/cleanup approval；live behavior remains unverified。
- **Provider drift:** credit/error/help pages already show conflicting historical
  facts；must recheck before every live acceptance。
- **Metadata/abstract:** missingness, independent abstract integrity findings,
  dynamic index, third-party rights；identity remains unverified。
- **Research quality:** no S2/Crossref independent check；Fake LLM cannot establish
  scientific synthesis；abstract-only。
- **Runtime/operations:** synchronous inline HTTP, no durable worker/lease,
  authentication, production monitoring or cancellation channel。
- **Storage:** filesystem/PostgreSQL non-atomicity and no orphan/retention worker。
- **Environment:** HTTP package naming drift remains (`environment.yml` package
  `httpx2`, runtime import `httpx 0.28.1`)；no exact Python lock；Docker remains
  unverified and intentionally unchanged。
- **UI policy visibility:** shared v2 form still permits `max_papers` through 8
  for fake mode；OpenAlex request identity rejects a selected-paper limit above
  5 before reservation。A future provider-aware form constraint may improve the
  message；no frontend change was made in this backend-only milestone。

## 12. Exact next milestone

Recommendation: **Phase 9B-1 supervised live OpenAlex acceptance**，不是 S2、
Crossref 或 real LLM implementation。

Entry conditions:

1. owner provides/authorizes a free OpenAlex API key without exposing it；
2. owner approves one narrow query, one page/max 20 and existing zero-cost caps；
3. owner approves real normalized metadata/abstract retention only in
   `reagent_9b1_acceptance` + ignored isolated artifact root；
4. owner chooses retention/cleanup time；
5. official auth/pricing/rate/error/terms pages are rechecked immediately before
   execution。

Completion gate：opt-in live test passes through OpenAlex discovery → exact
approval → Fake SourceContent → Fake LLM → report/provenance → reload；actual
request count/credit cost and all settled operations recorded；no key/raw response
leak；artifacts inspected then retained/cleaned only per owner decision。
