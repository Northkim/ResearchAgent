# 0049: Current exact plan governs Local Artifact readiness

- Status: Accepted
- Date: 2026-08-20

## Context

During D1, changing an exact Artifact binding left the prior Local input and its
receipt internally valid. The materializer could not distinguish that proven
ReAgent-managed copy from arbitrary user content, an unchanged sibling receipt
became invalid solely because the aggregate plan checksum changed, and offline
`workflow list` could still call the stale input runnable. Materialization also
required a separate manual Artifact Index refresh.

## Decision

The Local Workspace persists the last exact Cloud materialization plan observed
by a networked materialization operation. Local readiness is true only when every
entry in that current plan has its exact binding receipt under the same plan and
the target bytes match the entry's Artifact checksum and size.

ReAgent may atomically replace a prior input only when one valid receipt proves
that the target is the prior ReAgent-managed materialization. It stages and
validates the new exact Artifact, records a durable replacement intent, publishes
the target atomically, writes the current receipt, and preserves the superseded
receipt in managed history. Existing exact user or ambiguous files are not
claimed. A verified unchanged sibling may have its receipt reissued under the
new complete plan without copying its bytes again.

Normal materialization reconciles the exact Artifact Index itself and rechecks
the Cloud plan after local publication. A concurrent plan change is persisted
and fails closed; the just-materialized older plan is not runnable.

## Consequences

Binding replacement no longer needs manual movement of a proven managed input.
Stale bytes or receipts cannot advertise runnable under the last observed Cloud
plan. Recovery is possible across interruption between atomic target publication
and receipt publication. Offline readiness remains deliberately bounded: it
cannot discover a Cloud edit that no networked operation has observed.

The plan snapshot, replacement intent, and receipt history are Local coordination
metadata, not scientific evidence and not Cloud authority over Local bytes.

## Alternatives considered

Treating receipt self-consistency as readiness was rejected because it caused the
D1 stale-input defect. Overwriting any conflicting path was rejected because it
would violate user ownership. Making the aggregate plan checksum irrelevant was
rejected because whole-plan completion must remain atomic. Requiring a manual
Artifact refresh or operator file move was rejected as normal Owner orchestration.
