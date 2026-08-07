# Project Workflows and Progress

NIGHT-B5 adds a Project control surface for multiple Workflow Instances. It
does not change the cloud/local execution boundary: ReAgent Cloud stores
configuration, bounded Progress Reports, projections, and installation
acknowledgement metadata; the complete research files remain in the local
Project Workspace.

## Project navigation

Every Project has four product routes:

- **Overview** summarizes actual Workflow Instances, recent activity, current
  Desired Manifest revision, and the latest client-reported installation state.
- **Workflows** lists Registry-backed Workflow Instances and keeps lifecycle,
  research progress, desired state, and installation knowledge separate.
- **Progress** shows a paginated Project history and filters by exact Workflow
  Instance. Two instances of the same Workflow type remain distinct.
- **Help** explains the current cloud/local workflow and recovery boundary.

The navigation intentionally does not expose empty Artifacts, Resources,
Skills, Activity, or Settings sections. Literature Search is currently the only
production Registry entry and executable Workflow. No unratified IDs or fake
Capsules are presented for later Workflows.

## Progress identity

New Progress Reports belong to both a Project and an exact Workflow Instance.
An adopted or synchronized Capsule reads the trusted identity from its
Package/Capsule contract. A supported standalone legacy Literature Search
Package maps through its verified Package/Project binding and the frozen B1
deterministic instance rule. Directory names and display labels are not
identity.

Upload retry remains idempotent. An exact retry returns the canonical receipt;
reusing an identity with different bytes is rejected and never overwrites
history. Retiring a Workflow Instance does not delete or reassign its reports.

## Reading status correctly

The UI presents independent dimensions:

- Workflow lifecycle, such as active or retired;
- research progress from the latest machine-readable Progress Report, or not
  started when no report exists;
- cloud desired state from the current Project Manifest;
- local installation knowledge reported by acknowledgement.

`ACKNOWLEDGED_CURRENT` means that a local client reported a checksum-bound
installation matching a Manifest revision. It is not research completion,
inspection of current local files, upload of outputs, or Workspace backup.
Similarly, `ACK_PENDING` does not mean that the research task failed.

There is deliberately no Project completion percentage. Research Workflows
are optional, repeatable, can be retired, and may form loops rather than a
fixed pipeline.

## Managing Workflows

The Workflows page uses the existing cloud mutation APIs. Adding an available
Workflow changes the Desired Manifest and tells the user to run:

```bash
python reagent_local.py sync .
```

The browser never writes the local Workspace. A Manifest revision conflict
refreshes Project state instead of overwriting another change. Retiring an
Instance preserves its cloud Progress history and local Capsule; run explicit
local sync to refresh the retained/not-desired status.

## Literature Search compatibility

Existing standalone Packages, B3-adopted Capsules, B4-synchronized Capsules,
the launcher, OpenAlex proxy boundary, Progress upload/retry, Package download,
and Literature Search result links remain supported. The legacy Project-level
result route remains available while the multi-Workflow Progress page provides
the general history view.

## Current boundary

Progress Reports provide bounded cognitive and Project continuity. They do not
contain the complete Workspace, code, datasets, memory, or output bytes.
NIGHT-B5 does not implement typed Artifact handoff/materialization, an Artifact
index, Idea Discovery, another executable Workflow, background sync, or
cross-device Workspace backup.
