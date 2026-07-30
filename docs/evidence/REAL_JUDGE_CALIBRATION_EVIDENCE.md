# Real Judge Calibration Evidence

Date: 2026-07-29
Phase: 9B-2C-3A
Decision status: Proposed; design evidence only

## Narrow objective

The only allowed Judge task is:

> Based only on the supplied research topic, title and bounded abstract preview,
> determine whether the paper topically addresses the stated topic.

The allowed outcomes are direct/high topical relevance, substantial relevance,
partial relevance, non-relevance, and insufficient information. The Judge may
not assess scientific correctness, methodology quality, experimental
credibility, novelty, venue quality, citation impact, factual truth, causal
validity, overall scientific merit, or whether the paper should be trusted as
final evidence.

Calibration is required because schema capability and general multilingual
claims do not establish that a particular provider/model/prompt behaves
reliably on this five-label task. A bounded calibration must expose prompt
sensitivity, repeated-run instability, unsupported evidence, position bias,
multilingual variance, human disagreement, token/cost behavior, and operation
failures before any live pool can be judged.

Passing a code test is not calibration acceptance. Passing calibration is not
permission to judge the full OpenAlex pool.

## Evidence hierarchy

- **Class A:** official provider contracts; dynamic facts in
  `REAL_JUDGE_PROVIDER_MATRIX.md`.
- **Class B:** primary research below.
- **Class C:** mature evaluation practice. ReAgent already follows immutable
  prompts, artifact checksums, operation settlement, replay, and human override.
- **Class D:** ReAgent sample sizes, budgets, thresholds, and gates. These are
  proposals requiring owner approval.

## Primary research review

| Primary study | Venue/status | Task, models, sample | Finding relevant to ReAgent | Limitation / what it does not prove |
|---|---|---|---|---|
| Faggioli et al., “Perspectives on Large Language Models for Relevance Judgment” | ICTIR 2023; primary perspectives paper with preliminary experiment | IR relevance judgment; a human-machine collaboration spectrum plus an early trained-assessor comparison; the landing-page abstract does not enumerate pilot n | Fully automated relevance labels need explicit caution and a human-machine boundary. | Preliminary evidence with earlier models; no ReAgent rubric, languages, or current provider. |
| Sun et al., “Is ChatGPT Good at Search?” | EMNLP 2023 | GPT-3.5/GPT-4 passage reranking on standard IR benchmarks plus NovelEval; the landing-page abstract does not enumerate total judgments | Pointwise/listwise LLM relevance ranking is empirically testable, and contamination must be considered. | Passage ranking is not five-label paper relevance; ranking quality does not validate evidence spans or confidence. |
| Qin et al., “Large Language Models are Effective Text Rankers with Pairwise Ranking Prompting” | Findings of NAACL 2024 | Flan-UL2 20B and other LLM rankers on TREC-DL 2019/2020 and seven BEIR tasks | Pairwise prompts can outperform pointwise/listwise rankers and are useful as a bounded consistency signal. | Benchmark ranking gains do not establish label correctness; pairwise calls add order bias and cost. |
| Yan et al., “Consolidating Ranking and Relevance Predictions…” | EMNLP 2024 | LLM relevance labels combined with pairwise preferences on retrieval benchmarks; the landing-page abstract does not enumerate total judgments | Pointwise labels and pairwise preferences can conflict; pairwise is a distinct signal. | Their post-processing alters labels to satisfy ranking. ReAgent deliberately does not do that; conflict triggers audit. |
| Zheng et al., “Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena” | NeurIPS 2023 Datasets and Benchmarks | MT-Bench, about 3,000 expert votes, and about 30,000 human-preference conversations; GPT-4 and other judges | Reports human-level aggregate agreement while documenting position, verbosity, self-enhancement, and reasoning biases. | Assistant-response preference is not scholarly relevance; an aggregate “over 80%” cannot set a ReAgent threshold. |
| Shi et al., “Judging the Judges: A Systematic Study of Position Bias” | IJCNLP-AACL 2025 | 15 Judge models, MTBench/DevBench, 22 tasks, about 40 candidate models, over 150,000 evaluations | Position effects vary by Judge, candidate gap, and task; mirrored comparisons are necessary to measure order consistency. | It does not prove mirrored consistency implies a correct topical label. |
| Bhat and Varma, “All Prompts Are Created Equal?” | Findings of ACL 2026 | Eight models, four NLG tasks, ten equivalent paraphrases, about 115,000 evaluations | Semantically equivalent prompt variants can expose an accuracy/robustness gap; task verifiability matters. | NLG evaluation differs from paper relevance and does not establish two prompts as independent samples. |
| Bavaresco et al., “LLMs instead of Human Judges?” | ACL 2025 | JUDGE-BENCH: 20 human-annotated NLP datasets and 11 proprietary/open models | Reliability varies materially by task, property, human expertise, and source text; human validation is needed. | Broad aggregate evidence supplies no model selection or pass threshold for ReAgent. |
| Fu and Liu, “How Reliable is Multilingual LLM-as-a-Judge?” | Findings of EMNLP 2025 | Five model families, five tasks, 25 languages | Cross-language consistency was low on average (reported Fleiss' kappa about 0.3) and worse in some low-resource languages. | Generation evaluation is not Chinese scholarly relevance; language-level averages do not predict this sample. |
| Thakur et al., “Judging the Judges: Evaluating Alignment and Vulnerabilities…” | GEM workshop 2025 | 13 Judges evaluating nine base/instruction-tuned exam-taker models | Percent agreement alone can hide score differences; prompt complexity and leniency remain vulnerabilities. | Exam scoring is not a relevance task; workshop findings are model/task specific. |
| Lu et al., “Is LLM an Overconfident Judge?” | Findings of ACL 2025 | Multiple LLMs on offensive-language data stratified by human annotation agreement; the landing-page abstract does not enumerate total examples | Models can be overconfident on human-disagreement/ambiguous cases. | Binary moderation differs from ordinal relevance; it supports measuring confidence association, not trusting verbal confidence. |
| Chuang et al., “FaithLM” | EACL 2026 | Multiple backbones on three multi-domain explanation datasets | Natural-language explanations can be unfaithful to decision evidence. | It does not test abstract supporting spans. ReAgent therefore verifies span presence mechanically and does not equate a reason with causal faithfulness. |
| Li et al., “Preference Leakage” | primary preprint, 2025 | Three generator/Judge relatedness regimes across multiple models and benchmarks; the abstract does not enumerate total instances | Same-family relationships can create preference leakage/self-preference. | ReAgent evaluates papers rather than model-generated answers, but contamination and family correlation still caution against treating agreement as truth. |

## Evidence synthesis for the calibration

1. Pointwise A/B is the primary label experiment because each candidate remains
   independently auditable.
2. A and B are semantically equivalent paraphrases, not independent model
   families. Agreement measures prompt stability, not correctness.
3. Pairwise comparison is limited to three deliberately ambiguous pairs and is
   run in both orders. It cannot create or overwrite a label.
4. Every non-English real candidate enters human checking regardless of model
   confidence. Multilingual provider claims are hypotheses.
5. Supporting spans are checked as literal normalized substrings of the exact
   supplied preview. A plausible reason cannot substitute for evidence.
6. Verbal confidence is recorded but not trusted as a production threshold.
   Association with human agreement is informational in this small sample.
7. Human labels are a compact calibration reference, not expert gold. Reviewer
   identity is pseudonymous and the Judge cannot see the labels.
8. Model/provider identity, request ID, usage, operation settlement, prompt hash,
   input/output checksum, and retry count are part of the result.

## Threats and controls

| Threat | Calibration control | Residual limitation |
|---|---|---|
| Prompt sensitivity | frozen A/B paraphrases, exact hashes, same input fields | only two prompts; correlated errors remain |
| Position bias | three pairs, both orders, canonicalized preference comparison | too few pairs for a population estimate |
| Self-preference / contamination | no generated answer authorship signal, no Judge output shown to another run | model training data and shared heuristics are opaque |
| Verbosity/prestige bias | bounded previews; hide rank, citations, authors, DOI, provider score | title/venue wording may still influence output |
| Multilingual variance | four real non-English cases, human checker, no silent translation | n=4 cannot characterize a language |
| Confidence miscalibration | report agreement by confidence bin and variance; no production threshold | verbal confidence may have little resolution |
| Unsupported rationale | exact span-in-preview validation; reasons remain non-authoritative | literal support does not prove faithful internal reasoning |
| Model drift | exact canonical model ID, effort, adapter, SDK, prompt/schema hashes | serving infrastructure may change |
| Human disagreement | blinded primary reference plus targeted independent checker | most English cases have one primary reference |
| Structured-output exceptions | constrained schema, bounded retry, malformed/refusal accounting | provider guarantees have documented exceptions |

## Sources and access record

All sources below are Class B primary research and were accessed 2026-07-29:

- Faggioli et al.: https://arxiv.org/abs/2304.09161
- Sun et al.: https://aclanthology.org/2023.emnlp-main.923/
- Qin et al.: https://aclanthology.org/2024.findings-naacl.97/
- Yan et al.: https://aclanthology.org/2024.emnlp-main.25/
- Zheng et al.: https://proceedings.neurips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html
- Shi et al.: https://aclanthology.org/2025.ijcnlp-long.18/
- Bhat and Varma: https://aclanthology.org/2026.findings-acl.1929/
- Bavaresco et al.: https://aclanthology.org/2025.acl-short.20/
- Fu and Liu: https://aclanthology.org/2025.findings-emnlp.587/
- Thakur et al.: https://aclanthology.org/2025.gem-1.33/
- Lu et al.: https://aclanthology.org/2025.findings-acl.293/
- Chuang et al.: https://aclanthology.org/2026.eacl-long.177/
- Li et al.: https://arxiv.org/abs/2502.01534

Applicability limitation: no cited study evaluates the proposed provider with
ReAgent's exact topics, bounded previews, five-label rubric, prompt A/B hashes,
Chinese material, and human-reference procedure. That is why ADR 0006 proposes
an experiment rather than accepting a model.
