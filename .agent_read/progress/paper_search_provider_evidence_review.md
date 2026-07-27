# Phase 9B-0 — Paper Search Provider Evidence Review

Date: 2026-07-27  
Status: **PASS_WITH_WARNINGS**  
Nature: documentation/evidence/architecture decision only; no provider adapter,
runtime code, dependency, database, migration, application stack or credentials.

## Outcome

The working hypothesis is supported as a **Proposed layered target**, not an
owner-approved selection:

```text
OpenAlex
  broad candidate discovery
    ↓
Semantic Scholar Academic Graph
  selected/ambiguous paper identity verification and enrichment
    ↓
Crossref REST
  agency-aware DOI canonical metadata fallback
```

The next permitted milestone is owner review to **approve or revise ADR 0004**.
Adapter implementation is not yet authorized because provider roles, keys,
request/cost caps, real-data retention, fixtures, attribution and evaluation
policy remain owner decisions.

Warnings:

- Semantic Scholar’s API/data/third-party licensing and future commercial use
  need owner/legal-policy review; its role is proposed, not cleared for product
  redistribution.
- Abstract rights vary by upstream source. OpenAlex CC0 dataset messaging and
  Crossref generally open metadata do not make every abstract freely
  redistributable.
- No live provider call was made, so current docs were reviewed but actual
  account-specific quota, response behavior and live field availability remain
  unverified.
- OpenAlex/S2/Crossref indices and contracts change; all Class A facts must be
  checked again immediately before implementation.

## ReAgent baseline inspected

Required `.agent_read/**/*.md`, development/demo/environment/compose/Makefile
documents and current research implementation were reviewed before external
research. Key facts confirmed from source:

- current port:
  `backend/research/ports/providers.py::PaperSearchProvider`;
- current contracts:
  `backend/research/contracts/models.py::{ResearchQuery, PaperRecord,
  SourceContent, RankedPaper, ProviderUsage, ProviderOperation}`;
- fake adapters:
  `backend/research/adapters/fake_providers.py`;
- operation lifecycle/budget:
  `backend/research/services/budget.py`;
- research Skills:
  `backend/research/skills.py`;
- composition:
  `backend/api/composition.py` currently injects fake providers;
- immutable workflow:
  `demo/workflows/guided_literature_review.v2.json`,
  `guided-literature-review@2.0.0`, hash
  `af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`;
- Phase 9A-2 historical verified baseline:
  130 backend passed/0 skipped, real PostgreSQL HTTP and real-stack Playwright,
  eight research artifacts, exact approval, zero-cost settled operations and
  provenance publication gate.

The next change can replace only the Paper Search boundary. Current
`search_papers` Skill still carries fake-specific logical-call/live-budget
metadata; a future adapter milestone must make provider mode explicit through
composition/capabilities and existing operation service, not let the Skill read
environment or instantiate HTTP adapters.

## Research questions answered

The evidence register answers all 14 required questions. Principal answers:

- broad discovery and identity verification are different roles;
- no single provider provides independent verification of itself;
- layered sources improve conflict visibility but add requests, latency,
  licensing, retention and merge complexity;
- current `PaperRecord` can carry the first OpenAlex adapter without in-place
  schema change, while publication date/language/type/OA/citation/update time and
  external IDs need additive enrichment later;
- DOI/native IDs are stronger identity evidence than names/titles, but DOI
  mismatches/version relationships still require sanity checks;
- provider relevance/citation count, abstract, language/type/venue and “no
  retraction flag” cannot be hard quality gates;
- primary discovery failure blocks; optional verification may degrade only for
  unambiguous identity;
- normalized minimum metadata/hashes are safer to retain than raw payloads;
- evaluation must compare primary-only and layered with human-reviewed pooled
  records, not screenshots.

## Teacher-recommended repositories

| Repository | Revision reviewed | Version metadata | License |
|---|---|---|---|
| `academic-research-skills` | `e624c5a0682176415b97db4dc3b53a3ec2b556da` (current main on access date) | plugin 3.19.0; deep-research 2.11.0 | CC BY-NC 4.0 |
| `academic-research-skills-codex` | `f8d6b061efe98564a3f554c917fce66dcef6ca54` | adapter 0.1.22; vendored upstream `828ef3b613b0e8b91830da3328a1e33d4eb5ab4c` | CC BY-NC 4.0 |

Reviewed files include plugin/package metadata, deep research router/workflow,
bibliography and source-verification agents, S2 protocol, architecture/shared
handoff/provenance/degradation materials, Codex Runtime Mapping, manifest and
licenses.

Adopt/adapt:

- strategy before execution, exact database/query documentation;
- Boolean/filter/criteria plan;
- two-pass candidate screening;
- conservative DOI/S2 identity resolution and dedup;
- graceful degradation with explicit authority;
- PRISMA-style accounting without compliance claim;
- content-as-data security boundary;
- human checkpoints, phase ownership, provenance/citation verification;
- distributional-skew and claim-faithfulness advisories/gates.

Defer/reject:

- corpus-first until ReAgent has project corpus/upload;
- full 13-agent and research-to-paper pipelines;
- Claude hooks/slash commands/model routing;
- direct vendoring/copying of CC BY-NC prompts/templates/code.

Licensing assessment is documented as engineering risk, not legal advice.
Default is attribution + methodological inspiration + independent
implementation. Substantial adaptation may carry NonCommercial restrictions and
is inappropriate for an assumed future commercial product without review.

An important conflict was recorded: ARS’s fixed S2 rate-limit numbers are older
than the current official S2 contract. Current official provider docs are the
implementation source of truth.

## Provider findings

### OpenAlex

Best evidence-supported first discovery adapter:

- domain-general works catalog, search/filter/sort/cursor/field selection;
- stable IDs and DOI/external IDs;
- current key/credit/rate headers and free daily credit documented;
- CC0 dataset and strong reproducibility properties.

Limitations: dynamic index, mixed metadata/abstract completeness and independent
2026 preprint evidence of abstract integrity issues; no promise of exact rerun
sets or unbiased ranking.

### Semantic Scholar

Best proposed selected-paper verification/enrichment role:

- paper/corpus IDs, DOI/external IDs, abstracts and citation graph;
- exact/batch paper retrieval;
- mature use in PaperQA2/ARS.

Limitations: API/data/third-party licenses are separable and restrictive; rate
depends on anonymous pool/issued key; service/feature can change. Citation count
is advisory only.

### Crossref

Best proposed Crossref-DOI metadata fallback:

- exact DOI endpoint and registration-agency endpoint;
- member-deposited metadata, update/relation fields;
- no signup, polite `mailto`, current documented public/polite limits and cache
  guidance.

Limitations: not every DOI belongs to Crossref; deposited fields are incomplete;
abstract may be copyrighted; not preferred for relevance-ranked broad discovery.

Domain-specific providers (PubMed/Europe PMC/arXiv/CORE) were not retained in the
V1 domain-general architecture. They remain revisit candidates after evaluation
shows a domain gap.

## Decision matrix and alternatives

The evidence register exposes 18 criteria and weights totaling 100. Weighted
cross-role scores:

- OpenAlex: 4.37 / 5;
- Crossref: 4.04 / 5;
- Semantic Scholar: 3.63 / 5.

Scores are Class D and role-dependent. Alternatives reviewed:

- A OpenAlex-only: lowest complexity, valid first adapter but no independent
  verification;
- B S2-only: rich metadata, not preferred due license/retention/operational risk;
- C layered OpenAlex→S2→Crossref: proposed target, highest audit reliability and
  complexity;
- D OpenAlex→Crossref: fallback if S2 permission is not approved.

## Identity and merge policy

Proposed deterministic policy:

1. normalized DOI + metadata sanity check;
2. exact namespaced external-ID crosswalk;
3. same-provider exact native ID;
4. normalized title + year forms candidate cluster only;
5. title + first author + year similarity is advisory/manual;
6. unresolved remains separate.

No fuzzy automatic merge in the first live milestone. Unicode/title/author
normalization is versioned. Preprint/journal and conference/journal versions
remain separate but related unless authoritative evidence proves the same
manifestation. Evaluation requires zero false merge in the small reviewed set.

S2 scope recommendation: selected 3–5 plus identity-ambiguous candidates. All
20 maximizes requests/legal exposure; top-10 is intermediate; DOI-only misses
non-DOI ambiguity; ambiguous-only provides less independent audit.

## Search and artifacts

Proposed additive `SearchPlan` records topic/question, keywords/synonyms, exact
provider/Boolean queries, date/language/type, inclusion/exclusion, limits,
provider/adapter/API contract version, time, pagination/cursor, sort,
user-corpus and expansion policies.

New future artifacts:

- `search_plan.json`;
- `search_execution.json`;
- `search_statistics.json`;
- `provider_verification.json`.

Because provider indices change, ReAgent records reproducible procedure,
timestamp and captured response/result hashes; it does not promise identical
future search results or systematic-review compliance.

## Failure, budget, retention and security

Primary discovery fails closed after bounded retry. Verification can degrade only
for unambiguous identity; DOI mismatch/provider identity conflict pauses before
approval. Partial pagination is explicitly incomplete. Every call is reserved
and settled through existing ProviderOperation contracts; events are sanitized.

Proposed owner limits: 3 discovery requests/2 pages/20 candidates, 5
verification, 3 DOI fallback, 12 total attempts, 15 s per request, max two
retries after initial, 90 s total, selected 3–5, cost 0, raw response default off
and at most 2 MiB/run if enabled.

Retrieved metadata/content is untrusted data. Adapters enforce schema/length/
Unicode/markup controls; frontend escapes; provider data never becomes system
instructions; logs/events exclude secrets, raw bodies and abstracts.

Retention recommendation: normalized minimum metadata and hashes; private real
abstract/live artifacts for 30 days only after owner approval; synthetic/
hand-authored committed fixtures; attribution in provenance/artifact/UI/report.

## Evaluation protocol

Recommended 12 topics across CS/AI, biomedical, social/humanities and
climate/engineering, including non-English/Global South, version ambiguity and
abstract-missingness cases. Pool top-20 from primary-only and layered, blind
provider signals, two independent reviewers plus adjudication.

Metrics: Precision@5/@10, pooled Recall@K, nDCG@10, yield; DOI/title/year/author/
abstract/venue/conflicts; false merge/missed duplicate/unresolved; requests,
latency, 429/retry/failure/cost/replay/cache; manual review and artifact evidence
completeness. Proposed thresholds are labeled Class D and require approval.

## Architecture impact

- Existing `PaperSearchProvider` is sufficient for first OpenAlex search mapping.
- No new verifier port is justified in this phase. Before S2 implementation,
  test whether a purpose-specific additive verifier/resolver port is cleaner than
  overloading `search()`.
- S2 comparison belongs in a versioned Skill; Crossref is a DOI metadata
  fallback service.
- `ProviderOperation` persistence semantics do not need redesign; fake/live
  identity/budget/logical call must become correct configuration in the future.
- Layered verification requires a new immutable workflow version/step before
  approval; do not mutate v2.0.0.
- Current approval fingerprint can remain if verified metadata and selected
  artifact are finalized before approval.
- Frozen Domain/Workflow/Skill/Runtime/UoW ownership and migrations 0001/0002
  remain unchanged.

## Deliverables

- `docs/evidence/PAPER_SEARCH_EVIDENCE_REGISTER.md`
- `docs/evidence/ACADEMIC_RESEARCH_SKILLS_INFLUENCE_MAP.md`
- `docs/evidence/PROVIDER_FIELD_MAPPING.md`
- `docs/evidence/PROVIDER_FAILURE_MATRIX.md`
- `docs/evidence/SEARCH_EVALUATION_PROTOCOL.md`
- `.agent_read/decisions/0004-first-paper-search-provider.md` (**Proposed**)
- this progress report
- narrow update to `.agent_read/context.md`

## Validation performed

Documentation-only checks:

- all required deliverable paths exist;
- source URLs/access dates/evidence classes and limitations are present;
- unstable access/rate/license claims use current official sources;
- official versus independent versus open-source evidence is distinguished;
- ARS revisions/version/license and Codex vendoring metadata recorded;
- ADR 0004 remains `Proposed`;
- no backend/frontend/migration/dependency/compose/env source was intentionally
  changed by this phase;
- no runtime tests, provider APIs, database, Docker or application stack were
  run; no test is claimed as newly passing.

## Owner decisions and blockers

Blocking the first live implementation/acceptance:

1. approve/revise OpenAlex primary;
2. API key availability and secret ownership;
3. max request count and cost 0;
4. abstract/raw/live artifact retention and acceptance-DB real metadata;
5. fixture policy and public attribution;
6. monitored Crossref email if that layer is authorized;
7. confirm abstract-only;
8. approve evaluation size/thresholds before promotion.

S2/Crossref role and verification scope block the layered milestone but do not
have to block a separately approved OpenAlex-only adapter milestone.

## Exact next milestone

**Owner review: approve or revise ADR 0004.**

Entry evidence is complete enough for an architecture review, but implementation
must wait for the above owner policy decisions. If approved, a later prompt may
scope one supervised OpenAlex `PaperSearchProvider` adapter with synthetic
fixtures and an opt-in isolated live acceptance test; it must not add a real LLM
or full-text provider.

