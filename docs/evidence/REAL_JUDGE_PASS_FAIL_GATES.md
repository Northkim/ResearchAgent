# Real Judge Calibration Pass, Warning, and Failure Gates

Gate-set version: `reagent-real-judge-gates/v1-proposed`
Status: Proposed Class D ReAgent policy; unapproved

Every numeric gate below is Class D project policy, not a universal
research-established threshold. The tiny sample cannot support statistical
significance.

## Blocking gates

| Gate | Proposed pass condition | Rationale and evidence | Alternatives / tradeoff | Owner / revisit |
|---|---|---|---|---|
| authorization and credentials | all ADR/provider/key/ZDR/preview/budget/reviewer approvals recorded; zero credential leakage | security and provider contracts | no hosted processing; local-only design | owner approval required; revisit any account/config change |
| exact identity | 100% of attempts report the approved canonical model ID, adapter and prompt hashes | model drift is an evaluation variable | accept alias (less reproducible) | revisit model deprecation/ID change |
| structured output | 100% of required logical calls schema-valid after allowed retry | malformed output cannot enter aggregation | allow missing calls to audit (weaker calibration evidence) | revisit if one documented refusal occurs |
| operation settlement | 100% required operations terminal and usage-complete; zero unsettled | existing publication invariant | none | permanent architecture gate |
| replay | zero new provider calls and reservations; checksum reconstruction exact | existing idempotency contract | none | permanent architecture gate |
| evidence spans | 100% of non-CANNOT pointwise outputs contain at least one short span found in the supplied preview | mechanically tests evidence grounding; rationale faithfulness remains limited | 95% plus audit (weaker, one unsupported span at n=30) | revisit only with a new rubric/schema |
| budget | attempts/tokens/runtime/cost remain at or below approved caps | fail-closed spend and data-volume control | larger approved envelope | owner required on every change |
| human exact agreement | at least 9 of 12 real candidates (75%) match the locked human-reference label exactly | Class B studies show task-specific validation is necessary; 9/12 is a screening floor | 10/12 stronger; 8/12 cheaper acceptance | owner required; revisit with larger calibration or label-distribution imbalance |
| human adjacent agreement | at least 11 of 12 (91.7%) are exact or adjacent; no HIGHLY_RELEVANT/RELEVANT ↔ NOT_RELEVANT severe reversal left unaudited | ordinal errors differ in consequence | require 12/12 stronger; 10/12 weaker | owner required; revisit any severe error |
| A/B exact agreement | at least 12 of 15 (80%) | two prompts are stability probes, not independent truth | 13/15 stronger; adjacent-only weaker | owner required; revisit prompt/model change |
| A/B adjacent agreement | at least 14 of 15 (93.3%) and every non-adjacent conflict audited | prevents broad rubric instability | 15/15 stronger; 13/15 weaker | owner required; revisit prompt/model change |
| mirrored pair consistency | at least 2 of 3 pairs order-consistent; every inconsistent pair routed to audit | position-bias research motivates mirroring; n=3 is diagnostic only | require 3/3 stronger; no numeric gate and audit all | owner required; revisit if any inconsistency or more pairs added |
| multilingual safety | all four non-English cases schema-valid, span-valid, and human-checked; no systematic severe reversal across all cases | multilingual reliability varies strongly | exclude non-English (defeats objective) | owner required; any translation/provider/language change |
| retention | approved ZDR and local expiry/deletion controls verified | hosted previews are unapproved and rights-sensitive | local-only calibration | owner required; revisit provider/region/terms change |

Failure of any blocking gate rejects the calibration. It does not silently route
the full sample to production audit or authorize another provider.

## Warning gates

Warnings require owner review and a written accept/reject rationale even when
blocking gates pass:

- any retry, refusal, truncation, malformed first response, timeout, or 429;
- first-attempt schema-valid rate below 97% (with 36 logical calls, any initial
  schema failure triggers this warning);
- any A/B disagreement or mirrored pair inconsistency;
- any severe human/Judge reversal;
- exact human agreement below 10/12 (83.3%) even if the 9/12 floor passes;
- any non-English A/B or human disagreement;
- any inappropriate CANNOT_JUDGE on a human-decidable case, or failure to use it
  on the designed insufficient-information case;
- any verbal confidence at or above 0.80 on a disagreement;
- p95 attempt latency above 30 seconds or total runtime above 10 minutes;
- actual cost above the conservative USD 0.41976 Sonnet standard-price token
  estimate, while still below the owner cap;
- unresolved human-reference disagreement;
- model serving/SDK/provider contract change between evidence review and run.

The 97%, 83.3%, 0.80, 30-second, and 10-minute warning values are **Proposed
Class D policy**. They give the owner early visibility before a blocking cap is
reached. Alternatives are warning on any deviation (more sensitive) or using
only blocking gates (less informative). Revisit after the first calibration.

## Informational metrics

These never rescue a failed blocking gate:

- weighted kappa and adjacent agreement;
- per-label precision/recall/confusion matrix where denominators exist;
- human-human agreement and unresolved count;
- confidence mean/variance, confidence bins, Brier score if a defensible binary
  mapping is predeclared, and confidence/agreement association;
- CANNOT_JUDGE agreement/rate;
- TIE and pairwise/pointwise conflict rates;
- English/non-English agreement difference;
- latency p50/p95, tokens, retry count, and settled cost;
- first-attempt versus final schema validity;
- audit workload and human override rate.

Confidence association is informational because verbal confidence is often
miscalibrated and n=12 is too small for a stable curve.

## Gate evidence

Class B sources motivating—not numerically determining—these gates:

- task-specific human validation: https://aclanthology.org/2025.acl-short.20/
- relevance human-machine boundary: https://arxiv.org/abs/2304.09161
- pairwise utility: https://aclanthology.org/2024.findings-naacl.97/
- position bias: https://aclanthology.org/2025.ijcnlp-long.18/
- prompt robustness: https://aclanthology.org/2026.findings-acl.1929/
- multilingual variance: https://aclanthology.org/2025.findings-emnlp.587/
- confidence/ambiguity risk: https://aclanthology.org/2025.findings-acl.293/
- explanation-faithfulness risk: https://aclanthology.org/2026.eacl-long.177/

## Three distinct decisions

1. **Code accepted:** adapter/substrate tests pass.
2. **Calibration accepted:** every blocking gate passes and the owner resolves
   warnings.
3. **Full-pool permission:** always **NO** under ADR 0006. A later explicit
   owner decision and policy update are required even after accepted
   calibration.

