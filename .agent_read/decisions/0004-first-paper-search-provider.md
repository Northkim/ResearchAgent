# ADR 0004: First Paper Search Provider

- **Status:** Proposed
- **Date:** 2026-07-27
- **Decision owners:** ReAgent owner / architecture reviewer
- **Evidence review:** `docs/evidence/PAPER_SEARCH_EVIDENCE_REGISTER.md`

## Context

ReAgent has verified `guided-literature-review@2.0.0` end to end using
deterministic fake Paper Search, Source Content and LLM providers, PostgreSQL,
filesystem artifacts, exact approval, provenance and a real Next.js/FastAPI
stack. The next permitted real capability is **only** the Paper Search boundary.
No real LLM or full-text provider is part of this ADR.

The current port is
`backend/research/ports/providers.py::PaperSearchProvider.search(ResearchQuery,
limit, ProviderRequestContext) -> PaperSearchResult`. Current `PaperRecord`,
`ProviderIdentity`, `ProviderUsage`, `ProviderOperationService`, budgets,
idempotency and provenance contracts already exist. API composition currently
injects `FakePaperSearchProvider`; the research Skill’s live/fake operation
metadata is currently fake-specific and must be made explicit in a future
implementation, without redesigning ownership or persistence.

Evidence classes:

- **Evidence-backed conclusion:** supported by current official contracts or
  research/mature implementations.
- **ReAgent project inference:** an engineering choice made for this architecture.
- **Unresolved owner policy:** no implementation authority until approved.

## Decision drivers

1. broad, domain-general candidate discovery;
2. stable identifiers, DOI/external-ID resolution and deterministic replay;
3. current abstract-only `PaperRecord`/workflow fit;
4. documented search/filter/pagination and reproducibility evidence;
5. bounded request/cost and transparent failures;
6. metadata licensing, attribution and retention compatible with a future
   commercial path;
7. additive implementation respecting existing ports and ownership;
8. independent identity/metadata verification without treating citation count
   as quality.

Weights, scores and source limitations are explicit in the evidence register;
the matrix proposes OpenAlex 4.37, Crossref 4.04 and S2 3.63 on the cross-role
criteria, but role suitability overrides a raw total.

## Evidence summary

### Evidence-backed conclusions

- OpenAlex offers broad searchable/filterable scholarly metadata, cursor
  pagination, stable OpenAlex IDs and external IDs under a currently documented
  key/credit API; its complete dataset is advertised CC0.
- Independent work finds strong broad/reference coverage but mixed field-level
  metadata and abstract completeness/integrity. OpenAlex output therefore needs
  validation, missingness and source provenance.
- S2 provides stable paper/corpus IDs, external IDs, abstract/citation graph
  enrichment and batch paper lookup. Its API and underlying/third-party data are
  governed by more restrictive and separable terms; future commercial use and
  redistribution require cautious review.
- Crossref provides registry-deposited metadata and exact lookup for Crossref
  DOIs, current public/polite limits and `mailto` etiquette. It does not cover
  every DOI agency and abstracts may be copyrighted.
- PRISMA-S and retrieval studies support recording exact platforms, queries,
  dates, filters, limits, dedup and result accounting; they do not make this
  workflow a systematic review.
- ARS, PaperQA2 and OpenScholar support strategy-first, multi-provider,
  evidence/citation and human-evaluation patterns as Class C experience; they
  are not provider contracts.

### ReAgent project inferences

- OpenAlex is the best first adapter fit for `PaperSearchProvider`.
- S2 should verify/enrich only selected and identity-ambiguous candidates.
- Crossref should be an agency-aware DOI metadata fallback.
- Primary provider failure must not silently change the SearchPlan; enrichment
  may degrade only for unambiguous identity.
- First supervised live runs stay at zero monetary cost and small request caps.

### Unresolved owner policy

Provider roles, credentials, request cap, retention/fixtures/attribution,
Crossref contact email, real-data storage and evaluation thresholds remain
unapproved.

## Proposed decision

Adopt a **layered target architecture**, implemented in separately reviewed
milestones:

```text
OpenAlex discovery
  → deterministic normalize/rank
  → Semantic Scholar selected/ambiguous verification and enrichment
  → Crossref agency-aware DOI fallback for unresolved/conflicting DOI metadata
  → exact paper-set approval
```

The first implementation milestone, after owner approval, adds only the
OpenAlex adapter and supervised contract tests. S2/Crossref remain documented
target roles until their terms, keys and field policies are approved and their
own adapters are reviewed.

## Primary provider

**Proposed: OpenAlex.**

- API base: `https://api.openalex.org`.
- Use server-side API key/credit headers according to the current official
  contract; never expose key in API/UI/events.
- Exact provider query, filters, selected fields, sort, page/cursor policy,
  retrieval time, adapter/API contract version and response hash must be recorded.
- Maximum 20 normalized candidates in supervised V1.
- OpenAlex relevance/citation count is not a quality score.

## Verification/enrichment provider

**Proposed: Semantic Scholar Academic Graph API**, for selected (3–5) plus
identity-ambiguous candidates only.

- Compare DOI/external IDs/title/year/authors; add field-level assertions rather
  than silent overwrite.
- S2 citation count and inferred fields remain advisory.
- If unavailable and identity is unambiguous, continue visibly as unverified;
  ambiguity/mismatch pauses before approval.
- API key, public display, retention and future commercial permission require
  owner/legal-policy confirmation.

## DOI fallback provider

**Proposed: Crossref REST**, only for DOI-bearing unresolved/conflicting records.

- Confirm/handle registration agency; Crossref absence does not invalidate a
  non-Crossref DOI.
- Use owner-approved `mailto` for polite pool.
- Canonical role applies to deposited DOI metadata, not discovery relevance or
  unrestricted abstract rights.
- DataCite is a revisit option if evaluation finds material non-Crossref DOI
  unresolved rate.

## Search methodology

Add a versioned `SearchPlan` and four immutable evidence artifacts:

- `search_plan.json`;
- `search_execution.json`;
- `search_statistics.json`;
- `provider_verification.json`.

Record topic/question, keywords/synonyms, exact provider queries and Boolean
expression, year/language/type policy, criteria, max results, provider/adapter/
contract versions, timestamps, pagination/cursor and sort, corpus/expansion
policy. Reproducibility means exact procedure plus captured result hashes;
provider indices change, so future identical result sets cannot be guaranteed.

Do not claim systematic-review compliance.

## Data scope

- V1 stays **abstract-only**.
- No PDF/full text retrieval, real LLM or source-content provider change.
- Map current `paper-record/v1` fields only in the first adapter; put absent/
  differing semantics in `metadata_limitations`.
- Future fields (publication date, language, type, OA, citation count, provider
  updated timestamp, external IDs) belong in an additive v2/enrichment contract,
  not an in-place schema mutation.
- Citation count is advisory and cannot affect quality/inclusion without a new
  approved policy.

## Identity and deduplication

Proposed order:

1. normalized exact DOI plus title/year sanity check;
2. exact namespaced external-ID crosswalk;
3. exact provider-native ID within provider namespace;
4. normalized exact title + year creates candidate cluster only;
5. title + first-author + year similarity is manual/advisory;
6. ambiguous stays unresolved/separate.

Unicode normalization, author comparison and version relations use explicit
versioned algorithms. Preprint/journal and conference/journal manifestations
remain separate but related unless authoritative evidence proves identity.
False merge fails the evaluation gate.

## Request budget

Proposed owner policy:

- discovery: max 3 requests / 2 pages / 20 candidates;
- verification: max 5 logical lookups;
- DOI fallback: max 3;
- total live requests: max 12, retries included;
- 15 s request timeout; initial + max 2 retryable attempts;
- 90 s total provider runtime;
- selected papers 3–5;
- monetary cost: **0**;
- retained raw response: default off, hard max 2 MiB/run if explicitly enabled.

Official provider caps/headers may be stricter and always take precedence.
Reserve before invocation and settle actual success/failure/zero cost through
existing `ProviderOperationService`; replay cannot reserve or invoke twice.

## Failure policy

- Primary discovery invalid/auth/permission/quota/final timeout/network/5xx/
  malformed/contract/pagination failures block after bounded retries.
- Never silently switch primary provider: that changes methodology.
- Partial pages can be preserved with `complete=false` but not represented as a
  complete search.
- S2/Crossref failure degrades only when identity is unambiguous and a visible
  verification state is recorded.
- DOI mismatch, ambiguous identity, duplicate-page loop, contract drift,
  unsettled operation or provenance failure fails/pauses before approval/
  publication.
- Public errors/events contain sanitized codes/IDs/hashes/counts only.

## Attribution

- Preserve provider identity, source URL, adapter/API version and query timestamp
  in artifact provenance and UI/report references.
- Cite OpenAlex in research outputs according to official guidance.
- Follow S2 API/data/third-party license and branding/link terms if public data is
  displayed.
- Use owner-approved Crossref `mailto`; identify Crossref-derived DOI metadata.
- ARS is cited only as methodology influence; no prompt/code/template vendoring.

## Retention

Proposed:

- normalized minimum metadata, provider assertions, source URLs, operation data
  and hashes may persist in a private isolated acceptance store;
- raw provider bodies default off;
- real abstracts/live artifacts private for 30 days, then owner-controlled
  deletion;
- committed fixtures are synthetic/hand-authored; no real provider abstract/raw
  payload committed;
- field-level license/usage metadata must travel with retained abstract.

All durations and real-data storage require owner approval. This is engineering
risk assessment, not legal advice.

## Security boundary

Retrieved titles, abstracts, venues, author names, API fields, URLs and errors are
untrusted data, not instructions. Adapters enforce schemas/limits/Unicode/control
character handling; markup is sanitized and frontend-rendered safely; prompts
use delimited data and never promote content to system instructions; secrets and
raw content are excluded from events/logs/public diagnostics.

## Exact architecture impact

1. **Is existing `PaperSearchProvider` sufficient for OpenAlex?** Yes for the
   first keyword discovery adapter and current `PaperRecord`; pagination/search
   execution metadata needs a separate artifact/result extension, not port
   ownership redesign.
2. **Separate `PaperIdentityVerifier` port?** Not for the OpenAlex milestone.
   Do not overload `search()` with batch identity semantics. Before S2 work,
   spike whether an additive `PaperMetadataVerifier/Resolver` port is warranted.
3. **S2 as another Skill?** Yes: a versioned `verify_selected_papers` Skill with
   injected verifier capability is preferred; it owns comparison policy, not
   transport.
4. **Crossref role?** Metadata fallback/resolver, not general verifier or primary
   search.
5. **Existing identity/version fields?** `ProviderIdentity.provider`,
   `adapter_version`, `model_or_endpoint`; `ProviderUsage` and
   `ProviderOperation` record category/kind/fingerprint/idempotency/usage/cost.
6. **Raw metadata retained?** request/response hash, retrieved time, adapter/API
   version, selected headers, pagination/sort/query plan, field assertions and
   missingness; raw body off by default.
7. **ProviderOperation changes?** No persistence-semantic redesign. Future
   implementation must stop hardcoding fake/live/logical-call metadata, set
   `is_live_provider`, budget and actual identity correctly; additive sanitized
   attempt/response metadata may be needed.
8. **New artifacts?** SearchPlan, SearchExecution, SearchStatistics and
   ProviderVerification.
9. **DAG change?** OpenAlex-only can replace the boundary without mutating
   immutable v2 definition if composition/mode is explicitly pinned; layered
   verification requires a new immutable workflow version with a verification
   step before approval.
10. **Approval payload?** Existing selected IDs/checksum/version fingerprint can
    remain; verified metadata must be finalized before generating the bound
    selected artifact.
11. **Composition configuration?** explicit mode/provider registry, injected
    HTTP transport/clock, budgets, server-only secret loading, no Skill env reads.
12. **Environment variables?** proposed names:
    `REAGENT_PAPER_SEARCH_MODE`, `OPENALEX_API_KEY`; later
    `S2_API_KEY`, `CROSSREF_POLITE_EMAIL`. Values never logged. Exact names need
    implementation review.
13. **Tests?** schema/field fixtures, query/pagination, 429/timeout/5xx/malformed/
    contract drift, identity/dedup conflicts, operation reservation/settlement/
    replay, secret sanitization, license/retention evidence, isolated live
    supervised acceptance and evaluation comparison.

Frozen Domain lifecycle, Workflow Engine, Skill System, Runtime ownership,
persistence ports/UoW semantics, migrations 0001/0002 and fake providers remain
unchanged.

## Alternatives considered

### OpenAlex only

Lowest request/implementation/legal complexity; suitable as first adapter.
Rejected as final architecture because it lacks independent identity and
registry fallback.

### Semantic Scholar only

Rich abstract/graph metadata. Not preferred because broad discovery evidence is
not stronger enough to offset API/data license, attribution/retention and
at-will change risk.

### Layered OpenAlex → S2 → Crossref

**Proposed target.** Best separation of role and conflict visibility, with higher
request/latency/legal/testing cost.

### OpenAlex → Crossref only

Viable if S2 permission/owner policy is not approved. It loses S2 identity/graph
enrichment but preserves open discovery plus DOI metadata fallback.

### Domain-specific providers

PubMed/Europe PMC/arXiv may improve specific domains. Deferred because V1 is
domain-general and evaluation should first expose domain gaps.

## Consequences

Positive:

- smallest first adapter change;
- methodology and provider assertions become auditable;
- independent verification/fallback can be added without changing runtime
  ownership;
- bounded supervised risk and explicit legal/security handling.

Negative:

- additional artifacts/contracts and eventually a new immutable workflow version;
- layered calls add latency, failures and license/attribution surfaces;
- exact future rerun results cannot be guaranteed;
- owner decisions and evaluation are mandatory before promotion.

## Risks

- OpenAlex abstract quality/missingness and dynamic index;
- S2 license/commercial/retention uncertainty;
- Crossref abstract copyright and non-Crossref DOI gaps;
- false merge/version collapse;
- API/rate/pricing/term drift;
- synchronous HTTP execution/no durable worker remains unsuitable for production;
- filesystem/PostgreSQL atomicity, auth and retention are unresolved production
  concerns.

## Revisit triggers

- official contract/license/rate/pricing changes;
- evaluation gates fail or layered adds no material value;
- non-Crossref DOI unresolved rate >5%;
- any false merge or real abstract rights incident;
- commercial/public release;
- V1 leaves abstract-only scope;
- provider failure/429 >1% in supervised evaluation;
- need for domain-specific systematic review.

## Owner approvals required

Before implementation:

1. approve/revise OpenAlex primary role;
2. approve target S2/Crossref roles and selected/ambiguous verification scope;
3. provide/authorize server-side API keys and monitored Crossref contact email;
4. approve max 12 requests and monetary cost 0;
5. approve abstract/raw/live-artifact retention and real metadata in isolated DB;
6. approve synthetic-only fixture default and attribution placement;
7. confirm V1 remains abstract-only;
8. approve evaluation size (recommended 12 topics) and proposed thresholds.

Until these are resolved, the next milestone is **owner review and
approve/revise ADR 0004**, not adapter implementation.

## Deliberately not decided

- any LLM provider/model/prompt/cost;
- real source-content/full-text/PDF provider;
- authentication/multi-user policy;
- worker/queue/async persistence;
- S3/cache/retention enforcement implementation;
- production deployment/Docker remediation;
- a new verifier port or workflow version number before the implementation
  design spike;
- acceptance of this ADR.

