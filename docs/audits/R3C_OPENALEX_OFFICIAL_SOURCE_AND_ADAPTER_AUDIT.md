# R3C OpenAlex Official-Source and Existing-Adapter Audit

Date: 2026-08-04
Status: **QUALIFIED WITH CURRENT-SOURCE WORDING WARNINGS**
Scope: documentation/source audit only; no Provider API call, key, database,
server, Workflow or production-source change

## 1. Authority and method

The teacher architecture and ADRs 0009–0011 govern the product boundary. The
only network retrieval in this audit was exact documentation content from
`developers.openalex.org`, `openalex.org`, and `blog.openalex.org`. The audit did
not contact `api.openalex.org` or `content.openalex.org` and did not read a
credential.

Each fingerprint below is SHA-256 of the exact response bytes retrieved on
2026-08-04 UTC with redirects disabled. The Terms and Privacy PDFs were also
text-extracted and all 15 and 17 rendered pages, respectively, were visually
inspected. A byte fingerprint makes the evidence reproducible but is not a
promise that a mutable documentation page will retain those bytes.

## 2. Official source ledger

| Official source | Stated revision/publication | Retrieved UTC | Exact-byte SHA-256 | Product decision affected | Recheck before R3C-A? |
|---|---|---|---|---|---|
| [Overview](https://developers.openalex.org/) | page metadata modified 2026-08-03T18:32:01.465Z | 2026-08-04 | `1c55bb3e20ca204fbf2b5b1f41e315de56127cf312df97664efa669e1baf4aa2` | API key, free allowance, CC0 dataset statement | Yes: mutable access/pricing summary |
| [Authentication & Pricing guide](https://developers.openalex.org/guides/authentication) | page metadata modified 2026-06-20T17:21:14.897Z | 2026-08-04 | `25b949ab879de50b77a6d8f5b8fc1eb71462be3498a7d5b173c6b886f5efe03d` | key transport, action prices, daily allowances, headers, `meta.cost_usd`, limits | Yes: blocking pre-live check |
| [Authentication & Pricing reference](https://developers.openalex.org/api-reference/authentication) | no page revision marker found | 2026-08-04 | `1440293a600926f8e43a34608b18969426c2d2b9a894324b307adb9046a80393` | reference form of the same key/pricing contract | Yes: blocking pre-live check |
| [Search](https://developers.openalex.org/guides/searching) | page metadata modified 2026-06-25T02:18:03.099Z | 2026-08-04 | `5de66b5769cac8d7804c3d5c733d0ab149d7796bd8ad7fbf7977932d1ea0a681` | ordinary `search=` syntax and exclusion of exact/semantic variants | Yes: query behavior can change |
| [Deprecations](https://developers.openalex.org/guides/deprecations) | page metadata modified 2026-02-19T01:12:08.670Z | 2026-08-04 | `7b8bde5192ee1cad731ed3ee06830fc467c4d4994ddd3eaa745de083517c9772` | removal of legacy search filters and obsolete Work fields | Yes |
| [Works overview](https://developers.openalex.org/api-reference/works) | page metadata modified 2026-06-01T13:43:56.211Z | 2026-08-04 | `e056e251f0450fe965f030604205b7dd1971935bf48e4f323cabad134e5a3fa3` | current Work field names | Yes |
| [List works](https://developers.openalex.org/api-reference/works/list-works) | page metadata modified 2026-08-03T18:31:54.210Z | 2026-08-04 | `6a06ea78b37116a11daed7132371cb30f39ae4c9004a8765b3ac5d0e57add8ec` | one-page `GET /works`, `per_page` 1–100, `meta.cost_usd` | Yes |
| [Select fields](https://developers.openalex.org/guides/selecting-fields) | page metadata modified 2026-02-17T21:24:14.081Z | 2026-08-04 | `7ebf3f06729e0d53ecee57ebd05a925be7d277271959387be8b3fc5cbfc7e9fc` | top-level-only fixed `select` allowlist | Yes |
| [Error handling](https://developers.openalex.org/api-reference/errors) | page metadata modified 2026-02-19T00:53:51.039Z | 2026-08-04 | `a837a68a5dde561430f1d5dfe0c673bed2de9821a369c50ce1517b59dd448cd1` | status categories, rate-limit headers, Provider backoff guidance | Yes |
| [Check rate-limit status](https://developers.openalex.org/api-reference/rate-limits/check-rate-limit-status) | page metadata modified 2026-08-03T18:31:54.190Z | 2026-08-04 | `1ed0893395fb24d37619967a0883f01ed06f9466bffd6349259e91bb75f08f0b` | current budget/credit field names; not an approved extra R3C call | Yes |
| [Terms of Service](https://openalex.org/OpenAlex_termsofservice.pdf) | last revised 2024-02-07 | 2026-08-04 | `b59bcbd2ed0fb550d35a989961c47b8fc29f22be89167e9c4789cdf1c4fa5fc4` | supervised integration eligibility, prohibited use, third-party rights | Yes: Terms may be amended |
| [Privacy Policy and Promise](https://openalex.org/OpenAlex_privacy_policy.pdf) | last revised 2026-02-17 | 2026-08-04 | `97b8eb0f03b06819f50d1b7b345eaad6847aa63283684f6535f1809fbdbfb67c` | query/key/IP/technical-metadata disclosure and Provider retention risk | Yes: blocking privacy recheck |
| [New Features and Usage-Based Pricing](https://blog.openalex.org/openalex-api-new-features-and-usage-based-pricing/) | published 2026-02-25T02:44:20Z; modified 2026-02-25T02:59:07Z | 2026-08-04 | `47e4430d6e738b6177f377bffa1b5c716ae5c103ecf8aaa07f598b889cd3ef4b` | rollout context for keys, free credit and per-action pricing | Yes: explanatory, not contract authority |

## 3. Current official facts and qualification

### Authentication and pricing

- Current scalable/normal API use is key-based. The approved R3C-A path must
  use an owner-provided key and must not rely on anonymous service.
- The Authentication & Pricing pages state `$1/day` of free usage with a free
  API key and `$0.10/day` without one. Search is `$1 per 1,000 calls`, or
  `$0.001` for one `search=` request. At the current price, 20 searches report a
  maximum expected cost of `$0.02`, below the owner cap of `$0.05`.
- Official current pages expose `X-RateLimit-Limit`,
  `X-RateLimit-Remaining`, `X-RateLimit-Credits-Used`,
  `X-RateLimit-Reset`, and response `meta.cost_usd`.
- Current documentation states a 100-requests/second service ceiling,
  `per_page` range 1–100, and a 10,000-result basic-paging limit. R3C is much
  narrower: one request, one page, at most 20 results, no cursor.
- Official guidance recommends exponential backoff for transient conditions.
  The owner-approved R3C policy is stricter: **zero automatic retries** and
  explicit Proxy reconciliation.

The Overview, deprecation language, and Privacy Promise describe keys as
required, while the authentication guide and pricing announcement still
describe a very small unauthenticated/demo allowance. This is a current
official wording inconsistency. It does not affect the approved keyed R3C path,
but it is a current-source warning and must be rechecked before R3C-A.

### Search, result limits and deprecations

- Current ordinary Works search is `GET /works?search=<query>`.
- `search` covers titles, abstracts and indexed full text. R3C returns only the
  fixed metadata/abstract field allowlist; it does not fetch content or full
  text.
- `search.exact` and `search.semantic` are different operations and are not
  approved. The cloud does not insert Boolean syntax or quote/rewrite terms.
- Legacy `filter=<field>.search:` forms and `default.search` are deprecated;
  the ordinary `search=` parameter replaces them.
- Root fields currently used by the proposed mapping remain current:
  `id`, `doi`, `display_name`, `authorships`, `abstract_inverted_index`,
  `publication_year`, `primary_location`, and `language`.
- `select` supports top-level fields only. The fixed list above is therefore
  valid without selecting nested subfields.
- Other deprecations include `host_venue`/`alternate_host_venues`, `grants`,
  `has_ngrams`, concepts and the `/text` endpoint. The R3C allowlist uses none
  of them.

### Terms, license and privacy

The Terms grant a limited right to use free Service features subject to
continued compliance, applicable law and prohibited-use rules. This narrow,
low-volume metadata integration appears compatible with those published terms;
that is an engineering source assessment, not legal advice. The Terms also
warn that referenced publications and third-party material can carry separate
rights and that data may be incomplete or change.

OpenAlex describes the downloadable dataset as CC0. That does not erase rights
or restrictions in linked publications or third-party content, so R3C retains
only the approved normalized fields for the acceptance lifetime and does not
retain raw bodies, PDF or full text.

There is also a source-age/licensing wording tension: the mutable current
developer Overview labels the complete dataset CC0, while the older 2024 Terms
use reserved-rights language for the Database/Data and prohibit unauthorized
reproduction or redistribution. This audit does not attempt to resolve that
legal scope. The supervised acceptance reads a few API records and retains
minimal normalized metadata temporarily; public redistribution and production
retention remain unapproved and require a fresh owner/legal review.

The 2026 Privacy Promise says request and technical metadata—including
timestamps, endpoints, errors, performance data, IP/user-agent and key-linked
usage—are collected. The full Privacy Policy also identifies API keys, IPs,
URLs, device/browser information and request times and says information may be
retained for up to six months after use ends unless deletion is requested.
Therefore R3C-A uses fictional public non-sensitive queries and a future real-
user product must disclose third-party transmission before sending a query.

## 4. Existing implementation inventory and classification

### Active contracts, adapter and composition

| Path | Classification | Audit result |
|---|---|---|
| `backend/research/adapters/openalex.py` | `REUSABLE_AFTER_ADAPTATION`; current Hosted path | Current `search=` and field mapping are useful. Query rewriting, fixed filters, cursor, `/rate-limit` preflight, retries, limits and ambient proxy behavior conflict with R3C. |
| `backend/research/adapters/__init__.py` | `REQUIRES_NEW_PROXY_COMPOSITION` | Exports the Hosted adapter; the teacher-aligned route must compose only behind `cloud_api_proxy`. |
| `backend/research/ports/providers.py` | `REUSABLE_AFTER_ADAPTATION` | `PaperRecord`/safe result and error concepts are reusable; the Hosted `PaperSearchProvider` call contract is not the Proxy authorization/persistence boundary. |
| `backend/research/contracts/models.py` | `REUSABLE_AFTER_ADAPTATION` | `PaperRecord` and canonical serialization are compatible. `ProviderUsage.estimated_cost_minor_units` cannot exactly represent `$0.001`; Proxy cost evidence needs an exact decimal/credit representation. |
| `backend/research/services/execution_policy.py` | `HOSTED_MODE_ONLY` | Reserves Hosted ProviderOperations, allows extra requests/retries and is tied to research Skill execution. Do not use for R3C Proxy admission. |
| `backend/api/composition.py` | `HOSTED_MODE_ONLY` | Chooses OpenAlex for Hosted research Skills and reads the existing safe credential source `REAGENT_OPENALEX_API_KEY`. The variable is reusable; this composition path is prohibited. |
| `backend/research/skills.py` | `PROHIBITED_FOR_R3C` | Interprets/normalizes/ranks and later produces Hosted research artifacts/reports. The Proxy must not call it. |
| `backend/cloud_api_proxy/contracts.py` | `REUSABLE_AFTER_ADAPTATION` | Provider-neutral request/idempotency identities remain authoritative; current adapter allowlist and zero-money usage are fake-only. |
| `backend/cloud_api_proxy/ports.py` | `REUSABLE_AFTER_ADAPTATION` | Separate Proxy adapter port is correct; it needs a live adapter result/failure contract without Hosted types. |
| `backend/cloud_api_proxy/service.py` | `REUSABLE_AFTER_ADAPTATION` | Separate operation ledger/idempotency/reconciliation are correct; live call/cost settlement and uncertain Provider outcomes need scripted qualification. |
| `backend/cloud_api_proxy/composition.py` | `REQUIRES_NEW_PROXY_COMPOSITION` | Fake-only, disabled-by-default composition must remain; OpenAlex needs a separately gated fixed-adapter branch. |
| `backend/cloud_api_proxy/sql.py` and `backend/database/migrations/versions/20260804_0004_cloud_api_proxy.py` | `REUSABLE_AFTER_ADAPTATION` | Separate Proxy tables are correct. R3C needs additive live-adapter/cost metadata and query-free request identity without Hosted foreign keys. |

### Hosted persistence and execution graph

These exact paths are `HOSTED_MODE_ONLY` and are prohibited as R3C authority:

- `backend/persistence/models/provider_operation_record.py`
- `backend/persistence/ports/provider_operation_repository.py`
- `backend/database/repositories/provider_operation.py`
- `backend/database/migrations/versions/20260721_0002_provider_operations.py`
- `backend/database/tests/test_openalex_provider_operation_postgresql.py`
- `backend/integration/tests/test_http_postgresql_openalex_live.py`

The Hosted `provider_operations` table has foreign keys to `workflow_runs` and
`workflow_step_runs`; R3C must not fabricate those rows. The old live
integration test starts a Hosted Workflow, approval and report path, so it is
not an R3C-A acceptance route.

### Network-free tests and evidence that can inform R3C-I

| Path | Classification |
|---|---|
| `backend/research/tests/test_openalex_provider.py` | `REUSABLE_AFTER_ADAPTATION` — useful synthetic transport, mapping, redaction and malformed-response cases; retry/preflight/limit expectations are not R3C policy. |
| `backend/api/tests/test_openalex_composition.py` | `HOSTED_MODE_ONLY` — proves the old Hosted opt-in/key path only. |
| `backend/integration/tests/test_http_postgresql_openalex_contract.py` | `REUSABLE_AFTER_ADAPTATION` — scripted transport/SQL patterns, but it still drives Hosted runtime. |
| `docs/evidence/PROVIDER_FIELD_MAPPING.md` | `REUSABLE_AFTER_ADAPTATION` — current normalized field provenance; remove unused requested fields for R3C. |
| `docs/evidence/PROVIDER_FAILURE_MATRIX.md` | `UNCLEAR_OR_UNVERIFIED` for R3C — bounded retries and Hosted settlement conflict with zero-retry Proxy policy. |
| `docs/evidence/OPENALEX_DATA_RETENTION_POLICY.md` | `HOSTED_MODE_ONLY` / evaluation history — 14/30-day local evaluation retention is not R3C acceptance-lifetime policy. |
| `docs/evidence/PAPER_SEARCH_EVIDENCE_REGISTER.md` | `REUSABLE_AFTER_ADAPTATION` — historical source ledger; this audit’s current official facts supersede its mutable July snapshot. |

The following are historical evaluation/Hosted artifacts, not R3C Proxy
components: `evaluation/topics/openalex_v1.json`,
`evaluation/topics/openalex_chinese_multilingual_v1.json`, all
`backend/research/evaluation/` OpenAlex references, and the OpenAlex evaluation,
pilot, human-review and Judge documents under `docs/evidence/` and
`.agent_read/progress/`. They remain preserved history and must not be loaded
into R3C-A.

### Exact direct-component inventory

The following is the complete direct source/persistence/test/config inventory
used for this adapter decision. Each path has exactly one whole-file reuse
classification; behavior-level current/deprecated findings remain in section 5.

`REUSABLE_UNCHANGED_BEHIND_PROXY`:

- `backend/cloud_api_proxy/__init__.py`
- `backend/cloud_api_proxy/errors.py`
- `backend/cloud_api_proxy/package_identity.py`
- `backend/cloud_api_proxy/in_memory.py` (unit tests only)
- `backend/cloud_api_proxy/fake_adapter.py` (retained R3B path; never selected by
  the R3C live token)
- `backend/progress_reports/tests/test_boundary.py`
- `backend/workflow_packages/tests/test_state_and_boundary.py`

`REUSABLE_AFTER_ADAPTATION`:

- `backend/research/adapters/openalex.py`
- `backend/research/ports/providers.py`
- `backend/research/contracts/models.py`
- `backend/research/tests/test_openalex_provider.py`
- `backend/cloud_api_proxy/contracts.py`
- `backend/cloud_api_proxy/ports.py`
- `backend/cloud_api_proxy/service.py`
- `backend/cloud_api_proxy/sql.py`
- `backend/cloud_api_proxy/api.py`
- `backend/cloud_api_proxy/client.py`
- `backend/cloud_api_proxy/operator_cli.py`
- `backend/database/migrations/versions/20260804_0004_cloud_api_proxy.py`
- `backend/cloud_api_proxy/tests/conftest.py`
- `backend/cloud_api_proxy/tests/test_contracts.py`
- `backend/cloud_api_proxy/tests/test_service.py`
- `backend/cloud_api_proxy/tests/test_api.py`
- `backend/cloud_api_proxy/tests/test_client_and_security.py`
- `backend/database/tests/test_cloud_api_proxy_postgresql.py`
- `backend/integration/tests/test_http_postgresql_openalex_contract.py`
- `docs/evidence/PROVIDER_FIELD_MAPPING.md`
- `docs/evidence/PAPER_SEARCH_EVIDENCE_REGISTER.md`

`REQUIRES_NEW_PROXY_COMPOSITION`:

- `backend/research/adapters/__init__.py`
- `backend/cloud_api_proxy/composition.py`

`HOSTED_MODE_ONLY`:

- `backend/api/composition.py`
- `backend/api/tests/test_openalex_composition.py`
- `backend/research/services/execution_policy.py`
- `backend/persistence/models/provider_operation_record.py`
- `backend/persistence/ports/provider_operation_repository.py`
- `backend/database/repositories/provider_operation.py`
- `backend/database/migrations/versions/20260721_0002_provider_operations.py`
- `backend/database/tests/test_openalex_provider_operation_postgresql.py`
- `docs/evidence/OPENALEX_DATA_RETENTION_POLICY.md`
- `evaluation/topics/openalex_v1.json`
- `evaluation/topics/openalex_chinese_multilingual_v1.json`
- `backend/research/evaluation/__init__.py`
- `backend/research/evaluation/candidate_pool.py`
- `backend/research/evaluation/cli.py`
- `backend/research/evaluation/contracts.py`
- `backend/research/evaluation/judgments.py`
- `backend/research/evaluation/multilingual.py`
- `backend/research/evaluation/operation_journal.py`
- `backend/research/evaluation/prompts.py`
- `backend/research/evaluation/report.py`
- `backend/research/evaluation/synthetic_fixtures.py`
- `backend/research/tests/test_evaluation_candidate_pool.py`
- `backend/research/tests/test_evaluation_contracts_and_judgments.py`
- `backend/research/tests/test_evaluation_metrics_and_report.py`
- `backend/research/tests/test_fake_relevance_judge.py`
- `backend/research/tests/test_grounded_v3.py`
- `backend/research/tests/test_multilingual_search.py`
- `backend/research/tests/test_research_skills.py`

`PROHIBITED_FOR_R3C`:

- `backend/research/skills.py`
- `backend/integration/tests/test_http_postgresql_openalex_live.py`
- `backend/research/grounded_prompts.py`

`UNCLEAR_OR_UNVERIFIED` for the current R3C contract:

- `docs/evidence/PROVIDER_FAILURE_MATRIX.md`
- `docs/evidence/OPENALEX_EVALUATION_TOPIC_SET.md`
- `docs/evidence/OPENALEX_HUMAN_REVIEW_PROTOCOL.md`
- `docs/evidence/OPENALEX_THREE_TOPIC_PILOT_REVIEW_GUIDE.md`

No direct current adapter component is classified `CURRENT_API_DEPRECATED` as a
whole file. The existing adapter's `search=` and selected Work fields are
`CURRENT_API_COMPATIBLE` behaviors, while its non-search filters and cursor are
current API features that are nevertheless prohibited by the narrower R3C
policy. Historical `filter=<field>.search`, `default.search`, `host_venue`,
`grants`, `has_ngrams`, concepts and `/text` forms are
`CURRENT_API_DEPRECATED`; the proposed adapter uses none of them.

## 5. Detailed adapter findings

1. **Search parameter:** current adapter uses `search=`, not deprecated
   `filter=<field>.search` syntax.
2. **Query integrity:** `_exact_query` tokenizes, quotes and joins terms with
   `AND`; `_filters` adds `has_abstract` and date filters. R3C requires direct
   `query -> search` mapping and no filters.
3. **Pagination:** it sends `cursor=*` for one page. Cursor is current API, but
   explicitly prohibited for R3C.
4. **Credential:** key is added as the current supported `api_key` parameter.
   `OpenAlexConfiguration` redacts repr and transport removes credential-
   bearing HTTPX exception context. R3C still needs route-wide logging and
   outbound-URL canaries.
5. **Origin/redirect/TLS:** base origin is exactly
   `https://api.openalex.org`, redirects are disabled and HTTPX verifies TLS by
   default. HTTPX environment proxy inheritance is not disabled; R3C must use
   `trust_env=False` or an equivalent explicit no-proxy transport.
6. **Retries:** current adapter automatically retries 403/429/5xx/timeouts up to
   twice. R3C permits zero automatic Provider retries.
7. **Calls:** current adapter performs `/rate-limit` before `/works`, so a
   success uses two Provider calls. R3C permits exactly one Works call per new
   operation and must enforce its local acceptance ledger without that extra
   preflight.
8. **Limits:** current timeout is 15 seconds and raw response cap 2 MiB. R3C
   requires 10 seconds and 512 KiB of Provider response bytes.
9. **Usage:** current adapter allowlists current rate headers and validates
   `meta.cost_usd`, but records project cost as whole minor units (`0`). R3C
   must persist exact decimal USD/credit evidence and detect missing,
   contradictory or changed cost semantics.
10. **Result retention:** raw HTTP body remains transient in adapter memory and
    is not directly stored. Mapped `PaperRecord.raw_metadata_hash` binds each
    selected mapping. The new Proxy must retain no raw body and only approved
    normalized metadata.
11. **Hosted coupling:** the adapter itself does not import AgentRuntime or an
    LLM, but its production composition leads through Hosted research Skills,
    ProviderOperation, WorkflowRun, approval and report generation. That path
    is prohibited for R3C.
12. **Normalized compatibility:** the existing `PaperRecord` mapping is
    compatible with `paper.search/v0.1`; unused requested fields
    `publication_date`, `type`, and `updated_date` should not be selected in
    R3C.

## 6. R3C-I blocking adaptation list

R3C-I must implement a new adapter/composition behind `backend/cloud_api_proxy/`
using a scripted HTTP transport only. It must pass the trimmed query unchanged,
send one `GET /works`, use only `search`, `per_page`, fixed `select` and the
server key, disable redirects and ambient proxies, enforce TLS, 10 seconds and
512 KiB, make zero automatic retry, normalize current cost/usage evidence, and
persist no raw body or query text beyond the minimum immutable identity needed
for reconciliation.

The Hosted adapter is therefore **not approved unchanged**. No contradiction
was found between the current official keyed Works-search contract and the
owner’s E1–E11 decisions. The qualified decision is:

```text
R3C_OFFICIAL_SOURCE_QUALIFICATION = PASS
R3C_OPENALEX_ADAPTER_AUDIT = COMPLETE
R3C_DECISION_RATIFICATION = PASS_WITH_CURRENT_SOURCE_WARNINGS
```
