# Human Audit Protocol for Silver Labels

Protocol ID: `reagent-human-audit/v1`  
Status: Proposed

## Purpose

The owner task is deliberately narrow:

> Based on the title and abstract preview, does this paper principally address
> the stated topic?

The reviewer need not be a domain expert and does not assess method quality,
truth, novelty, prestige, or scientific merit. A result from this protocol is an
audited silver label, not expert gold.

## Workflow

1. Automated pointwise runs evaluate every reviewable candidate.
2. Aggregation creates automated consensus or a required-review state.
3. The audit queue contains all disagreements, low-confidence cases,
   `CANNOT_JUDGE` cases, missing evidence, pairwise conflicts, non-English
   uncertainty, metadata warnings, and the deterministic consensus sample.
4. The reviewer assigns a relevance label, accepts or overrides the silver
   proposal, records confidence and reason, or marks information insufficient.
5. Raw-silver and audited-silver metrics are generated separately only after the
   required queue is complete.

## Queue priority

1. metadata warnings and corrupt/truncated input;
2. `CANNOT_JUDGE` and missing evidence;
3. label and pairwise disagreements;
4. low confidence and all `PARTIALLY_RELEVANT`;
5. non-English/translated items;
6. random consensus audit;
7. per-topic minimum audit.

Within a tier, sort by topic ID then a deterministic candidate hash. Provider
rank is never a queue sort key.

## Information displayed

- topic title/description, research question, inclusion and exclusion rubric;
- paper title, abstract preview, year, venue, and language metadata;
- original text always; translated text beside it only when explicitly marked
  machine translated with separate provenance/checksum;
- safe metadata warnings;
- concise automated reasons and supporting spans;
- proposed silver label and the audit-routing reason;
- progress, required fields, and immutable candidate checksum.

To reduce anchoring, the reviewer should make a provisional label before
revealing the automated proposal for required-exception audits. For the reduced
accept/override path, the proposal may then be revealed. Random-consensus audits
should use the same reveal behavior.

## Information hidden

- OpenAlex/provider result rank and relevance score;
- deterministic rank score;
- citation count;
- author prestige, impact factor, or venue ranking;
- another human review, if one exists;
- cost/token telemetry irrelevant to the topical decision.

## Reviewer response

Required:

- one of the five relevance labels;
- `agree`, `override`, or `no proposal`;
- concise reason tied to title/preview;
- audit confidence (`LOW`, `MEDIUM`, `HIGH`);
- if overriding, one reason:
  `CENTRALITY_MISREAD`, `KEYWORD_OVERLAP`, `INSUFFICIENT_INFORMATION`,
  `TRANSLATION_UNCERTAINTY`, `EVIDENCE_MISMATCH`, `METADATA_PROBLEM`, or
  `OTHER_EXPLAINED`.

The reviewer may not retrieve full text or use citation count to resolve the
task. If the bounded evidence is insufficient, select `CANNOT_JUDGE`.

## Completion criteria

- every required-exception request is completed;
- deterministic random sample and per-topic minimum are completed;
- each result checksum matches its request and candidate metadata;
- no result is missing label, reason, confidence, reviewer ID, or timestamp;
- zero-candidate topics remain explicitly reported, not waived or populated.

Incomplete audit means audited-silver metrics are unavailable. Raw-silver
metrics may be reported only for their labeled coverage with an explicit
denominator.

## Proposed burden

These are **Class D ReAgent planning estimates**, not measured pilot outcomes:

- expected automatic high-confidence consensus: 60–80% of 40 candidates;
- expected required-review population: 8–16;
- 10% consensus sample: approximately 3–4, subject to per-topic minimum;
- expected total audit: approximately 10–20;
- maximum initial burden: 20 candidates; exceeding it pauses for owner review.

The 60–80% consensus rate is a capacity-planning assumption only. ReAgent has
generated no automated judgments, labels, agreement rates, or audit counts.

## Quality controls

- deterministic queue and sampling;
- exact prompt/model/rubric and source checksums;
- audit-time hiding of rank/citation signals;
- provisional response before proposal reveal;
- reasons required for both agreement and override;
- raw-silver retained beside audited-silver;
- agreement/override reported per topic and overall;
- no claim that one non-expert audit resolves scientific relevance as an expert
  would.

## Escalation

Pause rather than force completion when:

- more than 20 items enter the queue;
- a topic rubric is ambiguous;
- the source and translation materially conflict;
- metadata checksum changes;
- the reviewer cannot interpret a language and no approved translation exists;
- systematic audit disagreement suggests prompt/rubric/model failure.

Such a pause triggers policy/rubric revision or expert-gold planning; it does not
authorize additional judge calls or live search.

## Synthetic queue implementation boundary

Phase 9B-2C-2 implements the queue contract without implementing human
completion. All exception cases, non-English cases, and metadata warnings are
included. High-confidence consensus sampling is deterministic and topic
stratified. The committed 10% sample, per-topic minimum, and 20-item cap are
explicitly `TEST_POLICY_ONLY`.

`HumanAuditResult` is an immutable input contract only: the command never
creates one. Consequently, the standard synthetic run reports raw-silver
metrics and marks audited-silver metrics unavailable with a reason. Tests may
construct synthetic human results to verify that overrides affect only the
audited family. The reviewer question remains limited to topical relevance
based on title and bounded preview; provider rank and citation count are absent.
