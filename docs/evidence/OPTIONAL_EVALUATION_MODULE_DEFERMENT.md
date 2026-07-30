# Optional Evaluation Module Deferment

Date: 2026-07-30
Status: **DEFERRED — retained, not rejected**

## Route decision

The automated-relevance evaluation work is an optional evaluation module. Its
contracts, deterministic Fake Judge, aggregation, audit queue, tests, ADRs,
calibration design, and blank review packets remain technically valid and are
preserved. They are not required for the first useful ReAgent product version.

The product path now prioritizes an owner-approved, abstract-based grounded
literature report because it produces an immediately usable research artifact
from capabilities ReAgent already has: real discovery, exact paper-set
approval, provenance, durable artifacts, APIs, and report UI. A real Judge
calibration would measure a screening component but would not replace the Fake
LLM that currently writes the product output.

This is a priority and reviewer-availability decision, not a finding that the
earlier work was incorrect or wasted. The higher-rigor evaluation route remains
available.

## Preserved evidence

The following must not be deleted, weakened, or presented as current product
authorization:

- `AutomatedRelevanceJudge`, Fake Judge, aggregation, audit queue, and tests;
- ADR 0005 and ADR 0006;
- silver-label and calibration evidence documents;
- blank reviewer A/B packets and retained evaluation evidence.

## Resume triggers

Resume only through a new owner decision when one or more applies:

- retrieval-quality or automatic-screening claims become a release requirement;
- qualified reviewers and a calibration budget are available;
- the grounded-report path is stable enough to evaluate end-to-end quality;
- a deployment or research claim requires measured screening performance;
- the owner explicitly reactivates ADR 0006 and approves provider, model,
  abstract processing, ZDR, human reference labels, and spend.

## Still prohibited

No real Judge call, relevance label, full-pool automatic screening, Judge API
key, non-zero Judge spend, expert-gold claim, or deletion of review provenance is
authorized. ADR 0006 is Deferred, not Accepted.

