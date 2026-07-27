# Phase 9A-0 Real Research Vertical Slice Contract Completion

- Date: 2026-07-21
- Phase status: `PASS_WITH_WARNINGS`
- Scope: architecture, product contract, and implementation planning only
- Production/provider code added: none
- Dependencies changed: none
- Runtime tests executed: none

## Frozen contract

The proposed implementation contract is
`.agent_read/progress/real_research_vertical_slice_contract.md`.

It defines immutable `guided-literature-review@2.0.0` as a sequential static
DAG:

```text
validate_query
-> search_papers
-> normalize_and_deduplicate
-> rank_and_select
-> approve_sources
-> retrieve_source_content
-> summarize_sources
-> synthesize_findings
-> generate_report
-> persist_artifacts
```

The one approval boundary binds the selected-paper artifact checksum, paper
identities, ranker/workflow/Skill versions, and query hash before source
retrieval or LLM synthesis.

The user-visible result is a citation-aware Markdown literature review plus
selected-paper metadata, per-paper summaries, themes, disagreements,
limitations, possible gaps, machine-readable evidence/provenance, and sanitized
provider usage. The contract does not claim systematic-review compliance or
full-text access.

## Proposed architecture additions

New framework-independent ports:

- `PaperSearchProvider`;
- `SourceContentProvider`;
- `LLMProvider` with separate text and structured generation;
- `ArtifactContentStorage`;
- `ArtifactCatalog`;
- `ProviderOperationRepository`.

Proposed Skill API additions:

- scoped provider/artifact read capabilities in `SkillExecutionContext`;
- immutable artifact write requests and normalized usage in `SkillResult`;
- an application Artifact Service that writes through storage and stages
  existing `ArtifactMetadata`;
- budgeted provider-operation gateway around every external call.

Proposed Workflow Engine decision addition:

- `WaitingApproval` carries Engine-resolved approval inputs so Runtime can create
  an exact selection fingerprint without owning reference resolution.

No Domain lifecycle or module-ownership change is proposed. These additions are
recorded in proposed ADR
`.agent_read/decisions/0003-real-research-provider-and-artifact-boundaries.md`.
The ADR is not accepted.

## Persistence impact

Existing WorkflowRun, StepRun, checkpoint, memory, artifact metadata, approval,
and event entities are reused.

One new `provider_operations` table and repository are proposed to persist:

- pre-call budget reservation;
- request hash and logical idempotency;
- provider/adapter/model identity;
- operation status and optimistic version;
- actual or conservatively reserved token/cost usage;
- latency, retries, normalized failure, and restricted request reference.

The table requires project/run/Step foreign keys, unique logical operation
attempt and idempotency constraints, nonnegative usage checks, and run/status
indexes. One Alembic revision after `20260721_0001` is planned.

Large paper, content, evidence, report, provenance, and usage bodies remain
outside PostgreSQL in immutable content storage. Existing `artifacts` rows hold
relative storage keys, checksums, media types, sizes, schemas, visibility, and
producer identities. No V1 relational paper/claim/evidence tables are proposed.

## API and frontend impact

Additive application/API proposal:

- catalog-pinned run creation through `POST /runs/from-catalog`;
- run artifact list;
- artifact metadata and content streaming;
- provider usage view;
- explicitly eligible provider-operation retry.

The existing inline-definition demo endpoint remains for compatibility. The
real workflow must use the catalog-pinned path so the browser cannot move the
approval point or choose unreviewed Skills.

Minimal frontend changes:

- typed Guided Literature Review v2 form;
- ranked candidate-paper approval preview;
- source-scope labels;
- rendered Markdown report and citation links;
- artifact downloads;
- sanitized provider error and optional usage/cost views;
- reload-persistence browser acceptance.

The existing Next.js pages, React Query layer, typed API client, and same-origin
rewrite remain.

## Provenance and artifact outcome

Completion is fail-closed:

```text
GroundedClaim
  -> EvidenceUnit
  -> SourceContent hash/location
  -> selected PaperRecord
  -> CitationReference
  -> report label and source URL/DOI
```

Unknown citations, missing evidence, unknown papers, duplicate DOI values,
misstated source scope, missing version data, unresolved provider reservations,
or invalid artifact checksums block report completion.

Planned artifacts are:

- `papers.json`;
- `selected_papers.json`;
- restricted `source_content.json`;
- `paper_summaries.json`;
- `evidence.json`;
- `report.md`;
- `provenance.json`;
- `usage.json`.

## Recommended providers

Conditional paper-search recommendation:

1. OpenAlex;
2. Semantic Scholar Academic Graph as fallback.

Conditional LLM recommendation:

1. OpenAI API with an owner-approved currently supported structured-output
   model;
2. Anthropic API with an owner-approved structured-generation model as
   fallback.

No provider documentation or service was contacted in this phase. Current API
availability, authentication, model support, pricing, limits, data handling,
and terms are unverified. The recommendations describe architectural fit only
and require current official-document review and owner approval.

## Unresolved owner decisions

- initial paper search provider and current terms/authentication;
- initial LLM provider and exact model;
- API-key availability and allowed secret boundary;
- hard estimated-cost cap per real run;
- abstract-first versus permitted open full text;
- local artifact root and future container storage;
- artifact/source/diagnostic retention;
- permitted excerpt policy;
- whether sanitized live responses may become recorded fixtures;
- citation style;
- minimum usable paper count;
- provider usage/cost visibility;
- acceptance or revision of proposed ADR 0003;
- whether Docker remediation must precede Phase 9 implementation.

Real adapters remain blocked by the provider/model/key/cost/data decisions.
Provider-independent fake Milestone 1 is blocked only by contract/ADR approval.

## Recommended first implementation milestone

Implement exactly **Milestone 1: Contract substrate and local artifact
storage** after ADR review.

Scope:

- immutable research/provenance schemas and validators;
- normalized provider error and budget contracts;
- provider ports and deterministic fakes;
- `ArtifactContentStorage` plus temporary/local filesystem adapter;
- `ProviderOperationRepository`, InMemory/SQL adapters, Alembic migration;
- additive Skill schema constraints and artifact/usage results;
- Engine-resolved approval inputs.

Proposed implementation locations, following the current repository rather
than creating a second packaging tree:

- new `backend/research/contracts/`, `backend/research/ports/`, and
  `backend/research/tests/`;
- new `backend/artifact_storage/ports/`, `backend/artifact_storage/adapters/`,
  and contract tests;
- new persistence model/port for provider operations plus updates to
  `backend/persistence/adapters/in_memory.py`;
- updates to `backend/database/orm/models.py`,
  `backend/database/unit_of_work.py`, a new provider-operation repository, and
  one new Alembic revision;
- updates to `backend/skill_system/models/skill_contract.py` and
  `backend/skill_system/results/skill_result.py`;
- updates to Workflow Engine decision/resolution code for approval inputs;
- application artifact/provider-operation gateway modules and composition
  wiring;
- focused tests beside each changed module plus shared adapter contracts.

Exclusions:

- no real provider SDK or network call;
- no API key;
- no production S3 adapter;
- no frontend feature;
- no worker queue;
- no authentication;
- no Docker redesign.

Completion gate:

- pure contracts and provenance validation pass;
- InMemory/PostgreSQL provider-operation contract tests pass;
- artifact write/read/hash/restart/path-safety tests pass;
- deterministic fakes pass;
- approval preview fingerprint test passes;
- all existing backend/frontend regressions remain green;
- import-boundary scan finds no provider SDK/ORM/FastAPI/concrete storage import
  in Domain, Workflow Engine, Skills, or Runtime core.

## Implementation readiness score

**82 / 100**

Strengths:

- working supervised full-stack platform and durable lifecycle;
- inspected, explicit module ownership;
- complete proposed schemas, DAG, artifacts, provenance gates, failures,
  budgets, tests, milestones, and API/frontend impact;
- fake-first path does not depend on vendor choice.

Reasons the score is not higher:

- proposed ADR 0003 is not accepted;
- provider/model/API-key/cost/content/retention decisions are open;
- current provider documentation was intentionally not verified;
- no content storage or provider-operation ledger exists;
- current Skill schema/context/result contracts need additive work;
- current dispatcher is synchronous and there is no authentication;
- Docker clean-machine acceptance remains unverified.

## Validation performed

Documentation checks only:

- required Markdown deliverables created;
- all contract sections present;
- internal repository references checked;
- only `.agent_read` Markdown files modified/created;
- no source, migration, dependency, Compose, Make, environment, or frontend
  package file changed;
- no API key or credential added.

Runtime/backend/frontend tests were not rerun because this phase was
documentation-only. Earlier results remain evidence from their own reports,
not Phase 9A-0 execution evidence.
