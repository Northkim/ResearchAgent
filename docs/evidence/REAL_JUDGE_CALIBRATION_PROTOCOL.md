# Bounded Real Judge Calibration Protocol

Protocol version: `reagent-real-judge-calibration/v1-proposed`
Date: 2026-07-29
Status: Proposed Class D ReAgent policy; execution is not authorized

## Preconditions

Execution is fail-closed until the owner explicitly approves ADR 0006,
provider/model ID, key availability, ZDR configuration, hosted abstract-preview
processing, sample manifest, reviewers, budget, limits, retention, and gates.
Prices and model contracts must be rechecked on the execution date.

No approved future calibration may imply permission to judge the full live pool.
That requires a later owner decision after the calibration report.

## Sample

Maximum request sample: **15 candidates**:

- **12 private real candidates**: four from each of two English topics and four
  from one multilingual/non-English topic;
- **3 committed synthetic canaries**: adapter/schema/replay regression only.

The real candidates form the human-agreement denominator. Synthetic canaries
are reported separately and cannot improve a provider-quality metric.

Across the 12 real selections, the private selector should cover the following
rationale categories without asserting the final label: likely direct,
substantial, partial, not relevant, insufficient preview, metadata warning,
non-English uncertainty, pairwise boundary ambiguity, and one likely
order-sensitive pair. Selection must not use Judge output.

This 12+3 design is **Proposed Class D policy**. Rationale: it is large enough to
exercise all architecture paths and three topics while keeping human review and
hosted data volume small. Alternatives are 12 real only (less adapter isolation)
or 15 real plus synthetic preflight (stronger coverage, higher human/call cost).
Tradeoff: no statistical significance or stable subgroup estimate is possible.
Owner approval is required. Revisit after any rubric/language/provider change or
if a category cannot be represented safely.

## Private ignored manifest

The later manifest must live under an owner-approved ignored calibration root
and contain no title or abstract:

```json
{
  "schema_version": "reagent-real-judge-calibration-manifest/v1",
  "evaluation_id": "owner-assigned",
  "entries": [
    {
      "topic_id": "string",
      "candidate_id": "pseudonymous string",
      "candidate_checksum": "sha256:...",
      "selection_rationale_category": "enum",
      "human_reference_status": "NOT_STARTED|PRIMARY_COMPLETE|CHECK_REQUIRED|LOCKED",
      "retention_expires_at": "RFC3339"
    }
  ],
  "manifest_checksum": "sha256:..."
}
```

Candidate text is resolved from the existing private artifact only during an
approved execution. The manifest is immutable after the first provider
reservation; a change creates a new evaluation ID and checksum.

## Frozen call plan

1. Run all three synthetic canaries through the future real adapter only after
   authorization. These verify schema, identity, usage, and span handling; they
   are not calibration labels.
2. Run pointwise prompt A once for every 15 candidate.
3. Run pointwise prompt B once for every 15 candidate.
4. Select three real pairs before viewing model output: one pair per topic,
   adjacent or ambiguous under the blinded human reference/selection rationale.
5. Run each pair in left/right and right/left order: six pairwise logical calls.
6. Verify operation settlement, checksums, schema, evidence spans, and exact
   model identity before aggregation.
7. Generate a calibration report with synthetic and real evidence separated.
8. Replay from journal/artifacts. Replay must make zero provider calls and zero
   reservations.

Logical calls: 30 pointwise + 6 mirrored pairwise = **36**. The three synthetic
records are included in the 30 pointwise calls. Maximum physical attempts are
42 under the retry budget in `REAL_JUDGE_COST_MODEL.md`.

## Pointwise interpretation

Prompt A and B are equivalent paraphrases sharing one rubric and output schema.
They are not independent model families. Report:

- exact-label agreement;
- adjacent-label agreement using the ordered sequence `NOT_RELEVANT`,
  `PARTIALLY_RELEVANT`, `RELEVANT`, `HIGHLY_RELEVANT`;
- CANNOT_JUDGE agreement separately;
- per-candidate confidence variance;
- any systematic directional shift between A and B.

Do not majority-vote two labels. Any disagreement remains a human-audit case.

## Pairwise interpretation

- Pair inputs include only topic, pseudonymous candidate IDs, titles, bounded
  previews, and rubric scope.
- Output is left ID, right ID, or `TIE`, plus a concise topical-relevance reason.
- Canonicalize the mirrored result back to original IDs.
- `order_consistent=true` only when both orders select the same canonical ID or
  both return `TIE`.
- A pairwise/pointwise conflict occurs when a stable pairwise preference is
  irreconcilable with the pointwise ordinal labels, or when mirrored order is
  inconsistent.
- Pairwise results route cases to audit. They never assign or overwrite a
  pointwise relevance label.

Three pairs/six calls is **Proposed Class D policy**. It avoids an all-pairs
tournament while guaranteeing each topic has an order-bias probe. Alternatives:
two pairs (cheaper, misses a topic) or five pairs (more signal, more cost).
Revisit if any pair is unusable or if order inconsistency exceeds the proposed
gate.

## Metrics

### Structured-output reliability

- final schema-valid response rate;
- first-attempt schema-valid response rate;
- retry rate;
- malformed, refusal, truncation, and normalized failure rates.

### Repeated-run stability

- A/B exact-label agreement;
- A/B adjacent-label agreement;
- label-transition matrix;
- confidence mean, median, and within-candidate variance.

### Human agreement

- exact-label agreement on the 12 real candidates;
- linearly weighted Cohen's kappa where the data support it, reported with its
  tiny-sample warning;
- adjacent-label agreement;
- disagreement rate;
- CANNOT_JUDGE agreement;
- human override rate.

The primary-reference label is used for items not independently checked. For
checked items, the locked resolution label is used. These are human-reference
labels, not expert gold.

### Evidence fidelity

- supporting-span presence for every non-CANNOT pointwise result;
- normalized exact-substring presence in the exact supplied preview;
- unsupported-reason rate, manually audited on disagreements and the selected
  random sample.

### Pairwise

- mirrored-order consistency;
- TIE rate;
- pairwise/pointwise conflict rate.

### Multilingual

- English and non-English exact/adjacent human agreement shown separately;
- non-English CANNOT_JUDGE rate;
- non-English A/B disagreement;
- translation uncertainty only if a separately approved translation path is
  later added. V1 proposes no machine translation.

### Engineering

- latency per attempt and p50/p95 descriptively;
- input/output/cache/reasoning tokens;
- estimated, reserved, and settled cost;
- retry/failure count;
- ProviderOperation reserved/attempted/settled counts;
- request-ID completeness;
- replay calls/reservations.

No confidence interval, significance claim, or subgroup ranking should be
presented as reliable for n=12.

## Result classification

- **Code acceptance:** adapter and architecture tests pass. This says nothing
  about model quality.
- **Calibration acceptance:** every blocking gate in
  `REAL_JUDGE_PASS_FAIL_GATES.md` passes and the owner reviews warnings.
- **Permission for full-pool judgment:** prohibited by this protocol regardless
  of calibration outcome; requires a later explicit owner authorization.

## No-execution record

Phase 9B-2C-3A created this contract only. It made no LLM/OpenAlex request,
selected no real candidate, generated no label, imported no human judgment, and
calculated no real metric.

