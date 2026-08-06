# 0024: Pull sync, Installed Workspace Lock, and installation acknowledgement

- Status: Accepted
- Date: 2026-08-07

## Context

ADR 0022 froze pull-based Project Workspace synchronization and ADR 0023
implemented identity/bootstrap plus non-destructive legacy Package adoption.
NIGHT-B4 must make cloud desired state installable without turning the B3
Capsule registry into a second mutable truth source, overwriting local research
state, or claiming that cloud acknowledgement proves possession of local bytes.

## Decision

The cloud endpoints are `POST /projects/{project_id}/workspace/sync-plan` and
`POST /projects/{project_id}/workspace/sync-ack`. A plan contains the exact
current Desired Manifest revision/checksum, deterministic per-instance actions,
and a Project/Workflow-Instance/Capsule-bound acquisition record. Downloadable
Literature Search Capsules are persisted in
`local_workflow_capsule_artifacts`; every additional instance receives its own
deterministic Package identity and archive binding. Planned Workflows never
receive an artifact.

The canonical local installed-state source is
`.reagent/installed-lock.json` using
`reagent.workspace-installed-lock/v0.1`. The lock binds exact pins and an
immutable-contract checksum but excludes declared mutable outputs, memory,
Progress and receipts. `.reagent/capsule-registry.json` is retained unchanged
as legacy adoption evidence and is read only to perform one verified,
idempotent migration into the Installed Lock; it is never dual-written.

`python reagent_local.py sync <workspace>` is an explicit owner-authorized
pull. It uses an OS advisory write lock, same-filesystem staging, archive and
identity verification, atomic per-Capsule publication, a checksummed recovery
journal, atomic Installed Lock replacement, and a pending acknowledgement
envelope. Retired/not-desired Capsules remain locally retained. Exact-pin
upgrade in place and deletion are forbidden.

Cloud acknowledgement is a checksum-bound client installation report, not
cloud verification or backup of local files. It is stored in
`workspace_installation_acknowledgements`, bound to the current Project,
Workspace and Manifest, and idempotent by key and payload. A network failure or
local receipt crash leaves the verified Lock and Capsules intact; retry reuses
the same envelope and idempotency key. A stale Manifest acknowledgement is
rejected and requires a new plan.

## Consequences

An adopted Capsule migrates without download or mutable-state rewrite; a
missing Literature Search Capsule can be safely acquired and installed.
Installation state survives process/database restart, while cloud and UI must
still distinguish client-reported installation from actual current local
files. Multi-Workflow Progress, Artifact handoff, new executable Workflows,
background sync, deletion, in-place upgrades, device sync and Workspace backup
remain deferred.

## Alternatives considered

- Continuing to update the B3 registry was rejected because two writable local
  truth sources can diverge.
- Treating acknowledgement as proof or backup of local bytes was rejected
  because the cloud cannot inspect the Workspace.
- Overwriting a Capsule on version mismatch was rejected because mutable
  research state cannot be safely merged implicitly.
- Automatically syncing from `run` or the browser was rejected because local
  filesystem mutation requires an explicit owner command.
