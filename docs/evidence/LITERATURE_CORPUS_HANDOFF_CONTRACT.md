# Literature Corpus Handoff Contract

Status: **Proposed `LiteratureCorpus/v1`**
Date: 2026-07-30

`literature_corpus.json` is the stable, machine-readable output for future Idea,
Writing, Review, and Reproduction/Experiment workflows. It is not itself an
authorization to run any downstream workflow.

## Content

- corpus ID, project/run/workflow/input checksums and schema version;
- research topic/query hash and abstract-only disclosure;
- ordered approved-paper descriptors and deterministic citation labels;
- PaperRecord/SourceContent references and checksums, not embedded full
  abstracts;
- validated per-paper summaries and missing-information flags;
- EvidenceUnit paraphrases, locators, hashes, and content scope;
- GroundedClaims, categories, support links, inference flags, and limitations;
- CitationReferences and validated safe source links;
- report/provenance/usage/generation-manifest artifact references/checksums;
- provider/model/adapter/prompt/skill/workflow identities and timestamps.

It excludes keys, raw HTTP, full prompts/responses, long verbatim spans, ranks,
citation counts, unapproved papers, unsettled outputs, and hidden reasoning.

## Integrity and downstream use

Canonical JSON and SHA-256 bind every collection in deterministic order. The
corpus is written only after the report publication gate. A future consumer
must verify its checksum/schema/provenance, show the abstract-only limitation,
and obtain a separate owner approval/fingerprint. It may not silently retrieve
new sources, reinterpret inference as source fact, or use corpus confidence as
scientific truth.

Future Idea may consume supported themes/gaps as hypotheses; Writing may consume
claims/citations with disclosures; Review may inspect evidence links;
Reproduction may use only explicitly source-stated methodology and must mark
missing details. None is implemented or authorized here.

## Artifact policy

Artifact kind `research.literature_corpus`, media type
`application/vnd.reagent.literature-corpus+json`, immutable relative storage
key scoped to project/run/input checksum. It is user-visible and downloadable
only after owner approval, retained with the final report, and replayed by
checksum without a provider call.

Any source/report correction produces a new corpus ID/version; published bytes
are never overwritten.

## Complete artifact set

All storage keys are relative, project/run/input-checksum scoped, immutable, and
represented by existing database ArtifactMetadata. Unless stated otherwise,
replay verifies bytes/checksum and makes no provider call.

| File | Kind / media / schema | Content and visibility | Retention / downstream |
|---|---|---|---|
| `papers.json` | `research.paper_records`; vendor JSON; v1 | normalized metadata; user | 30 days with real abstracts excluded or redacted |
| `selected_papers.json` | `research.selected_papers`; vendor JSON; v1 | approved ordered IDs/checksums; user/download | report lifetime; approval input |
| `source_content.json` | `research.source_content`; vendor JSON; v1 | abstract records/checksums; private controlled | 30 days; never committed |
| `paper_summaries.json` | `research.paper_summaries`; vendor JSON; v1 | validated structured summaries; user after gate | 12 months; corpus input |
| `evidence.json` | `research.evidence`; vendor JSON; v2 | statements/locators/private short spans; controlled | 12 months; corpus omits private spans |
| `claims.json` | `research.grounded_claims`; vendor JSON; v2 | support-linked claims/inference flags; user | 12 months; report/corpus input |
| `report.md` | `research.report`; `text/markdown`; v2 | final validated report; user/download if approved | 12 months |
| `provenance.json` | `research.provenance`; vendor JSON; v2 | full identity/link/gate result; user/audit | report lifetime |
| `usage.json` | `research.provider_usage`; vendor JSON; v1 | calls/tokens/cost/latency, no content; user/audit | report lifetime |
| `generation_manifest.json` | `research.generation_manifest`; vendor JSON; v1 | input, prompt, operation and artifact checksums; audit | report lifetime |
| `literature_corpus.json` | `research.literature_corpus`; vendor JSON; v1 | stable content-minimized handoff; user/download if approved | report lifetime; future approved workflows |

Each artifact metadata record includes media type, schema version, byte length,
SHA-256, storage key, producing run/step/skill, visibility, creation time, and
retention expiry. No raw response is an artifact.
