# Real Grounded Report Live Acceptance Protocol

Date: 2026-07-30  
Status: **Proposed Phase 9C-2A contract; execution is not authorized**

## Objective and non-claims

The proposed acceptance answers one narrow question:

> Can one current hosted model use the existing
> `guided-literature-review@3.0.0` workflow to produce an abstract-only,
> citation-aware, provenance-valid literature report from exactly three
> owner-approved real papers?

It measures structured-output reliability, citation-label preservation,
evidence-span containment, claim/evidence alignment, inference labelling,
disclosures, report readability, usage/cost/latency, operation settlement,
failure handling, restart, artifact reload, and zero-call completed replay.

It does **not** establish scientific correctness, expert-level review,
systematic-review compliance, full-paper understanding, production readiness,
provider superiority, multilingual generalization, or statistical
significance.

## Frozen acceptance shape

All numeric limits are **Proposed Class D ReAgent policy**. They are informed
by the verified synthetic V3 path, current provider contracts, and the need for
a low-exposure supervised test. They are not research-established thresholds
and require owner approval.

1. Use exactly three papers from one topic.
2. Bind the exact ordered paper set through the existing approval fingerprint.
3. Materialize abstract-only `SourceContent`; no PDF or full text.
4. Execute, in approved order:
   - three summary/evidence operations;
   - one cross-paper claim-synthesis operation;
   - one report-composition operation;
   - at most one mechanical repair operation.
5. Allow at most six logical operations and eight total attempts.
6. Enforce aggregate caps of 60,000 input tokens, 20,000 output tokens,
   15 minutes, and USD 1.00.
7. Use one provider/model only. No fallback, comparison, batch, prompt-cache
   discount assumption, tool call, or parallel provider race.
8. Run the complete V3 provenance gate before any publication.
9. Obtain one human acceptance decision.
10. Reconstruct in a fresh process and prove that completed replay makes zero
    generation calls and reloads identical report, provenance, and corpus
    checksums.

The stricter live envelope is below the Phase 9C-1 substrate limits of eight
logical calls, eleven attempts, 90,000/32,000 tokens, 20 minutes, and USD 1.25.
It reduces financial and content exposure while retaining one repair and two
transient retry attempts.

## Report policy

- Report language: English.
- Preserve original paper titles.
- Use only deterministic `[P1]`, `[P2]`, and `[P3]`.
- Show the abstract-only disclosure prominently.
- Mark unavailable information as unavailable.
- Keep source-stated limitations distinct from system inference.
- Qualify research gaps as tentative.
- Use paraphrased evidence in the report; bounded private spans are not
  displayed by default.
- Do not claim scientific correctness, full-text analysis, expert review, or
  systematic-review compliance.

Chinese report generation is deferred until the first English acceptance
passes. This does not claim English is intrinsically more reliable; it limits
the first experiment to one output-language variable.

## Execution states

`PREFLIGHT_BLOCKED` means no call started. `RUNNING_PRIVATE` means operations
may execute but no report is published. `PROVIDER_FAILED`,
`GROUNDING_FAILED`, `PUBLICATION_BLOCKED`, and `HUMAN_REJECTED` are terminal
private outcomes. `ACCEPTED` and `ACCEPTED_WITH_EDITS` require all mechanical
gates; the latter creates a new report version and requires revalidation.

No partial report may be presented as completed. Any ambiguous transport
settlement remains unsettled and prevents retry until reconciled.

## Phase boundaries

Phase 9C-2B implementation approval and live execution approval should be
recorded separately:

- implementation approval permits the injected transport, explicit live
  composition, network-free tests, and preflight command;
- execution approval names the account, model, retention policy, key
  availability, exact private manifest, budget, reviewer, and live window.

This document provides neither approval.

