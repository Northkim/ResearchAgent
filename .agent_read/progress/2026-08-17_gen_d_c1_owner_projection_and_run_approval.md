# GEN-D-C1 Owner projection and Run Approval integration

## Authorized change packet

Status: IMPLEMENTATION AUTHORIZED by the Owner's GEN-D-C1 directive.

### Problem

Experiment 0.6 Workflow Detail currently derives pre-Artifact readiness from
Artifact presentation blocks, leaks durable checkpoint codes into primary copy,
and does not expose the already-published controlled-local Run Approval action.
The exact R1 approval primitive exists, but the frontend has no typed client or
Owner action integration.

### Source-of-truth recovery

- Pre-Artifact lifecycle authority: existing Project Progress / Workflow Instance
  action and `latest_summary` checkpoint projection.
- Run authorization authority: the existing
  `reagent.controlled-local-run-approval/v0.1` observe/approve/reject endpoints.
- Post-Artifact scientific content authority: exact `experiment-record/v4`
  Artifact plus its exact bounded presentation companion.
- Local-only plan/package/runtime bytes and absolute launcher paths are not Cloud
  presentation data and must not be invented.

No missing persistence primitive was found. The Cloud-visible checkpoint supports
truthful aggregate readiness when individual local facts are unavailable, and the
R1 projection supplies the exact bounded execution summary and approval lineage.

### Bounded implementation

- Add frontend DTOs, API client methods, query keys, and hooks for observing and
  deciding the existing controlled-local approval request.
- Add an explicit Experiment checkpoint-to-Owner projection and pre/post Artifact
  merge rule in Workflow Detail.
- Render Resource, preparation prerequisite/completion, runtime, Run Approval,
  post-approval local handoff, and Technical details from their existing exact
  authorities.
- Keep checksums and raw internal codes confined to collapsed Technical details.
- Add focused component coverage and a repository-native Playwright E6 fixture/spec
  if the existing controlled fixture cannot express the required states.

### Explicit non-goals

No generic Experiment contract, Capability, Resource, runtime, package, v4,
Capsule, controlled-local approval persistence, hosted approval, Path B,
downstream Workflow, Full Research preset, Terminal architecture, D1, or migration
change is authorized.

### Verification contract

Focused Vitest coverage, full affected frontend regression, TypeScript, ESLint,
production Next.js build, `git diff --check`, Alembic sole-head check, historical
0.4/0.5 and non-Experiment component smoke, then repository-native Playwright E6
against system Chrome and a marked disposable PostgreSQL stack. Verifier
independence is LIMITED because implementation and verification share this agent;
the real controlled browser/database evidence is not substituted.

### Stop conditions

Stop for `GEN_D_C1_PERSISTENCE_EXPANSION` if new persistence is required, or for
architecture expansion if the frozen contracts must change. Once browser E6
starts, newly discovered defects are reported rather than patched silently.

## Completion evidence

Status: PASS, ready for Owner review.

The frontend now derives pre-Artifact readiness from the durable Experiment
checkpoint and exact controlled-local approval projection. All current checkpoint
codes have bounded Owner titles/actions; Resource, preparation prerequisite/
completion, and runtime states no longer depend on Artifact presentation. Exact
run details come from the R1 bounded summary. Owner approval and request-changes
use the existing R1 decision endpoint with a stable request-bound idempotency key.
Successful approval says to continue locally; Cloud does not dispatch execution.
Checksums and provenance remain inside collapsed Technical details.

Verification independence is LIMITED. Focused Workflow Detail passed `20`; full
frontend passed `17 files / 59 tests`; TypeScript, ESLint, production Next.js
build, compile, and diff checks passed. Generic publication/R1/Artifact regressions
passed `28` with one existing skip. The historical runtime suite passed `9` through
the approved macOS no-egress boundary after its sandboxed invocation could not
exercise sandbox-exec.

Repository-native Playwright E6 used system Google Chrome, real controlled
FastAPI/Next.js, and a fresh marked disposable PostgreSQL database through
`20260817_0030`. The final run passed `5/5`, including the complete GEN-D-C1 state
journey and existing controlled journeys. The browser exercised actual approve,
reject, and stale-plan paths. Fourteen bounded PNG screenshots are retained under
ignored `frontend/test-results/gen-d-c1-e6/screenshots/`. All disposable databases
were dropped and controlled processes stopped. No Owner database, Workspace, D1,
migration, immutable publication, or scientific dependency was touched.
