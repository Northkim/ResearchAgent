# Workflow Instance, Progress, and Continuity Design V0.1

> **Design only.** Existing Progress Report v0.2 bytes and projections remain
> unchanged until a separately approved backward-compatible implementation.

## 1. Instance and round model

A Workflow Definition describes a type. A Workflow Instance is a stable,
Project-owned occurrence of that type with exact Definition and Capsule pins.
The domain permits multiple instances of one Definition; the initial UI permits
at most one active instance per type. Retirement is reversible desired-state
metadata and never removes local or cloud history.

Rounds belong to a Workflow Instance. New rounds have both an append-only
integer sequence within the instance and a globally unique `round_id`. An
accepted report may advance only its bound instance chain. Cross-instance
report submission, round reuse, and checksum rebinding fail closed.

## 2. Legacy mapping

Current report v0.2 envelopes identify Project, Package, Workflow ID/version,
and integer execution round. Their exact bytes remain immutable. A compatibility
record deterministically maps the tuple `(project_id, package_id, workflow_id,
workflow_version)` to a legacy `workflow_instance_id`; the existing report ID,
original checksum, normalized checksum, and projection stay unchanged. New
per-instance projections reference that mapping. No historical report gains a
synthetic field inside its stored bytes.

Current local-session scopes remain valid only for existing Package behavior.
Future instance/workspace/report scopes use new version identifiers and exact
instance/round bindings.

## 3. Per-instance projection

The per-instance projection is derived from accepted Progress reports and
installation acknowledgements; it does not inspect the local filesystem. It
contains:

- Project and Workflow Instance identity;
- Workflow Definition/version and current desired Capsule pin;
- latest cloud-accepted round number and optional new-schema `round_id`;
- status and bounded current/next-action summary;
- last report identity and content checksums;
- typed Artifact metadata referenced by that report;
- manifest revision and installation acknowledgement known to cloud;
- sync uncertainty; and
- blocking Artifact/Skill/Resource dependencies.

Status is one of `NOT_STARTED`, `READY`, `RUNNING`, `UPLOAD_PENDING`,
`COMPLETED`, `FAILED`, `BLOCKED`, or `UNKNOWN_LOCAL_STATE`. `RUNNING` and
`UPLOAD_PENDING` may appear only from explicit local reports; absence of a
report is not evidence that no local work occurred.

## 4. Project aggregation

`GET /projects/{project_id}/progress` returns a graph/list, never a mandatory
pipeline:

```json
{
  "schema_version": "reagent.project-progress/v0.1",
  "project_id": "project-…",
  "manifest_revision": 4,
  "cloud_observed_at": "2026-08-06T12:00:00Z",
  "instances": [
    {
      "workflow_instance_id": "wfi-…",
      "workflow_definition_id": "literature-search-local-experimental",
      "status": "COMPLETED",
      "latest_round": 1,
      "latest_cloud_known_state": "One bounded round was accepted.",
      "sync_uncertainty": "LOCAL_STATE_UNKNOWN",
      "artifact_metadata": [],
      "blocking_dependencies": [],
      "recommended_next_workflows": ["idea-discovery"]
    }
  ],
  "dependency_edges": []
}
```

The `recommended_next_workflows` field is bounded product guidance, not cloud
research judgment and not automatic execution. Dependency edges state typed
Artifact requirements; they do not force Workflow order.

## 5. Knowledge qualifiers

Every view distinguishes:

- **cloud-known state:** accepted manifest, report, metadata, or ack;
- **local-reported state:** a bounded assertion supplied by a validated local
  client at a particular time; and
- **actual local state:** unknown to cloud after that observation.

Cloud copy must say “No Progress Report received” rather than assert that a
local round has not started. Installation acknowledgement means content was
verified at one logical Workspace event, not that it remains on every copy or
device.

## 6. Continuity Capsule

“Continuity Capsule” is an export view, not a Workflow Capsule and not a new
execution container. It may contain:

- bounded Project summary and owner decisions;
- desired manifest revision and Workflow Instance states;
- accepted Progress summaries and next actions;
- Artifact reference metadata and compatibility status;
- exact Skill pins and Resource bindings; and
- warnings about unavailable local content.

It excludes complete source trees, datasets, complete Artifact bytes, bearer
tokens, credentials, database URLs, private absolute paths, and full local
reports by default. Existing Progress Report original-byte retention remains
unchanged and is not generalized into Artifact storage.

## 7. Continuity claims

- **Project continuity: supported.** Cloud preserves identity, desired
  Workflows, configuration, Progress, and metadata.
- **Cognitive continuity: supported within bounded reports.** Decisions,
  summaries, references, and next actions can be reconstructed.
- **Execution continuity: partial.** Code, data, environments, complete outputs,
  and credentials require the Workspace, revision-pinned Resources, optional
  future backup, or explicit owner transfer.

The product must not claim that Progress Reports alone restore execution on a
new computer.
