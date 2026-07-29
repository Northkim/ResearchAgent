# Automated Silver Evaluation Contract Progress

Phase: 9B-2C-0  
Date: 2026-07-29  
Status: documentation contract complete; ADR 0005 remains Proposed

## Outcome

Phase 9B-2C-0 reframes the prototype evaluation as **automated silver-label
relevance evaluation with targeted human audit**. It is not expert ground truth.
It also proposes a separately owned multilingual SearchPlan expansion based on
explicit, versioned query variants.

No real LLM judge, translation, OpenAlex request, candidate regeneration,
judgment label, human-label import, metric calculation, source/dependency change,
or database was created.

## Frozen proposed contracts

- immutable request, judgment, consensus, audit-request, and audit-result schemas;
- five-label topical relevance rubric with preview-only supporting spans;
- two pointwise prompt versions plus selected mirrored pairwise consistency;
- conservative automated dispositions and fail-closed human routing;
- raw-silver versus audited-silver metric naming;
- reduced non-expert human-audit queue and burden cap;
- provider-independent judge and immutable prompt registry;
- ArtifactContentStorage + evaluation-private journal +
  ProviderOperationService reuse; no new table;
- bounded call/token/runtime/retry/failure/cost policy;
- QueryVariant and MultilingualSearchPlan schemas;
- exact DOI/ID merge, advisory title/year clustering, per-variant provenance and
  normalized coverage diagnostics;
- formal deferral, not deletion, of the two-human review method.

## Provider recommendation

Conditional Class D recommendation: calibrate OpenAI `gpt-5.6-terra` first,
compare a bounded subset with Anthropic `claude-sonnet-5`, and use no provider if
pinning, retention, usage, cost, or audit validation fails. `gpt-oss-20b` is a
feasible local comparison but its mostly-English training makes it an unsuitable
uncalibrated multilingual default.

No provider/model/key/budget is approved.

## Chinese-topic evidence

The pilot retained one OpenAlex result and zero normalized candidates. The
generic safe diagnostic proves a field-length boundary rejection but omits field
name and measured length. The exact field/limit cannot be recovered; it was not
guessed. The later plan adds field-specific safe diagnostics and boundary
fixtures without weakening the gate.

## Open owner decisions

Owner approval is required for the silver objective, provider/model/version,
key, money/call/token budgets, repetition/pairwise strategy, confidence
threshold, audit percentage/cap, partial/non-English routing, preview retention,
machine translation, query variants, metric gains, packet retention/cleanup, and
whether expert gold is deferred or cancelled.

## Next permitted milestone

Only **approve or revise ADR 0005**. After acceptance, choose exactly one
separate implementation milestone. No real judge implementation is permitted
until provider/model/cost/retention policies are approved.

