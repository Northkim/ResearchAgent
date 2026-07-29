# ADR 0005: Automated Relevance Judge and Multilingual Search

Status: **Proposed**  
Date: 2026-07-29  
Owners: ReAgent owner approval required  
Scope: architecture contract only; implementation is not authorized

## Context

Phase 9B-2B-1 retained a bounded OpenAlex pilot:

- `cs-machine-unlearning`: 20 normalized candidates;
- `social-algorithmic-management`: 20 normalized candidates;
- `nonenglish-chinese-digital-humanities`: one provider result, zero normalized
  candidates after a field-length safety rejection.

Forty candidates are reviewable. Reviewer A/B packets are blank. No human label,
adjudication, retrieval metric, automated judgment, or expert-gold label exists.

The two-human blind protocol is rigorous but currently impractical. Separately,
the one-query SearchPlan does not represent a deliberate multilingual strategy.
Automated evaluation and multilingual search affect the same future candidate
evidence but have separate ownership and must be implemented in separate
milestones.

## Problem

ReAgent needs a lower-burden, auditable relevance-evaluation method that cannot
be mistaken for gold truth, plus a deterministic multilingual query-expansion,
merge, and diagnostic contract that preserves original-language provenance and
safety boundaries.

## Decision drivers

- explicit silver-versus-gold epistemic boundary;
- topical relevance only from title/abstract preview;
- immutable provenance and replay identity;
- prompt/model drift visibility;
- rank/citation/other-label blinding;
- bounded cost and fail-closed usage settlement;
- targeted human oversight and measurable override;
- multilingual source/translation integrity;
- deterministic exact-ID merge and no fuzzy false merges;
- reuse of existing ports, artifact storage, and ProviderOperation ledger;
- no database or production coupling without demonstrated need.

## Evidence summary

Primary research supports treating LLM judges as potentially useful but
task-sensitive proxies. It documents prompt sensitivity, position bias,
inconsistency, multilingual variance, model/human disagreement, and
self-preference/verbosity risks. Pointwise judgments are simple to audit;
pairwise ranking can add a local consistency signal but introduces order bias.

Official provider evidence shows schema-capable hosted candidates and one
feasible local option. Hosted retention, model lifecycle, deterministic controls,
rate limits, cost, and request identity differ. No provider has been validated
on ReAgent's five-label paper-relevance rubric.

Evidence and source limitations are registered in:

- `docs/evidence/AUTOMATED_RELEVANCE_JUDGE_EVIDENCE.md`;
- `docs/evidence/LLM_JUDGE_PROVIDER_MATRIX.md`;
- `docs/evidence/MULTILINGUAL_SEARCH_FAILURE_ANALYSIS.md`.

## Proposed automated silver-label architecture

`EvaluationCandidate`
→ deterministic metadata validation
→ pointwise judgment A
→ pointwise judgment B with equivalent separately versioned prompt
→ selected mirrored pairwise consistency
→ immutable consensus
→ `AUTO_ACCEPTED`, `AUTO_REJECTED`, or `NEEDS_HUMAN_REVIEW`
→ targeted human audit
→ raw-silver and audited-silver reports.

Conceptual schemas:

- `AutomatedJudgmentRequest/v1`;
- `AutomatedJudgment/v1`;
- `JudgmentConsensus/v1`;
- `HumanAuditRequest/v1`;
- `HumanAuditResult/v1`.

Their required and prohibited fields are frozen in
`SILVER_LABEL_AGGREGATION_POLICY.md`.

### Port boundary

Add a provider-independent `AutomatedRelevanceJudge` evaluation port accepting
one request and returning one structured judgment with identity, usage, errors,
timeout, and cancellation. The semantic adapter may use the existing
`LLMProvider`; provider SDK/client code stays in adapters/composition.

Add an immutable `JudgePromptRegistry` for prompt/rubric/language versions and
hashes. It has no runtime mutation.

The judge never mutates evaluation state, accesses SQLAlchemy/FastAPI/
`WorkflowRun`, reads arbitrary environment variables, or sees provider rank,
deterministic score, citation count, another judge output, or reviewer label.
Aggregation—not the judge—reads multiple judgments.

### Persistence

Use existing `ArtifactContentStorage` for canonical immutable artifacts, an
evaluation-private append-only checksum journal for references/state, and the
existing `ProviderOperationService`/evaluation operation journal for reservation,
attempts, settlement, usage, request IDs, and unsettled checks.

No database table or new persistence port is proposed. Revisit only for
concurrent writers, indexed cross-evaluation queries, access control, or
retention behavior that existing storage cannot satisfy.

## Proposed human-audit boundary

Audit all label disagreements, confidence below the approved threshold,
`PARTIALLY_RELEVANT`, `CANNOT_JUDGE`, missing evidence, mirrored-pair conflict,
non-English/translation uncertainty, and blocking metadata warning. Also audit a
deterministic sample of high-confidence consensus and at least one item per topic
with candidates. A zero-candidate topic remains an explicit coverage warning.

The non-expert human answers only whether title/preview principally addresses the
topic. Human override affects audited-silver metrics, never raw-silver artifacts
and never creates expert gold.

## Proposed multilingual SearchPlan

Add immutable `QueryVariant/v1` and `MultilingualSearchPlan/v1`. Variants record
source query/language, target language/type, generator and method version, exact
provider query, checksum, and owner approval.

V1 executes only explicit approved variants as separate bounded provider
operations. It preserves original text; translations are separately labeled and
checksummed. It records first-seen and all-matched variants, per-variant
statistics, and normalized warnings.

Merge exact DOI, then exact OpenAlex ID. Title/year similarity is advisory only;
no fuzzy automatic merge. The Chinese-topic phrases in
`MULTILINGUAL_SEARCH_PLAN.md` are proposals for human review, not hard-coded
queries.

The existing length gate remains. Later safe diagnostics must record field name,
measured length, configured limit, and a safe fragment/hash without full rejected
content.

## Judge provider candidates

- OpenAI `gpt-5.6-terra`: balanced hosted candidate, current structured output,
  multilingual support, and detailed usage; distinct dated snapshot not found in
  the inspected current model page.
- Anthropic `claude-sonnet-5`: hosted candidate with structured JSON and a
  documented pinned ID; non-default sampling parameters are unsupported.
- Local `gpt-oss-20b`: Apache-2.0, locally controllable, structured-output
  capable through an approved serving stack; mostly-English training and
  operator-owned reliability make it unsuitable as the uncalibrated
  multilingual default.

## Provider/model recommendation

Conditionally calibrate OpenAI `gpt-5.6-terra` first and compare a bounded subset
with Anthropic `claude-sonnet-5`. Terra is recommended as a Class D balance of
consequence and cost, not as proven superior. If a sufficiently pinned OpenAI
identity cannot be established, prefer Sonnet 5 for the reproducibility pilot.

No provider/model is approved by this Proposed ADR. No key or non-zero spend is
authorized.

## Prompt/rubric versioning

Use `reagent-topic-relevance/v1`,
`relevance-pointwise-a/v1`, `relevance-pointwise-b/v1`, and a separately
versioned pairwise prompt. Store canonical prompt hash, rubric hash, schema
version, language variant, adapter version, model identity, input/output
checksums, and created time. Any semantic change creates a new immutable version.

Supporting spans are short excerpts only from the provided preview. Original and
translated text have distinct checksums; translation never replaces the source.

## Aggregation policy

Initial proposed **Class D** policy:

- auto-accept only exact A/B agreement on `HIGHLY_RELEVANT` or `RELEVANT`, each
  confidence at least 0.80, evidence present, and no conflict/warning;
- auto-reject only exact A/B `NOT_RELEVANT`, each at least 0.80, reason/evidence
  present, and no conflict/warning;
- route every other state to human review;
- audit 10% of high-confidence consensus with a deterministic seed and per-topic
  minimum;
- report raw-silver and human-audited-silver metrics separately.

No threshold is accepted by this ADR.

## Cost policy

Initial proposed **Class D** pilot limits: 40 candidates, two pointwise calls per
candidate, 10 total pairwise calls, 90 logical calls, 100 attempts including
retries, 4,000 input/512 output tokens per pointwise call, 360,000 aggregate
input and 46,080 aggregate output tokens, 15 minutes, one transient retry, stop
at five failed attempts or two incomplete candidates, and no more than 20 human
audit items.

Authorized monetary budget remains USD 0.00. A planning envelope up to USD 1.00
requires explicit owner approval and execution-time price reservation. Missing
usage, excess estimate, unavailable model, repeated structured-output failure,
or unsettled judgment fails closed.

## Data-retention policy

Send only frozen topic context, title, bounded abstract preview, and minimal
metadata. Exclude full abstract, rank, citation count, and other labels. Retain
canonical hashes, short evidence spans, reasons, identity, usage, cost, latency,
and provider request IDs under the approved evaluation policy.

Hosted provider use requires owner approval of abstract-preview retention and
account/endpoint/ZDR configuration. A key is adapter-only and never stored in an
artifact. Local use requires explicit backup, swap, telemetry, and deletion
policy.

## Security boundary

- delimit title/preview as untrusted data and ignore embedded instructions;
- reject unknown schema fields and validate spans against source offsets;
- never log keys, auth headers, raw response bodies, or full rejected text;
- enforce reservation before call and settlement after response;
- normalize timeout/rate-limit/unavailable/schema/refusal/cancellation errors;
- allow cancellation but no evaluation-state mutation from an adapter;
- keep judge/multilingual execution out of general Skill capability injection
  until each separate milestone is approved.

## Alternatives

1. **Full two-human blind review now:** highest rigor; deferred for prototype
   scope and reviewer availability.
2. **One LLM call per candidate:** lowest cost; inadequate instability signal.
3. **Three or more full calls:** more samples; not justified before two-prompt
   calibration.
4. **Full pairwise/listwise ranking:** expensive and order-biased; not needed for
   label assignment.
5. **Independent model families for every item:** better diversity, greater cost
   and integration; optional calibration only.
6. **Local-only judge:** best data locality, weakest initial multilingual
   evidence and highest operational burden.
7. **LLM-generated query expansion:** flexible but unbounded and hard to replay;
   prohibited in V1.
8. **Relax field-length validation:** might admit the rejected record but weakens
   safety without knowing the field; rejected.
9. **New evaluation database tables:** unnecessary until current append-only
   artifact storage proves insufficient.

## Consequences

Positive:

- sharply reduced routine human workload;
- reproducible silver evidence and visible uncertainty;
- explicit audit and override measures;
- deterministic multilingual provenance and coverage diagnostics;
- existing provider-operation and artifact boundaries reused.

Negative:

- silver labels remain correlated model estimates;
- provider drift/retirement and hosted retention become dependencies;
- two prompt calls double the pointwise cost;
- non-English cases initially remain audit-heavy;
- raw and audited reporting is more complex;
- the Chinese rejection's exact field/length cannot be reconstructed from current
  evidence.

## Risks

Position bias, prompt sensitivity, self-preference, multilingual variance,
overrating/leniency, model drift, structured-output failure, provider outage,
usage/cost gaps, anchoring in human audit, translation loss, exact-ID conflicts,
and false coverage claims. Controls reduce but do not eliminate these risks.

## Revisit triggers

- provider model/price/retention/deprecation/API changes;
- prompt A/B or human-audit agreement below owner-approved limits;
- override, `CANNOT_JUDGE`, or required-review rates exceed policy;
- systematic language-specific disagreement;
- more than 20 of 40 items require audit;
- exact OpenAI model pin remains unavailable;
- current artifact storage cannot satisfy concurrency/query/retention needs;
- query variants produce high duplicate concentration, conflicts, or only one
  language;
- expert/publication/systematic-review claims are planned.

## Owner decisions required

| Decision | Recommendation | Alternatives | Evidence / consequence | Blocks implementation? |
|---|---|---|---|---|
| adopt automated silver labels | approve only with targeted audit and explicit no-gold language | retain full two-human plan | research supports bounded proxy, not ground truth; determines evaluation path | yes |
| provider | calibrate OpenAI primary, Anthropic comparison | Anthropic primary; local | provider matrix; affects adapter, retention, key, cost | yes |
| model/version | `gpt-5.6-terra` if adequate pin is confirmed | `claude-sonnet-5`; Luna; gpt-oss | exact identity controls replay and drift | yes |
| API key availability | owner-supplied scoped server-side key | local-only; defer | hosted adapters cannot call without key | yes |
| maximum monetary budget | approve at most USD 1.00 pilot after reservation review | USD 0/defer; lower cap | current authorization is zero | yes |
| maximum calls | 90 logical / 100 attempts | lower pairwise cap; no pairwise | bounds exposure and runtime | yes |
| pointwise repetition | two prompt versions | one; three | two exposes wording sensitivity at bounded cost | yes |
| pairwise strategy | five neighboring pairs, mirrored (10 calls) | none; more pairs | position-bias evidence requires order reversal | yes |
| confidence threshold | 0.80 Class D pilot | 0.75; 0.90; calibrated threshold | uncalibrated threshold controls audit/automation | yes |
| random audit | 10%, deterministic, per-topic minimum | 5%; 20% | detects consensus error at added burden | yes |
| PARTIALLY_RELEVANT audit | audit all initially | allow consensus partial | boundary class is most ambiguous | yes |
| non-English audit | audit all initially | threshold-based after calibration | multilingual consistency varies | yes |
| preview retention | allow bounded preview only under evaluation policy/provider terms | hashes/spans only; local-only | affects replay, privacy, and provider eligibility | yes |
| machine translation | prohibit V1 unless separately approved and provenance-preserving | approved translator; manual only | translation may alter relevance evidence | blocks translated execution |
| Chinese/English variants | review four proposals in multilingual plan | original only; revised set | affects coverage and call budget | blocks multilingual implementation |
| old blank packets | retain until owner-approved cleanup | retain indefinitely; later delete | provenance and future gold option | no, but cleanup needs approval |
| expert gold | defer, not cancel | perform now; cancel | preserves future rigorous evaluation | yes for supersession policy |
| metric gain mapping | retain versioned existing Class D mapping for silver | report binary only; new mapping | affects nDCG comparability | blocks metric implementation |
| audit cap | pause above 20 items | higher cap; no cap | bounds owner burden and signals judge failure | yes |

## Deliberately excluded decisions

This ADR does not authorize a real judge call, OpenAlex search, query translation,
backend/frontend/migration/workflow/dependency change, database, SDK install,
review-label import, metric calculation, source retrieval, or deletion of review
packets. Automated judge and multilingual SearchPlan implementation must occur in
separate later milestones after owner approval.

