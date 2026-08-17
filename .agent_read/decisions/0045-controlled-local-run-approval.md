# 0045: Controlled-local Run Approval is Cloud authorization, not execution

- Status: Accepted
- Date: 2026-08-17

## Context

Experiment 0.6 executes only in the controlled Local Workspace, while the Owner
must authorize an exact prepared plan from the browser. The historical hosted
approval subsystem is coupled to hosted Workflow and Step Runs and dispatches
Cloud execution, so reusing it would violate both the frozen hosted boundary and
the local-execution topology.

## Decision

Use a dedicated Project/Workflow-Instance-scoped controlled-local approval
contract and table. Local reports an exact plan-checksum-bound bounded summary;
Cloud records an idempotent Owner approve/reject decision; Local observes and
atomically consumes that approval once for an exact attempt, revalidates the
plan, and only then calls the existing bounded-runner boundary. Cloud approval
never dispatches execution. Supersession prevents an older plan from
authorizing a newer one, and consumed approval is never recycled.

## Consequences

Browser authorization and local execution remain auditable without uploading
the full plan or local bytes. Database row locking and a unique active-request
constraint provide exactly-one consumption under races. Transport uncertainty
is recoverable through exact request, decision, and same-attempt consumption
idempotency. Multi-user authorization remains deferred under the accepted
loopback single-Owner deployment boundary.

## Alternatives considered

- Reuse hosted `/approvals`: rejected because it is keyed to hosted runs and
  dispatches hosted execution.
- Let the browser invoke Local directly: rejected because the browser must not
  write or execute in the Workspace.
- Store the complete execution plan in Cloud: rejected because the exact plan
  remains Local and a checksum plus bounded Owner summary is sufficient.
- Reuse a consumed authorization after launch failure: rejected because it
  breaks the one-attempt authority model.
