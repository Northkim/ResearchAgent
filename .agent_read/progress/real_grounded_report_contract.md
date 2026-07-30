# Phase 9C-0 — Real Grounded Report Contract

Date: 2026-07-30
Status: **Documentation complete; ADR 0007 accepted with limited implementation scope**

## Owner decision recorded

The owner authorized Phase 9C-1 to implement the immutable V3 workflow,
abstract-only grounded contracts, staged Fake/synthetic generation, deterministic
citations, fail-closed provenance, immutable report/corpus artifacts, and an
Anthropic `claude-sonnet-5` adapter target tested without network.

Real calls, keys, real abstracts, spend, OpenAlex report generation, live
acceptance, fallback/comparison, full text, relevance judging, and downstream
Idea/Writing remain deferred. Phase 9C-2 requires separate approval for the
provider account/key, ZDR/retention, abstract transmission, budget, exactly
three live papers, retention duration, and live gates.

## Outcome

Phase 9C-0 froze a proposed approved-source, abstract-only, staged grounded
report architecture. No production/dependency/workflow source changed; no LLM,
OpenAlex, database, runtime-data, report, or relevance-label execution occurred.

The optional automated-relevance evaluation module and ADR 0006 are Deferred,
not rejected. All Judge code/tests/evidence and blank packets remain retained.

## Source-confirmed findings

- `guided-literature-review@2.0.0` remains immutable at hash
  `af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`.
- Current V2 summary/report skills are Fake-oriented; adapter composition alone
  cannot provide the approved abstract prompt and claim/evidence semantics.
- Existing LLMProvider already has text/structured generation, identity, usage,
  request context, and cancel boundaries. Additive real-adapter contract needs
  exact snapshot, adapter/prompt/schema hashes, request ID, latency/retry/
  refusal/error, timeout/idempotency metadata.
- ProviderOperationService, immutable ArtifactContentStorage, approval
  fingerprint, SQL ArtifactMetadata, APIs/UI, and provenance validator are
  reusable; no new DB table was demonstrated necessary.

## Proposed architecture

New immutable V3 workflow and v2 grounded skills:

approved set → combined per-paper summary/evidence → cross-paper claims →
Markdown report → blocking provenance → artifacts/API/UI → corpus handoff.

Artifacts: papers, selected papers, source content, summaries, evidence, claims,
report, provenance, usage, generation manifest, and literature corpus.

Primary provider proposal is `claude-sonnet-5`; `gpt-5.6-terra` is manual
fallback; gpt-oss-20b is a local development alternative. No selection is
approved.

## Implementation sequence

### Phase 9C-1 — adapter substrate and Fake/synthetic validation

- Goal: additive LLM port metadata, prompt registry, v2 contracts, V3 workflow/
  skills, provider adapter boundary, Fake vertical slice, operation/replay and
  artifact validation.
- Likely modules: research contracts/skills/providers, application composition,
  provider operations, provenance validator, workflow registry, focused API DTOs.
- Excludes: real SDK/call unless separately authorized, real abstracts, real
  report, full text, Judge.
- Tests: pure contracts, failure injection, fake end-to-end, immutable V2 hash,
  full backend/frontend regression if touched.
- Entry: owner approves/revises ADR 0007 architecture and Fake-only scope.
- Completion: network-free V3 report/corpus with zero-call replay; no ownership
  violation.

### Phase 9C-2 — bounded real summary/evidence acceptance

- Goal: adapter and exactly three owner-approved real abstracts through
  per-paper summary/evidence only.
- Excludes: cross-paper/report publication, extra papers/providers, full text.
- Tests: official contract recheck, isolated DB/root, usage/cost/ZDR,
  operations/restart/replay, span validation.
- Entry: provider/model/key/ZDR/abstract rights/budget/retention approvals and
  Phase 9C-1 pass.
- Completion: three valid private summaries/evidence artifacts, no unsettled
  operations or duplicate call.

### Phase 9C-3 — real report full-stack E2E

- Goal: synthesis/claims/report, publication gate, corpus, API/UI and
  restart/reload.
- Excludes: Judge, full text, multi-user production, downstream workflows.
- Tests: bounded real run plus frontend citations/disclosure/download and
  idempotent replay.
- Entry: Phase 9C-2 product review and explicit remaining call/spend approval.
- Completion: readable report with zero unknown/unsupported citations/claims,
  all artifacts and operations settled.

## Testing evidence

Runtime tests were not required or run. Documentation validation must include
deliverable existence, ADR statuses, `git diff --check`, ignore checks, and
source/dependency scope.

## Current limitations

Abstract incompleteness and rights, no provider validation, no authentication,
synchronous execution, local retention cleanup, manual variants, no independent
scientific verification, and no full-text evidence. A grounded report remains
model-assisted orientation, not scientific truth.

## Next permitted milestone

Next permitted milestone: **implement Phase 9C-1** within the accepted
Fake/synthetic, network-free boundary. No Phase 9C-2 or real-provider action is
permitted.
