# R3C-D OpenAlex Source Qualification and Owner Decisions

Date: 2026-08-04
Status: **PASS_WITH_CURRENT_SOURCE_WARNINGS**
Baseline: `78d46b7eae4a177858fe34ed2320af1719628b85` on clean `main`

## Scope

R3C-D was documentation and current-source audit only. It did not implement
R3C-I, start R3C-A, contact `api.openalex.org`, read a key, call any Provider,
start FastAPI/PostgreSQL, create a database, run a Workflow/AgentRuntime/LLM or
change production/test/Package code.

Official content was retrieved only from `developers.openalex.org`,
`openalex.org` and `blog.openalex.org`. Exact response bytes were SHA-256
fingerprinted. The current 15-page Terms and 17-page Privacy PDFs were fully
text-extracted, rendered and visually reviewed.

## Official-source result

Current sources support one keyed, single-page Works metadata search using
ordinary `search=`, `per_page<=20` and a fixed top-level `select` list. Current
official pricing reports `$0.001` per search and `$1/day` free usage with a free
key; every response exposes rate/credit headers and `meta.cost_usd`. Current
Terms do not contradict the narrow supervised software integration, subject to
their conditions and third-party rights. Current Privacy text confirms that
query/request technical metadata and key-linked usage can be collected and may
be retained by the Provider.

Official pages use inconsistent language about whether tiny no-key/demo usage
remains available. The R3C decision is unaffected because it requires an owner
key and prohibits anonymous use. Pricing, Terms, Privacy and API behavior are
mutable and must be rechecked immediately before R3C-A.

Detailed URLs, revision dates and exact byte fingerprints are in
`docs/audits/R3C_OPENALEX_OFFICIAL_SOURCE_AND_ADAPTER_AUDIT.md`.

## Existing-adapter result

The existing Hosted adapter uses current `search=` and current Work fields, a
fixed official HTTPS origin, redirect refusal and safe exception handling. It
does not accept an arbitrary URL or use deprecated `filter=<field>.search`.

It is not reusable unchanged for the teacher-aligned Proxy because it:

- rewrites the query into quoted `AND` terms;
- adds `has_abstract`/date filters and `cursor=*`;
- calls `/rate-limit` before `/works`;
- automatically retries up to twice;
- permits 15 seconds and 2 MiB;
- inherits ambient HTTP proxy settings by default;
- represents the `$0.001` Provider cost outside a whole-cent usage field;
- is composed through Hosted research Skills and Hosted ProviderOperation/
  WorkflowRun persistence.

R3C-I must implement a new adapter/composition branch behind
`backend/cloud_api_proxy/`, retain the existing Proxy ledger/idempotency, use a
scripted transport only and never import the Hosted research graph.

## Ratified owner boundary

Accepted ADR 0012 records:

- R3C-I mocked-transport implementation, then separately gated R3C-A live
  acceptance;
- OpenAlex only, `paper.search/v0.1` only, one Works metadata request/page;
- direct unchanged query mapping and maximum 20 results;
- fixed field list `id,doi,display_name,authorships,abstract_inverted_index,publication_year,primary_location,language`;
- sole key source `REAGENT_OPENALEX_API_KEY`, server-side only;
- fixed `https://api.openalex.org/works`, TLS verified, redirects and ambient
  proxies disabled;
- no more than 20 live calls/operations, `$0.05`, 512 KiB, 10 seconds, no
  automatic retry, no prepaid authorization;
- existing Proxy exact-replay/conflict/reconciliation semantics;
- acceptance-lifetime normalized metadata only, no raw body/key/query/PDF/full
  text;
- fictional public non-sensitive acceptance queries and future third-party
  privacy disclosure;
- stable safe Provider error categories;
- public/production/multi-user/paid/live-retention gates closed.

## Documents

Created:

- `.agent_read/decisions/0012-r3c-supervised-openalex-metadata-search-boundary.md`
- `docs/audits/R3C_OPENALEX_OFFICIAL_SOURCE_AND_ADAPTER_AUDIT.md`
- `docs/architecture/OPENALEX_PAPER_SEARCH_V0_1_ADAPTER_CONTRACT.md`
- `docs/security/R3C_OPENALEX_CREDENTIAL_PRIVACY_AND_COST_POLICY.md`
- `docs/acceptance/R3C_OPENALEX_IMPLEMENTATION_ACCEPTANCE.md`
- `docs/acceptance/R3C_OPENALEX_LIVE_ACCEPTANCE.md`
- this progress record

Updated only for the ratified R3C profile:

- `.agent_read/context.md`
- `docs/architecture/CLOUD_API_PROXY_V0_1_CONTRACT.md`
- `docs/security/CLOUD_API_PROXY_THREAT_MODEL.md`
- `docs/PROJECT_DEVELOPMENT_PLAN.md`

## Validation

Validation is documentation/static only by design:

- exact initial HEAD/branch/clean-tree gate passed;
- 13 approved official source objects were retrieved and their SHA-256 values
  rechecked against the tracked source ledger;
- all 15 Terms pages and 17 Privacy pages were rendered and visually inspected;
- targeted source inspection confirmed the existing adapter's request mapping,
  credential handling, redirects, retries, limits, usage parsing and Hosted
  composition findings;
- static import grep confirmed `backend/cloud_api_proxy/` has no runtime import
  of AgentRuntime, ExecutionDispatcher, WorkflowRun, Hosted ProviderOperation,
  OpenAlex or LLM code (only a test canary names them);
- changed/untracked scope contains documentation and `.agent_read` only; no
  backend, frontend, migration, test, fixture or Package file changed;
- added-line/new-file scans found no machine-specific path, credential-like
  value, real R1B evidence, raw Provider body or production-ready/live-pass
  claim;
- `.env` and `runtime_data/` remain ignored;
- `git diff --check` exits 0;
- no repository-owned documentation/link checker was found.

Backend tests, database, FastAPI, Provider and Workflow execution were
intentionally not run. No API key or `.env` file was read.

## Remaining warnings

- Official no-key/demo wording is inconsistent; R3C never relies on it.
- Current CC0 developer wording and older Terms database/redistribution wording
  are not treated as blanket publication or production-retention permission.
- Every mutable official API/pricing/Terms/Privacy fact requires a fresh R3C-A
  check.
- Exactly-once live Provider execution cannot be proven after an uncertain
  network outcome; R3C uses reconciliation and zero automatic retry.
- Production authentication, multi-user authorization, proof of possession,
  HTTPS/public deployment, paid/prepaid use, production secret management and
  production retention remain unapproved.
- Claude Code and the optional frontend remain outside this phase; all existing
  R2/R3B warnings remain unchanged.

## State

```text
R3C_DECISION_RATIFICATION = PASS_WITH_CURRENT_SOURCE_WARNINGS
R3C_OFFICIAL_SOURCE_QUALIFICATION = PASS
R3C_OPENALEX_ADAPTER_AUDIT = COMPLETE
R3C_PROVIDER = OPENALEX_PAPER_SEARCH_APPROVED_FOR_EXPERIMENTAL_R3C
R3C_CREDENTIAL_POLICY = APPROVED_FOR_SUPERVISED_R3C
R3C_BUDGET_POLICY = MAX_20_CALLS_AND_USD_0_05
R3C_RETENTION_POLICY = ACCEPTANCE_LIFETIME_NORMALIZED_METADATA_ONLY
R3C_I_IMPLEMENTATION_GATE = OPEN
R3C_A_LIVE_ACCEPTANCE_GATE = CLOSED
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
R3B_STATE = FAKE_PROXY_ACCEPTED
R2_STATE = UPLOAD_ACCEPTED
```
