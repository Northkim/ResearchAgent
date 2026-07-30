# Real Grounded Literature Report Evidence

Date/access date: 2026-07-30
Status: **Architecture evidence; no real report generated**

## Objective and product boundary

Allowed task:

> Given one owner-approved topic and exactly 3–5 owner-approved papers, use only
> their metadata and bounded abstract-only SourceContent to produce structured
> paper summaries, evidence-linked claims, cross-paper synthesis, and a
> citation-aware report.

The result is useful as an orientation and durable corpus for students,
researchers, and later Idea/Writing workflows. It is abstract-based, not a
full-paper review, systematic review, expert peer review, scientific-correctness
assessment, or exhaustive evidence synthesis.

- A student receives a readable map of approved papers, terms, themes, and
  explicit limitations with direct references.
- A researcher receives inspectable source/checksum/evidence links and clearly
  separated source statements versus tentative system inference.
- A future Idea workflow may consume supported themes and explicitly inferred
  gaps only as hypothesis inputs.
- A future Writing workflow may consume claims/citations/disclosures without
  treating the corpus as full-text evidence.

## Repository evidence

Current code already provides exact selected-set approval and fingerprinting,
PaperRecord/SourceContent, EvidenceUnit/GroundedClaim/CitationReference/
ResearchReport, ProviderOperation reservation and settlement, immutable
artifact storage, provenance validation, report/artifact APIs, frontend
citations, and restart/replay.

The pinned `guided-literature-review@2.0.0` hash is
`af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`.
It must remain unchanged. Its current summary/report skills construct
deterministic fake outputs and do not pass real abstract data through production
prompts. Composition-only adapter selection therefore cannot satisfy this
contract.

**Proposed Class D decision:** add `guided-literature-review@3.0.0` with pinned
`research.*@2.0.0` grounded-generation skills. Preserve V2 and the Fake
provider. A mere execution profile is rejected because it would obscure prompt
and skill semantics; mutating V2 is rejected because it breaks reproducibility.
Owner approval is required; revisit if a code review proves the new semantics
can be expressed without changing any immutable skill behavior.

The future source-content boundary should add a small
`ApprovedAbstractSourceContentProvider` (provisional name) that materializes the
already approved normalized `PaperRecord.abstract` into immutable
`SourceContent` with paper ID, `ABSTRACT` scope, content checksum,
retrieval/provider identity, access limitation, and available license metadata.
It performs no new network request and cannot supply full text. The existing
FakeSourceContentProvider remains the default Fake path.

## Real LLMProvider additive boundary

The existing port already supports provider identity, structured and text
requests/responses, usage, execution context, and cancellation. The smallest
additive contract records exact model snapshot, adapter/prompt/schema versions
and hashes, provider request ID, latency, normalized refusal/error, timeout and
cancellation outcome, retry attempts, request fingerprint/idempotency key, and
actual cost/currency.

The provider accepts one immutable request and returns one normalized result. It
never mutates WorkflowRun, imports SQLAlchemy/FastAPI, reads arbitrary
environment variables, writes artifacts, approves sources, adds citations, or
introduces papers. SDK clients and the one documented secret lookup remain in
adapter/composition boundaries. Skills own research transformations;
ProviderOperationService owns reservation/settlement; application services own
use-case coordination; the API transports state only.

## Generation alternatives

| Alternative | Reliability/provenance | Cost/latency | Recovery | V1 assessment |
|---|---|---|---|---|
| A. one-shot report | weakest evidence and citation control | lowest | entire call repeats | reject |
| B. per-paper summary then synthesis | moderate | moderate | per-paper checkpoint | viable simpler fallback |
| C. summary, evidence, claims, report | strongest explicit links | highest | fine-grained | **proposed** |

V1 applies C with one combined structured summary+evidence operation per paper,
one structured synthesis+claim operation, one Markdown report operation, and at
most one mechanical repair. The schemas/artifacts remain separate even when a
call returns two structures. This reduces calls without hiding provenance.

## Why staged grounding

Primary research establishes risks and useful patterns, not a guarantee:

- abstractive summaries can contain substantial input-unfaithful content;
- retrieval/source access improves factual tasks but does not eliminate
  hallucination;
- citation generation still leaves unsupported claims;
- atomic claim decomposition makes support checking more inspectable;
- long contexts can underuse evidence based on position;
- specialized scientific systems use retrieval, evidence contexts, citations,
  verification/self-feedback, and human evaluation.

For 3–5 abstracts, staged calls, deterministic citation labels, atomic claims,
and a blocking provenance validator directly address these risks. They cannot
establish scientific truth because the inputs themselves are abstracts.

## Evidence hierarchy register

| Evidence | Class | Task/sample | Finding used | Limitation / what it does not prove |
|---|---|---|---|---|
| [Maynez et al., ACL 2020](https://aclanthology.org/2020.acl-main.173/) | B, peer reviewed | large human evaluation of neural summaries | abstractive summaries can hallucinate input-unsupported content | older systems/news domain; no ReAgent model |
| [Lewis et al., NeurIPS 2020](https://papers.nips.cc/paper_files/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html) | B, peer reviewed | knowledge-intensive NLP | retrieved external evidence can improve generation and provenance | not scientific report validation |
| [Gao et al., EMNLP 2023 (ALCE)](https://arxiv.org/abs/2305.14627) | B, peer reviewed | cited long-form QA across datasets | citation correctness/completeness require separate evaluation; best systems still lacked support | web QA differs from fixed approved abstracts |
| [Min et al., EMNLP 2023 (FActScore)](https://aclanthology.org/2023.emnlp-main.741/) | B, peer reviewed | long-form biography facts | atomic facts permit fine-grained support checking | automatic evaluator is not accepted here |
| [Liu et al., TACL 2024](https://aclanthology.org/2024.tacl-1.9/) | B, peer reviewed | multi-document QA/key-value retrieval | relevant-information position affects long-context use | not a summary/report experiment |
| [Rashkin et al., Computational Linguistics 2023 (AIS)](https://direct.mit.edu/coli/article/49/4/777/116438/Measuring-Attribution-in-Natural-Language) | B, peer reviewed | attribution definition/evaluation | source-attributable propositions need identified evidence | human attribution judgment still varies |
| [PaperQA2](https://arxiv.org/abs/2409.13740) | B paper + C system | literature search, summary, contradiction benchmarks | evidence contexts, citation checking, and task-specific human comparison are mature patterns | full-text agent and private infrastructure exceed V1 |
| [OpenScholar, Nature 2026](https://www.nature.com/articles/s41586-025-10072-4) | B, peer reviewed + C system | 2,967 queries, 208 long answers, 16 expert evaluators | retrieval, citations, self-feedback, and domain evaluation materially affect synthesis | 45M-paper datastore/full-text system is not ReAgent |
| `ACADEMIC_RESEARCH_SKILLS_INFLUENCE_MAP.md` | C, pinned repositories | staged research workflow | instruction/data separation, claim gates, provenance, human checkpoints | CC BY-NC code/prompts must not be copied |

## Class D decision discipline

Every number in the input, prompt, cost, retention, and acceptance documents is
a ReAgent proposal. Rationale is bounded V1 usefulness; evidence is the staged
patterns above and current repository constraints; alternatives include fewer
papers/calls, one-shot generation, local-only generation, or deferral.
Tradeoffs are cost/latency versus auditability. Owner approval is mandatory.
Revisit after the first Fake vertical slice, any provider-contract change, or
the bounded real acceptance.

## Route

The optional Judge module is Deferred. Grounded report generation does not
perform automatic relevance screening: the owner approves the exact paper set
first. No LLM/OpenAlex call, real abstract summary, report, relevance label, or
retrieval metric was produced in Phase 9C-0.

## Phase 9C-1 implementation evidence

ADR 0007's limited scope is now implemented with network-free synthetic data.
The immutable V3 hash is
`c103aa95290ed13407cf5fa5e9984bcd9cd0efb7cc5451176b73c6fbcf1cb0ec`;
the V2 hash remains unchanged. Additive V3 contracts preserve historical V2
serialization. A provider-independent structured-generation port, immutable
prompt registry, fixture-driven synthetic provider, and inactive
transport-injected Anthropic `claude-sonnet-5` protocol adapter now exist.

The successful synthetic path used three fictional papers, five grounded
evidence units, five category-checked claims, three deterministic citations,
five generation calls, thirteen artifacts, zero cost, and zero generation calls
on completed replay. These are architecture-test facts, not evidence about
Anthropic, scientific quality, retrieval quality, or real-report usefulness.
No real API, key, title, abstract, identifier, or response was used.
