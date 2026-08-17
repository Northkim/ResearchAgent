# Experiment 0.5 sklearn reference-slice freeze

- Date: 2026-08-17
- Status: PASS
- Scope: governance/reference-slice freeze only

## Classification

`REFERENCE_SLICE_IMPLEMENTATION = PRESENT`

`REFERENCE_SLICE_CONTRACT_REGRESSION = PASS`

`REFERENCE_SLICE_SUPPORTED_RUNTIME_QUALIFICATION = PENDING`

`REFERENCE_SLICE_REAL_CODEX_OWNER_LIFECYCLE = PENDING`

`GENERIC_DEFAULT_STATUS = NOT_EXPERIMENT_0_5`

`D1 = PAUSED`

Experiment Definition 0.5.0, Capsule 0.8.0, `experiment-record/v3`, and
`SKLEARN_TABULAR_CLASSIFICATION_V1` are frozen as the
`SKLEARN_REFERENCE_SLICE`. ADR 0042 remains the historical authority for why
the constrained slice was built. ADR 0043 supersedes only its interpretation as
the generic default Path A and records the research-domain-agnostic forward
direction.

## Immutable reference identity

- Workflow: `reproduction-experiment-local-experimental@0.5.0`
- Contract checksum:
  `sha256:23b6e3cae5746c8589927d2380595df61d01c6fb3f487cf47e09753f3ef8b600`
- Capsule: `capsule-5e02c832357355b6036b7e21cfbae306@0.8.0`
- Capsule checksum:
  `sha256:5e02c832357355b6036b7e21cfbae3061306b16268d04ee75c764c56c759bd98`
- Artifact: `experiment-record/v3`
- Publication migration: `20260817_0027`

The forward generic identities `0.6.0`, Capsule `0.9.0`, and
`experiment-record/v4` are reserved but not implemented or published. The
future reference Skill
`sklearn-tabular-classification-preparation-local-builtin@0.1.0` is reserved as
a `REFERENCE_PREPARATION_ADAPTER`.

## Governance boundary

The forward scope is generic local computational experiments within the existing
controlled-local boundary, not universal physical, human-subject, HPC,
distributed, notebook-orchestration, or hostile-code execution. ReAgent Core
owns generic lifecycle, exact objective/input and capability identity, Resource
readiness, approvals, package identity, runtime compatibility, execution,
normalized status, provenance, and finalization. Codex and reviewed Experiment
Capabilities own domain-specific methodology-to-implementation and evaluation
knowledge. Capability priority cannot silently resolve materially different
scientific choices; ADR 0043 defines the exact selection rule.

Cloud presentation persistence, D1 0.4-to-0.6 transition mechanics, Full
Research preset advancement, and scientific runtime provisioning remain
explicitly deferred. No GEN implementation, Project/Workspace/Resource/Artifact
state change, dependency installation, or KNN/Wine execution belongs to this
freeze.

## Verification evidence

- Focused EP-A/EP-B1 contract, prepared-path, v3, and publication-authority
  tests: `20 passed, 1 skipped`; the one skip was the guarded PostgreSQL case
  before its explicit disposable fixture was supplied.
- Guarded disposable PostgreSQL publication qualification: `2 passed` after a
  fresh upgrade through 0027 and `alembic check`; the generated database was
  identity-verified and dropped.
- A second explicitly marked disposable database passed upgrade through 0027,
  downgrade to 0026, re-upgrade to 0027, and `alembic check`; it was
  identity-verified before deletion and confirmed absent afterward.
- Historical Experiment 0.4 regression: `9 passed`, including no-egress and
  credential scrubbing, truthful timeout/nonzero/evaluation behavior, and
  exactly-once v2 finalization. The first managed-sandbox run could not nest
  macOS `sandbox-exec` (`6 passed, 3 failed`); the exact suite passed outside
  that outer sandbox so the product's own enforcement boundary could operate.
- Python source compile check: 9 affected production/migration modules passed.
- Experiment 0.5 contract checksum, Capsule 0.8 checksum, and Capsule ID match
  migration 0027 before and after governance edits.
- `git diff --check` passed before staging; staged diff checks are recorded at
  the commit gate.

No NumPy/scikit-learn installation or KNN/Wine execution was performed. The
supported-runtime and real Codex Owner lifecycle qualifications remain pending
and are not relabeled as contract regression failures.
