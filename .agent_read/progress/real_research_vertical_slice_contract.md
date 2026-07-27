# Phase 9A-0: First Real Research Vertical Slice Contract

- Date: 2026-07-21
- Status: Frozen for implementation review; owner-gated decisions unresolved
- Product slice: `guided-literature-review@2.0.0`
- Workflow schema: `reagent/v1alpha1`
- Architecture authority: `.agent_read/progress/architecture_contract.md`
- Related proposed decision: `.agent_read/decisions/0003-real-research-provider-and-artifact-boundaries.md`

## Contract status and interpretation

This document freezes the proposed product behavior and dependency-ordered
implementation plan for ReAgent's first real research workflow. It does not
select credentials, a billable model, a retention policy, or a production
storage service. Items explicitly marked **owner decision required** remain
gates and must not be inferred as accepted.

The phase was documentation-only. No provider API, LLM API, or external
documentation site was called. Provider capabilities, authentication,
pricing, rate limits, model availability, and terms are therefore marked
unverified and must be checked against current official documentation before
an adapter is implemented.

The frozen dependency direction remains:

```text
Next.js
  -> FastAPI
  -> Application Services
  -> ExecutionDispatcher
  -> AgentRuntime
  -> Workflow Engine + Skill System
  -> framework-independent ports
  -> adapters
```

Domain lifecycle semantics, Workflow Engine scheduling ownership, Skill System
capability ownership, and PostgreSQL authority do not move. Section 9 documents
one additive persistence-port requirement whose blocking reason is durable
provider-call budgeting and recovery.

## 1. Product Outcome

### 1.1 Target user and problem

The target user is a researcher, research engineer, or technically informed
reviewer who needs a small, inspectable literature overview before deciding
where to investigate further. The primary problem is not “generate prose about
a topic”; it is “find a bounded set of real papers, review the selected
evidence, and receive a report whose claims can be traced back to known source
records.”

The canonical example topic is:

```text
persistent research agents
```

The canonical example input is:

```json
{
  "topic": "persistent research agents",
  "keywords": [
    "persistent agents",
    "long-running AI agents",
    "agent memory"
  ],
  "year_from": 2020,
  "year_to": 2026,
  "max_results": 8,
  "language": "en",
  "inclusion_criteria": [
    "Research addresses persistence, memory, recovery, or long-running agent execution"
  ],
  "exclusion_criteria": [
    "Non-research marketing pages",
    "Records without sufficient bibliographic identity"
  ]
}
```

`year_to` is an explicit user input, not a hidden current-year default. Tests
must use a fixed value so fixture behavior does not change with the clock.

### 1.2 User-visible processing stages

1. Validate and normalize one research query.
2. Search one configured scholarly-paper provider.
3. Normalize metadata and deterministically deduplicate records.
4. Rank candidates and select at most the approved paper budget.
5. Pause for a human to inspect the selected titles, authors, years, source
   links, DOI values, relevance scores, and selection rationales.
6. After approval, retrieve abstracts and permitted source content without
   bypassing access restrictions.
7. Produce per-paper structured summaries and evidence units.
8. Synthesize themes, agreements, disagreements, limitations, and candidate
   gaps.
9. Validate claim-to-evidence and citation relationships.
10. Produce immutable artifacts and a citation-aware Markdown report.

The single approval boundary is after ranking and before content retrieval or
LLM synthesis. Approving binds the exact selected-paper artifact checksum,
paper IDs, workflow/Skill versions, and run/step attempt. A changed selection
requires a new approval request.

### 1.3 Final outputs

A completed run exposes:

- selected paper list;
- title, authors, publication year, abstract, venue, source URL, and DOI when
  available;
- ranking score and human-readable selection rationale;
- per-paper structured summary;
- cross-paper synthesis;
- themes;
- disagreements and source limitations;
- possible research gaps explicitly marked as synthesis or inference;
- citation-aware Markdown report;
- machine-readable papers, evidence, provenance, and provider-usage data;
- artifact metadata, checksums, and download links permitted by policy.

The report is useful for real research only if a reader can move from a report
claim to evidence, from evidence to a stable paper identity, and from that
identity to a source URL or DOI. It is a guided starting point, not a
systematic-review certification or a substitute for reading the papers.

### 1.4 Expected frontend experience

The user selects **Guided Literature Review v2**, completes a focused input
form, launches a run, watches ordered progress, and reaches an approval card
that shows the exact candidate papers rather than an opaque Step ID. After
approval, the Run page shows retrieval/synthesis progress and then a rendered
Markdown report with linked citation labels. An artifact panel permits
download of the report and machine-readable provenance. Reloading the page
must show the same report, citations, artifact checksums, and completion state.

## 2. Explicit Scope and Non-goals

### 2.1 Phase 9A implementation scope

The first implementation should support:

- exactly one `ResearchQuery` per run;
- one immutable workflow, `guided-literature-review@2.0.0`;
- a configurable `max_results` with a hard server-side ceiling;
- inclusive publication-year filters;
- one real `PaperSearchProvider` adapter and one fallback adapter contract;
- one real `LLMProvider` adapter;
- one `SourceContentProvider` adapter, which may initially reuse the paper
  provider's permitted abstract content;
- one approval boundary;
- sequential execution within the existing static DAG;
- Markdown report output;
- deterministic fake provider testing in the normal suite;
- sanitized recorded fixtures without live network;
- optional, explicitly enabled real-provider integration tests;
- local filesystem artifact content storage for development;
- immutable artifact metadata in the existing PostgreSQL `artifacts` table;
- durable, bounded provider-operation usage and failure records.

### 2.2 Non-goals

V1 does not require or promise:

- full text for every paper;
- paywall, access-control, robots, or license bypass;
- full systematic-review protocol compliance or PRISMA certification;
- citation-count completeness or bibliometric authority;
- vector retrieval or embeddings;
- semantic vector databases;
- arbitrary web browsing;
- dynamic DAG creation, loops, branching, or parallel Workflow nodes;
- multi-agent review panels;
- autonomous research-idea execution;
- arbitrary user documents or confidential uploads;
- code execution;
- automatic publication or external writes;
- cross-provider search fusion;
- citation-style configurability beyond one selected V1 style;
- authentication, multi-user authorization, or public artifact sharing;
- durable queue/worker implementation in the first fake-provider milestone;
- real-time token streaming to the browser;
- guaranteed exact prose across model versions.

Abstract-only evidence must be labeled as abstract-only. The report must never
imply that the full paper was reviewed when only metadata or an abstract was
available.

## 3. Canonical Workflow DAG

### 3.1 Identity and graph

- Workflow ID: `guided-literature-review`
- Workflow version: `2.0.0`
- Schema: `reagent/v1alpha1`
- Display name: `Guided Literature Review v2`
- Definition rule: immutable after publication; canonical JSON and SHA-256
  hash recorded by the Seeder

Required workflow inputs are the fields of `ResearchQuery`. Required workflow
outputs resolve from `persist_artifacts`:

```text
report_artifact_id
provenance_artifact_id
selected_papers_artifact_id
usage_artifact_id
artifact_manifest
```

The approval prompt is:

```text
Review the ranked paper selection, source identities, and access limitations
before ReAgent retrieves content and begins LLM synthesis.
```

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

No Workflow-node parallelism is required. Within `summarize_sources`, provider
calls occur in stable selected-rank then paper-ID order. This preserves the
existing one-node-at-a-time runtime and makes fixture behavior auditable.

The existing execution-event taxonomy is sufficient for V1. The semantic
stream is `WORKFLOW_STARTED`, then `STEP_STARTED`/`SKILL_EXECUTED` for each of
the nine Skill steps, with `APPROVAL_REQUESTED` between ranking and retrieval,
and `WORKFLOW_COMPLETED` after required artifact/provenance validation.
`CHECKPOINT_CREATED` events remain interleaved at durable boundaries. Any
terminal failure emits `WORKFLOW_FAILED` with a normalized category and no raw
provider payload.

### 3.2 Step contract: `validate_query`

- Type / SkillReference: `skill` /
  `research.validate_research_query@1.0.0`
- Input: `ResearchQuery`
- Output: normalized `ResearchQuery`, canonical query hash, validation warnings
- Dependencies: none
- Timeout: 5 seconds
- Retry: one attempt; validation is non-retryable
- Idempotency: pure function of schema version and input
- Approval: none
- Checkpoint: after success
- Failure: `INVALID_QUERY` or `SCHEMA_VALIDATION`; fail the run
- Partial retention: no artifact; invalid user input remains only in the
  already persisted run input

### 3.3 Step contract: `search_papers`

- Type / SkillReference: `skill` / `research.search_papers@1.0.0`
- Input: normalized query, query hash, provider search limit
- Output: immutable search-response artifact reference, provider identity and
  version, result count, provider-operation IDs
- Dependencies: `validate_query`
- Timeout: 60 seconds
- Retry: maximum three attempts for rate limit, timeout, or unavailability;
  bounded exponential backoff and provider retry hints
- Idempotency: operation key is derived from run, step attempt, normalized query
  hash, provider identity/version, and limit
- Approval: none; read-only external operation
- Checkpoint: after result artifact metadata and usage are durable
- Failure: normalized provider category; malformed responses are not retried
  unless the adapter explicitly classifies a transient transport truncation
- Partial retention: successful provider pages and usage records may be retained
  internally; incomplete result sets are not presented as complete

### 3.4 Step contract: `normalize_and_deduplicate`

- Type / SkillReference: `skill` /
  `research.normalize_paper_metadata@1.0.0`
- Input: search-response artifact reference
- Output: `papers.json` artifact reference, paper count, duplicate count,
  normalization version, warnings
- Dependencies: `search_papers`
- Timeout: 30 seconds
- Retry: one attempt; deterministic schema/data failures are non-retryable
- Idempotency: search artifact checksum plus normalization version
- Approval: none
- Checkpoint: after immutable `papers.json` metadata is committed
- Failure: `SCHEMA_VALIDATION` or `MALFORMED_PROVIDER_RESPONSE`
- Partial retention: raw normalized records may remain internal for diagnosis;
  invalid records are quarantined with reason, never silently accepted

Deduplication precedence is canonical DOI, then exact provider identity within
one provider, then a conservative normalized fingerprint of title, year, and
first author. Fuzzy title matching may produce a warning but must not merge
records automatically in V1.

### 3.5 Step contract: `rank_and_select`

- Type / SkillReference: `skill` / `research.rank_papers@1.0.0`
- Input: `papers.json` reference, normalized query, inclusion/exclusion criteria,
  `max_results`
- Output: `selected_papers.json` artifact reference and a bounded approval
  preview containing paper IDs, titles, authors, year, DOI, URL, score,
  inclusion status, and rationale
- Dependencies: `normalize_and_deduplicate`
- Timeout: 30 seconds
- Retry: one attempt
- Idempotency: papers checksum, query hash, ranker version, and budget
- Approval: none at this step
- Checkpoint: after selected artifact metadata is committed
- Failure: `SCHEMA_VALIDATION`; fail if no eligible paper remains
- Partial retention: all ranked candidates remain in the selected artifact,
  including excluded records and reasons

V1 ranking is deterministic and does not use an LLM. It combines normalized
topic/keyword matches, year-filter eligibility, metadata completeness, and
explicit criteria. Scores are not scientific quality judgments.

### 3.6 Step contract: `approve_sources`

- Type: `approval`
- SkillReference: none
- Input mapping: selected artifact ID/checksum, compact selected-paper preview,
  ranking version, query hash
- Output: approved selection fingerprint
- Dependencies: `rank_and_select`
- Timeout/expiry: no Skill timeout; approval expiry defaults to 24 hours unless
  an accepted policy changes it
- Retry: no automatic approval retry
- Idempotency: existing ApprovalRequest decision idempotency plus action
  fingerprint
- Approval: required, policy `project_reviewer`
- Checkpoint: immediately before `WAITING_FOR_APPROVAL`, atomically with request
  and event
- Failure: rejection or expiry cancels under current V1 lifecycle
- Partial retention: search, papers, selected papers, ranking, usage, events,
  and checkpoints remain available

The Engine must resolve approval-node inputs and include them in
`WaitingApproval`. Runtime must fingerprint those resolved values. This is an
additive Engine decision-contract extension; resolving them in Runtime would
violate Workflow Engine ownership.

### 3.7 Step contract: `retrieve_source_content`

- Type / SkillReference: `skill` /
  `research.retrieve_source_content@1.0.0`
- Input: approved selection artifact and fingerprint
- Output: restricted `source_content.json` artifact reference, per-paper access
  status, content hashes, and retrieval provider operations
- Dependencies: `approve_sources`
- Timeout: 180 seconds total with a per-paper deadline
- Retry: maximum two attempts per logical paper retrieval for transient
  provider failures
- Idempotency: paper ID, selected artifact checksum, content provider version,
  and requested content class
- Approval: covered by the selected-source approval; retrieval remains
  read-only and cannot bypass access controls
- Checkpoint: after artifact and provider-operation records are durable
- Failure: `CONTENT_UNAVAILABLE` is paper-local when the minimum evidence
  threshold remains satisfied; provider-wide failures follow normalized policy
- Partial retention: permitted content and explicit unavailability records are
  retained; restricted or unlicensed text is not stored

### 3.8 Step contract: `summarize_sources`

- Type / SkillReference: `skill` / `research.summarize_papers@1.0.0`
- Input: selected papers, source-content artifact, prompt version, LLM profile,
  budget remainder
- Output: `paper_summaries.json`, preliminary `evidence.json`, GroundedClaim
  candidates, usage records
- Dependencies: `retrieve_source_content`
- Timeout: 300 seconds total
- Retry: maximum two structured-generation attempts per paper; schema repair
  consumes the same call/token/cost budget
- Idempotency: paper content hash, prompt version, model identity, structured
  schema version
- Approval: none after approved sources
- Checkpoint: after all accepted per-paper outputs and artifacts are durable
- Failure: `LLM_STRUCTURED_OUTPUT`, provider categories, or
  `BUDGET_EXCEEDED`
- Partial retention: successful per-paper summaries and usage remain internal;
  step succeeds only if the configured minimum evidence threshold is met

### 3.9 Step contract: `synthesize_findings`

- Type / SkillReference: `skill` /
  `research.synthesize_literature@1.0.0`
- Input: selected papers, summaries, evidence, query, prompt version
- Output: themes, disagreements, limitations, research gaps, validated
  GroundedClaim candidates, updated evidence/provenance draft
- Dependencies: `summarize_sources`
- Timeout: 180 seconds
- Retry: maximum two structured-generation attempts
- Idempotency: input artifact checksums, model identity, prompt version, schema
  version
- Approval: none
- Checkpoint: after immutable synthesis/provenance draft is durable
- Failure: provider, structured-output, schema, budget, or initial provenance
  validation category
- Partial retention: summaries/evidence remain; invalid synthesis is internal
  and cannot be marked complete

### 3.10 Step contract: `generate_report`

- Type / SkillReference: `skill` /
  `research.generate_research_report@1.0.0`
- Input: query, selected papers, summaries, grounded synthesis, citation map,
  report prompt/style/schema version
- Output: Markdown draft, structured `ResearchReport`, citation references, and
  provenance-validation result
- Dependencies: `synthesize_findings`
- Timeout: 180 seconds
- Retry: maximum two structured-generation attempts
- Idempotency: all input artifact hashes, report prompt version, model identity,
  citation style
- Approval: none
- Checkpoint: after validated report draft is durable but before completion
- Failure: `LLM_STRUCTURED_OUTPUT`, `PROVENANCE_VALIDATION`,
  `BUDGET_EXCEEDED`, or provider category
- Partial retention: invalid report draft is restricted diagnostic content and
  never user-visible as a completed report

### 3.11 Step contract: `persist_artifacts`

- Type / SkillReference: `skill` /
  `research.persist_research_artifacts@1.0.0`
- Input: validated artifact drafts and manifest, workflow/run identities,
  schema versions, visibility/retention policy
- Output: final report artifact ID, provenance artifact ID, usage artifact ID,
  complete artifact manifest and checksums
- Dependencies: `generate_report`
- Timeout: 60 seconds
- Retry: maximum three attempts for idempotent storage failures
- Idempotency: content checksum plus logical artifact identity/version; an exact
  repeated write returns the existing immutable reference
- Approval: none
- Checkpoint: artifact content verified and metadata committed before the
  terminal workflow checkpoint
- Failure: `ARTIFACT_STORAGE` or `PROVENANCE_VALIDATION`
- Partial retention: verified orphan content may be garbage-collected later;
  metadata-visible artifacts remain immutable

The Skill prepares artifact write requests; an application `ArtifactService`
materializes them through `ArtifactContentStorage` and stages existing
`ArtifactMetadata` records in the Runtime Unit of Work. The Skill must not
import a filesystem adapter or SQLAlchemy.

### 3.12 V1 merge decision

No Workflow steps are merged. Keeping normalization separate from search makes
provider adapters replaceable; keeping ranking separate makes approval
auditable; keeping report generation separate from final persistence makes
provenance validation fail closed. Provider calls inside
`summarize_sources` remain sequential and bounded rather than expanding the DAG
per paper.

## 4. Core Data Contracts

All contracts are immutable, JSON-serializable values. Timestamps are
timezone-aware UTC ISO-8601 strings. Hashes use `sha256:<lowercase hex>`.
Unknown fields are rejected at contract boundaries unless a schema version
explicitly permits an extension object.

### 4.1 `ResearchQuery`

```text
schema_version: "research-query/v1"
topic: non-empty string
keywords: ordered unique string array
year_from: integer or null
year_to: integer or null
max_results: positive integer, bounded by server policy
language: BCP-47-like configured language code
inclusion_criteria: ordered string array
exclusion_criteria: ordered string array
```

Validation trims Unicode whitespace, preserves the user's original topic in
provenance, creates a normalized form for hashing, requires
`year_from <= year_to`, rejects unknown languages under policy, and rejects
empty criteria. The canonical query hash covers the normalized value and
schema version.

### 4.2 `PaperRecord`

```text
schema_version: "paper-record/v1"
paper_id: stable internal ID
provider_id: provider's stable record ID
title: string
authors: ordered array of {name, provider_author_id?, orcid?}
abstract: string or null
publication_year: integer or null
publication_venue: string or null
source_provider: provider identity/version
source_url: absolute HTTPS URL or null
doi: canonical lowercase DOI or null
retrieved_at: UTC timestamp
raw_metadata_hash: SHA-256 of canonical provider record
normalized_metadata_version: "paper-normalization/v1"
metadata_limitations: string array
```

Internal identity is `paper:sha256:<hash>` over canonical `doi:<doi>` when DOI
exists, otherwise `provider:<provider>:<provider_id>`. A provider-local ID may
not merge records across providers. Canonical DOI removes URL prefixes,
whitespace, and case differences without guessing missing DOI values.

### 4.3 `SourceContent`

```text
schema_version: "source-content/v1"
paper_id: internal paper ID
content_type: "metadata_only" | "abstract" | "full_text"
abstract: string or null
full_text: string or null
content_source: provider identity and source URL
retrieved_at: UTC timestamp
content_hash: SHA-256 of retained content
access_limitation: "none" | "unavailable" | "restricted" | "abstract_only"
license_or_usage_metadata: object or null
source_locations: structured section/page/offset metadata when available
```

`full_text` is null unless content was lawfully available and retention is
allowed. `abstract_only` is never promoted to `full_text`. Source content is
restricted by default and not returned inline from normal run APIs.

### 4.4 `RankedPaper`

```text
schema_version: "ranked-paper/v1"
paper_id: internal paper ID
relevance_score: finite number in [0, 1]
ranking_explanation: non-empty string
inclusion_status: "selected" | "excluded" | "ineligible"
exclusion_reason: string or null
rank: positive integer or null
ranker_version: immutable version string
score_components: bounded object of named finite values
```

Sorting is score descending, then publication year descending with null last,
then paper ID. The ranking explanation states the matched inputs; it must not
claim paper quality, correctness, or impact.

### 4.5 `CitationReference`

```text
schema_version: "citation-reference/v1"
citation_id: stable ID within the report
paper_id: internal paper ID
title: string
authors: ordered author display strings
year: integer or null
source_url: HTTPS URL or null
doi: canonical DOI or null
report_citation_label: deterministic label such as "[P1]"
```

Labels follow selected-paper rank and remain stable during one report version.

### 4.6 `EvidenceUnit`

```text
schema_version: "evidence-unit/v1"
evidence_id: stable ID
paper_id: internal paper ID
source_content_hash: SHA-256
source_location: structured location or "abstract"
source_excerpt: short permitted excerpt or null
source_summary: generated bounded summary or null
evidence_hash: SHA-256 over identity, location, and retained representation
supported_claim_ids: ordered claim ID array
content_scope: "metadata" | "abstract" | "full_text"
```

At least one of `source_excerpt` or `source_summary` is present. Verbatim
excerpts are optional, policy-gated, and narrowly bounded; the design does not
require storing large copyrighted passages. When an excerpt is not permitted,
the system stores a source-linked summary and hash instead.

### 4.7 `GroundedClaim`

```text
schema_version: "grounded-claim/v1"
claim_id: stable ID
claim_text: non-empty string
supporting_evidence_ids: non-empty ordered array
confidence: "low" | "medium" | "high"
limitations: ordered string array
claim_kind: "source_statement" | "cross_source_synthesis" | "inference"
generation_model: provider/model identity
prompt_version: immutable prompt version
```

Confidence is qualitative provenance metadata, not a calibrated probability.
Inference claims must be labeled in prose and cannot be presented as directly
reported source facts.

### 4.8 `ResearchReport`

```text
schema_version: "research-report/v1"
report_id: opaque ID
project_id: project scope
workflow_run_id: producer run
title: string
executive_summary: Markdown-compatible string
methodology: structured description including search provider and filters
selected_papers: CitationReference array
paper_summaries: structured per-paper summary array
thematic_synthesis: structured themes and claim IDs
disagreements: structured claim/evidence references
limitations: ordered strings
research_gaps: structured inference claim references
references: CitationReference array
provenance_artifact_id: opaque artifact ID
generated_at: UTC timestamp
report_schema_version: "research-report/v1"
```

The Markdown artifact is a rendering of this structured value, not the sole
source of provenance.

### 4.9 `ProviderUsage`

```text
schema_version: "provider-usage/v1"
provider: stable adapter identity/version
model_or_endpoint: configured model or endpoint identity
operation_kind: search | retrieve | generate_text | generate_structured
request_count: nonnegative integer
input_tokens: nonnegative integer or null
output_tokens: nonnegative integer or null
estimated_cost: decimal string or null
cost_currency: ISO currency code or null
latency_ms: nonnegative integer
retry_count: nonnegative integer
failure_category: normalized category or null
provider_request_ids: restricted hashed/reference values
```

Unknown provider usage remains null, never zero. Estimated cost records the
pricing-table/version reference used for the estimate and is not presented as
an invoice.

### 4.10 Storage placement

| Contract | Normalized PostgreSQL columns | PostgreSQL JSONB | Artifact content |
|---|---|---|---|
| `ResearchQuery` | run/project/workflow identity already normalized | canonical query in existing `workflow_runs.inputs_json`; compact query hash in Step output | copied into `papers.json` and `provenance.json` |
| `PaperRecord` | none in V1 | only compact paper IDs/counts/previews in Step/approval payloads | full normalized array in `papers.json` |
| `SourceContent` | artifact metadata only | access-status counts and artifact ID | restricted `source_content.json` |
| `RankedPaper` | artifact producer/run identity | compact approval preview and selection checksum | `selected_papers.json` |
| `CitationReference` | report/provenance artifact IDs through existing artifact rows | compact final output artifact IDs | report/provenance/reference content |
| `EvidenceUnit` | artifact metadata only | counts and validation status | `evidence.json` |
| `GroundedClaim` | artifact metadata only | counts and validation status | `provenance.json` |
| `ResearchReport` | existing artifact ID, project/run/step producer, checksum, media type, size | display metadata such as report schema/title | structured provenance plus `report.md` content |
| `ProviderUsage` | new `provider_operations` identity/status/cost/token/latency columns | sanitized provider-specific extension metadata | final aggregate `usage.json` |

No `papers`, `claims`, or `evidence` relational table is required for V1
because the product does not yet query those records across runs. Adding such
tables before a query need exists would duplicate immutable artifact authority.

## 5. Provider Architecture

### 5.1 `PaperSearchProvider`

Framework-independent conceptual contract:

```text
identity() -> ProviderIdentity
capabilities() -> PaperSearchCapabilities
search(query: ResearchQuery, filters, limit, context) -> PaperSearchResult
```

Responsibilities:

- execute read-only scholarly search;
- expose provider and adapter versions;
- return a normalized response envelope plus canonical raw-record hashes;
- preserve provider record IDs, source URLs, and DOI values;
- report pagination/completeness limitations;
- classify authentication, rate-limit, timeout, unavailable, malformed, and
  cancellation errors;
- never expose SDK response objects above the adapter.

`PaperSearchResult` includes ordered provider records, query/request hash,
retrieval timestamp, completeness/page metadata, provider-operation reference,
and warnings.

### 5.2 `SourceContentProvider`

```text
identity() -> ProviderIdentity
capabilities() -> SourceContentCapabilities
retrieve(paper: PaperRecord, requested_scope, context) -> SourceContentResult
```

Responsibilities:

- retrieve an abstract or explicitly permitted content;
- preserve retrieval URL, timestamp, content hash, license/usage metadata, and
  access limitation;
- distinguish unavailable, restricted, metadata-only, abstract, and full text;
- never scrape around authentication or bypass a paywall;
- classify per-paper and provider-wide errors.

The adapter must return `CONTENT_UNAVAILABLE`, not fabricated content, when
permitted source material cannot be obtained.

### 5.3 `LLMProvider`

The existing architecture contract already defines provider-neutral generation.
This slice requires:

```text
identity() -> provider, adapter version, actual model
capabilities() -> structured output, cancellation, usage availability
generate_text(request, context) -> LLMTextResponse
generate_structured(request, schema, context) -> LLMStructuredResponse
cancel(provider_request_ref) -> best-effort outcome
```

Required request fields:

- approved model identity from composition/configuration;
- ordered provider-neutral messages;
- structured output schema when applicable;
- prompt name and immutable prompt version;
- deadline and maximum output tokens;
- project/run/step/operation correlation;
- idempotency key where supported;
- remaining token/cost/call budget.

Required response fields:

- text or schema-validated structured value;
- actual provider/model identity;
- prompt version;
- finish reason;
- input/output/cached token usage when supplied;
- latency;
- provider request reference stored only in restricted form;
- retry/cancellation classification;
- policy-safe diagnostic metadata.

Text and structured generation remain distinct operations. Embeddings remain a
separate future port and are out of scope. Skills receive a budgeted,
instrumented provider implementation from composition; they do not instantiate
SDK clients or read API-key environment variables.

### 5.4 Provider operation boundary

Every external call is wrapped by an application
`BudgetedProviderOperationGateway`:

1. canonicalize the request and compute a request hash;
2. reserve call/token/cost budget in a durable provider-operation record;
3. commit the reservation before external I/O;
4. invoke the configured provider adapter;
5. normalize/redact the response or error;
6. persist actual usage, latency, request reference, retry data, and status;
7. return only the normalized response to the Skill.

This ledger is required because a process can fail after a billable call but
before a Step checkpoint. A provider that lacks request idempotency cannot
guarantee exactly-once billing; recovery conservatively charges the reservation
until an operator or supported provider lookup reconciles it.

### 5.5 `ArtifactContentStorage`

```text
write_immutable(request) -> StoredContent
open_read(storage_key) -> byte stream
verify(storage_key, expected_checksum, expected_size) -> VerificationResult
stream(storage_key, byte_range?) -> byte stream
delete(storage_key, lifecycle_authorization) -> DeletionResult
```

Responsibilities:

- write immutable content and reject conflicting content at one key;
- compute/verify checksum and size;
- support bounded reads and API streaming;
- prevent path traversal and symlink escape;
- keep storage keys independent of local absolute paths;
- delete only through an explicit retention/deletion use case;
- leave failed transaction orphans invisible because API discovery requires
  committed PostgreSQL metadata.

Initial adapter: `LocalFilesystemArtifactStorage`.

Future adapter: `S3CompatibleArtifactStorage`.

Recommended storage-key form:

```text
projects/{project_id}/runs/{run_id}/artifacts/{logical_artifact_id}/v{version}/{sha256}.{extension}
```

All components are validated opaque identifiers; adapters construct the key.
Database rows store this relative key, never `/Users/...`, `/workspace/...`, or
another absolute host/container path.

Local writes use a temporary file in the same storage root, checksum/size
verification, and atomic rename to the immutable key. If the subsequent
PostgreSQL transaction fails, the content is an unreferenced orphan eligible
for later explicit garbage collection.

## 6. Real Skill Contracts

### 6.1 Cross-Skill rules

Every Skill:

- has immutable semantic version `1.0.0`;
- uses `reagent.skill/v1beta1`, an additive proposal supporting scoped provider
  gateways, artifact write requests, usage metadata, and the minimal enum,
  length, and numeric constraints needed by these contracts;
- receives only required ports through `SkillExecutionContext`;
- returns schema-validated values, artifact requests, and ProviderUsage;
- is deterministic for identical fake-provider inputs;
- never mutates WorkflowRun or StepRun state;
- never imports FastAPI, SQLAlchemy, ORM models, provider SDK types, or concrete
  filesystem adapters;
- never reads arbitrary environment variables;
- never instantiates provider clients;
- never writes artifact bytes outside `ArtifactContentStorage`.

### 6.2 Skill matrix

| Canonical name | Responsibility | Required ports | Permission / side effect | Timeout / retry | Artifacts and usage | Failure categories |
|---|---|---|---|---|---|---|
| `research.validate_research_query@1.0.0` | Normalize and validate one query | none | none | 5s / no retry | none / none | `INVALID_QUERY`, `SCHEMA_VALIDATION` |
| `research.search_papers@1.0.0` | Call paper search and normalize the provider envelope | `PaperSearchProvider` | `papers:search_external`; `read_external` | 60s / max 3 transient attempts | internal search response; search usage | authentication, rate limit, timeout, unavailable, malformed, cancelled, budget |
| `research.normalize_paper_metadata@1.0.0` | Create stable PaperRecords and conservative deduplication | artifact read facade | `artifacts:read`; none | 30s / no retry | `papers.json`; no provider usage | malformed response, schema |
| `research.rank_papers@1.0.0` | Deterministically score/select papers and explain inclusion | artifact read facade | `artifacts:read`; none | 30s / no retry | `selected_papers.json`; no provider usage | schema, invalid query |
| `research.retrieve_source_content@1.0.0` | Retrieve abstract/permitted content with access labels | `SourceContentProvider`, artifact read | `sources:read_external`; `read_external` | 180s / max 2 transient attempts per paper | restricted `source_content.json`; retrieval usage | authentication, rate, timeout, unavailable, content unavailable, budget |
| `research.summarize_papers@1.0.0` | Structured per-paper summaries and evidence | `LLMProvider`, artifact read | `llm:generate`; `read_external` through provider | 300s / max 2 schema/provider attempts per paper | `paper_summaries.json`, preliminary evidence; LLM usage | provider, structured output, provenance, budget |
| `research.synthesize_literature@1.0.0` | Cross-paper themes, disagreements, limitations, gaps, claims | `LLMProvider`, artifact read | `llm:generate` | 180s / max 2 | synthesis/provenance draft; LLM usage | provider, structured output, provenance, budget |
| `research.generate_research_report@1.0.0` | Produce structured report and citation-aware Markdown draft | `LLMProvider`, artifact read | `llm:generate` | 180s / max 2 | report draft/provenance draft; LLM usage | provider, structured output, provenance, budget |
| `research.persist_research_artifacts@1.0.0` | Validate the final manifest and emit immutable write requests | artifact read/verification facade | `artifacts:create`; none | 60s / max 3 storage attempts | final report/provenance/usage requests | artifact storage, schema, provenance |

Provider retries are executed by the budgeted gateway, not an unbounded loop
inside a Skill. Skill retryability is returned as normalized failure metadata;
Workflow Engine remains the owner of Step-attempt retry decisions.

## 7. Provenance and Grounding Contract

### 7.1 Definition of source-grounded

A ReAgent V1 report is source-grounded only when:

1. every paper has a stable internal identity;
2. every report citation label resolves to exactly one `CitationReference`;
3. every `CitationReference.paper_id` resolves to one selected `PaperRecord`;
4. every substantive claim has at least one supporting `EvidenceUnit`;
5. every EvidenceUnit resolves to a known selected paper and retained content
   hash/location;
6. cross-paper synthesis has evidence from the papers it claims to compare;
7. unsupported language is removed or explicitly labeled as inference;
8. provider, adapter, actual model, prompt version, workflow hash, Skill
   versions, timestamps, and artifact checksums are recorded;
9. source URLs and DOI values are preserved when supplied;
10. metadata-only, abstract-only, and full-text evidence are visibly distinct;
11. the report methodology states search provider, date, query filters,
    selection count, approval decision, and source-content limitations;
12. a provenance artifact is durable before the run becomes `COMPLETED`.

A substantive claim is a factual statement, comparison, theme, disagreement,
limitation attributed to papers, or proposed research gap. UI labels, section
headings, process descriptions, and clearly marked reviewer decisions are not
substantive research claims.

### 7.2 Completion validation

Before Workflow completion, `ProvenanceValidator` must reject:

- unknown or duplicate citation IDs;
- citation labels that do not match the reference list;
- report references to papers outside the approved selection;
- claims without evidence;
- claim evidence IDs that do not exist;
- evidence referencing unknown papers or missing content hashes;
- evidence whose `supported_claim_ids` disagrees with the claim side;
- duplicate canonical DOI values after normalization;
- a `full_text` claim when only an abstract was retrieved;
- artifact IDs/checksums missing from the final manifest;
- provider/model/prompt/workflow/Skill versions missing from provenance;
- report sections containing unknown citation labels;
- a completed output without report and provenance artifact IDs;
- budget usage with negative values or unresolved in-flight reservations;
- secrets or configured credential patterns in user-visible artifacts.

Warnings that do not block completion:

- a selected paper has no DOI but has provider identity and source URL;
- full text is unavailable and the report is accurately labeled abstract-only;
- a provider does not return token usage, recorded as null;
- fewer papers than requested are found, provided the configured minimum count
  is met and the limitation is explicit.

`PROVENANCE_VALIDATION` is a terminal Step failure by default. The system must
not mark a report complete and merely hide broken provenance in a warning.

## 8. Artifact Design

### 8.1 Run artifact set

| Logical artifact | Media type / schema | Content | Visibility | Retention | Download |
|---|---|---|---|---|---|
| `papers.json` | `application/json`; `papers/v1` | query, provider envelope metadata, PaperRecords, duplicate/quarantine reasons | user | same as run until policy exists | yes |
| `selected_papers.json` | `application/json`; `selected-papers/v1` | RankedPapers, CitationReferences, ranking version, selection checksum | user | same as run | yes |
| `source_content.json` | `application/json`; `source-content-set/v1` | permitted SourceContent and access limitations | restricted | shortest policy; owner decision required | no by default |
| `paper_summaries.json` | `application/json`; `paper-summaries/v1` | per-paper structured summaries and source scope | user | same as run | yes |
| `evidence.json` | `application/json`; `evidence/v1` | EvidenceUnits and validation results | user with excerpt policy | same as run | yes after redaction |
| `report.md` | `text/markdown; charset=utf-8`; report `v1` | citation-aware rendered report | user | same as run | yes |
| `provenance.json` | `application/json`; `provenance/v1` | claims, evidence/citation maps, versions, hashes, approval fingerprint, manifest | user, with restricted diagnostics omitted | at least as long as report | yes |
| `usage.json` | `application/json`; `provider-usage-set/v1` | sanitized aggregate usage/cost/latency/failures | reviewer | same as run | yes |

Each artifact has:

- existing `ArtifactMetadata.id`;
- project scope;
- logical artifact identity and version;
- kind;
- relative storage key;
- SHA-256 checksum;
- media type and byte size;
- producer run and StepRun IDs;
- metadata JSON containing schema version, visibility, retention class,
  disposition filename, content encoding, and related artifact IDs;
- creation time.

Artifacts are immutable. Re-generation creates the next artifact version and a
new report ID; it does not overwrite earlier evidence.

### 8.2 API surface proposal

```text
GET /runs/{run_id}/artifacts
GET /artifacts/{artifact_id}
GET /artifacts/{artifact_id}/content
```

The list returns metadata and content links, never absolute paths. Metadata
responses include ETag/checksum, schema version, size, visibility, producer,
and downloadable status. Content responses stream through the backend with
`Content-Type`, `Content-Disposition`, and checksum-based `ETag`. JSON and
Markdown may render inline; explicit download uses the same authorized
endpoint.

Until authentication exists, these endpoints may run only in a trusted
single-user environment bound to loopback/private demo access. Restricted
source content must not be exposed by the frontend.

## 9. Persistence Impact

### 9.1 Existing entities reused

- `workflow_definitions`: immutable `guided-literature-review@2.0.0`, canonical
  JSON, schema version, and definition hash.
- `workflow_runs`: canonical ResearchQuery in `inputs_json`; only compact final
  artifact references in `outputs_json`.
- `workflow_step_runs`: compact input/output references, provider operation IDs,
  counts, and validation state; no report/full-text bodies.
- `checkpoints` and `checkpoint_records`: unchanged lifecycle/recovery authority.
- `memory_revisions`: budget summary, artifact references, and bounded working
  context, not raw full text.
- `artifacts`: existing immutable metadata record and producer provenance.
- `approval_requests`: exact selected artifact checksum/preview in
  `requested_action`, fingerprinted before synthesis.
- `execution_events`: existing seven-event audit taxonomy; `SKILL_EXECUTED`
  payload may include sanitized artifact/usage counts without raw content.

### 9.2 Required new table: `provider_operations`

One additive table is required for durable budget reservation and provider-call
recovery:

```text
id
project_id
workflow_run_id
step_run_id
operation_key
attempt
operation_kind
provider
adapter_version
model_or_endpoint
status: RESERVED | IN_FLIGHT | SUCCEEDED | FAILED | CANCELLED | UNKNOWN
idempotency_key
request_hash
provider_request_ref_restricted
request_count
reserved_input_tokens
reserved_output_tokens
actual_input_tokens
actual_output_tokens
estimated_cost_decimal
cost_currency
pricing_reference
latency_ms
retry_count
failure_category
diagnostic_json
row_version
created_at
updated_at
```

Raw prompts, provider responses, API keys, and authorization headers are not
stored in this table.

No new field is required on an existing table for V1. Existing artifact
`metadata_json`, run/Step JSONB outputs, approval `requested_action`, and event
payloads carry bounded schema/version/reference summaries. If implementation
inspection later proves an existing column inadequate, that change requires a
separate documented migration review rather than silently widening this
contract.

Required constraints/indexes:

- primary key `id`;
- unique `(workflow_run_id, operation_key, attempt)`;
- unique `(project_id, idempotency_key)`;
- project/run and run/Step composite foreign keys;
- nonnegative request/token/cost/latency/retry checks;
- legal status transition check in application/domain record;
- index `(workflow_run_id, created_at, id)`;
- index `(status, updated_at)` for interrupted-operation recovery;
- index `(provider, failure_category, created_at)` for operations review.

### 9.3 Port and Unit-of-Work impact

Existing repository methods remain unchanged. Add:

- `ProviderOperationRepository` for reserve, load, complete/fail, list by run,
  and optimistic version;
- `ArtifactContentStorage` outside PostgreSQL;
- read-only `ArtifactCatalog` for project/run-scoped metadata listing without
  loading every project artifact.

`UnitOfWork` must add a `provider_operations` repository so reservation/final
usage can share application transactions with checkpoints/events where
applicable. This is an additive persistence-port contract revision and requires
owner approval of proposed ADR 0003 before implementation.

Blocking reason: without a durable pre-call reservation, a crash can lose
billable request/accounting state, exceed a run budget, and retry an external
operation without knowing whether it already completed. Execution events alone
are appended after Runtime boundaries and cannot provide this reservation.

### 9.4 Migration and consistency

Create one Alembic revision after `20260721_0001` that:

- creates `provider_operations`;
- adds artifact indexes for `(producer_run_id, kind, created_at)` and optionally
  `(project_id, checksum)`;
- does not alter current run/step/checkpoint/approval lifecycle columns;
- is reversible without deleting existing tables;
- has metadata-drift and PostgreSQL contract tests.

Artifact content and PostgreSQL cannot be committed atomically. The application
writes and verifies immutable content first, then commits artifact metadata,
Step output, usage, event, and checkpoint. A failed database transaction leaves
only an undiscoverable orphan. An exact replay finds the content by checksum and
reuses it.

Provider operations have their own optimistic `row_version`. Artifact rows are
immutable. Workflow aggregate `persistence_version` continues unchanged.

Canonical idempotency:

- provider call:
  `run + step + Step attempt + logical call + provider/model + request hash`;
- artifact:
  `project + run + logical artifact + version + content hash`;
- report:
  all source artifact checksums + prompt/style/report schema versions;
- approval:
  selected artifact ID/checksum + paper IDs + workflow/Skill versions.

## 10. Application and API Impact

### 10.1 Required application use cases

`CreateRealLiteratureReviewRun`

- accepts a catalog workflow identity/version and `ResearchQuery`;
- loads the persisted immutable definition instead of trusting an inline
  provider/Skill graph from the browser;
- validates provider configuration, required secrets by presence only, and a
  complete fail-closed budget before creating the run;
- returns the existing run for an exact idempotent replay.

`ListRunArtifacts`

- verifies run/project association;
- queries `ArtifactCatalog` by producer run;
- filters restricted content according to the current trusted-environment
  policy;
- returns metadata only.

`GetArtifactMetadata`

- resolves one opaque artifact ID;
- never exposes a local path or provider credential;
- returns checksum, media type, size, schema, visibility, producer, and content
  endpoint.

`ReadArtifactContent`

- verifies metadata before opening the storage key;
- supports bounded streaming and checksum ETag;
- rejects restricted content unless the policy context permits it;
- records no content body in normal logs.

`RetryProviderOperation`

- is allowed only for a retryable normalized failure or an interrupted
  operation that the recovery policy has classified;
- reserves remaining budget before dispatch;
- creates a new provider-operation attempt without overwriting history;
- submits the existing run through `ExecutionDispatcher`; it does not mutate a
  Step directly.

`GetProviderUsage`

- reads provider-operation summaries and the final `usage.json`;
- returns sanitized totals and breakdowns;
- does not return raw provider request/response bodies.

`ValidateResearchProvenance`

- executes the Section 7 validation independently of report generation;
- returns blocking errors and warnings;
- must pass before the application permits terminal completion.

`MaterializeArtifactRequests`

- consumes schema-validated Skill artifact requests;
- writes/verifies content through `ArtifactContentStorage`;
- creates existing `ArtifactMetadata`;
- stages metadata and compact artifact references with Runtime state in the
  Unit of Work.

### 10.2 Proposed transport DTOs

Additive catalog-run request:

```json
POST /runs/from-catalog
{
  "project_id": "prototype-project",
  "actor_user_id": "prototype-user",
  "idempotency_key": "client-generated",
  "agent_profile_ref": "research-profile@1.0.0",
  "workflow_id": "guided-literature-review",
  "workflow_version": "2.0.0",
  "inputs": {
    "topic": "persistent research agents",
    "keywords": ["persistent agents"],
    "year_from": 2020,
    "year_to": 2026,
    "max_results": 8,
    "language": "en",
    "inclusion_criteria": [],
    "exclusion_criteria": []
  },
  "budget": {
    "max_provider_requests": 25,
    "max_llm_calls": 15,
    "max_input_tokens": 200000,
    "max_output_tokens": 30000,
    "max_estimated_cost": "OWNER_APPROVED_DECIMAL",
    "cost_currency": "USD",
    "max_runtime_seconds": 1800,
    "max_artifact_bytes": 104857600
  }
}
```

The actual cost value is not valid until the owner decides it. Real-provider
mode rejects a missing cost cap.

Run artifact list:

```json
{
  "artifacts": [
    {
      "id": "artifact_...",
      "logical_name": "report.md",
      "kind": "research_report",
      "media_type": "text/markdown; charset=utf-8",
      "size": 12345,
      "checksum": "sha256:...",
      "schema_version": "research-report/v1",
      "visibility": "user",
      "downloadable": true,
      "content_url": "/artifacts/artifact_.../content"
    }
  ]
}
```

Provider usage response:

```json
{
  "workflow_run_id": "run_...",
  "totals": {
    "request_count": 7,
    "input_tokens": 12000,
    "output_tokens": 3500,
    "estimated_cost": "0.00",
    "cost_currency": "USD",
    "latency_ms": 9000
  },
  "operations": [],
  "complete": true
}
```

Unknown usage and cost values are `null`, not invented zero values.

### 10.3 Proposed endpoints

Keep existing endpoints and add:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/runs/from-catalog` | Create a run from a server-persisted immutable definition |
| `GET` | `/runs/{run_id}/artifacts` | List run-produced artifact metadata |
| `GET` | `/runs/{run_id}/provider-usage` | Sanitized usage/budget view |
| `GET` | `/artifacts/{artifact_id}` | Artifact metadata |
| `GET` | `/artifacts/{artifact_id}/content` | Authorized streaming/read |
| `POST` | `/runs/{run_id}/provider-operations/{operation_id}/retry` | Explicit application-level retry when eligible |

The existing `POST /runs` inline-definition endpoint remains for current demo
compatibility. The real workflow UI must use `/runs/from-catalog` so a browser
cannot alter Skill references, timeout policy, or approval placement.

### 10.4 HTTP error mapping

Provider errors are persisted in normalized form and mapped without raw
provider payloads:

| Application condition | HTTP behavior |
|---|---|
| invalid query/schema/budget request | `422`, stable ReAgent error code |
| run/artifact/operation not found | `404` |
| stale approval, ineligible retry, idempotency drift | `409` |
| provider authentication/configuration unavailable before execution | `503`, sanitized configuration message |
| accepted execution later hits provider failure | run/Step state and event API show normalized failure; command response returns the durable run, not a raw upstream exception |
| restricted artifact content | `403` after authorization exists; trusted V1 may fail closed with `404` |
| content missing or checksum mismatch | `409` or `503` with `ARTIFACT_STORAGE`; never a local storage path |

Provider names may be visible; credentials, headers, raw responses, internal
stack traces, provider request bodies, and absolute paths are not.

### 10.5 Synchronous boundary

The current `SyncExecutionDispatcher` runs the full resumed segment inside the
HTTP request. It is acceptable for the deterministic fake vertical slice and a
strictly bounded, supervised local provider test. It is not acceptable for
production traffic or long real runs. Before team-hosted use, a durable worker
must replace the dispatcher and implement claim/lease, retry time, cancellation,
deadline, and crash recovery without moving workflow semantics.

## 11. Frontend Impact

### 11.1 Minimal changes

The existing App Router, React Query, typed API client, same-origin rewrite, and
page structure remain. Add:

- a Guided Literature Review v2 input form with topic, keywords, year range,
  maximum papers, language, and optional inclusion/exclusion criteria;
- client validation that mirrors only basic transport rules while the backend
  remains authoritative;
- use of `POST /runs/from-catalog`, never a client-supplied real workflow graph;
- rank/selection summary on the Run page;
- approval card with selected paper titles, authors, year, DOI/source links,
  score, rationale, selection checksum, and count;
- retrieval limitation labels: metadata only, abstract only, full text, or
  unavailable;
- Markdown report viewer with sanitized rendering;
- citation labels linking to the report references section and external DOI or
  source URL;
- artifact list/download actions;
- provider error presentation using stable ReAgent codes and user-safe
  messages;
- optional usage/cost summary when values are present;
- explicit “abstract-only review” methodology/limitation badges;
- loading, partial-results, failure, retry-eligible, and empty-artifact states.

Do not add a workflow editor, project redesign, chat interface, vector-search
UI, model picker, or broad visual redesign.

### 11.2 Exact end-to-end journey

1. User opens `/workflows`.
2. User selects **Guided Literature Review v2**.
3. User enters topic, keywords, years, maximum papers, language, and criteria.
4. UI creates the catalog-pinned run and navigates to `/runs/{id}`.
5. Run timeline advances through validation, search, normalization, and ranking.
6. Run pauses at `WAITING_FOR_APPROVAL`.
7. User opens `/approvals` and sees the exact ranked selection and source links.
8. User approves or rejects the fingerprinted selection.
9. Approval resumes the same run; rejection cancels it.
10. Approved run retrieves permitted content, summarizes, synthesizes, validates,
    and persists artifacts.
11. Run page shows `COMPLETED`, a rendered report, citations, limitations,
    artifact downloads, and optional usage.
12. User opens a citation link or downloads `report.md`/`provenance.json`.
13. Page reload returns the same persisted artifacts and citation mapping
    without provider re-execution.

## 12. Failure, Retry and Recovery Model

### 12.1 Normalized categories

| Category | Retry / maximum attempts | Backoff | Human intervention | Partial retention | User-facing message | Internal diagnostic detail |
|---|---|---|---|---|---|---|
| `INVALID_QUERY` | no retry | none | user edits input | original input and validation event | “The research query is invalid. Review the highlighted fields.” | field paths and rule IDs |
| `PROVIDER_AUTHENTICATION` | no automatic retry | none | operator fixes secret/config | prior durable artifacts/usage retained | “The configured research provider is unavailable.” | provider, adapter version, sanitized auth class; no credential |
| `PROVIDER_RATE_LIMIT` | retryable, max 3 | provider hint then bounded exponential | only after exhaustion | completed pages/calls retained internally | “The provider is busy; ReAgent will retry within this run’s budget.” | status class, retry hint, operation ID |
| `PROVIDER_TIMEOUT` | retryable, max 3 search/2 content or generation | bounded exponential | optional after exhaustion | successful prior operations retained | “The provider did not respond before the deadline.” | deadline, latency, operation ID |
| `PROVIDER_UNAVAILABLE` | retryable, max 3 | bounded exponential | optional after exhaustion | successful prior operations retained | “The provider is temporarily unavailable.” | transport class and sanitized status |
| `MALFORMED_PROVIDER_RESPONSE` | no retry by default; one retry only for explicitly transient truncation | bounded once | operator/adapter review | raw hash and sanitized fixture candidate restricted | “The provider returned data ReAgent could not validate.” | schema paths, response hash, adapter version |
| `CONTENT_UNAVAILABLE` | no retry for a stable access restriction; transient transport follows provider category | none | reviewer may accept reduced corpus in a new run | explicit unavailable record retained | “Source content was unavailable; the report may use metadata or abstract only.” | paper ID, source, access category, no protected body |
| `SCHEMA_VALIDATION` | no retry | none | developer/provider adapter correction | valid upstream artifacts retained | “A research result did not match the required schema.” | schema version and paths |
| `LLM_STRUCTURED_OUTPUT` | retryable once, total max 2 calls | immediate bounded repair | prompt/model review after exhaustion | source artifacts and accepted per-paper results retained | “The model could not produce a valid structured result.” | schema paths, model/prompt version, output hash; no unrestricted body |
| `PROVENANCE_VALIDATION` | no automatic retry by default | none | reviewer/developer must correct generation contract | invalid draft restricted; evidence retained | “The report failed source-grounding validation and was not completed.” | missing claim/evidence/citation IDs and validator version |
| `ARTIFACT_STORAGE` | retryable, max 3 for idempotent writes | bounded exponential | storage operator after exhaustion | verified existing objects/metadata retained; orphans recorded | “A research artifact could not be stored safely.” | storage adapter, key hash, checksum stage; no absolute path |
| `BUDGET_EXCEEDED` | no retry | none | owner starts a new run with an approved budget | all completed operations/artifacts retained | “The run stopped at its configured cost or resource limit.” | budget dimension, reserved/actual values |
| `CANCELLED` | no retry | none | user starts a new linked run | all committed history retained | “The run was cancelled.” | actor/policy and safe boundary |

Every retry consumes call and runtime budget. Retry-After values are bounded by
the run's remaining runtime. Random jitter belongs in the dispatcher/provider
gateway with injectable deterministic tests; Workflow Engine continues to own
Step-attempt retry decisions.

### 12.2 Restart behavior

Provider failure:

- persist the normalized failed operation and usage;
- if retryable and budget remains, return a retryable Skill failure to Workflow
  Engine;
- recovery creates the next Step/provider attempt without overwriting history.

Process crash:

- load the latest checkpoint, Step attempt, artifact metadata, and provider
  operations;
- reuse succeeded operations/artifacts by request/content hash;
- treat `RESERVED`/`IN_FLIGHT` as interrupted;
- reconcile through provider-supported request lookup/idempotency when
  available;
- otherwise conservatively retain the reservation and require remaining budget
  for a new call.

Approval pause:

- selection artifact, preview, checksum, ApprovalRequest, event, and checkpoint
  survive process restart;
- approval resumes only the matching fingerprint;
- changed/corrupt selection invalidates the request.

Artifact write failure:

- exact content-hash replay is idempotent;
- metadata without verifiable content blocks reads and completion;
- content without metadata is an invisible orphan;
- no run completes until all required artifact metadata/content verify.

Report validation failure:

- keep the invalid draft restricted for bounded diagnostics if policy permits;
- keep selected papers/evidence/usage;
- mark the Step/run failed with `PROVENANCE_VALIDATION`;
- never publish the draft as `report.md` and never return `COMPLETED`.

## 13. Security, Privacy and Secret Management

- API keys enter only at the composition/configuration boundary and are passed
  into concrete adapters; no Skill, Workflow definition, request DTO,
  checkpoint, event, artifact, or provider-operation record contains a key.
- Workflows name provider capabilities/profiles, not environment-variable names
  or credentials.
- Provider errors are normalized and sanitized before persistence or HTTP
  mapping.
- Authorization headers, signed URLs, API keys, cookies, and full provider
  request/response bodies are excluded from normal logs/events.
- Prompt templates are versioned source code/configuration. Persist the prompt
  name, version, request hash, and policy-safe input references. Raw prompts or
  responses are retained only under an explicit restricted diagnostic policy.
- User input is length-bounded, Unicode-normalized for hashing, treated as data,
  and never interpolated into executable code, SQL, filesystem paths, or
  environment-variable names.
- Provider-supplied text is untrusted content. It cannot inject Workflow
  instructions, change permissions, request tools, or alter citation mappings.
- V1 does not accept private/confidential document uploads. If later enabled,
  provider data-handling approval, tenant isolation, encryption, retention, and
  deletion must be accepted first.
- Artifact reads are project-scoped conceptually, but the current system has no
  authentication. Real-provider demonstrations are restricted to a trusted
  single-user environment and loopback/private access.
- Artifact access URLs never reveal absolute storage paths. Source content is
  restricted by default.
- Deletion is disabled from Skills and public V1 APIs. Retention/deletion occurs
  only through a future authorized lifecycle use case with audit records.
- The system respects source terms, licenses, and access limitations and does
  not bypass paywalls. It minimizes stored verbatim text and labels excerpts.
- Source URLs/DOI values are citations, not proof that ReAgent acquired or may
  redistribute full text.

Until authentication and authorization exist, this slice must not be exposed as
a shared or public service, must not process confidential inputs, and must not
provide unrestricted artifact URLs.

## 14. Cost and Budget Controls

### 14.1 Proposed default hard bounds

| Budget | Proposed V1 bound |
|---|---:|
| search candidates fetched | 50 |
| selected papers (`max_results`) | default 8, hard maximum 10 |
| provider requests, all kinds | 25 |
| LLM calls | 15 |
| input tokens | 200,000 |
| output tokens | 30,000 |
| estimated cost | required decimal cap; real mode disabled until owner approves a value |
| wall-clock runtime | 1,800 seconds |
| total artifact content | 100 MiB |
| one artifact | 25 MiB |
| retained excerpt | policy-gated and narrowly bounded; no large passages |

These are contract proposals, not provider-capability claims. Lower provider
limits win. Test configurations use much lower limits.

### 14.2 Enforcement

- Validate budgets before creating a real run.
- Reserve the worst-case allowed request/token/cost amount before each external
  call.
- Reject a call if the reservation would exceed any dimension.
- Reconcile actual usage after a response; unknown actual usage keeps the
  conservative reservation.
- Include retries and schema-repair calls in every budget.
- Count content retrieval and search requests, even if they return no results.
- Stop before writing an artifact that would exceed individual or run size.
- Persist current budget state at provider-operation/checkpoint boundaries.
- Return `BUDGET_EXCEEDED` and fail closed; never silently continue, switch to a
  cheaper/unapproved model, reduce evidence requirements, or omit provenance.

Real-provider tests should select at most three papers, use at most two LLM
calls where the test contract permits, and set an owner-approved low cost cap.

## 15. Testing Strategy

### A. Pure contract tests

No network, database, or filesystem outside a temporary test directory:

- serialize/deserialize every schema;
- canonical hashes and immutable values;
- DOI/identity normalization and conservative deduplication;
- rank stability and tie-breaking;
- provider error mapping;
- budget reservation/reconciliation;
- storage-key construction/path traversal rejection;
- artifact checksum verification;
- claim/evidence/citation/provenance validation;
- copyright rule: report creation does not require large excerpts;
- workflow and Skill schema compatibility.

### B. Fake provider vertical slice

Normal backend/frontend suite uses:

- deterministic fake `PaperSearchProvider`;
- deterministic fake `SourceContentProvider`;
- deterministic fake `LLMProvider` with structured outputs and usage;
- temporary `LocalFilesystemArtifactStorage`;
- InMemory adapters for fast tests and PostgreSQL adapter contract coverage.

The full fake scenario must execute:

```text
topic input
-> deterministic papers
-> normalization/deduplication
-> ranking
-> visible candidate approval
-> deterministic source retrieval
-> grounded structured synthesis
-> report/provenance/usage artifacts
-> API content retrieval
-> frontend report/citations
-> reload persistence
```

It must be part of the default suite and assert exact fixture output,
checksums, event order, no duplicate provider operation, and no secret-like
values in logs/events/artifacts.

### C. Recorded-fixture tests

- store sanitized, legally retainable provider response fixtures;
- no credentials, signed URLs, headers, request IDs tied to accounts, or
  copyrighted full text;
- record source provider, retrieval date, adapter version, fixture license/use
  rationale, and SHA-256;
- replay entirely offline;
- assert normalization, error classification, and schema handling rather than
  current result ranking;
- review fixtures before commit and version them when provider schema changes.

### D. Real provider tests

Real tests require explicit variables/configuration and a positive enable flag.
They:

- skip by default;
- use isolated database/storage and low budgets;
- never print keys or raw request/response bodies;
- record provider/adapter/actual model/prompt/schema versions;
- assert schema, provenance, citations, budgets, and persistence, not exact
  prose or exact live search ordering;
- report request count, tokens when supplied, estimated cost, and duration;
- clean only test-owned state under explicit authorization;
- fail rather than silently replacing the real adapter with a fake.

Suggested gating names are conceptual until implementation:

```text
REAGENT_ENABLE_REAL_PROVIDER_TESTS=1
REAGENT_TEST_PAPER_PROVIDER=...
REAGENT_TEST_LLM_PROVIDER=...
```

Secret variable names are selected by the adapter/composition design and must
not appear in Workflow definitions.

### 15.1 Exact end-to-end acceptance

The acceptance scenario is:

```text
topic input
-> real paper search
-> candidate approval
-> permitted source retrieval
-> grounded synthesis
-> report artifact
-> API retrieval
-> frontend report display
-> citation/source link inspection
-> page reload
-> persisted identical artifact IDs/checksums
```

Acceptance requires the real frontend, FastAPI, application services, Runtime,
provider adapters, artifact storage, SQL Unit of Work, and PostgreSQL. The run
must have no unknown citations, evidence gaps, secret leaks, budget overrun, or
duplicate provider execution after reload/resume.

## 16. Provider Decision Matrix

### 16.1 Verification disclaimer

No official provider documentation was accessed in this phase because the task
forbids external-service calls. All current authentication, limits, pricing,
model names, API availability, and terms are **UNVERIFIED AS OF THIS PHASE**.
Before implementation, an approved reviewer must check current official
documentation and record the result. A recommendation below is an
architecture-fit recommendation, not a statement of current service terms.

### 16.2 Paper search candidates

| Candidate | API availability / auth | Metadata, DOI, abstract | Limits/stability/terms | Reproducibility | Development complexity |
|---|---|---|---|---|---|
| OpenAlex | unverified; official API/auth requirements must be checked | target-field fit appears promising but DOI/abstract coverage must be measured with the canonical topic | all current limits, snapshot/API stability, and terms unverified | preserve work ID, query, filters, response hash, retrieval time; live ordering not assumed stable | medium: provider schema normalization and abstract reconstruction/absence handling may be needed |
| Semantic Scholar Academic Graph | unverified; key requirements must be checked | target-field fit appears promising; DOI/abstract presence must be measured | all current limits, service policy, and terms unverified | preserve paper ID, request hash, retrieval time; do not assert live ordering | medium: pagination/field selection/error adapter required |
| Crossref REST | unverified; polite-pool/auth behavior must be checked | strong DOI-oriented candidate in principle; abstract completeness for this product must be measured | limits, etiquette, terms, and current behavior unverified | DOI-centric identity supports normalization; query ranking must be treated as provider-specific | low/medium adapter, but likely insufficient alone if abstract coverage fails acceptance |

Preferred initial provider: **OpenAlex, conditional on official-document and
canonical-topic validation**. Rationale: it is the best architectural candidate
for broad scholarly metadata and stable external identities, while ReAgent's
normalization/artifact contracts absorb provider-specific shape.

Fallback: **Semantic Scholar Academic Graph**, conditional on the same review.

Crossref is a metadata enrichment/fallback candidate, not the preferred sole
search provider unless measurement shows acceptable abstract and ranking
coverage.

### 16.3 LLM candidates

| Candidate | Structured output | Token/cost visibility | SDK/retry/model pinning | Latency/data handling | Testability |
|---|---|---|---|---|---|
| OpenAI API | current model-level support unverified; must pass a strict structured-output probe | pricing, usage fields, and limits unverified | current SDK, retry semantics, idempotency, and pinning unverified; adapter must record actual model | current latency/retention/data terms require owner review | fake adapter and schema contract are straightforward; live prose never asserted |
| Anthropic API | current model-level support unverified; must pass equivalent schema probe | pricing, usage fields, and limits unverified | current SDK/retry/model identity behavior unverified | current latency/retention/data terms require owner review | same provider-neutral fake/fixture contract |
| Local OpenAI-compatible model server | availability depends on owner-provided runtime; structured reliability unverified | direct API cost may be zero but hardware/operations are not; token accounting varies | server/version/model pinning is owner-operated | data can remain local; latency/hardware requirements unverified | deterministic fake remains separate; live local model quality must meet provenance gates |

Preferred initial LLM provider: **OpenAI API with an owner-approved,
currently supported structured-output model**, conditional on official
verification, data-handling approval, and cost cap.

Fallback: **Anthropic API with an owner-approved structured-generation model**.

The local option is a deployment alternative, not a silent fallback. ReAgent
must never switch providers/models without recording it and verifying remaining
budget/capability.

### 16.4 Owner approval gates

Implementation of a real adapter requires owner approval of:

- first paper provider and its current terms/authentication;
- first LLM provider and exact model/profile;
- available API keys and allowed secret store/environment boundary;
- data retention/provider training/privacy settings;
- per-run cost cap;
- fixture-retention permission.

## 17. Implementation Sequence

### Milestone 0: Contract approval

Entry: this document and proposed ADR 0003 are reviewed.

Work:

1. decide all blocking owner items in Section 19;
2. verify current official provider documentation;
3. accept, revise, or reject ADR 0003;
4. assign immutable workflow/prompt/schema versions.

Exit gate: provider-independent boundaries, cost policy, content scope, storage
root, retention, citation style, and test-fixture policy are explicitly
accepted.

### Milestone 1: Contract substrate and local artifact storage

Work:

1. implement immutable schemas and provenance validator;
2. implement `ArtifactContentStorage` port and local adapter;
3. add provider ports, normalized errors, budget gateway contracts;
4. add `ProviderOperationRepository`, SQL/InMemory adapters, migration, and
   contract tests;
5. add fake providers;
6. add minimal Skill schema enum/length/range constraints plus artifact/usage
   result extensions;
7. add the approval resolved-input decision extension.

Exit gate: no network; pure/adapter tests pass; content survives process
restart; current regression suite passes; no frozen ownership moved.

### Milestone 2: Fake-provider backend vertical slice

Work:

1. implement all real Skill contracts against fakes;
2. publish hash-pinned `guided-literature-review@2.0.0`;
3. materialize artifacts through Runtime/application boundaries;
4. add catalog-run, artifact, usage, and retry application services/APIs;
5. execute complete fake flow through PostgreSQL.

Exit gate: deterministic create -> approval -> report -> content retrieval ->
application reconstruction passes with exact provenance/checksums and no
duplicate operations.

### Milestone 3: Minimal frontend report experience

Work:

1. real workflow input form;
2. candidate preview approval;
3. report/citation/artifact viewer;
4. provider error and usage states;
5. browser fake-provider E2E and reload.

Exit gate: the complete fake flow is user-visible and accessible through stable
roles/labels without API mocks.

### Milestone 4: First real paper provider

Work:

1. implement the owner-approved PaperSearchProvider adapter;
2. implement or configure the approved SourceContentProvider behavior;
3. add sanitized fixtures and opt-in low-budget integration tests;
4. measure canonical-topic metadata/DOI/abstract coverage.

Exit gate: real search produces schema-valid, deduplicated, auditable records
and never bypasses content restrictions.

### Milestone 5: First real LLM provider

Work:

1. implement the owner-approved LLM adapter;
2. implement structured prompt versions for summaries/synthesis/report;
3. add live opt-in schema/provenance/budget tests;
4. verify cancellation/error normalization and actual-model recording.

Exit gate: low-budget live outputs pass provenance and secret scans; fake and
fixture suites remain green.

### Milestone 6: Supervised real acceptance

Work:

1. run the exact Section 15 acceptance scenario;
2. inspect paper quality, evidence/claim mapping, report limitations, usage,
   cost, failure behavior, and reload persistence;
3. retain only policy-approved evidence.

Exit gate: architecture reviewer and owner accept one real, auditable report.
Any provenance, secret, budget, content-rights, persistence, or duplicate-call
failure blocks acceptance.

## 18. Acceptance Criteria

### 18.1 Blocking gates

- no Domain lifecycle, Workflow Engine ownership, Skill System ownership, API
  transport ownership, or adapter dependency-direction change;
- proposed additive persistence/Skill/Engine decision contracts accepted before
  implementation;
- deterministic fake vertical slice passes in the normal suite;
- PostgreSQL and artifact content survive application/process restart;
- all report citations resolve to approved PaperRecords;
- all substantive claims resolve to EvidenceUnits;
- no evidence references an unknown paper/content hash;
- provider errors use the normalized taxonomy;
- secrets do not appear in logs, events, checkpoints, database JSON, artifacts,
  screenshots, or test output;
- every external call is budget-reserved and usage-recorded;
- budget limits fail closed;
- real-provider tests are opt-in and low-budget;
- report/artifacts are retrievable through API and visible in frontend;
- page reload preserves identical report/citation/artifact identities;
- approval fingerprint includes selection checksum and candidate identities;
- metadata/abstract/full-text scope is accurately labeled;
- existing backend/frontend regression tests pass.

### 18.2 Blocking failures

- any unknown citation or unsupported substantive claim;
- report completion after provenance validation failure;
- provider SDK/ORM/FastAPI/concrete filesystem access inside a Skill;
- API key or raw sensitive provider payload persisted;
- missing cost cap in real mode;
- budget overrun or unrecorded provider attempt;
- content-access bypass or misleading full-text claim;
- artifact database metadata referencing missing/corrupt content;
- duplicate logical provider execution after supported idempotent recovery;
- real test silently using a fake/InMemory adapter;
- changed frozen lifecycle or ownership without an accepted ADR.

### 18.3 Acceptable warnings

- no DOI for a paper that retains stable provider ID and URL;
- abstract-only content, accurately disclosed;
- provider token/cost usage unavailable and represented as null with a
  conservative reservation;
- fewer results than requested above the accepted minimum;
- Docker remediation remains unexecuted if local acceptance is clearly scoped;
- synchronous dispatcher used only for bounded trusted demonstration.

### 18.4 Deferred production requirements

- authentication, authorization, project membership, approval-role enforcement;
- durable queue/worker leases, retry clock, cancellation channel;
- proactive approval expiry;
- asynchronous database boundary or explicit worker-thread isolation;
- production S3-compatible storage, encryption, backup, retention deletion;
- observability, alerting, audit retention, data-loss recovery;
- load/performance tests and provider failover;
- accessibility/cross-browser coverage;
- production secret manager, TLS, deployment, high availability;
- systematic-review compliance and richer retrieval.

## 19. Open Decisions

No row is an owner decision until explicitly accepted.

| Decision | Recommended option | Alternatives | Consequence of delay |
|---|---|---|---|
| paper search provider | OpenAlex after current official-doc and canonical-topic verification | Semantic Scholar fallback; Crossref enrichment/conditional sole provider | does not block fake Milestones 1–3; blocks real adapter Milestone 4 |
| LLM provider/model | OpenAI API plus a currently supported structured-output model after review | Anthropic; explicitly configured local model | does not block fakes; blocks prompt/live adapter Milestone 5 |
| API key availability | composition-injected local secret/environment for supervised test; never Workflow data | managed secret store later | blocks all live-provider tests |
| maximum cost per real demo run | owner-approved low decimal cap; suggested review starting point USD 2.00, not active by default | lower/higher explicit cap | real mode must remain disabled |
| source scope | abstract-first V1; full text only when explicitly permitted and labeled | metadata+abstract only; permitted open full text | blocks SourceContentProvider policy and report claims |
| local artifact directory | repository-root ignored `runtime_data/artifacts`, configured at composition | external absolute root mapped by configuration; container named volume | blocks local adapter configuration and Compose design |
| retention policy | keep user artifacts with run; shortest retention for source content and raw diagnostics | fixed-day expiry; manual deletion only | blocks handling of real full text/diagnostic payloads |
| source excerpts | short, policy-gated excerpts only when permitted; summaries otherwise | no verbatim excerpts | blocks evidence rendering/copyright policy |
| recorded real responses | retain only sanitized metadata/abstract fixtures after legal/terms review | synthetic fixtures only | blocks recorded-fixture coverage, not fake/live tests |
| citation style | deterministic numeric labels `[P1]`, `[P2]` with full reference metadata | author-year; CSL style later | blocks final Markdown rendering contract |
| minimum usable paper count | 3 selected papers, unless user explicitly requests fewer within policy | 1 or 5 | blocks partial-content success rule |
| provider usage visibility | show aggregate calls/tokens/cost estimate to trusted reviewer | hide cost, keep internal | blocks final frontend usage presentation only |
| additive ADR 0003 | accept new provider/artifact/operation boundaries and approval input extension | revise port/UoW design; reject and redesign recovery | blocks Milestone 1 implementation |
| Docker remediation | keep as a separate environment acceptance stream | require before any Phase 9 code | does not block local fake contract work; still blocks clean-machine evidence |

## Contract recommendation

ReAgent is ready to begin the provider-independent first implementation
milestone once proposed ADR 0003 is approved or revised. Provider/model choice
does not block schemas, fake providers, artifact storage, provenance, or
provider-operation persistence. It does block real network adapters and live
acceptance.
