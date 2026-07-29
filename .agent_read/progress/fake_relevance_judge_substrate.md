# Phase 9B-2C-2: Fake Relevance Judge Substrate

Date: 2026-07-29  
Status: implementation and regression verification complete  
Scope: synthetic candidates and deterministic Fake Judges only

## Outcome

ReAgent now has an end-to-end automated-silver evaluation substrate without a
real model adapter. It builds bounded preview-only requests, executes two
independently versioned pointwise fixture runs, optionally performs a mirrored
pairwise check, records zero-cost ProviderOperations, aggregates conservative
dispositions, creates a pending human-audit queue, and reports raw versus
audited synthetic silver metrics.

This phase did not load or label an OpenAlex candidate, fill a human result,
change an old review packet, call a network, or claim expert ground truth.

## Contracts and registry

- `AutomatedJudgmentRequest` excludes rank, deterministic score, citations,
  provider relevance score, other judgments, and human labels. Unknown fields
  fail closed.
- `AutomatedJudgment` records provider/model/snapshot/adapter, prompt and rubric
  identity, label/confidence/evidence/reason/uncertainty, request/output
  checksums, usage, latency, and time.
- Mirrored pairwise, consensus, audit request/result/queue, and silver metric
  contracts are frozen and canonically serializable.
- The immutable registry contains `relevance-pointwise-a/v1`,
  `relevance-pointwise-b/v1`, and
  `relevance-pairwise-mirrored/v1`. Prompts restrict assessment to topical
  relevance and prohibit scientific-quality inference.

## Fake adapter and orchestration

`FakeAutomatedRelevanceJudge` is configured by candidate ID and prompt version.
It never computes a label from title or preview text. Supporting evidence must
match an exact short substring of the supplied synthetic preview. Fixture flags
produce controlled malformed output, timeout, provider failure, disagreement,
low confidence, and order bias.

Each logical call reserves, commits, starts, commits, and settles a
ProviderOperation in the evaluation-private append-only journal. Successful and
failed receipts are immutable artifacts. Aggregation refuses unsettled
operations. A completed `synthetic_run.json` is replayed from immutable storage
without calling the Fake Judge.

No PostgreSQL table was needed.

## TEST_POLICY_ONLY

The implemented policy version is
`reagent-silver-aggregation/TEST_POLICY_ONLY/v1`:

- two agreeing relevant labels at confidence at least 0.80, with evidence and no
  conflict/warning, become `AUTO_ACCEPTED`;
- two agreeing `NOT_RELEVANT` labels under the same conditions become
  `AUTO_REJECTED`;
- every other path becomes `NEEDS_HUMAN_REVIEW`;
- all required cases plus a deterministic 10% per-topic consensus sample enter
  audit, with at least one eligible sample per topic;
- all items are retained above the 20-item burden cap and queue state becomes
  `AUDIT_CAP_EXCEEDED`.

These values are synthetic test controls. ADR 0005 does not approve them for a
real Judge.

## Synthetic fixture evidence

The committed `evaluation/fixtures/synthetic_silver_v1.json` contains 20
invented records: highly relevant, relevant, partial, not relevant, cannot
judge, disagreement, low confidence, missing span, pairwise conflict,
non-English, metadata warning, random-audit eligible consensus, malformed
output, and timeout/failure paths.

Observed deterministic command result:

- candidates: 20;
- pointwise calls attempted: 40;
- successful pointwise judgments: 37;
- mirrored pairwise calls: 2;
- settled ProviderOperations: 42;
- dispositions: 7 auto accepted, 3 auto rejected, 10 human review;
- audit queue: 10 required plus 1 sampled consensus;
- Raw Silver Precision@5: 0.8;
- Raw Silver Precision@10: 0.7;
- audited-silver metrics: unavailable, because no `HumanAuditResult` exists;
- replay: zero additional Judge calls.

These values reflect fixture construction and code-path coverage, not Judge
accuracy, calibration, multilingual performance, or scientific relevance.

## Command

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  judge-synthetic synthetic-silver-v1
```

The default output is under the ignored `runtime_data/evaluations/openalex`
root. No generated evidence is committed.

## Verification

Focused substrate test:

```text
conda run --no-capture-output -n reagent-dev \
  python -m pytest -q backend/research/tests/test_fake_relevance_judge.py
exit 0: 15 passed
```

Required focused research regression:

```text
conda run --no-capture-output -n reagent-dev \
  python -m pytest -q backend/research/tests
exit 0: 105 passed
```

Required full backend regression:

```text
conda run --no-capture-output -n reagent-dev \
  python -m pytest -q backend
exit 0: 188 passed, 18 skipped
```

Required compile check:

```text
conda run --no-capture-output -n reagent-dev \
  python -m compileall -q backend
exit 0
```

Synthetic CLI acceptance used evaluation ID `synthetic-silver-v1`, exited 0,
reported the deterministic counts above, and verified zero-call replay. The
second command invocation reconstructed the run after process restart with
status `resumed`, still at 42 operations and zero additional Judge calls. The
retained generated root is
`runtime_data/evaluations/openalex/synthetic-silver-v1/`; it is ignored.
PostgreSQL tests were not separately run because no SQL persistence changed.
Frontend tests were not run because no frontend or API source changed.

## Compatibility and retention

- OpenAlex adapter and multilingual execution code are unchanged.
- `guided-literature-review@2.0.0` is unchanged.
- Fake paper search remains the default.
- No real Judge adapter, SDK, API key, machine translation, Semantic Scholar,
  Crossref, or relevance label for live data exists.
- Existing reviewer A/B packets and retained live roots are untouched.
- Synthetic generated artifacts can be removed only by explicit owner action:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  clean synthetic-silver-v1 \
  --confirm synthetic-silver-v1
```

## Next milestone

Design and owner-approve a bounded real-Judge calibration contract and
calibration subset. Execution remains blocked on provider/model/snapshot, key,
budget, retention, thresholds, and explicit authorization of the selected
candidate subset.
