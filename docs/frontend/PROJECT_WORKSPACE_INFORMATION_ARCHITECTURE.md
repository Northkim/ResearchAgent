# Project Workspace Frontend Information Architecture

> **Design only.** No frontend route or component is implemented by ARCH-D1.

## 1. Navigation and route model

The initial visible Project navigation is exactly **Overview**, **Workflows**,
**Progress**, and **Help**. Artifacts, Resources, Skills, Activity, and Settings
are future concepts and must not appear in navigation until their product
capabilities and authorization/error states exist.

| Route | Purpose | Initial scope |
|---|---|---|
| `/projects` | List/open Projects and create a new one. | Active |
| `/projects/new` | Four-step Project wizard. | Active |
| `/projects/{project_id}` | Project overview, desired/local uncertainty, next actions. | Active |
| `/workflow-catalog` | Reusable Workflow catalog; planned items visible and disabled. | Active |
| `/projects/{project_id}/workflows` | Board of configured Workflow Instances. | Active |
| `/projects/{project_id}/workflows/{instance_id}` | Instance pins, dependencies, rounds, local launch/help. | Active |
| `/projects/{project_id}/progress` | Per-instance graph/list and immutable histories. | Active |
| `/projects/{project_id}/help` | Project/Workspace/Workflow operating guide. | Active |
| future `/artifacts`, `/resources`, `/skills`, `/activity`, `/settings` | Reserved product areas. | Hidden; no links/routes that imply implementation |

Literature Search is Available. Idea Discovery, Writing, Review, and
Reproduction/Experiment appear as Planned catalog cards and cannot be selected.
The data model can show multiple same-type instances, while the initial wizard
and add flow enforce one active instance/type.

## 2. New Project wizard

1. **Project information:** name and research topic; explain cloud/local data
   boundary.
2. **Workflow selection:** select available Workflow Definitions; recommend the
   future full pipeline visually but disable Planned Workflows.
3. **Skills:** show reviewed built-ins automatically recommended/pinned; no
   private upload/import controls.
4. **Workspace and outputs:** confirm one long-lived Workspace, isolated
   Capsules, expected Artifact types, execution-continuity limitation, and no
   cloud research execution.

Back/forward preserves local form state, final submission is idempotent, and a
revision conflict offers refresh/review rather than automatic merge.

## 3. Text wireframes

### Projects

```text
[ReAgent]  Projects                                      [New project]
Local-only research workspaces

[Project name]  Literature Search  Completed  Cloud update: …  [Open]
[Project name]  2 Workflows       Needs sync  Local state may differ [Open]

Empty: No Projects yet. Create a Project to initialize a long-lived Workspace.
```

### New Project

```text
Create Project  Step 2 of 4
[1 Information]—[2 Workflows]—[3 Skills]—[4 Workspace]

[✓ Literature Search] Available
[ Idea Discovery ] Planned — cannot select
[ Writing ] Planned — cannot select
…
[Back]                                                [Continue]
```

### Project Overview

```text
Project name                         Cloud manifest r4
Topic …                              Workspace: sync status unknown/current
[Recommended next action: Run sync to install one new Capsule] [View Workflows]

Workflow summary                     Progress summary
Literature Search · Completed        Latest cloud-known report …
Idea Discovery · Planned             Actual local state may be newer

[Overview] [Workflows] [Progress] [Help]
```

### Workflow Catalog

```text
Workflows
[Literature Search] Available  Inputs … Outputs … [View] [Add]
[Idea Discovery]    Planned    Inputs … Outputs … [View]
[Writing]           Planned    …
Filter/status controls; no unavailable Add action.
```

### Project Workflows board

```text
Desired Workflows                         [Add Workflow]
[Literature Search · instance label]
Desired: active  Installed: reported r4  Progress: completed [Open]
Dependencies: none

Retired (collapsed, never deleted)
[Literature Search · prior instance] History retained [Open]
```

### Workflow Instance

```text
Literature Search / instance label             [Retire…]
Desired Capsule v0.5 · Installed observation … · Local now unknown
[Recommended next action]

Inputs / dependencies        Outputs / Artifact metadata
Skill pins                   Round history
[Run locally] [Read guide] [Technical details]
```

### Progress

```text
Project Progress — cloud-known reports; not a live filesystem view
[Workflow instance] Completed · round 1 · observed …
Summary …  Artifacts: metadata only  Blocking dependencies: …
[Round history]

No report: No Progress Report received. Local work may not have started or may
be awaiting upload. [Read guide] [Retry from the same Workspace]
```

### Help

```text
Project Workspace guide
What cloud remembers | What remains local | Add/sync a Workflow | Run a Capsule
Artifact handoff | Offline behavior | Recovery and errors | Continuity limits
Workflow guides: Literature Search [Available], Idea Discovery [Planned]
```

### Sync/update/error states

```text
Update available: manifest r5 adds Idea Discovery Capsule. No local files have
been changed. Run `python reagent_local.py sync .` and review the plan.

Acknowledgement pending: Installation is valid locally; ReAgent has not yet
recorded the acknowledgement. Retry acknowledgement only.

Immutable drift detected: ReAgent will not overwrite changed Capsule files.
[Inspect recovery steps] [Technical details]
```

## 4. Reusable components

- `WorkflowCard`: catalog/instance mode, availability and action policy.
- `WorkflowStatusBadge`: desired, installed-observation, and progress status
  remain visually distinct.
- `WorkflowDependencyList`: typed Artifact/Skill/Resource requirements and safe
  recovery.
- `ArtifactReferenceList`: metadata, schema/checksum/availability qualifier;
  never implies byte upload.
- `WorkspaceSyncStatus`: revision, last ack, cloud/local uncertainty, explicit
  sync action.
- `RecommendedNextAction`: bounded operational guidance, not research judgment.
- `ProgressSummary`: cloud-known bounded report summary.
- `RoundHistory`: immutable per-instance report chain.
- `TechnicalDetails`: collapsed IDs, versions, checksums, and revisions.
- `EmptyState`: truthful explanation plus one possible action.
- `ErrorRecoveryPanel`: stable code, stage, retryability, and safe owner action.

Components consume registry/API types rather than Workflow-specific conditionals.
Workflow Help content and expected inputs/outputs come from reviewed catalog
metadata. Research values remain untrusted text and are rendered without HTML
execution.

## 5. Responsive and accessibility contract

- At ≥1024 px, navigation and summary/dependency columns may be side by side;
  below that, preserve semantic heading order and stack actions.
- At ≤640 px, tables become labelled lists; checksums wrap/copy without
  horizontal page overflow; primary action remains first.
- All functions are keyboard operable with visible focus. Stepper, tabs, status,
  dialogs, disclosure panels, and toast updates use appropriate semantic roles
  and accessible names.
- Status never relies on color alone. Icons have text labels; contrast targets
  WCAG 2.2 AA; reduced-motion preferences are respected.
- Revision conflicts and destructive-looking retirement require focus-managed
  confirmation and explicitly state that local files/history are retained.
- Loading, empty, stale, offline, error, and success states are announced
  without fabricated percentages. Polling does not steal focus.

## 6. Product-boundary language

Use “desired configuration,” “last reported installed state,” and “cloud-known
Progress.” Never say the cloud installed a local Capsule, currently has an
Artifact, or knows the Workspace's present contents. Add Workflow means desired
state changed; Sync is the explicit local installation step. Retire never says
delete. Hosted Run/Resume and cloud LLM actions do not appear.
