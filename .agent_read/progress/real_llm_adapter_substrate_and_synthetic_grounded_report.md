# Phase 9C-1 — Real LLM Adapter Substrate and Synthetic Grounded Report

Date: 2026-07-30  
Status: **IMPLEMENTED / NETWORK-FREE VALIDATION**

## Scope and route

ADR 0007 remains **Accepted with limited implementation scope**. This phase
implemented only the provider-independent and synthetic architecture. It did
not install a provider SDK, read or configure a key, call Anthropic/OpenAI/a
local model/OpenAlex, transmit real content, spend money, resume relevance
judging, or authorize Phase 9C-2. The Optional Evaluation Module remains
**DEFERRED**.

## Immutable workflows

- V2 remains `guided-literature-review@2.0.0` with unchanged hash
  `af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`.
- V3 is `guided-literature-review@3.0.0` with hash
  `c103aa95290ed13407cf5fa5e9984bcd9cd0efb7cc5451176b73c6fbcf1cb0ec`.

V3 has a static 12-node DAG:

1. `validate_query`
2. `search_papers`
3. `normalize_and_deduplicate`
4. `rank_and_select`
5. `approve_sources`
6. `load_approved_source_content`
7. `build_grounded_report_input`
8. `summarize_papers_and_extract_evidence`
9. `synthesize_grounded_claims`
10. `compose_grounded_report`
11. `validate_grounded_provenance`
12. `persist_grounded_artifacts`

The first four Skills remain their pinned V2-compatible `@1.0.0` versions
because their semantics are unchanged. All grounded post-approval Skills are
new `@2.0.0` versions. Approval outputs now carry the resolved approval request
ID, fingerprint, status, and timestamp; this additive generic engine/runtime
output lets downstream Skills bind the exact approved action. V2 does not
consume the new fields.

## Contracts and provider boundary

Additive V3 contracts live in `backend/research/contracts/grounded.py` so V2
serialization remains unchanged:

- `GroundedReportInput`
- `PerPaperSummary`
- `GroundedEvidenceUnit` (`EvidenceUnit/v2`)
- `GroundedClaimV2` (`GroundedClaim/v2`)
- `GroundedCitationReference` (`CitationReference/v2`)
- `GroundedResearchReport` (`ResearchReport/v2`)
- `LiteratureCorpus`

All are frozen, canonical-JSON serializable, checksum-bound, and contain no
provider clients, credentials, ORM objects, executable logic, or paths.
`GroundedReportInput` enforces 3–5 ordered papers, one ordered SourceContent per
paper, exact checksum maps, abstract-only scope, and deterministic `[P1]`–`[P5]`
labels.

`StructuredGenerationProvider` is additive to the historical `LLMProvider`.
Requests bind operation/model policy, prompt version/hash, instruction,
untrusted data payload, schema, output/timeout caps, fingerprint, input hash,
and schema version. Results normalize provider/model/snapshot/adapter/request
identity, structured value, raw-retention flag, usage/cost/latency/retry,
finish state, response checksum, and schema version.

## Adapter and prompts

`AnthropicStructuredAdapter` targets `claude-sonnet-5` only as an inactive
protocol substrate. It accepts an injected `AnthropicStructuredTransport`;
there is no SDK, socket/client construction, environment/key lookup, default
live registration, fallback, or raw-response retention.

`SyntheticGroundedProvider` is fixture-driven and supports configured success
or normalized failure. It performs no heuristic judgment over source text and
reports deterministic IDs, usage, checksums, latency, and USD 0.00 cost.

The immutable prompt registry contains:

- `grounded-paper-summary-evidence@1.0.0`
- `grounded-cross-paper-claims@1.0.0`
- `grounded-report-composition@1.0.0`
- `grounded-mechanical-repair@1.0.0`

Hashes are derived from the complete immutable prompt record. Every prompt
declares source delimiters, allowed/prohibited fields, abstract-only scope,
missing-information rules, inference rules, citation constraints, and the rule
that retrieved text is untrusted data rather than instructions.

## Generation, operations, repair, and replay

The successful three-paper fixture executes:

- 3 summary/evidence operations;
- 1 cross-paper claim operation;
- 1 report composition operation;
- 0 repair operations.

There is at most one mechanical repair operation per run. It may repair only
missing/invalid output structure and cannot add papers, citations, evidence, or
claims. A second repair or an invalid repaired structure fails the node.
Evidence-span mismatch and unsupported support IDs are not mechanically
repairable.

Each logical generation call reserves and starts a ProviderOperation before
invocation, normalizes/validates identity and response checksum, settles usage,
then writes a private immutable generation checkpoint. A matching settled
operation reuses the verified checkpoint with no provider call. A settled
operation without a checkpoint or any unsettled operation fails closed rather
than duplicating the call.

Accepted architecture limits are 8 logical generation operations, 11 attempts,
90,000 input tokens, 32,000 output tokens, 20 minutes, one repair, and a USD
1.25 configured cap. Real authorized spend remains USD 0.00. Publication
rechecks attempts, tokens, cost, operation settlement, and complete usage.

## Grounding and publication

The combined per-paper Skill verifies PaperRecord/SourceContent identities and
checksums, sends one approved synthetic abstract, requires unavailable fields
where source information is absent, and checks each private evidence span is an
exact substring no longer than 200 characters.

The synthesis Skill validates category cardinality, evidence and paper IDs,
two-sided disagreement support, and explicit inference flags. Report
composition uses validated structures; Markdown is rendered deterministically
by ReAgent rather than accepted as arbitrary provider Markdown.

`GroundedProvenanceValidator` blocks publication unless the approved order,
source checksums, summary/evidence/claim links, span containment, claim
cardinality, inference labels, citation set/order, abstract disclosure, and
all ProviderOperations are valid. The final persistence Skill also verifies
budget envelopes and writes no artifact before the gate succeeds.

## Artifacts and downstream handoff

The complete immutable set is:

1. `papers.json`
2. `selected_papers.json`
3. `source_content.json`
4. `grounded_report_input.json`
5. `paper_summaries.json`
6. `evidence.json`
7. `claims.json`
8. `report.json`
9. `report.md`
10. `provenance.json`
11. `usage.json`
12. `generation_manifest.json`
13. `literature_corpus.json`

Private spans are not copied into `literature_corpus.json`. The corpus contains
content-minimized summaries, paraphrased evidence, claims, deterministic
citations, inference disclosures, abstract-only scope, and a downstream-use
policy. It is eligible as a future Idea/Writing input only after a later
workflow verifies its checksum and scope; this phase authorizes no downstream
execution.

## Synthetic acceptance evidence

The command is:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.synthetic_grounded_acceptance
```

It uses an ignored artifact root, InMemory persistence, three entirely
fictional papers, exact synthetic approval, five generation calls, deterministic
restart, and no network. The successful architecture evidence was:

- papers/summaries/citations: 3 / 3 / 3;
- EvidenceUnits: 5;
- GroundedClaims: 5 (`CROSS_SOURCE_THEME`, `AGREEMENT`, `DISAGREEMENT`,
  `LIMITATION`, `RESEARCH_GAP`);
- public artifacts: 13;
- generation calls: 5; all ProviderOperations including search: 6;
- replay generation calls: 0;
- actual cost: USD 0.00.

Checksums are stable for replay within the same run. Run IDs are intentionally
opaque, so a separately created run has new run-bound artifact identities.
Synthetic content and metrics demonstrate architecture only, not scientific or
provider quality.

## Validation record

Executed during Phase 9C-1:

- focused V3 tests: initially `12 passed`, then `13 passed` after adding
  partial-retry/reuse coverage;
- research suite before final documentation: `117 passed`;
- first full backend run: `199 passed, 18 skipped, 1 failed` because a historical
  dispatcher test stub did not accept the new optional approval-output keyword;
  compatibility was corrected by omitting the keyword when absent.

Final regression/compile counts are recorded after documentation in the
completion response. Frontend, PostgreSQL, and Docker validation are not
required because no frontend, API DTO, SQL mapping, migration, or dependency
changed.

Final executed results:

- focused V3: `13 passed`, exit 0;
- `backend/research/tests`: `118 passed`, exit 0;
- full `backend`: `201 passed, 18 skipped`, exit 0;
- `python -m compileall -q backend`: exit 0;
- synthetic acceptance command: exit 0.

Final retained acceptance output reported:

- report checksum:
  `sha256:6a5578b61bf741f2d9125ca075b3e46e1fcecd461c29411a8e875a2b546c7094`;
- provenance checksum:
  `sha256:455b0c784f0a978ddb1d0f3464c693e5193175e2b656e7b94ec19be7a27e6f45`;
- literature-corpus checksum:
  `sha256:4c03dcd853a38e7455276669bae4e2b454ce2067c13ad26b9fff51b8f7814b0f`.

## Retention and cleanup

Synthetic generated evidence remains under ignored `runtime_data/`. No tracked
fixture contains real titles, authors, abstracts, DOI/OpenAlex IDs, provider
responses, or credentials. Optional cleanup after owner review:

```bash
rm -rf \
  runtime_data/grounded_v3_dev_acceptance \
  runtime_data/grounded_v3_dev_acceptance_2 \
  runtime_data/grounded_v3_dev_acceptance_3 \
  runtime_data/grounded_v3_dev_acceptance_4 \
  runtime_data/grounded_v3_dev_acceptance_5 \
  runtime_data/grounded_v3_dev_acceptance_6 \
  runtime_data/grounded_v3_dev_acceptance_7 \
  runtime_data/grounded_v3_dev_acceptance_8 \
  runtime_data/grounded_v3_dev_acceptance_9 \
  runtime_data/grounded_v3_synthetic_acceptance
```

These commands target only the named ignored synthetic roots and were not run.

## Phase 9C-2 blockers

Separate owner approval is still required for the real provider/account, exact
model and pinning policy, API key, ZDR/retention, permission to transmit real
abstracts, exactly three approved real papers, non-zero budget, runtime/retry
limits, isolated acceptance storage and retention, report language, and live
acceptance gates.

Next permitted milestone after owner review: **Phase 9C-2 bounded real grounded
report acceptance decision**. No live execution follows automatically.
