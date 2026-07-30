# ADR 0006: Bounded Real-Judge Calibration

Status: **Deferred**
Date: 2026-07-29
Owners: ReAgent owner
Scope: calibration design and owner-approval boundary only

## Route status update — 2026-07-30

The owner has moved the V1 product priority to real grounded literature-report
generation. This ADR is **Deferred**, not rejected or accepted for execution.
The calibration design, Fake Judge substrate, tests, evidence, and blank review
packets remain preserved as an Optional Evaluation Module. No real Judge call,
non-zero Judge spend, calibration execution, relevance label, or full-pool
screening is authorized.

Resume requires an explicit owner decision after the grounded-report path is
stable or when retrieval/screening evaluation becomes a product or research
claim, with fresh provider/model/ZDR/abstract/human-reference/budget approval.

## Context

Phase 9B-2C-2 verified the provider-independent automated-silver substrate with
deterministic Fake Judges and synthetic candidates. It includes immutable
requests/results, prompt/rubric versions, pointwise A/B, mirrored pairwise
consistency, ProviderOperation settlement, aggregation, human-audit queue,
raw/audited-silver separation, and idempotent replay.

No real Judge provider is selected. No real LLM has been called and no OpenAlex
candidate has been judged. Synthetic metrics are architecture-test evidence,
not model-quality or retrieval-quality evidence.

## Problem

A real Judge cannot safely evaluate the retained live pools until a small,
auditable experiment tests schema compliance, prompt/repeat stability,
supporting evidence, CANNOT_JUDGE behavior, order bias, multilingual behavior,
human-reference agreement, usage, latency, cost, retention, operation
settlement, and replay.

## Decision drivers

- topical relevance only; no scientific-quality judgment;
- provider/model/adapter/prompt/schema identity and reproducibility;
- small human-blinded reference set;
- prompt A/B and mirrored-order diagnostics;
- non-English caution;
- exact supporting-span verification;
- fail-closed cost, usage, retries, and operation settlement;
- ZDR and minimum-data processing;
- no gold-standard overclaim;
- explicit separation among code acceptance, calibration acceptance, and
  full-pool authorization.

## Evidence summary

Primary relevance and LLM-Judge research supports task-specific human
validation and documents prompt sensitivity, position bias, multilingual
variance, confidence overstatement, explanation unfaithfulness, and
model/human disagreement. It does not establish a universally reliable Judge
or threshold.

Current official contracts identify three feasible families:

- OpenAI `gpt-5.6-terra`: schema-capable and cost-balanced, but the inspected
  current page exposes no distinct dated pin;
- Anthropic `claude-sonnet-5`: schema-constrained, officially multilingual, and
  documented as a canonical pinned snapshot; no seed or sampling controls;
- local `gpt-oss-20b`: Apache 2.0 and locally controllable, but mostly-English
  training and operator-owned serving guarantees make it a poor initial
  multilingual candidate.

Evidence is recorded in `docs/evidence/REAL_JUDGE_CALIBRATION_EVIDENCE.md` and
`docs/evidence/REAL_JUDGE_PROVIDER_MATRIX.md`.

## Proposed decision

After all owner approvals, run one bounded calibration with one primary hosted
Judge: Anthropic `claude-sonnet-5`. Use no comparison model in the first
experiment. This is a **Proposed Class D** reproducibility/cost decision, not a
claim that the model is more accurate.

If Anthropic access or ZDR cannot be approved, do not switch silently. Revise
this ADR to approve either OpenAI `gpt-5.6-terra` with its pinning limitation or
a separately specified local experiment.

## Calibration sample

- 12 private real candidates: four from each of two English topics and four from
  one multilingual/non-English topic;
- 3 committed synthetic canaries for adapter/schema/replay regression;
- no actual paper identity, title, or abstract in committed documentation;
- private ignored manifest contains only evaluation/topic/candidate IDs,
  candidate checksum, selection-rationale category, human-reference status, and
  retention expiry.

The real sample covers likely direct/substantial/partial/non-relevance,
insufficient information, metadata warning, non-English uncertainty, pairwise
ambiguity, and likely order sensitivity.

## Human reference-label procedure

One primary human labels all 12 real cases before seeing Judge output. A
secondary checker independently labels all four non-English cases, all primary
CANNOT_JUDGE/uncertain cases, every later Judge dispute, and a deterministic 25%
sample of remaining English cases with one per English topic. Disagreements are
resolved or explicitly retained as unresolved.

Reviewers see only topic, title, bounded preview, rubric, and approved minimal
metadata. Rank, citations, provider score, Judge output, and another review are
hidden. Labels are human calibration references, not expert gold. Codex is not
a reviewer.

## Prompt A/B contract

Freeze without source change:

- `relevance-pointwise-a/v1`,
  `sha256:aa3adfa637b510ff90da5a3885cc5092ccd798d7e4efd87c15e3b2f0c77345e0`;
- `relevance-pointwise-b/v1`,
  `sha256:da33134eda1397604c442fd1d76a8c9dcd34453da8a26c97a7acf91326a5a918`;
- rubric `reagent-topic-relevance/v1`;
- registry schema `reagent-judge-prompt-registry/v1`.

A/B are semantically equivalent paraphrases with distinct structures. They are
correlated stability checks, not independent models. Both require short preview
spans and CANNOT_JUDGE for insufficient evidence and prohibit scientific-quality
assessment.

## Pairwise contract

Select three real pairs before viewing Judge output: one per topic, each near a
human/selection-rationale boundary. Freeze
`relevance-pairwise-mirrored/v1`,
`sha256:440b5a34c29a4802226b3f4e315b5259751c48a4c668d2d3f56263abb7dfbb92`.
Run each pair in both orders, six logical calls. `TIE` is valid. Pairwise
conflict routes to human audit and never creates or overwrites a label.

## Data-processing policy

Send only topic/rubric/schema, title, at most 500 normalized characters of
preview, minimal year/venue, and pseudonymous candidate ID. Exclude full
abstract, authors, DOI/OpenAlex ID, rank, citations, scores, raw provider
response, other judgments, database IDs, paths, and secrets.

Hosted execution requires confirmed organization-level ZDR for the exact
endpoint/model/features and explicit owner permission to process previews. No
Batch, Files, tools, feedback sharing, background mode, or consumer product.
Current authorization does not satisfy this requirement.

## Retention

Proposed:

- canonical request/structured response: 14 days maximum or seven days after
  report decision, whichever is earlier;
- manifest: 14 days after calibration;
- ProviderOperation metadata: 30 days without content;
- human labels: 12 months without duplicated preview;
- aggregate content-free report: retained with project evidence;
- credentials and raw HTTP bodies: never retained.

These periods are Class D proposals and require owner approval.

## Budget

Proposed limits:

- 15 candidates;
- 30 pointwise + 6 mirrored pairwise = 36 logical calls;
- one transient retry per call but six retries globally;
- 42 maximum attempts;
- 90,000 input and 9,984 output tokens;
- 15 minutes;
- USD 0.75 hard cap;
- at most two failed logical calls, while any unresolved required result rejects
  calibration.

Conservative Sonnet 5 standard-price token estimate: USD 0.41976. Current
authorized budget remains USD 0.00.

## Metrics

Report schema validity/retries/malformed responses; A/B exact and adjacent
agreement/confidence variance; human exact/weighted/adjacent agreement and
override; CANNOT_JUDGE behavior; span presence/exact containment and unsupported
reasons; mirrored-order/TIE/pairwise conflict; English/non-English differences;
latency/tokens/cost/failures/settlement/replay.

No significance claim is allowed for 12 real candidates.

## Proposed pass/fail gates

Blocking gates include approvals/credential safety, exact identity, final
schema validity, operation settlement, zero-call replay, evidence-span validity,
approved budgets, human and A/B agreement floors, pairwise consistency,
multilingual human checking, and retention compliance. Numeric details and
warning/informational separation are in
`docs/evidence/REAL_JUDGE_PASS_FAIL_GATES.md`.

Every numeric threshold is Proposed Class D policy, requires owner approval, and
must be revisited after the first calibration or any provider/model/prompt/
rubric/language change.

## Security

- adapter composition alone reads the API key;
- requests treat title/preview as delimited untrusted content;
- logs contain IDs/hashes/counts, not candidate text or keys;
- SDK auto-retries are disabled or counted;
- wrong model, missing request ID/usage, schema failure, retention uncertainty,
  or budget overrun fails closed;
- all private artifacts remain under an injected ignored root with immutable
  relative keys and checksum verification.

## Alternatives

1. **OpenAI Terra primary:** lower current calculated token estimate and existing
   generic port fit; weaker current exact-pinning evidence.
2. **Primary plus comparison model:** better family-disagreement evidence;
   doubles adapter, privacy, cost, and interpretation burden.
3. **Local gpt-oss first:** hosted disclosure avoided; larger hardware/serving
   scope and weak multilingual starting evidence.
4. **No real calibration:** lowest privacy/cost risk; automated-silver remains
   Fake-only.
5. **Full dual-independent human review:** stronger reference evidence; higher
   burden and still not expert gold without qualified reviewers/adjudication.

## Consequences

Positive: a narrow experiment can reject an unsuitable model before pool-wide
harm, quantify actual operation/cost behavior, and preserve a human boundary.

Negative: integration effort is required for one small experiment; n=12 cannot
establish production reliability; hosted preview processing introduces rights,
privacy, and provider-contract risk; current prompt A/B checks remain
correlated.

## Risks

- provider/model/serving drift;
- schema refusal/truncation despite constrained output;
- human-reference error and limited expertise;
- prompt and position bias;
- multilingual underperformance;
- confidence miscalibration;
- supporting spans that are present but not causally faithful;
- training-data contamination or shared heuristic errors;
- price/tokenizer/rate-limit change;
- ZDR or region misconfiguration;
- retained/orphaned private artifacts;
- overinterpreting a passed small sample.

## Revisit triggers

Provider/model/snapshot, SDK/adapter, price, ZDR/region, prompt/rubric/schema,
preview length, language/translation, sample design, reviewer procedure, budget,
gate, or retention changes; any unsupported span, severe reversal, credential
incident, uncounted retry, unsettled operation, replay call, or proposed
full-pool/public/expert-gold use.

## Owner approvals required

| Decision | Recommendation | Alternatives | Evidence / consequence | Blocks execution |
|---|---|---|---|---|
| perform calibration | approve only after this ADR is revised/accepted | defer | bounded evidence before live labels | **yes** |
| provider | Anthropic first-party API | OpenAI; local; defer | clearer canonical pin; hosted risk | **yes** |
| model | Claude Sonnet 5 | Terra; gpt-oss | current provider matrix | **yes** |
| exact ID | `claude-sonnet-5` | revised approved ID | fixed ID is run identity | **yes** |
| key | scoped server-side commercial-org key | no key/defer | never print/store | **yes** |
| ZDR | confirmed for exact org/endpoint/model | local-only/defer | hosted previews otherwise prohibited | **yes** |
| preview permission | permit title + ≤500-char preview | synthetic-only; smaller preview | rights/privacy engineering risk | **yes** |
| preview length | 500 normalized characters | 300; 1,000 after review | current substrate compatibility | **yes** |
| sample | 12 real + 3 synthetic | 12 real; 15 real | coverage versus burden | **yes** |
| real/synthetic mix | synthetic canaries excluded from quality metrics | real-only | isolates adapter regression | **yes** |
| primary reviewer | assign one human | defer | human reference cannot be automated | **yes** |
| secondary checker | all non-English/uncertain/disputed + 25% English | all 12; none | minimum practical independence | **yes** |
| pointwise count | A+B once each | one; three+ | prompt-stability signal | **yes** |
| pairwise count | 3 pairs × 2 orders | 2 or 5 pairs | one topic probe each | **yes** |
| monetary cap | USD 0.75 | USD 0/defer; smaller approved cap | estimate USD 0.41976 standard price | **yes** |
| token caps | 90k input / 9,984 output | revise after token preflight | prevents estimation drift | **yes** |
| runtime | 15 minutes | 10 or 30 | bounded synchronous experiment | **yes** |
| retries | 1/call, 6 global, 42 attempts | zero; larger budget | fail-closed transient handling | **yes** |
| pass/warning gates | approve proposed gate document | strengthen/revise | no universal thresholds | **yes** |
| multilingual cases | four original-language real cases; no machine translation | smaller set; separately approved manual translation | multilingual objective and uncertainty | **yes** |
| retention | content ≤14d; ops 30d; labels 12mo | ephemeral; shorter | auditability/privacy tradeoff | **yes** |
| comparison model | no comparison in first calibration | limited Terra subset | narrower privacy/cost surface | no, if “no” |
| full-pool judgment | remain prohibited after calibration | later separate approval | calibration is only a gate | **yes for any full-pool action** |

## Explicit exclusions

This ADR does **not** authorize:

- any real LLM call;
- any non-zero spend;
- any provider adapter implementation;
- any API key;
- hosted abstract-preview processing;
- selection or judgment of a real candidate;
- import of human labels;
- full-pool judgment;
- production confidence thresholds;
- automatic human-audit completion;
- expert-gold or scientific-quality claims.
