# Progress: Bounded Real-Judge Calibration Contract

Date: 2026-07-29
Phase: 9B-2C-3A
Status: Documentation contract complete; owner approval pending

## Outcome

Phase 9B-2C-3A defined a bounded calibration experiment without implementing or
calling a real Judge. Proposed ADR 0006 remains Proposed.

The proposed experiment uses 12 private real candidates across two English and
one multilingual topic plus three synthetic adapter canaries; pointwise A/B for
all 15; three real pairs in both orders; a blinded primary human reference with
targeted secondary checking; exact supporting-span validation; ProviderOperation
settlement; and zero-call replay.

## Proposed provider

`claude-sonnet-5` is the proposed one-provider calibration candidate because its
canonical current ID has a documented fixed-snapshot contract. OpenAI
`gpt-5.6-terra` remains a fallback with an unresolved stronger dated pin.
Local `gpt-oss-20b` remains a privacy-sensitive engineering alternative but is
mostly-English and unvalidated for the multilingual task.

No provider/model is approved.

## Hard proposal

- 36 logical calls, 42 maximum attempts;
- 90,000 input / 9,984 output tokens;
- 15-minute runtime;
- conservative Sonnet standard-price estimate USD 0.41976;
- proposed cap USD 0.75;
- current authorized budget USD 0.00;
- 500-character preview maximum;
- ZDR required;
- request/response retention no more than 14 days;
- full-pool judgment prohibited after calibration without a later decision.

Every numeric value is Class D project policy and unapproved.

## Repository evidence

Created:

- `docs/evidence/REAL_JUDGE_CALIBRATION_EVIDENCE.md`
- `docs/evidence/REAL_JUDGE_PROVIDER_MATRIX.md`
- `docs/evidence/REAL_JUDGE_CALIBRATION_PROTOCOL.md`
- `docs/evidence/REAL_JUDGE_HUMAN_REFERENCE_PROTOCOL.md`
- `docs/evidence/REAL_JUDGE_DATA_RETENTION_POLICY.md`
- `docs/evidence/REAL_JUDGE_PASS_FAIL_GATES.md`
- `docs/evidence/REAL_JUDGE_COST_MODEL.md`
- `docs/evidence/REAL_JUDGE_PROMPT_FREEZE.md`
- `.agent_read/decisions/0006-bounded-real-judge-calibration.md`
- this progress record

Updated the automated-Judge evidence/matrix, search protocol/evidence register,
and project context to point to ADR 0006 and preserve the no-execution boundary.

## Safety record

- baseline: `a904ec1`;
- production source/dependencies/workflows: unchanged;
- runtime data/databases: unchanged;
- real LLM/OpenAlex calls: none;
- credentials read/printed/added: none;
- real candidates selected or judged: none;
- human labels/real metrics: none;
- blank two-human packets: untouched;
- runtime tests: not required and not run for this documentation phase.

## Open decisions and next milestone

All ADR 0006 owner approvals remain open, especially provider/model, key, ZDR,
preview permission, reviewers, budget, limits, gates, and retention.

Next permitted milestone: **approve or revise ADR 0006**. Execution is not
permitted until every blocking decision is explicit.

