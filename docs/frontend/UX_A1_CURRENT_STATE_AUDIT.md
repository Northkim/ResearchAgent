# UX-A1 Current Frontend UX / IA Audit

Date: 2026-08-14  
Status: `PASS_UX_A1_WITH_VISUAL_EVIDENCE_GAPS`  
Baseline: `main` at `85b85251e005b6bc45d2ef7b98ee73867badc7ae` (`Complete controlled browser runtime qualification`)  
Repository state before audit: clean

## 1. Scope and plan alignment

`PLAN_ALIGNMENT = PASS`

The approved sequence is Engineering Harness (done/frozen) -> B0 (pass) ->
UX-A1 (this phase) -> S1 -> UI-P0 -> E1 -> W1 -> R1 -> W2 -> incremental
frontend completion. Writing #2 UX closure remains deferred and non-blocking
for this audit.

This audit covers only:

- Projects;
- Project Overview;
- Workflow Board and the missing focused Workflow Detail concept;
- directly supporting project navigation, Progress, Artifact input, Resource,
  state-label, and local-action components.

It does not reopen the Engineering Harness or B0, inspect owner Project data or
Experiment 0.4, audit all legacy routes, or authorize implementation.

## 2. Evidence and limitations

Evidence used: current routes, components, view-model types, next-action
derivation, responsive CSS, and relevant component tests; plus the already-
qualified B0 semantics (`COMPLETED`, `BLOCKED`, `AWAITING_OWNER_ACTION`, and
`ACKNOWLEDGED_STALE`) at `1440x900`, `1280x800`, and `390x844`.

The in-app browser was unavailable in this Codex session. No B0 target,
frontend server, backend, database, or alternative browser infrastructure was
started. B0 proves that the four states rendered at all required viewports with
the real controlled API; it does not prove that the hierarchy is effective.
Findings about information ordering and density are source-backed. Fine visual
judgments such as perceived scale, fold position, color contrast in context,
and actual whitespace balance require owner screenshots or a later approved
browser review.

No owner evidence, long-lived Workspace evidence, Real Core evidence, or
Experiment 0.4 evidence is used.

## 3. Frontend baseline

- Framework: Next.js `16.2.10`, React `19.2.4`, TypeScript, App Router, and
  TanStack React Query `5.101.3` through a centralized API client.
- Styling/components: Tailwind is available, but the product uses bespoke
  React components and a hand-built semantic class system in one global CSS
  file; there is no external component/design system.
- Visual language: cream canvas and paper surfaces, dark forest identity,
  Georgia serif display headings, sans-serif UI text, compact uppercase labels,
  bordered cards, pills, and callouts.
- Global canonical routes: `/projects`, `/projects/new`, `/local-guide`.
- Project routes: `/projects/[id]`, `/projects/[id]/workflows`,
  `/projects/[id]/progress`, and `/projects/[id]/help`.
- Legacy hosted routes still exist but are outside this audit and absent from
  primary navigation.

The current component approach is consistent and accessible in several useful
ways: semantic headings and landmarks, explicit loading/error/empty states,
focus-visible rules, reduced-motion handling, and responsive single-column
fallbacks. The problem is not absence of UI structure. It is that product
state, safety explanation, setup mechanics, and backend taxonomy compete at
the same level.

## 4. Current user journey

The current canonical journey is: Projects -> Project Overview -> Workflow
Board -> find one task among full configuration/setup cards -> copy commands ->
act in the Local Workspace -> return to the Board or Progress to infer what
changed.

The journey is technically honest. It does not imply Cloud research execution
or browser writes to the Workspace. Its UX weakness is loss of focus: a user
must translate several system dimensions before discovering the one current
job and then switches between a project summary, a dense board, a local
terminal, and a report-ledger page without a stable Workflow-detail home.

## 5. Projects audit

### User job

Find the Project that needs attention and continue the correct research task.

### First viewport questions

- What Projects exist?
- Which are active?
- Which need my action?
- What changed recently?
- What should I continue?

### Current hierarchy

The largest elements are the statement “Research stays in your folder,” its
description, a local-first boundary callout, and 300-pixel-minimum Project
cards. Each card emphasizes Project name/topic, one raw latest status, round,
updated timestamp, and “Open project.”

### Required hierarchy

Project name, current research stage, owner/system actor, next valid action,
blocker, latest meaningful output, and recency should dominate. The local-first
boundary should remain available but not precede the actual work queue on every
visit.

### Primary action and state comprehension

“Create project” is obvious. Continuing an existing Project is not. The list
uses the legacy Project summary (`progress.latest_status`) and cannot expose the
multi-Workflow recommended action already available on Project Progress. A
Project with one completed Workflow and another blocked Workflow may look only
“COMPLETED.” “Open project” does not name the next task.

### Density and scanability

The cards are visually spacious but informationally thin. Large headings,
topic prose, fixed card height, and repeated “Research Project” labels reduce
cross-Project scanning. There is no attention grouping or task-oriented sort.

## 6. Project Overview audit

### User job

Understand the Project’s current position and take the one best next action.

### First viewport questions

- Where is the Project now?
- Which Workflow is next?
- Who must act?
- What is blocked, and why?
- What was recently produced?

### Current hierarchy

The Overview first presents a large Project header, project tab bar, a hero
explaining independent Workflows, and five aggregate counts. The recommended
action is one of three equal cards below the hero, beside permanent first-local-
setup controls and latest activity.

### Required hierarchy

The recommended Workflow/action, actor, blocker reason, and latest output must
be the dominant state summary. Aggregate counts and first-time setup are
supporting information. Setup should become prominent only when it is the
current blocker.

### Primary action and state comprehension

The recommendation logic is sound and avoids fake percentage completion, but
the UI turns the action into “Open workflows” rather than the specific action.
It does not structurally display “Owner action required,” the blocking reason,
or the expected result in the same dominant block. Permanent setup downloads
compete even after setup is no longer the next task.

### Density and scanability

The Overview combines a hero, five count tiles, three equal cards, recent
Workflow cards, and technical details. This creates several layers of summary
without one compact answer to “what should I do now?” Recent activity reports
are useful, but recent outputs are not promoted as a first-class Project fact.

## 7. Workflow Board / Workflow Detail audit

### User job

Choose a Workflow, understand its current stage and dependencies, and perform
the next valid browser or local action.

### First viewport questions

- What stage is this Workflow in?
- Are its inputs ready?
- Who must act?
- Why is it blocked?
- What is the next valid action?
- What output will it produce?

### Current hierarchy

There is no dedicated Workflow Detail route. The Board renders each Workflow as
a large card containing up to five status pills, maturity warnings, bundled
Skills, optional Resources, latest summary, next-action callout, report counts,
input selectors, materialization/run commands, technical identity, Progress
link, and retirement control. The same page also shows relationship guidance
and the full Workflow catalog.

### Required hierarchy

The Board should compare Workflows using only name, stage, actor/attention,
blocker, latest output, and next action. Selecting a Workflow should open one
focused detail screen where status, inputs, action, output contract, local
Workspace state, history, Resources, and technical evidence are progressively
disclosed.

### Primary action and state comprehension

The derived next-action contract is a strong foundation. However, it is one
callout among many elements and is not always a clickable action. The card can
show `Active`, `Cloud desired`, `Installed · sync needed`, `Core · Scaffold`,
`Needs attention`, and a prose summary simultaneously. The user must reconcile
those dimensions before acting.

The B0 states are observable but not uniformly comprehensible:

| State | What is currently clear | What remains weak |
|---|---|---|
| `COMPLETED` | Completed badge, summary, report count | Latest output and downstream choice are secondary |
| `BLOCKED` | “Needs attention” plus fixture summary | Actor and blocker category are not structured |
| `AWAITING_OWNER_ACTION` | Exact phrase appears in summary | It is still encoded as generic `BLOCKED`; owner action is not a primary badge/action |
| `ACKNOWLEDGED_STALE` | “Installed · sync needed” is visible | It competes with lifecycle, desired, research, and maturity states |

### Density and scanability

This is the main card-soup problem. Two-column cards become long independent
forms with repeated callouts, labels, metadata, commands, and disclosures.
Users cannot compare cards once their heights diverge. Available Workflows and
current Workflows also compete in the same page-level flow.

## 8. Cross-screen state comprehension

The system possesses the data needed for good state comprehension, including
`recommended_workflow_instance_id`, structured `next_action`, missing/bound
inputs, result count, installation state, summaries, and activity time. The
frontend problem is prioritization, not merely missing state.

| Question | Current answer |
|---|---|
| What happened? | Usually available in Progress summaries, but fragmented |
| What is happening? | Derivable from research status, but diluted by other dimensions |
| Who must act? | Implied by prose or local commands, not primary presentation |
| Why blocked? | Present in summaries/inputs, but not a stable blocker component |
| What next? | Derived correctly, but inconsistently actionable and absent from Projects |

Recommended presentation contract for every Project and Workflow state:

```text
stage + actor + blocker/reason + next action + expected result + last change
```

Installation, desired-state, readiness, and maturity facts should support that
contract rather than appear as peer statuses.

## 9. Technical taxonomy leakage

| Concept | Placement | Audit decision |
|---|---|---|
| Project | `PRIMARY_UI` | Primary navigation and identity |
| Workflow | `PRIMARY_UI` | Primary research unit and navigation |
| Progress | `SECONDARY_UI` | User-facing Activity/History; raw report mechanics in details |
| Artifact | `SECONDARY_UI` | User-facing Input/Output/Result; exact identity in details |
| Resource | `SECONDARY_UI` | Visible when required or blocking; otherwise contextual |
| Local Workspace state | `SECONDARY_UI` | Prominent only when it determines the next action |
| Installation | `SECONDARY_UI` | Translate to “Local Workspace current/sync needed” |
| Readiness | `SECONDARY_UI` | Express as actionable input/setup/run state, not taxonomy |
| Core maturity | `SECONDARY_UI` | Safety-critical, but use “Reviewed research” or “Scaffold only” |
| Capsule | `TECHNICAL_DETAILS_ONLY` | Never needed for ordinary task selection |
| Manifest | `TECHNICAL_DETAILS_ONLY` | Revision/conflict evidence only |
| Desired State | `TECHNICAL_DETAILS_ONLY` | Translate to included/retired where necessary |
| Requirement keys | `TECHNICAL_DETAILS_ONLY` | Replace with human input names |
| Checksums, IDs, receipts, versions | `TECHNICAL_DETAILS_ONLY` | Preserve for provenance and support |
| Skills and trust/version pins | `TECHNICAL_DETAILS_ONLY` | Secondary safety summary only when material |

## 10. Prioritized findings

### P0 — main-journey blockers or serious confusion

1. **P0-1 — Projects cannot identify the Project needing attention.** The list
   exposes a legacy latest status rather than the multi-Workflow recommendation,
   actor, blocker, or next action. A mixed-state Project can be misleadingly
   summarized as completed.
2. **P0-2 — There is no focused Workflow Detail information architecture.**
   The Workflow Board is simultaneously overview, state inspector, dependency
   editor, local-run launcher, Resource manager, technical console, retirement
   control, and catalog.
3. **P0-3 — User state is subordinated to system-state dimensions.** Generic
   research, lifecycle, desired, installation, readiness, and maturity pills
   force users to synthesize “who acts, why blocked, what next” themselves.
4. **P0-4 — Project Overview does not lead with the current research decision.**
   Aggregate counts and permanent setup content precede or compete with the
   recommended Workflow, actor, blocker, and latest output.

### P1 — material usability/comprehension loss

1. **P1-1 — Outputs, Progress, and Resources lack a coherent path.** Progress
   is a separate report-ledger page; outputs are embedded metadata; Resources
   are nested inside Workflow cards.
2. **P1-2 — Static local-first explanation consumes prime space repeatedly.**
   The boundary is important, but repetition displaces current work.
3. **P1-3 — Current Workflows and the Workflow catalog share one long page.**
   Managing what exists and discovering what to add are distinct jobs.
4. **P1-4 — Project cards are spacious but low-information.** Fixed height,
   topic prose, raw status, round, and timestamp do not support attention-based
   scanning.
5. **P1-5 — Workflow cards repeat setup and provenance content.** Skills,
   scaffold warnings, Artifact forms, Resources, commands, and IDs multiply
   card height and obscure comparison.
6. **P1-6 — `AWAITING_OWNER_ACTION` is not a first-class presentation state.**
   It appears as generic `BLOCKED` plus summary prose, weakening actor clarity.
7. **P1-7 — Project Progress is ledger-first.** Instance IDs, report IDs,
   receipt IDs, checksums, and immutable-history framing outweigh user-facing
   outcomes and decisions.

### P2 — polish and lower-value improvements

1. **P2-1 — Display-heading scale is likely too dominant.** The `68px` desktop
   and `42px` narrow heading rules may push task state below the fold; rendered
   confirmation is required.
2. **P2-2 — Status pills rely on many small uppercase labels and similar visual
   treatments.** Reserve color and pill treatment for attention and outcome.
3. **P2-3 — Disabled controls use a wait cursor even when permanently
   unavailable or planned.** This communicates loading rather than policy.
4. **P2-4 — Labels mix product language and architecture casing.** Repeated
   “Cloud,” “Local Workspace,” “Workflow Instance,” and “Progress Report” copy
   should be simplified outside technical details.

## 11. Recommended information architecture

Use one task-first hierarchy:

```text
Projects
└── Project Overview
    ├── Workflows
    │   └── Workflow Detail
    │       ├── Status and next action
    │       ├── Inputs
    │       ├── Output
    │       ├── Activity / Progress history
    │       ├── Resources (only when relevant)
    │       └── Technical details
    ├── Outputs
    └── Activity
```

Placement decisions:

- **Projects:** only global primary destination. “New project” is an action,
  not an equal navigation destination.
- **Project Overview:** Project home and attention summary.
- **Workflows:** compact Project-level board/list. Every row/card opens a
  focused Workflow Detail.
- **Progress:** user-facing Activity; summarized on Overview, scoped on
  Workflow Detail, with a Project Activity index for cross-Workflow history.
- **Artifacts:** user-facing Outputs at Project level and explicit Inputs /
  Output inside Workflow Detail. “Artifact” is secondary provenance language.
- **Resources:** contextual section inside relevant Workflow Detail; Project-
  wide inventory is secondary and need not be primary navigation initially.
- **Local Workspace state:** one secondary status/action panel on Overview and
  Workflow Detail, elevated only when setup/sync/materialization blocks work.
- **Technical details:** collapsed final section containing IDs, Capsule,
  Manifest revision, checksums, receipts, requirement keys, exact versions,
  Skills, and raw state dimensions.
- **Help / Local guide:** utility navigation, not a peer to current research
  work.

This IA preserves independent Workflows. It does not invent a linear persisted
pipeline or automatic latest-result selection.

## 12. Canonical screen specifications

### Projects

User job: choose what to continue.

First viewport, in order:

1. “Projects” title and Create Project action.
2. Needs-attention group, only when non-empty.
3. Active Project list sorted by actionable priority, then recent activity.

Each Project summary must show:

- name and concise topic;
- current/next Workflow;
- plain-language stage;
- actor: “Your action,” “Ready locally,” “Waiting for input,” or “No action”;
- blocker reason when present;
- one next-action label/CTA;
- last meaningful change and latest output, if any.

Do not lead with round number, Package readiness, raw enum, or boundary copy.
Empty/loading/error states remain explicit.

### Project Overview

User job: understand the Project and take the best next action.

First viewport, in order:

1. Project name/topic and compact breadcrumb/back path.
2. Dominant Current state panel: next Workflow, stage, actor, blocker reason,
   primary action, and expected result.
3. Recent output or last meaningful activity.
4. Compact Workflow map/list showing independent states and dependencies.

Below the first viewport:

- Outputs and Activity previews;
- Local Workspace state only when it affects action;
- initial setup guidance only when setup is actually required;
- technical details collapsed.

Avoid percentage completion. Preserve explicit Workflow independence and exact
input selection.

### Workflow Detail

User job: understand and advance one Workflow.

First viewport, in order:

1. Workflow name, instance label only when needed, and human stage.
2. Actor and primary next action.
3. Blocking reason or completion outcome.
4. Input readiness summary with exact selections in plain language.
5. Expected or produced output.

Primary state model:

```text
Not started | Ready | In progress | Needs your action | Blocked | Completed
```

Supporting sections:

- **Inputs:** required/optional, selected/missing, upstream source, one explicit
  selection action; exact IDs/checksums hidden by default.
- **Local action:** one command sequence appropriate to the current state, not
  all possible commands at once.
- **Output:** expected type before completion; latest produced result and next
  consumer choice after completion.
- **Activity:** meaningful history first; raw Progress Report records in
  technical details.
- **Resources:** visible only when required, configured, or blocking.
- **Safety:** “Reviewed research” or “Scaffold only” near capability claims,
  without a peer taxonomy badge row.
- **Technical details:** lifecycle, desired state, installation evidence,
  readiness, maturity enum, Capsule, Manifest, Skills, requirement keys,
  versions, checksums, IDs, and receipts.

## 13. Visual identity assessment

- Cream background: `KEEP`, with refinement to reduce same-weight paper cards.
- Dark green identity: `KEEP`; it is distinctive, calm, and appropriate for a
  research workspace.
- Serif/sans typography: `KEEP`; the editorial display voice and utilitarian UI
  voice are compatible.
- Overall direction: `REFINE`, not replace.

Required refinement is primarily hierarchy: reduce display scale where it
pushes state down, reserve strong surfaces/colors for the current action and
attention, reduce border/card repetition, increase list scanability, and make
technical disclosure visibly subordinate. These are not grounds for replacing
the brand identity.

Rendered evidence is still required before final decisions about exact type
scale, whitespace, color contrast, fold placement, and mobile density.

## 14. Owner decisions required

1. Accept the recommended task-first IA and a focused Workflow Detail as the
   canonical unit of work.
2. Choose user-facing labels: recommend **Outputs** for Artifacts and
   **Activity** for Progress history, while retaining exact terms in technical
   details.
3. Accept raw Capsule, Manifest, Desired State, Requirement keys, IDs,
   checksums, receipts, and version pins as technical-details-only.
4. Accept Core maturity as a secondary safety statement (“Reviewed research” /
   “Scaffold only”), not a peer primary status.
5. Decide whether S1 may extend the Projects list projection with recommended
   Workflow, actor, blocker, next action, latest output, and recency. The
   current list contract is insufficient for P0-1.
6. Confirm Resources remain contextual to a Workflow until a real user job
   justifies a Project-level Resource area.

Writing #2 UX closure remains `DEFERRED_NON_BLOCKING`. Legacy routes, general
accessibility automation, visual baselines, cross-browser coverage, and design-
system implementation are also `DEFERRED_NON_BLOCKING` for UX-A1.

## 15. Decision and safe next phase

`PHASE_STATUS = PASS_UX_A1_WITH_VISUAL_EVIDENCE_GAPS`

UX-A1 is complete at source/IA evidence level. The four B0 fixture states and
required viewports are accepted as existing controlled evidence; this session
adds no new rendered judgment.

The safe next phase is **S1 Shared Core Contracts**. S1 should carry the four P0
findings into view-model and state-contract decisions, especially actor,
blocker, next action, output identity, and the Projects-list projection. UI-P0
should begin only after the owner resolves the decisions above. No redesign or
frontend implementation is authorized by this audit.
