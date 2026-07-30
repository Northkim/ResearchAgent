# Automated Relevance Judge Evidence

Date: 2026-07-29  
Phase: 9B-2C-0 contract, updated by Phase 9B-2C-3A
Decision status: Proposed; Fake substrate verified, no real judge selected or authorized

## Evaluation objective

ReAgent distinguishes two kinds of evaluation.

**Expert Gold Evaluation** requires qualified domain experts, validated relevance
criteria, independent judgments, adjudication, and formal gold labels. It remains
the appropriate method for a systematic review, publishable benchmark, or claim
of expert ground truth.

**Automated Silver-label Evaluation** uses a versioned automated judge, an
explicit topical-relevance rubric, repeated judgments, consistency aggregation,
and targeted human audit. Phase 9B-2C proposes only:

> Automated silver-label relevance evaluation with targeted human audit.

It is not expert ground truth, scientific peer review, methodological-quality
assessment, a definitive paper-quality ranking, or a systematic-review gold
standard.

The judge may assess only topical relevance from the supplied title and abstract
preview: whether the topic is primary, substantial, secondary, absent, or cannot
be judged. It must not assess scientific-method correctness, experimental
credibility, novelty, venue quality, causal validity, factual truth of claims, or
overall scientific merit.

## Evidence hierarchy

- **Class A:** official provider/API/model/licensing/security documentation.
- **Class B:** primary peer-reviewed research or a clearly identified primary
  preprint.
- **Class C:** mature open-source implementation evidence.
- **Class D:** ReAgent engineering policy or owner choice. Class D is not an
  external fact and requires owner approval where stated.

## Research findings

The evidence supports using LLM judgments as a bounded, auditable proxy, not as a
drop-in replacement for experts:

- Relevance-assessment research describes a spectrum of human-machine
  collaboration and explicitly preserves concerns about fully automated labels.
- Pointwise relevance judgments are simple and independently auditable.
  Pairwise ranking can add a useful local ordering-consistency signal, but it is
  not uniformly superior and can amplify superficial preferences.
- Repeated equivalent prompts can expose prompt sensitivity. Agreement is
  evidence of stability under the tested prompts, not evidence that the agreed
  label is true.
- Pairwise comparisons exhibit position bias; reversing candidate order is
  therefore required for any pairwise signal used to block automation.
- Judges can show position, verbosity, leniency, and self-enhancement or
  self-preference effects. A judge must not see provider rank, citation count,
  another judge's answer, or irrelevant prestige signals.
- Multilingual judge consistency varies substantially by language. Provider
  claims of multilingual support do not establish reliable multilingual
  relevance judgment for ReAgent's topic and rubric.
- Human assessors also disagree. Human audit is a correction and calibration
  layer for silver labels; it does not become expert gold merely because a
  non-expert owner reviewed it.
- Model behavior may drift with aliases, serving infrastructure, safety systems,
  or deprecation. Provider/model/adapter/prompt/schema identities and checksums
  are therefore evaluation inputs, not incidental telemetry.

## Proposed multi-run strategy

All values in this section are **Class D ReAgent project policy proposals** and
are unapproved.

| Strategy | Expected reliability | Cost / latency | Complexity | Known bias | Reproducibility / provider need |
|---|---|---|---|---|---|
| One pointwise run | Lowest; no instability signal | 1 call; lowest | Low | prompt framing, leniency, model bias | pinned model identity, schema output |
| Two repeated identical pointwise runs | Detects stochastic instability but not wording sensitivity | 2 calls | Low | correlated errors | deterministic controls where supported; exact request hash |
| Pointwise A + equivalent prompt-paraphrase B | Preferred V1 base; exposes framing sensitivity | 2 calls | Medium | correlated model-family errors; rubric-option order | immutable prompt A/B versions and hashes |
| Selected neighboring pairwise comparison | Useful contradiction signal near a ranking boundary | selected extra calls only | Medium | position and superficial-comparison bias | run both candidate orders; exact pair-selection policy |
| Full pairwise/listwise reranking | Potential ranking signal, but expensive and bias-prone | quadratic or large-list cost | High | position, order, verbosity | not proposed for V1 |
| Independent model families | Better correlated-error diagnostic | higher integration and cost | High | judges can share training/data biases | optional calibration, not a V1 requirement |
| Self-consistency with three or more full runs | More samples can stabilize a mode | at least 3 calls/candidate | Low-medium | repeated correlated error can look confident | not silently required; only after validation |

Initial flow:

1. Pointwise run A uses `relevance-pointwise-a/v1`.
2. Pointwise run B uses `relevance-pointwise-b/v1`, an equivalent rubric with a
   separately frozen prompt structure and balanced label-order presentation.
3. A deterministic policy selects limited neighboring candidates for pairwise
   consistency. Each selected pair is shown in both orders. Pairwise output can
   create a conflict and route to human review; it cannot create the final
   relevance label.

The implementation must use the lowest variability settings the chosen model
officially supports. A seed must never be claimed when the provider does not
support one. Claude Sonnet 5 rejects non-default sampling parameters; the
proposed design must therefore rely on pinned identity, immutable prompts, and
repeat measurement rather than a fictitious temperature/seed guarantee.

## Conceptual architecture

### Fit with the inspected repository

The current evaluation package is pure and separate from runtime state. Its
frozen dataclasses cover topics, candidates, human judgments, adjudication, runs,
and metrics; canonical JSON/checksums and identity-bound import already provide
the right immutability pattern. Candidate generation already reuses
`PaperSearchProvider`, `ProviderOperationService`, and `ArtifactContentStorage`.
Metrics/report code currently describes human labels only, so a later
implementation must add distinct silver artifacts/metric names rather than
silently feed automated labels through `CandidateJudgment`.

The current `LLMProvider` exposes identity, text/structured generation,
cancellation, response schema, prompt name/version, usage, actual provider/model
identity, finish state, and provider reference. `FakeLLMProvider` supplies a
network-free deterministic test adapter. Existing research prompts use immutable
name/version values and propagate prompt version in provenance, but there is no
judge-specific prompt-hash/rubric/language registry. The proposed judge port and
registry are therefore additive semantic controls; they do not replace or widen
the generic LLM transport port.

Skill capabilities are injected deny-by-default. Automated evaluation should not
become a research Skill capability because it evaluates a frozen candidate pool
outside workflow execution. This also prevents a judge from modifying
`WorkflowRun` or gaining paper-search/source-content authority.

### AutomatedRelevanceJudge

A provider-independent evaluation port:

- accepts exactly one immutable, versioned `AutomatedJudgmentRequest`;
- returns one schema-validated `AutomatedJudgment`;
- exposes provider, model/snapshot, and adapter identity;
- reports usage, provider request ID, latency, and normalized errors;
- supports timeout and cancellation;
- never mutates evaluation state.

The semantic judge port may be adapted through the existing `LLMProvider`
transport contract, but it must not be a generic research Skill. Provider SDKs
remain in adapters and composition. The judge must not access SQLAlchemy,
FastAPI, `WorkflowRun`, arbitrary environment variables, OpenAlex rank, citation
count, or another judge's output.

### JudgePromptRegistry

An immutable registry of prompt version, rubric version, language variant,
canonical content, and SHA-256 hash. Runtime mutation is prohibited. A prompt
change creates a new version; it never edits a completed run's identity.

### Artifact and operation storage

The smallest additive design is:

- current `ArtifactContentStorage` for canonical request, judgment, consensus,
  audit request/result, and report artifacts;
- an evaluation-private append-only checksum journal for artifact references and
  state transitions;
- current `ProviderOperationService` and evaluation journal for reservation,
  attempts, settlement, request IDs, usage, cost, and unsettled-operation checks.

No database table or new persistence port is justified at this phase. Revisit
only if concurrent writers, indexed cross-evaluation queries, access-control, or
retention deletion cannot be satisfied by the current artifact boundary.

## Failure and security boundary

Fail closed to `NEEDS_HUMAN_REVIEW` or stop the evaluation when:

- a reservation exceeds an owner-approved monetary/call/token budget;
- the token estimate exceeds its cap;
- a model is unavailable or its identity is not the approved identity;
- schema-constrained output repeatedly fails;
- a required run is absent or unsettled;
- provider usage or request identity is missing;
- a judgment remains inconsistent;
- a metadata warning blocks automated disposition.

API keys are server-side adapter inputs, never request artifacts, prompts,
reports, logs, or source control. Abstract previews are untrusted third-party
content and are delimited as data. Prompt injection in a paper title or abstract
must not alter judge instructions.

## Cost-policy proposal

These are **Class D ReAgent project policy proposals**, not provider limits and
not approved spending authority.

| Limit | Proposed pilot value |
|---|---:|
| Candidates | 40 |
| Pointwise logical calls | 2 per candidate; 80 total |
| Pairwise logical calls | 10 total: 5 selected pairs in both orders |
| Total logical judge calls | 90 |
| Total provider attempts, including retries | 100 |
| Input tokens per pointwise request | 4,000 |
| Output tokens per judgment | 512 |
| Aggregate input tokens | 360,000 |
| Aggregate output tokens | 46,080 |
| Runtime | 15 minutes |
| Retry attempts | 1 retry for a transient failure; no retry for policy/schema-invalid input |
| Failure budget | stop at 5 failed attempts or 2 candidates lacking required runs |
| Random human audit | 10% of high-confidence consensus, deterministic; overall audit cap 20 items |
| Current authorized monetary budget | **USD 0.00** |
| Proposed low-cost pilot envelope | **up to USD 1.00 only after explicit owner approval** |

Provider context windows and account rate limits are provider-imposed
constraints. Token/call/runtime/failure limits above are ReAgent policy. The
monetary reservation must use current official model prices at execution time;
missing usage makes settlement fail closed.

## Data retention

The judge receives only the frozen topic contract, title, bounded abstract
preview, and minimal metadata. Full abstracts and candidate rank/citation data
are excluded. ReAgent should retain canonical request/judgment metadata,
checksums, short supporting spans, reasons, usage, and provider request IDs under
the evaluation retention policy. Permitted abstract-preview retention and hosted
provider use remain owner decisions.

OpenAI states API data is not used for training by default; default abuse logs
may be retained up to 30 days and Responses application state has endpoint-
specific behavior. Anthropic states API inputs/outputs are normally deleted
within 30 days, with contractual ZDR exceptions; its structured-output schemas
may be cached temporarily. These are current official contracts, not guarantees
for every account configuration. The implementation milestone must re-check the
chosen endpoint, account, region, and ZDR eligibility.

## Primary research sources

| Source | Organization | URL | Class | Publication / update date | Access date | Supported claim | Limitation |
|---|---|---|---|---|---|---|---|
| Faggioli et al., “Perspectives on Large Language Models for Relevance Judgment” | ACM ICTIR authors | https://arxiv.org/abs/2304.09161 | B, primary conference paper/preprint | 2023-04-18; ICTIR 2023 | 2026-07-29 | automated relevance judgment needs an explicit human-machine boundary | early models and a preliminary experiment |
| Sun et al., “Is ChatGPT Good at Search?” | ACL / EMNLP | https://aclanthology.org/2023.emnlp-main.923/ | B, peer-reviewed primary research | 2023-12 | 2026-07-29 | LLM pointwise/pairwise/listwise relevance ranking is empirically testable | passage-ranking setup differs from paper title/abstract review |
| Qin et al., “Large Language Models are Effective Text Rankers with Pairwise Ranking Prompting” | ACL / NAACL Findings | https://aclanthology.org/2024.findings-naacl.97/ | B, peer-reviewed primary research | 2024-06 | 2026-07-29 | pairwise comparison can be a useful ranking signal | benchmark ranking gains do not validate ReAgent labels |
| Zheng et al., “Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena” | NeurIPS | https://proceedings.neurips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html | B, peer-reviewed primary research | 2023-12 | 2026-07-29 | position, verbosity, and possible self-enhancement bias; human/LLM disagreement | evaluates assistant responses, not scholarly relevance |
| Shi et al., “Judging the Judges: A Systematic Study of Position Bias” | ACL / IJCNLP-AACL | https://aclanthology.org/2025.ijcnlp-long.18/ | B, peer-reviewed primary research | 2025-12 | 2026-07-29 | pairwise order reversal is necessary to expose position inconsistency | task/model findings are not universal |
| Liu et al., “Judge as A Judge” | ACL Findings | https://aclanthology.org/2025.findings-acl.301/ | B, peer-reviewed primary research | 2025-07 | 2026-07-29 | judge outputs can be prompt-sensitive and inconsistent | RAG-output evaluation, not paper relevance |
| Fu and Liu, “How Reliable is Multilingual LLM-as-a-Judge?” | ACL / EMNLP Findings | https://aclanthology.org/2025.findings-emnlp.587/ | B, peer-reviewed primary research | 2025-11 | 2026-07-29 | multilingual judgment consistency varies by language and can be low | generation-evaluation tasks, not Chinese paper discovery |
| Karpinska et al., “LLMs instead of Human Judges?” | ACL | https://aclanthology.org/2025.acl-short.20/ | B, peer-reviewed primary research | 2025-07 | 2026-07-29 | judge reliability varies by task, property, and human expertise | aggregate study does not set a ReAgent threshold |
| Hashemi et al., “LLM-Rubric” | ACL | https://aclanthology.org/2024.acl-long.745/ | B, peer-reviewed primary research | 2024-08 | 2026-07-29 | explicit rubrics and calibration matter; humans also disagree | trained calibration method is outside V1 scope |

## Provider sources

Dynamic provider details are maintained in
`LLM_JUDGE_PROVIDER_MATRIX.md`. Every dynamic provider claim there is tied to an
official Class A source and must be reverified before implementation.

## Phase 9B-2C-3A calibration boundary

The Fake Judge substrate is verified, but synthetic metrics remain architecture
evidence only. Proposed ADR 0006 adds a required calibration gate before any
real candidate may be judged:

- 12 private real candidates across two English and one multilingual topic,
  plus three synthetic adapter canaries;
- pointwise A/B for all 15 request candidates;
- three real candidate pairs in mirrored order;
- a blinded primary human reference with targeted secondary checking;
- literal supporting-span containment, exact model/request/usage identity,
  ProviderOperation settlement, and zero-call replay;
- separate code acceptance, calibration acceptance, and full-pool permission.

The proposed calibration provider is now Anthropic `claude-sonnet-5` because the
current official contract identifies its canonical ID as a fixed snapshot.
OpenAI `gpt-5.6-terra` remains a fallback because its current page did not expose
a distinct dated pin. This is an unapproved Class D reproducibility choice, not
provider-quality evidence.

Current authorization still permits no real Judge call, hosted abstract-preview
processing, API key, non-zero spend, live-candidate selection/labeling, human
label import, or full-pool judgment. See:

- `REAL_JUDGE_CALIBRATION_EVIDENCE.md`;
- `REAL_JUDGE_CALIBRATION_PROTOCOL.md`;
- `REAL_JUDGE_PASS_FAIL_GATES.md`;
- `.agent_read/decisions/0006-bounded-real-judge-calibration.md`.
