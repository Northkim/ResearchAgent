# GEN-B generic Experiment coordinator and Capability isolation

- Date: 2026-08-17
- Status: `PASS_GEN_B_READY_FOR_REVIEW`
- Evidence: E2 internal/component, synthetic/fake-runner
- Verifier independence: `LIMITED`
- D1: `PAUSED`

## Change packet and authorization

The Owner request is the approved GEN-B design packet and explicit
implementation authorization. ADR 0043, the project plan, GEN-A contracts,
published identities, and source-of-truth policy align without conflict.
Scope is unpublished generic local computational orchestration only. Non-goals
remain GEN-C/publication, migration, API/frontend/Cloud persistence, Path B,
Terminal redesign, dependency installation, scientific execution, and D1.
Compatibility is forward-additive; 0.4/0.7/v2 and 0.5/0.8/v3 are prohibited
edit targets. Security retains explicit exact identities, no discovery/network,
Core-owned candidate roots, independent validation, no installs, and the
existing bounded-runner authority. Rollback may remove only these unpublished
GEN-B files and handoff notes. No Owner decision or source conflict remained.

Budget authorized: at most 6 production, 4 test, 2 governance, 12 total, 2,600
net lines, zero migrations. Actual: 3 production, 2 test, 2 governance, 7 total,
under 2,600 net lines, zero migrations.

## Implemented contract behavior

- Exact immutable Capability descriptors bind Skill, Capsule, interface,
  implementation entrypoint and all checksums. Resolution uses only an injected
  bounded tuple; no mutable registry or discovery exists.
- Support selection implements unsupported, needs-Owner-decision, one-supported,
  material-multiple, and explicitly fallback-equivalent multiple outcomes.
  Priority never resolves a material scientific choice.
- Typed checkpoints cover methodology, Capability selection, Design Approval,
  Resource readiness, preparation readiness, runtime incompatibility, run
  approval, result review, plus unsupported/no-PREPARE forward convergence.
- Design Approval remains Owner supplied. A durable exact binding couples it to
  the selected Capability evidence so later methodology/selection drift fails.
- Core retains only the opaque specification reference/checksum and validation
  receipt; only the Capability sees or validates domain fields.
- Resource, preparation, and runtime requirements/readiness remain distinct.
  Required unbound, metadata-only, unavailable, drifted, and checksum-mismatched
  Resource evidence stops fail-closed. No provider was added.
- Capability preparation receives a fresh Core-owned candidate directory. Core
  scans bytes independently and promotes only a valid package v0.2.
- Explicit local runtime candidates are checked for family, version,
  capabilities, dependencies, environment identity, and drift. No PATH scan or
  install occurs.
- Execution Plan v0.2 binds exact lifecycle, Resource, package, compatibility,
  launch, limits, network, expected-output and Capability-owned output-contract
  identity. Run Approval v0.2 is exact and one-use at handoff.
- Execution is delegated only to an injected bounded-runner collaborator.
  Capability code neither consumes approval nor invokes the runner.
- Core validates output identities/checksums/bounds but does not parse payloads.
  Only Capability evaluation parses domain results and returns normalized
  validity/evidence/limitations evidence.
- Valid Owner review enables unpublished v4 assembly. A minimal checksum-only
  continuation receipt distinguishes every required durable lifecycle stage.
- The sklearn forward wrapper is the only new module importing the frozen
  sklearn builder and is classified `REFERENCE_EXPERIMENT_CAPABILITY`.

## Verification packet

Requirement sources are the Owner GEN-B packet, ADR 0043, GEN-A contracts, and
the frozen historical identities. High-risk identity/drift/path/approval cases
are covered by synthetic CONTRACT/SERVICE_INTEGRATION fixtures at E1-E2.

- GEN-B focused: `10 passed`.
- GEN-B + GEN-A + 0.5/v3 contract set: `56 passed`.
- Frozen 0.4/v2 runtime: initial managed-sandbox run reproduced the known nested
  `sandbox-exec` limitation; the exact unchanged suite passed `9 passed` outside
  the outer sandbox, where its own no-egress mechanism operated.
- Full backend fail-fast: `337 passed, 7 skipped, 1 environment error`; the first
  error was the existing R3C PostgreSQL suite requiring unset
  `REAGENT_TEST_DATABASE_URL`. PostgreSQL/public API/browser/Workspace/Real Codex
  are not GEN-B evidence and are not claimed.
- Compileall, import/dependency scan, `git diff --check`, Alembic read-only sole
  head `20260817_0027`, and historical source checksums: PASS.
- Importing the sklearn reference wrapper reports NumPy and sklearn absent from
  loaded modules. No scientific dependency or Experiment was run.

Negative evidence includes exact descriptor drift, all support-selection modes,
missing/drifted approvals, zero/multiple Resource and dependency declarations,
metadata-only/drifted/mismatched Resources, missing preparation capability,
invalid candidate/no promotion, traversal-safe paths, symlink/hardlink/special
file/case-collision rejection, incompatible/non-Python/environment-drift runtime,
plan/approval drift, consumed approval, invalid and insufficient evidence, and
Capabilities without PREPARE or PRESENT.

`VERIFICATION_STATUS = PASS_AT_DECLARED_LEVEL` for unpublished GEN-B E2.
No E4-E9 or public-product claim is made. No implementation, contract, or
architecture drift finding remains within GEN-B. GEN-C and D1 remain closed.
