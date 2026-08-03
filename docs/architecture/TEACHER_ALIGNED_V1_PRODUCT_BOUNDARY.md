# Teacher-Aligned V1 Product Boundary

Status: **Frozen by accepted ADR 0009**

Date: 2026-08-03

Teacher source: `Meta-Research-Agent-架构.pdf`

Source SHA-256: `fa725dcd5a894f4025a94181e8595226c05d2895ae2f27c6a46c48a2fc5dd23c`

Source page count: 3

Source access date: 2026-08-03

## Purpose and authority

This document defines ReAgent's initial V1 product boundary after the owner
accepted the Teacher Design Alignment Audit verdict
`FUNDAMENTALLY_DIFFERENT_PRODUCT`. It is a boundary contract, not an
implementation claim.

The teacher PDF is the product-boundary authority. Page 1 defines one local
folder per Workflow instance, says the folder contains the task material/state,
and explicitly assigns management rather than concrete research execution to
the cloud. Page 2 assigns actual work to existing Claude Code/Codex and says
ReAgent does not develop the execution engine. Pages 2-3 identify five
composable Workflows, illustrate possible files, explicitly leave exact folder
and prompt structure undecided, and demonstrate Progress Report upload and
cross-session/Harness continuation.

Teacher requirement IDs below refer to
`docs/audits/TEACHER_DESIGN_REQUIREMENT_LEDGER.md`.

## V1 in one sentence

ReAgent V1 is a cloud management and supply system that generates versioned,
downloadable local Workflow Packages; an existing Claude Code or Codex Agent
Harness performs the concrete research from that folder and returns Progress
Reports to the cloud.

## Three-part responsibility boundary

```text
Cloud management and supply
  -> versioned downloadable Workflow Package
  -> movable local folder (authoritative Local Task State)
  -> existing Claude Code/Codex Agent Harness performs research
  -> local outputs + Progress Report
  -> explicit cloud upload, validation, history, and progress projection
```

The cloud may proxy bounded external API operations, but proxying does not make
the cloud the Workflow executor.

## Cloud V1

### Source-required responsibilities

| Responsibility | Teacher evidence |
|---|---|
| Project creation and management | TMR-006, TMR-018; PDF pages 1 and 3 |
| AG Admin and normalized internal/external Skill ingestion | TMR-005; page 1 |
| Workflow/template/Skill package management | TMR-005, TMR-006; page 1 |
| Reproducible local-folder package generation and download | TMR-002, TMR-006, TMR-018; pages 1 and 3 |
| Progress Report collection and unified project/workflow view | TMR-007, TMR-018; pages 1 and 3 |
| Continuity metadata across computers and Harnesses | TMR-007, TMR-016, TMR-018; pages 1 and 3 |
| Central external-provider credential custody | TMR-008; page 1 |
| API proxy used by local execution | TMR-008; page 1 |

### Source-supporting internal services

The source does not mandate implementation technology. The following are
allowed supporting details when they serve the responsibilities above without
moving concrete research into the cloud:

- PostgreSQL for Cloud Project State;
- file/object storage for package archives, uploads, Progress Reports, and
  returned artifact snapshots;
- package, Workflow, template, and Skill registries;
- canonical serialization, checksums, version pins, and immutable history;
- provider ports and adapters behind a Cloud API Proxy;
- `ProviderOperation` usage, idempotency, cost, and settlement accounting;
- FastAPI management/proxy APIs and a Next.js management/progress UI;
- deterministic validators for packages, uploaded reports, and returned
  artifacts.

These services may validate or store research output. They may not silently
generate it.

### Explicitly not Cloud V1 responsibilities

- executing research Workflow nodes;
- scheduling local research steps through backend `AgentRuntime`;
- invoking a hosted LLM to generate the final report;
- using hosted OpenAlex calls as an internal research step rather than a proxy
  response to the local Harness;
- keeping hidden server memory as the only continuation state;
- treating server `StepRun`, checkpoint, or `ExecutionEvent` records as the
  authoritative local task;
- replacing Claude Code, Codex, or another existing Harness;
- presenting browser Resume as the default V1 research-execution command.

This exclusion follows TMR-003, TMR-004, TMR-009, and TMR-010 (PDF pages 1-2).

## Local Workflow Folder V1

### Non-negotiable semantics

The folder must:

- correspond to one Workflow instance (TMR-002, page 1);
- be downloadable, unpackable, and movable between local paths or machines;
- be sufficient for a supported Harness to identify the task and current state
  from files (TMR-009, TMR-015, TMR-016; pages 1-3);
- contain or reference immutable, pinned Workflow, template, and Skill versions;
- retain Harness-readable instructions and prompts;
- retain user inputs without silently rewriting source material;
- hold concrete working context, outputs, local tool artifacts, Progress
  Reports, and continuation information;
- support a fresh session and, eventually, another approved Harness continuing
  from the files (TMR-016, TMR-018; page 3);
- contain Cloud API Proxy configuration without any provider credential;
- preserve checksums and identities needed to validate packages, inputs,
  outputs, and uploads.

### Source-undecided experiment areas

The following are explicitly **SOURCE_UNDECIDED — EXPERIMENTAL**:

- exact directory and file names;
- one root `AGENT.md` versus multiple scoped instruction files;
- prompt count, splitting, and precedence;
- Skill embedding versus validated references or a hybrid;
- context compression and memory layout;
- final Progress Report representation;
- package archive format;
- package update, refresh, merge, and conflict behavior;
- whether file-system read-only rules are technical enforcement or Harness
  instructions;
- exact handoff representation between Workflow outputs and inputs.

The illustrative tree on PDF pages 2-3 is evidence of intended roles, not a
final format (TMR-013, TMR-014). R1 may propose paths only when each is marked
`EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE`.

## Agent Harness V1

The Agent Harness is an existing Claude Code, Codex, or owner-approved
equivalent. It:

- reads local entry instructions, prompts, Skills, inputs, and context;
- interacts with the user;
- decides and performs the concrete research work within the packaged method;
- invokes local tools and, where authorized, the Cloud API Proxy;
- writes local outputs and tool artifacts;
- updates continuation context;
- writes a local Progress Report before the round ends.

ReAgent does not implement this Harness in initial V1 (TMR-010, PDF page 2).
The project may generate files, validate them, and test their compatibility with
existing Harnesses. The preserved Hosted AgentRuntime is not the
teacher-defined Agent Harness.

## State authority

### Local authoritative task state

The local folder is authoritative for:

- current concrete research progress;
- working research context;
- Harness decisions that must survive continuation;
- local outputs and drafts;
- local tool-generated artifacts;
- local failure/warning information needed to resume;
- continuation instructions and status;
- local Progress Reports before upload.

If the cloud is unavailable, the folder must still communicate the task and
current research state to the Harness. External API calls may be unavailable,
but task understanding must not depend on hidden backend memory.

### Cloud authoritative management state

The cloud is authoritative for:

- project identity and ownership when implemented;
- selected Workflow type and project/package association;
- package version, manifest, checksum, and generation history;
- pinned Workflow, template, and Skill versions;
- package download history and continuity metadata;
- uploaded Progress Report immutable history;
- cloud project/workflow progress projection;
- proxy policy, request identity, usage, cost, and settlement;
- cloud-stored user uploads and explicitly returned artifacts;
- package, upload, and artifact checksum metadata.

An uploaded snapshot can be cloud-authoritative as a record of what was
received. It does not silently supersede unuploaded active Local Task State.

### Not authoritative for V1 research execution

The following current hosted records are not V1 concrete task truth:

- backend `AgentRuntime` state;
- server `WorkflowRun`/`StepRun` lifecycle state;
- server checkpoint records;
- server memory revisions;
- hosted `ExecutionEvent` streams.

Current PostgreSQL tables remain valid internal-test and optional Hosted Mode
infrastructure. They may later be reused or extended for Cloud Project State.
Current SQL mappings do not already implement the accepted authority split.

## Workflow taxonomy

The teacher-defined product taxonomy remains (TMR-011, PDF page 2):

1. Literature Search;
2. Scientific Question / Idea Finding;
3. Writing;
4. Review;
5. Reproduction and Experiment.

Each can run independently. They may compose so that one Workflow's outputs
become another's inputs (TMR-012, TMR-017; pages 2-3). The taxonomy is not an
implementation-completeness claim. The teacher source does not select the
first Workflow or require all five to be complete in R1.

## Hosted Mode status

The current backend research path is preserved as the **Hosted AgentRuntime**:

- `KEEP_AS_INTERNAL_TEST_TOOL` for deterministic architecture/contract tests;
- `KEEP_AS_OPTIONAL_HOSTED_MODE` for a possible separately authorized future;
- non-default and outside teacher-aligned V1;
- frozen from additional product development during the V1 mainline.

The preserved Hosted Prototype Demo remains honest evidence of the current
implementation. It is not evidence that the teacher-aligned package path exists.

## Canonical terminology

| Term | Frozen V1 meaning |
|---|---|
| **Cloud Project State** | Project/package/Skill/progress/proxy management metadata for which the cloud is authoritative. |
| **Local Task State** | Concrete research execution state stored in the portable local folder. |
| **Agent Harness** | Existing Claude Code, Codex, or equivalent executor that performs the research. |
| **Hosted AgentRuntime** | ReAgent-owned backend execution loop preserved as an internal test Harness or optional future Hosted Mode. It is not the teacher-defined Agent Harness. |
| **Progress Report** | Local Harness-produced per-round summary explicitly uploaded to cloud management. |
| **ExecutionEvent** | Hosted prototype/internal execution record. It is not a Progress Report. |
| **Workflow Package** | Versioned downloadable local-folder bundle for one project/Workflow instance. |
| **Skill Package** | Pinned normalized capability material delivered in, or securely referenced by, a Workflow Package. |
| **Artifact** | A file or metadata object. Authority depends on whether it belongs to Cloud Project State or Local Task State. |
| **Cloud API Proxy** | Cloud boundary that protects credentials and translates/account provider calls requested by a local Harness without executing the full research Workflow. |

Avoid “Agent Runtime” for the external Harness. Qualify the current project
component as **Hosted AgentRuntime** or **hosted execution runtime**.

## Hosted-work freeze

No further V1 product work is authorized for backend research execution,
browser-triggered run/resume, Hosted AgentRuntime productionization, hosted LLM
activation, new hosted research-provider adapters, hosted worker/queue/lease,
automatic relevance evaluation, full-pool retrieval benchmark, or server-side
research-report UI expansion.

Preservation, repository-safety bug fixes, deterministic tests, reusable schema
or validator extraction, and a future separately authorized Hosted Mode are not
prohibited.

## No-code R0 boundary

The following are expected later but explicitly prohibited in R0:

- adding a teacher-aligned execution-mode boundary or feature flag;
- disabling or hiding hosted execution endpoints/UI in V1 mode;
- implementing a Workflow Package generator;
- implementing archive/ZIP creation or a package-download API;
- defining the final Progress Report schema;
- implementing Progress Report upload/history/projection APIs;
- implementing Cloud API Proxy endpoints or caller authentication;
- adding a local proxy-client Skill;
- adding local-folder/package validators;
- adding Codex/Claude Code compatibility tests;
- separating current SQL state models in code;
- changing frontend navigation or management views;
- modifying Workflow JSON, migrations, dependencies, source composition, or
  provider activation.

R0 changes documentation and authority only. Current behavior remains the
preserved hosted prototype until later owner-authorized implementation work.

## Traceability summary

| Boundary | Requirements | PDF pages |
|---|---|---:|
| Workflow standardization and local instance folder | TMR-001, TMR-002 | 1 |
| Cloud/local/Harness separation and no cloud research execution | TMR-003, TMR-004, TMR-009, TMR-010 | 1-2 |
| AG Admin, package delivery, progress, and proxy | TMR-005-TMR-008 | 1 |
| Five independent/composable Workflows | TMR-011, TMR-012 | 2 |
| Folder/prompt format remains experimental | TMR-013, TMR-014 | 1-2 |
| Harness instructions, memory, inputs, outputs, and continuity | TMR-015-TMR-017 | 3 |
| Full download/local-execution/upload/continuation journey | TMR-018 | 3 |
