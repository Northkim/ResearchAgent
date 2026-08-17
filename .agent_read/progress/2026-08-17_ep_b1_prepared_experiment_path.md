# EP-B1 prepared Experiment Path A

- Date: 2026-08-17
- Status: BLOCKED_QUALIFICATION
- Scope: EP-B1 only

## Implemented

- Additive Experiment 0.5.0 / Capsule 0.8.0 publication at Alembic 0027.
- Exact required selected Idea input; no Literature or Resource requirement.
- Real methodology proposal, material-decision checkpoint, checksum-bound design approval.
- Typed deterministic `SKLEARN_TABULAR_CLASSIFICATION_V1` specification and Builder.
- Workflow-local candidate generation, fail-closed validation, atomic promotion,
  provider-neutral prepared-package receipt, and shared validated-package identity.
- Exact execution plan and one-use checksum-bound run approval.
- Reuse of the unchanged Experiment 0.4 no-egress process engine.
- Structured condition/metric/robustness evaluation and provider-neutral
  `experiment-record/v3` finalization.
- Durable recovery through methodology, design approval, package validation,
  run approval, execution/evaluation evidence, Owner review, and terminal Progress.
- Public Workspace exact-pin recognition and exact Idea materialization for 0.5/0.8.

## Verification evidence

- EP-B1/EP-A focused tests: 20 passed; PostgreSQL test skipped without its guarded fixture.
- Guarded disposable PostgreSQL: upgrade through 0027, `alembic check`, 2 publication
  tests, downgrade to 0026, and re-upgrade all passed; database dropped.
- Historical Experiment 0.4 regression: 9/9 passed in the supported macOS sandbox.
- Combined affected backend regression: 144 passed.
- Python compileall and `git diff --check`: passed.
- Generated KNN/Wine implementation executed in an already-installed auxiliary
  Python 3.10 environment: RAW, STANDARD_SCALER, MINMAX_SCALER; accuracy and
  macro_f1; nine robustness entries.
- Scope: 16 tracked files after handoff records; 4 test files; 1 additive migration;
  no frontend/API/ORM/ResourceReference/downstream publication changes.

## Blocking evidence

The supported `reagent-dev` runtime has neither NumPy nor scikit-learn. EP-B1
correctly refuses dependency installation, so the supported-runtime KNN/Wine
execution and full real Codex lifecycle cannot be qualified. An auxiliary
environment demonstrates Builder output but is not relabeled as the supported
runtime. The real Codex qualification must also receive explicit Owner answers
for consequential unspecified folds/repeats/seeds/neighbor scope.

No current D1 Project, Workspace, Resource, package, or research Workflow state
was modified. D1 remains paused; EP-B2/C/D were not implemented.

## Subsequent governance classification

ADR 0043 preserves this implementation and its immutable 0.5/0.8/v3 identities
as `SKLEARN_REFERENCE_SLICE`. This report remains the historical implementation
and qualification record; Experiment 0.5 is not the generic default Experiment
architecture. No GEN implementation is included in this slice.
