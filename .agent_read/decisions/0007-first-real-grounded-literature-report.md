# ADR 0007: First Real Grounded Literature Report

Status: **Deferred by ADR 0009 — Optional Hosted Mode**
Date: 2026-07-30
Owner: ReAgent owner

## Route deferment record — 2026-08-03

This ADR originally authorized only the Phase 9C-1 Fake/synthetic grounded-
report substrate and explicitly withheld real provider calls, credentials,
abstract transmission, and spending. That historical implementation decision
and all verified evidence remain preserved.

ADR 0009 now governs the initial V1 product boundary: an existing Claude Code
or Codex Agent Harness executes concrete research from an authoritative local
Workflow Package, while the cloud manages packages, progress, credentials, and
API proxy operations. Continuing V3 as a default backend-executed research
Workflow or activating hosted report generation would conflict with that
owner-approved boundary. Hosted activation and further hosted product
development are therefore deferred to an optional future Hosted Mode requiring
separate owner authorization.

Reusable parts remain in scope for later teacher-aligned work: immutable
grounded summary/evidence/claim/citation/report contracts, prompts,
abstract-only disclosures, approval/checksum concepts, artifact schemas,
synthetic fixtures, ProviderOperation accounting, and fail-closed provenance
validators. They may be repackaged as local Literature Search Skills/contracts,
run as deterministic folder-side tooling, or validate explicitly uploaded
outputs cloud-side. Cloud validation does not authorize cloud generation.

No Phase 9C real call, hosted LLM activation, backend report execution,
browser-triggered research continuation, API-key use, abstract transmission, or
spend is authorized for teacher-aligned V1. Existing code, immutable Workflow
hashes, tests, and historical text below are not rejected or deleted.

## Owner decision — limited acceptance

The owner accepted this ADR for Phase 9C-1 with the following exact boundary.
Acceptance authorizes implementation of the Fake/synthetic substrate; it does
not authorize a real provider call, credential, real abstract processing, or
spend.

### Approved for Phase 9C-1

1. Create immutable `guided-literature-review@3.0.0`.
2. Preserve `guided-literature-review@2.0.0` unchanged.
3. Use staged generation:
   - one summary/evidence call per paper;
   - one cross-paper synthesis/claim call;
   - one report-generation call;
   - at most one repair call.
4. Support exactly 3–5 approved papers.
5. Use abstract-only `SourceContent`.
6. Implement `GroundedReportInput`, `PerPaperSummary`, `EvidenceUnit`,
   `GroundedClaim`, `CitationReference`, and `ResearchReport` contracts.
7. Require deterministic `[P1]`, `[P2]` citation labels.
8. Implement fail-closed provenance publication gates.
9. Implement immutable report and literature-corpus artifacts.
10. Use Anthropic `claude-sonnet-5` as the first adapter target.
11. Run only Fake and synthetic network-free tests.
12. Preserve the Optional Evaluation Module as **DEFERRED**.

“First adapter target” authorizes an adapter boundary and synthetic contract
tests only. It does not authorize installing an SDK, configuring a key, or
calling Anthropic.

### Deferred and not authorized

- real Anthropic API calls;
- API-key configuration;
- transmission of real abstracts;
- non-zero spending;
- real OpenAlex report generation;
- live provider acceptance;
- automatic provider fallback;
- provider comparison;
- full-text or PDF processing;
- relevance judging;
- downstream Idea or Writing execution.

### Separate Phase 9C-2 approval required

Phase 9C-2 remains prohibited until a later owner decision explicitly covers:

- API key and provider account;
- data retention or ZDR;
- abstract transmission;
- budget;
- exactly three-paper live sample;
- retention duration;
- live acceptance gates.

## Context and route change

ReAgent can discover real OpenAlex papers, bind exact owner approval, persist
artifacts/operations, validate provenance, and reload reports through API/UI.
The strongest path still uses FakeSourceContentProvider and FakeLLMProvider for
summary and report generation.

The automated-relevance Judge module is technically valid but not required for
the first useful product version. ADR 0006 is Deferred, not rejected. Its code,
tests, evidence, calibration design, and review packets remain preserved.

## Problem and product goal

Define the smallest safe path from one approved topic and exactly 3–5 approved
OpenAlex papers with abstract-only SourceContent to structured summaries,
EvidenceUnits, GroundedClaims, cross-paper synthesis, deterministic citations,
a Markdown report, provenance, usage, and a reusable literature corpus.

The report is abstract-based orientation: not full-paper review, systematic
review, expert peer review, or scientific-correctness evidence.

## Decision drivers and evidence

- exact approved-source binding and owner control;
- source-only generation and untrusted-data separation;
- recoverable stages and immutable replay;
- deterministic citation identifiers and fail-closed provenance;
- current provider identity, structured output, ZDR, usage, and cost;
- durable downstream handoff without premature Idea/Writing implementation;
- preservation of workflow/skill immutability.

Primary research documents unfaithful summarization, incomplete citation
support, atomic-support benefits, long-context position effects, and the value
of retrieval/evidence/citation/verification stages. PaperQA2, OpenScholar, and
Academic Research Skills provide Class C staged/provenance patterns, not code or
prompts to copy. See `REAL_GROUNDED_REPORT_EVIDENCE.md`.

## Proposed decision

Under the limited owner approval above, create a new immutable
`guided-literature-review@3.0.0` and pinned grounded-generation skills. Keep
`guided-literature-review@2.0.0` and its hash unchanged. A composition-only
adapter swap is insufficient because current V2 skills construct fake outputs
and do not implement the approved-source prompt/data contract.

Add a narrow approved-abstract SourceContent adapter/service that converts only
the approved normalized OpenAlex PaperRecord abstract into checksummed
`ABSTRACT` SourceContent. It makes no additional provider request, retains
available access/license metadata, never yields full text, and does not replace
the default FakeSourceContentProvider.

Use staged generation:

1. validate exact approved source set;
2. load PaperRecords and abstract-only SourceContent;
3. for each paper, one structured summary+evidence operation;
4. one structured cross-paper claim/synthesis operation;
5. one citation-aware Markdown report operation;
6. optional one mechanical schema repair;
7. deterministic provenance/publication validation;
8. immutable artifacts, API/UI publication, restart/reload.

Summary and evidence are distinct schemas/artifacts even when returned by one
call. No stage may introduce a paper or citation outside the input.

## Proposed provider/model

Primary: Anthropic `claude-sonnet-5`, a canonical pinned model ID with
structured outputs and an eligible ZDR path. Fallback/comparison:
`gpt-5.6-terra` only through a separate owner decision. Local `gpt-oss-20b`
remains a development/privacy alternative, not the initial multilingual
acceptance.

The adapter target is accepted for Fake/synthetic Phase 9C-1 implementation,
not as measured quality evidence. Provider account, key, ZDR, region, abstract
permission, live use, and spend remain unapproved.

## Approved-source contract

`GroundedReportInput/v1` binds project/run/workflow, selected artifact and
checksum, approval/fingerprint, ordered PaperRecord and SourceContent
IDs/checksums, citation mapping, query hash, disclosure, prompt/skill/provider
policy, budgets, and canonical checksum. Any change, duplicate DOI, unknown
label, unsettled search operation, or invalid approval stops before a call.

## Summary, evidence, claim, and report

- `PerPaperSummary/v1` represents objective, explicit methodology/findings/
  limitations/contribution/topic linkage, uncertainty, and evidence IDs.
  Missing abstract information is unavailable, never guessed.
- `EvidenceUnit/v2` binds a short exact private span or paraphrased statement to
  SourceContent checksum/locator and supported claims.
- `GroundedClaim/v2` categories are source summary, cross-source theme,
  agreement, disagreement, limitation, research gap, and system inference.
  Cross-source claims need at least two papers; inferred gaps are tentative.
- `ResearchReport/v2` has stable required sections, `[P1]` citations from the
  approved order, abstract-only/systematic-review disclaimers, deterministic
  references, and generation/provenance identity.

Unsupported claims and unknown citations fail; they are not published with a
warning.

## Prompt versioning

Freeze five registry records: per-paper summary, evidence extraction,
cross-paper synthesis, report Markdown, and mechanical repair. Each has an
immutable version/hash, explicit schemas, source-data delimiter, citation and
inference rules, allowed/prohibited fields, language, and known risks.
Retrieved content is untrusted data and never system instruction.

## Provenance publication gate

Publication requires exact approved set and source checksums, known summaries/
evidence/claims/citations, valid spans and bidirectional support, no duplicate
DOI/unapproved source/unsupported claim, marked inference, disclosures and all
version identities, settled operations, linked report/provenance checksums, and
successful immutable artifact writes. Any failure blocks completed status.

## Artifacts

| File | Kind / visibility | Purpose |
|---|---|---|
| `papers.json` | existing, user | normalized approved metadata |
| `selected_papers.json` | existing, user | exact approved order/checksum |
| `source_content.json` | private/controlled | abstract-only source records |
| `paper_summaries.json` | user after gate | structured summaries |
| `evidence.json` | controlled/user metadata | evidence statements/locators |
| `claims.json` | user after gate | grounded/inference-labelled claims |
| `report.md` | user/downloadable if approved | rendered report |
| `provenance.json` | user/audit | complete linkage/validation |
| `usage.json` | user/audit | calls/tokens/cost/latency |
| `generation_manifest.json` | audit | input/prompt/model/operation/artifact IDs |
| `literature_corpus.json` | downstream after separate approval | stable Idea/Writing handoff |

All use schema versions, SHA-256, immutable relative keys, DB ArtifactMetadata,
and checksum replay. Raw HTTP is never retained.

## ProviderOperation and cost

At most five paper operations, one synthesis, one report, and one repair:
8 logical calls, 11 attempts, 90k input/32k output tokens, 20 minutes, and
USD 1.25 hard cap. Standard Sonnet 5 upper-bound token price is USD 0.75 before
tax/variation. These are Proposed Class D limits; current budget is USD 0.00.
Reservations are worst-case, retries share the cap, missing usage or unsettled
operations block progress, and replay makes no provider call.

## Data processing, retention, and security

Hosted input is limited to topic, run-scoped ID/label, title, bounded abstract,
year, venue, disclosure, rubric, and schema. Exclude identifiers unnecessary to
the model, ranks, citation counts, notes, paths, raw responses, and secrets.
ZDR for the exact account/model/feature and explicit abstract-processing
permission are blocking. Real work is trusted single-user supervised because
the platform has no authentication.

Proposed local terms: abstracts 30 days; canonical requests/responses 14 days;
failed partials 7 days; published report/corpus/provenance/operation metadata
12 months or project deletion; sanitized logs 30 days; isolated acceptance
DB/root 30 days. Real content is never committed.

## Application/API/frontend impact

Prefer extending existing run/report/artifact/usage read APIs and the existing
run execution/resume path. Add only if absent: generation status and an explicit
retry use case. Proposed application use cases are
`GenerateGroundedReport`, `GetReportGenerationStatus`,
`GetGenerationUsage`, and `RetryFailedGeneration`; no router owns research
logic.

Minimal UI: generation state, per-paper summaries, report/citations,
provenance status, usage/cost, abstract-only warning, bounded retry/failure, and
existing artifact downloads. Remove fake/synthetic wording only in the new
profile; no broad redesign.

## Testing and sequence

- pure contract tests, no network;
- deterministic Fake LLM vertical slice in normal suite;
- recorded synthetic provider fixtures with no real content;
- opt-in isolated real acceptance only after all approvals.

Phase 9C-1 implements the provider-independent real adapter substrate and Fake/
synthetic validation. Phase 9C-2 accepts three real approved abstracts through
per-paper summary/evidence only. Phase 9C-3 adds real synthesis/report,
publication gate, API/UI, restart and zero-call replay.

## Alternatives

- Keep V2 and swap adapter: rejected; fake-oriented skill semantics remain.
- Same workflow with execution profile: insufficient audit identity.
- One-shot report: lower cost, weak support and recovery.
- Summary then synthesis only: viable fallback, but implicit evidence links.
- Fully separate call for every intermediate: strongest granularity, excessive
  V1 calls.
- Local first or defer hosted: privacy-safe alternatives with delayed value.

## Consequences and risks

Positive: explicit approvals, inspectable evidence, citation safety, staged
recovery, durable corpus. Costs: new immutable workflow/skills, more calls and
schemas, synchronous latency, retention cleanup, and UI disclosure work.
Residual risks: abstract incompleteness/rights, hallucination despite schemas,
model drift, multilingual variance, provider retention/region, no auth,
synchronous execution, and model-generated gaps being overread.

## Revisit triggers

Provider/model/price/retention/deprecation change; prompt/schema/version change;
rights or security incident; first Fake/live acceptance; more than five papers;
full text; multi-user deployment; unacceptable latency/cost/citation failures;
resumption of evaluation module.

## Owner approvals required beyond Phase 9C-1

| Decision | Recommendation | Alternatives | Consequence / blocking |
|---|---|---|---|
| live provider/model use | Anthropic / `claude-sonnet-5` | Terra; local; defer | blocks Phase 9C-2 calls, not Phase 9C-1 adapter work |
| fallback/comparison | disabled initially | one approved Terra comparison | blocks comparison only |
| key/ZDR/region | scoped server key + verified exact-feature ZDR/region | local; defer | blocks hosted calls |
| real abstract permission | permit approved bounded abstracts | synthetic/local only | blocks real acceptance |
| live abstract limit | 12,000 chars/paper | 8,000; approved excerpt | blocks Phase 9C-2 payload |
| Phase 9C-2 sample | exactly 3 papers | defer | blocks real acceptance |
| live report language | English, preserve titles | owner/source language | blocks live prompt manifest |
| evidence/quote | private ≤200 chars/25 words; paraphrase in report | no span; visible excerpt | blocks live rights/UI contract |
| live retries | 11 attempts maximum, one repair | stricter/no repair | blocks real operations |
| tokens/cost/runtime | 90k/32k, USD 1.25, 20 min | lower/zero/defer | blocks any spend |
| retention | policy durations above | shorter/immediate deletion | blocks real data |
| isolated acceptance storage | retain 30 days | ephemeral | blocks acceptance setup |
| downloads | report/corpus after gate | view only | blocks UI acceptance |
| corpus downstream use | allow only with new approval | do not expose | blocks future consumption, not V1 |
| full text | remain prohibited | separate future ADR | scope invariant |

## Explicit exclusions

No real LLM call, API-key configuration, real abstract transmission, non-zero
spend, full-text/PDF processing, automatic relevance Judge, full-pool
screening, provider fallback/comparison, real OpenAlex report, downstream
Idea/Writing execution, live provider acceptance, authentication/workers/
Redis/S3, or production deployment is authorized by this limited acceptance.
