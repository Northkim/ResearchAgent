# Post-D1 R3C — Generic Experiment browser entry

## Status

`R3C = PASS`

R3 remains open for controlled R3D product-width qualification.

## Ledger scope

- `D1-EXPERIMENT-ENTRY-01`
- Browser trust-boundary portion of `D1-EXPERIMENT-CAPABILITY-01`
- Browser run-plan/result portion of `D1-CHECKPOINT-PRESENTATION-01`

## Source changes

- Forward Experiment 0.8 routes through the existing custom Experiment detail.
- The detail queries exact `experiment-record/v5` outputs.
- Preparation and the Local command are unavailable until the exact required
  Research Idea binding is accepted.
- The shared exact Artifact selection component is rendered at `SELECT_INPUT`;
  an accepted binding remains inspectable/changeable secondarily.
- Generic Harness preparation is labelled `System path`, never `Reviewed`.
- Result validity refers to the exact scientific contract rather than claiming a
  reviewed Capability made the decision.

No backend/API/persistence/migration/publication/Artifact-schema change occurred.

## Evidence

- `frontend/tests/workflow-board.test.tsx`: 23 passed.
- TypeScript: passed.
- ESLint on changed source/tests: passed.
- Production Next.js build: passed (outside restricted sandbox because Turbopack
  starts an ephemeral loopback worker).

## Historical integrity

- Historical Experiment 0.6 continues to use v4 and its reviewed-path wording.
- Experiment 0.7 continues to use v5.
- Existing controlled-local run approval semantics are unchanged.
- Presentation remains optional and non-authoritative.
- No Owner D1 state was accessed.

## Safe next action

Run R3D against real FastAPI/Next.js, marked disposable PostgreSQL, a disposable
Workspace, and deterministic fake Harness execution. Do not close R3 from these
component tests alone.
