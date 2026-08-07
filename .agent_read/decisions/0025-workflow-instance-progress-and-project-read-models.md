# 0025: Workflow-instance Progress and Project read models

- Status: Accepted
- Date: 2026-08-07

## Context

NIGHT-B1 through NIGHT-B4 established Projects with multiple independently
identified Workflow Instances, including multiple instances of the same
Workflow Definition. The historical Progress contract was Project/Package
scoped and its Project view assumed Literature Search. Leaving that contract
unchanged would allow two instances to share a history and would make the
frontend infer Project state from unrelated endpoints.

Research progress and local Capsule installation are also separate facts. An
acknowledged installation does not mean that research is complete, and a
Progress Report is bounded cloud continuity rather than a Workspace backup.

## Decision

Every persisted Progress Report is bound to `project_id` and
`workflow_instance_id`. New Packages use an exact persisted Capsule-artifact
binding. Only an accepted standalone legacy Literature Search Package may use
the frozen deterministic B1 instance mapping. Display names, Workflow keys,
directory names, and "first instance" selection are never identity sources.

Migration `20260806_0011` non-destructively backfills historical Literature
Search reports to the deterministic legacy instance, preserves their IDs,
timestamps, JSON, bytes, checksums, artifact metadata and idempotency evidence,
then enforces the Project/Instance foreign key. Ambiguous or missing legacy
identity aborts the migration.

Workflow and Project progress are derived read models over immutable report
history. Latest report ordering is deterministic and each projection keeps its
Workflow Instance identity. Project aggregation is a non-linear list/graph of
instance states and counts; it has no overall completion percentage. Research
status, instance lifecycle, cloud desired state, and client-reported local
installation state remain distinct fields.

The canonical Project frontend navigation is Overview, Workflows, Progress,
and Help. The Workflow Board is driven by Registry, Instance, Manifest,
Progress, and acknowledgement data. Production renders only actual Registry
records; unratified Workflow IDs or executable Capsules are not fabricated.
Existing Literature Search result routes remain compatible.

## Consequences

Two Literature Search instances have isolated histories, cards, latest state,
and filters. Retiring an instance keeps all historical Progress. Project pages
can load one bounded aggregate instead of issuing a per-instance request.
Historical standalone upload/retry remains compatible, while new-style
clients must present exact instance identity.

Typed cross-Workflow Artifact references and materialization remain absent.
Artifact fields shown by Progress are metadata only. Idea Discovery and every
other new executable Workflow remain deferred.

## Alternatives considered

- Binding reports only to a Workflow Definition was rejected because it
  collapses multiple instances of the same type.
- Selecting the first matching Workflow Instance was rejected because it is
  ambiguous and unsafe once a Project has multiple Literature Search instances.
- Persisting another mutable current-status table was rejected because it
  would require dual writes with immutable Progress history.
- A Project completion percentage was rejected because Workflows are optional,
  repeatable, cyclic, and non-linear.
- Hardcoding five Workflow cards in the frontend was rejected because only
  Literature Search currently has a ratified production Registry identity.
