# ADR 0009: Teacher-Aligned Initial Product Boundary

Status: **Accepted**
Date: 2026-08-03
Owner: ReAgent owner
Decision scope: initial V1 product identity, execution authority, and route

## Context

The owner accepted the committed Teacher Design Alignment Audit and its verdict
`FUNDAMENTALLY_DIFFERENT_PRODUCT`. The current repository implements a hosted
Web Agent path in which FastAPI dispatches a project-owned `AgentRuntime`,
backend Skills call providers, and PostgreSQL stores authoritative hosted
execution state. That implementation is preserved as historical and reusable
work, but it does not define the initial V1 product boundary.

The teacher source `Meta-Research-Agent-架构.pdf` has higher product authority.
Page 1 assigns Skill/project/package/progress/API-proxy management to the cloud,
states that the cloud does not execute concrete research, and makes one local
folder the complete state of each Workflow instance. Page 2 assigns concrete
work to an existing Claude Code/Codex Agent Harness and says ReAgent does not
develop that execution engine. Pages 2-3 define five composable Workflow types,
illustrate a possible folder, explicitly leave its exact structure and prompt
decomposition undecided, and show local execution followed by Progress Report
upload and later continuation.

The stable requirement mapping is TMR-001 through TMR-018 in
`docs/audits/TEACHER_DESIGN_REQUIREMENT_LEDGER.md`. This ADR is the accepted
route correction authorized by the owner. Where earlier ADRs or plans assign
V1 research execution or concrete task-state authority to the backend, this ADR
governs the initial product boundary. Earlier facts and implementation history
remain valid historical records.

## Decision

### Product identity and three-part architecture

Initial V1 is a **cloud management and supply system for portable local
Workflow Packages executed by an existing Agent Harness**:

1. **Cloud:** manages projects, Skills, templates/packages, Progress Reports,
   continuity metadata, credentials, proxy operations, downloads, uploads, and
   returned artifacts. It does not execute concrete research in V1
   (TMR-003-TMR-008, PDF pages 1-2).
2. **Local Workflow Folder:** is the downloadable and movable working location
   and authoritative concrete task state for one Workflow instance
   (TMR-002, TMR-009, TMR-013-TMR-018, PDF pages 1-3).
3. **Agent Harness:** an existing Claude Code, Codex, or equivalent reads the
   folder, interacts with the user, invokes tools/proxy calls, performs the
   research, writes outputs, and records progress. ReAgent does not implement a
   replacement Harness for initial V1 (TMR-003, TMR-010, TMR-015-TMR-018, PDF
   pages 2-3).

### Cloud responsibilities

Cloud V1 owns:

- project identity and management;
- AG Admin, normalized Skill ingestion, versioning, and management;
- Workflow/template/Skill package management;
- reproducible package generation, checksum/version validation, and download;
- user-upload and returned-artifact storage;
- Progress Report upload, validation, immutable history, aggregation, and
  project/workflow progress projection;
- continuity metadata across machines and supported Agent Harnesses;
- external provider credential custody;
- a bounded external API proxy with normalized responses, policy, usage,
  accounting, and secret-safe diagnostics.

Supporting cloud implementation may use FastAPI, Next.js, PostgreSQL, file or
object storage, current provider ports, `ProviderOperation`, checksums, and
version registries. These are internal means, not permission for cloud research
execution.

### Local-folder responsibilities

The local folder owns concrete execution state, including Harness-readable
instructions, pinned Workflow and Skill identity, prompts, user inputs, active
context, local tool artifacts, outputs, Progress Reports, and continuation
information. It must be movable between local paths or machines, sufficient for
a fresh approved Harness to understand and continue the task from files, and
must contain no provider credential.

### Agent Harness responsibilities

Claude Code, Codex, or another owner-approved existing Harness owns concrete
research execution, user interaction, tool invocation, output production,
context updates, and Progress Report production. A Harness may call the cloud
API proxy; it does not receive the cloud-held provider key.

## State authority

### Local Task State

The local folder is authoritative for active research progress, working
context, local outputs, local tool-generated artifacts, Harness continuation
state, and local Progress Reports before upload.

### Cloud Project State

PostgreSQL or another cloud store may be authoritative for project identity,
ownership when implemented, selected Workflow type, package and Skill/template
versions, package checksum/download history, uploaded Progress Report history,
cloud progress projections, proxy requests/usage, cloud-stored uploads and
returned artifacts, and package metadata.

Backend `AgentRuntime` state, `StepRun`, checkpoint, memory revision, and
`ExecutionEvent` records are not authoritative for V1 concrete research. Their
current SQL mappings remain internal test or optional Hosted Mode state. This
ADR does not claim that current tables already implement the accepted
cloud/local authority split.

## Hosted execution classification

The existing Hosted AgentRuntime is preserved and reclassified as:

- an internal deterministic test Harness;
- an optional future Hosted Mode;
- non-default;
- outside the teacher-aligned initial V1 path;
- frozen from further product development until separately reauthorized.

It must not be described as the teacher-defined Agent Harness. Existing hosted
endpoints, UI, tests, migrations, artifacts, and evidence are not deleted by
this ADR. Later implementation work may hide or disable hosted execution in a
teacher-aligned mode only under explicit scope.

## Cloud API proxy

When local execution needs an external provider, the intended boundary is:

```text
local Claude Code/Codex
  -> authenticated cloud proxy
  -> cloud-held credential
  -> provider adapter
  -> normalized response
  -> local Harness
```

The proxy may authenticate, translate protocols, enforce request/cost/rate
limits, account via `ProviderOperation`, normalize failures/results, and retain
secret-safe audit evidence. It must not choose the research question, run the
full Workflow, generate the final V1 report, or invisibly mutate Local Task
State. No proxy protocol or endpoint is implemented or frozen in R0.

## Progress Reports

The local Harness produces a Progress Report after an execution round. Explicit
upload associates it with the exact project/package/Workflow versions; cloud
validates and appends immutable history, computes a progress projection, and
may later support package refresh or continuation. A Progress Report is not a
hosted `ExecutionEvent`, checkpoint, developer `.agent_read/progress` file, or
final research output. Its final schema and conflict semantics remain open.

## Five-Workflow taxonomy

The product taxonomy remains:

1. Literature Search;
2. Scientific Question / Idea Finding;
3. Writing;
4. Review;
5. Reproduction and Experiment.

They are independent and composable, and one Workflow's output may become the
next Workflow's input (TMR-011, TMR-012, TMR-017; PDF pages 2-3). This taxonomy
does not claim all five are implemented or that the PDF mandates an
implementation order.

## Explicitly accepted

1. Local folder plus Claude Code/Codex is V1's default execution model.
2. Cloud does not execute concrete research tasks in V1.
3. Local folder owns concrete execution state.
4. PostgreSQL owns cloud project/package/Skill/progress/proxy metadata only in
   the V1 product boundary.
5. Hosted AgentRuntime is internal or an optional future mode.
6. Provider credentials remain cloud-managed.
7. Local Harness uses a cloud API proxy when external provider calls are
   required.
8. Local Harness produces Progress Reports for cloud upload.
9. Exact folder structure remains experimental.
10. Existing code is preserved pending later targeted realignment work.

## Hosted-feature freeze and deferred work

The following receive no further V1 product development without separate owner
reauthorization:

- backend research execution;
- browser-triggered run/resume research execution;
- Hosted AgentRuntime productionization;
- hosted OpenAlex research execution;
- real hosted LLM activation and server-side report generation;
- additional hosted research-provider adapters;
- hosted worker, queue, lease, or scheduler productionization;
- automatic relevance Judge and full-pool evaluation;
- full-pool retrieval benchmark work;
- additional hosted approval, timeline, or research-report UX;
- Phase 9C hosted activation and production Hosted Mode.

The freeze permits preservation, repository-safety bug fixes, deterministic
tests, and extraction/repackaging of reusable schemas, prompts, validators, and
contracts. Any optional Hosted Mode development requires a later explicit owner
decision.

The Optional Evaluation Module remains **DEFERRED**. Hosted LLM execution and
Phase 9C-2B are **DEFERRED**. Grounded summary/evidence/claim/citation schemas,
prompts, abstract-only rules, provenance validators, synthetic fixtures, and
artifact contracts remain reusable candidates for local Workflow/Skill
packages and deterministic upload validation.

## Source-undecided matters

This ADR does not decide:

- exact local folder tree or directory names;
- one or multiple `AGENT.md` files;
- exact prompt-file decomposition;
- exact normalized Skill package format or embedding/reference strategy;
- exact Progress Report JSON/Markdown schema;
- package refresh, merge, and conflict-resolution policy;
- exact cloud API-proxy protocol, authentication, provider, or response shape;
- final AG Admin UI;
- number of Workflows in the first experimental slice;
- whether Claude Code, Codex, or both are blocking in the first acceptance.

These areas are `SOURCE_UNDECIDED` or require owner implementation decisions.
The illustrative tree on PDF pages 2-3 must not be represented as final.

## Existing-component preservation and migration principles

1. Preserve current code, migrations, immutable Workflow hashes, tests, and
   evidence unless a later authorized task targets them.
2. Separate Cloud Project State from Local Task State before presenting the new
   path as implemented.
3. Reuse validation, versioning, packaging, storage, provider, accounting, and
   UI infrastructure where it supports source-defined cloud responsibilities.
4. Keep hosted execution behavior explicit, non-default, and distinguishable
   from teacher-aligned V1.
5. Add the missing local-folder/Progress Report/proxy capabilities rather than
   relabelling hosted events, checkpoints, or artifacts as equivalents.
6. Do not delete hosted work solely to establish the new mainline.
7. Do not freeze source-undecided formats before experiment evidence and owner
   review.

## Next milestone

R1 is an **experimental local Literature Search Workflow Package and Agent
Harness compatibility slice**. Literature Search is an
`OWNER IMPLEMENTATION-SEQUENCING PROPOSAL`, not a teacher mandate. R1 must
generate one versioned downloadable package and prove that an existing Codex or
Claude Code session can execute and resume from its files without backend
AgentRuntime performing the research. R0 does not implement R1.

## Consequences

The initial product path changes from hosted research execution to cloud
management plus portable local execution. Existing hosted code remains useful
for regression, deterministic contract tests, extraction of reusable
components, and a possible later mode, but no longer sets V1 execution
authority. New mainline work prioritizes package generation, Progress Report
round-trip, API proxy, Skill administration, and continuation.

The route correction creates deliberate coexistence: current code still runs
the preserved hosted prototype until later scoped work establishes or exposes a
teacher-aligned mode. Documentation must not claim that R1 capabilities already
exist.

## Revisit triggers

Revisit this ADR only through a new owner-approved decision if:

- the teacher/owner changes the initial product boundary;
- a Hosted Mode is proposed as a default or production product;
- cloud generation or hidden server task memory is proposed for V1;
- the folder cannot provide independent continuation under an existing Harness;
- provider credentials would need to enter a Workflow Package;
- the five-Workflow taxonomy or output/input composition is changed;
- experiment evidence requires a final folder, Skill, Progress Report, merge,
  or proxy contract;
- security, rights, or operational evidence invalidates the proposed local or
  proxy model.

## Alternatives considered

- Continue the hosted Web Agent as V1: rejected for the initial product because
  it conflicts with the teacher's explicit responsibility boundary.
- Delete hosted infrastructure immediately: rejected; the owner requires
  preservation and later targeted decisions.
- Call the current backend runtime a Harness: rejected because the teacher
  explicitly assigns that role to existing Claude Code/Codex-like tools.
- Freeze the sample folder tree now: rejected because the PDF explicitly marks
  it as an experiment.
