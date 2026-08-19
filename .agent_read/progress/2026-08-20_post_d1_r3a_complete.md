# Post-D1 R3A completion report

Status: **R3A COMPLETE — R3B NEXT**

Date: 2026-08-20

Commit: `e22be88`

R3A added only new, non-published source modules. It did not change Experiment
0.7 / Capsule 0.10 checksums, presets, migrations, APIs, frontend behavior, or the
protected Owner D1 state.

The new exact contracts identify `GENERIC_AGENT_HARNESS` as a system-owned
implementation path that is neither a reviewed ExperimentCapability nor User Skill
authority. They bind implementation specification, package validation, runtime
requirements, execution units, exact outputs, and resume state. The Workspace owns
mutable Generic Experiment state at
`.reagent/experiments/<workflow-instance-id>/`, outside immutable Capsule package
comparison, with an exact Project/Workflow ownership marker.

Environment discovery inspects only explicit existing Python candidates, reports
version/package incompatibility, and performs no installation, upgrade, download,
or environment creation. Execution resume reuses a completed unit only after its
declared output set and every output checksum still match the exact plan.

Evidence:

- 8 focused Generic Harness contract/Workspace tests passed;
- 52 historical Generic Experiment coordinator/publication/v5 tests passed, with
  one explicit real-Codex test skipped by its existing opt-in gate;
- Python compileall and `git diff --check` passed;
- historical publication files and Alembic head were unchanged.

Safe next action is R3B forward publication and lifecycle integration. R3A alone
does not claim a usable Generic Experiment path or close any ledger finding.
