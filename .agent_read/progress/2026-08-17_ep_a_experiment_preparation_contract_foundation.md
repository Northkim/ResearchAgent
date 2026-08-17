# EP-A Experiment preparation contract foundation

- Date: 2026-08-17
- Baseline: `main` at `972377b0fdcb81fe5167a0feb90b4ba57f8893b7`
- Status: `PASS_EP_A_READY_FOR_REVIEW`
- Migration sole head: `20260815_0026` (unchanged)

## Implemented boundary

EP-A adds local, unpublished contract foundations only: methodology and design
approval, provider-neutral prepared-package receipt, shared validated package,
future one-use run approval, isolated `experiment-record/v3`, bounded exact
Artifact presentation, optional sanitized Git provenance, the reserved
SKLEARN tabular-classification Builder family, and an explicit unpublished
forward downstream compatibility map.

Historical Experiment 0.4/0.7/v2 and all published Writing/Review/Revision
contracts are unchanged. No Builder, Workflow/Capsule publication, package,
execution admission, API, UI, migration, persistence, ResourceReference,
network, Project, Workspace, or research state was added or changed.

## Verification

- Focused new plus historical contract/validator matrix: `62 passed`, three
  historical macOS execution tests deselected because EP-A forbids experiment
  execution.
- Python compile checks: passed.
- Alembic sole head: `20260815_0026`.
- `git diff --check`: passed.

An attempted sandbox run of the three historical runner tests failed at the
existing macOS no-egress enforcement boundary; no successful Experiment run or
package execution occurred. An outside-sandbox retry was denied as outside the
authorized EP-A scope and was not retried. Validator/golden regression evidence
for immutable v2 passed.

`VERIFIER_INDEPENDENCE = LIMITED` because the implementing session also ran the
focused verification. EP-B, EP-C, EP-D, publication, D1 continuation, package
creation, and experiment execution remain gated by new Owner authorization.
