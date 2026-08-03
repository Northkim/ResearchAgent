# ReAgent Project Development Plan

## Current governing route — teacher-aligned initial V1

Status: **OWNER-APPROVED IMPLEMENTATION SEQUENCE**

Order status: **NOT A TEACHER-MANDATED ORDER**

Governing decision: `.agent_read/decisions/0009-teacher-aligned-initial-product-boundary.md`

The owner accepted the committed Teacher Design Alignment Audit verdict
`FUNDAMENTALLY_DIFFERENT_PRODUCT`. For initial V1, the teacher PDF and ADR 0009
supersede the historical hosted-product assumptions below wherever they
conflict.

Initial V1 uses three parts:

- the cloud manages projects, Skills, Workflow Packages, downloads, Progress
  Reports, progress projections, provider credentials, and API proxy calls;
- the downloaded local Workflow folder is authoritative for concrete research
  execution state;
- an existing Claude Code or Codex Agent Harness performs the research, writes
  outputs, and produces Progress Reports.

The cloud does not execute concrete research in teacher-aligned V1. PostgreSQL
may be authoritative for Cloud Project State—project/package/Skill/progress/
proxy metadata—but not for hidden concrete Local Task State. The exact folder
tree, prompt decomposition, Skill package format, Progress Report schema,
conflict behavior, and Cloud API Proxy protocol remain experimental or require
later owner decisions.

### Teacher-aligned mainline

This is the owner-approved implementation sequence. The teacher source defines
the product responsibilities and five-Workflow taxonomy; it does not mandate
this engineering order.

| Phase | Owner-approved milestone | Boundary |
|---|---|---|
| R0 | V1 product-boundary freeze | Documentation/authority only; no production code |
| R1A | Experimental local Literature Search Workflow Package generator | **IMPLEMENTED** — deterministic, credential-free offline folder and ZIP with self-contained validation |
| R1B | External Agent Harness compatibility acceptance | **PASS_WITH_WARNINGS (CODEX)** — owner-attested fresh sessions plus checksum-verified execution, folder-only continuation, and moved-folder continuation; Claude Code untested |
| R2A | Progress Report contract, upload, immutable history and aggregation | **PASS_WITH_WARNINGS** — native v0.2, explicit before/after context digests, v0.1 normalization, upload/history/projection API, client and additive persistence |
| R2B | External upload and restart acceptance | **PASS_WITH_WARNINGS — UPLOAD_ACCEPTED** — external Package, loopback HTTP, isolated PostgreSQL, byte retention, idempotency, conflict exclusion and restart recovery passed |
| R3A | Cloud API Proxy contract, threat model and owner decision packet | **PASS; R3B OWNER DECISIONS RATIFIED** — ADR 0011 approves only the experimental fake-provider profile; no implementation or provider call |
| R3B | Fake-adapter API Proxy implementation and acceptance | **IMPLEMENTATION GATE OPEN — NOT STARTED** — disabled-by-default `paper.search/v0.1`, short-lived scoped bearer, fixed zero-cost/network limits and separate Proxy ledger |
| R3C | Supervised live-provider acceptance | **LIVE-PROVIDER GATE CLOSED** — production auth/HTTPS, current provider terms/credentials/rate/cost/retry/retention and public-network security require separate owner approval |
| R4 | Skill management/import and package delivery | Build AG Admin, normalized Skill ingestion, versioning, review, and packaging |
| R5 | Cross-machine and cross-Harness continuation | Refresh/move packages and verify continuity under owner-approved conflict policy |
| R6 | Workflow output-to-input handoff | Define and validate composable Workflow handoffs |
| R7 | Additional teacher-defined Workflow templates | Expand Idea Finding, Writing, Review, and Reproduction/Experiment according to owner priority |

Literature Search in R1 is an **OWNER IMPLEMENTATION-SEQUENCING PROPOSAL**, not
a teacher-mandated first Workflow. The exact R1 package layout must be marked
`EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE`.

R1A and R1B are deliberately separate. R1B proves the teacher-defined
local-folder and external-Harness boundary for the bounded offline Codex
experiment, with fresh-session facts owner-attested and file/checksum outcomes
independently verified. Claude Code remains untested, the tree remains
experimental, and no API-proxy capability is proved.
The acceptance record is
`docs/acceptance/R1B_CODEX_HARNESS_ACCEPTANCE_REPORT.md`.

R2A now reconciles the v0.1 mismatch without rewriting history. Native v0.2
uses deterministic non-cyclic report identity and exact context-before/context-
after file digests. The cloud explicitly receives and validates reports,
retains original bytes and immutable metadata, detects chain/conflict states,
and reconstructs a deterministic progress projection. The local client makes a
single explicit upload and never changes task state. Migration
`20260803_0003_progress_reports` is additive and does not repurpose hosted
events/checkpoints. The optional local-progress frontend view remains deferred.

R2B has accepted the external Progress Report path and R2 state is
`UPLOAD_ACCEPTED`. R3A defined the next boundary without implementation. ADR
0011 now ratifies for R3B only a disabled-by-default
`EXPERIMENTAL_FAKE_PROVIDER_VERTICAL_SLICE`: `paper.search/v0.1`, a short-lived
opaque bearer capability with exact project/Package/Workflow/fake-adapter
scope, deterministic idempotency/reconciliation, a separate Proxy operation
ledger, fixed request/result/time/count/concurrency limits, and zero money,
real-provider and external-network use. The R3B implementation gate is open;
R3B has not started. R3C remains a separately authorized live-provider phase
and its gate is closed.

### Preserved optional mode

Status: **DEFERRED_OPTIONAL_MODE**

The following historical work remains preserved but is not the default initial
V1 product path:

- Hosted AgentRuntime and backend Workflow/Skill research execution;
- hosted LLM and hosted grounded-report generation;
- hosted OpenAlex research execution;
- Optional Evaluation Module and automated relevance Judge;
- server execution, approval, event-timeline, and research-report UI;
- hosted worker/queue/lease productionization.

Further V1 product development in these areas is frozen unless the owner
separately reauthorizes it. The freeze allows preservation, repository-safety
bug fixes, deterministic regression tests, extraction/repackaging of reusable
schemas and validators, and a separately approved future Hosted Mode. ADR 0007
and ADR 0008 are deferred by ADR 0009; Phase 9C hosted activation is not
authorized.

### Immediate source-defined gaps

The mainline prioritizes capabilities absent from the current repository:

1. versioned local Workflow Package generation and download;
2. Harness-readable local instructions, pinned versions, inputs, outputs,
   context, Progress Reports, and continuation state;
3. Codex/Claude Code compatibility evidence without backend research execution;
4. externally accepted Progress Report upload, immutable history, and cloud progress projection;
5. a local-Harness-facing Cloud API Proxy with cloud-held credentials;
6. AG Admin and normalized Skill import/package delivery;
7. cross-machine/cross-Harness continuation;
8. Workflow output-to-input handoff and additional Workflow templates.

### R0 no-code boundary

R0 changes governance documentation only. It does not add mode flags, package
generation, downloads, progress schemas/APIs, proxy endpoints, local Skills,
validators, compatibility tests, state-model separation, frontend behavior, or
runtime disabling. Those require later scoped implementation tasks.

## Historical hosted-development plan — preserved, non-governing for initial V1

The sections below record the original hosted Web Agent direction and remain
useful implementation history. They are not deleted or retroactively declared
invalid. Where they describe a project-owned Agent Runtime, server execution,
PostgreSQL concrete-task authority, or browser monitoring as the V1 default,
ADR 0009 and the current governing route above take precedence.

## 1. Project Vision

ReAgent is a web-based research agent platform designed for long-running autonomous research workflows.

The goal is not to build a simple chatbot, but to build agent infrastructure that allows users to create research projects, define workflows, provide materials, and let AI agents continuously perform research tasks while maintaining memory, state, and generated artifacts.

The final system should allow users to:

1. Create a research project through a web interface.
2. Upload research materials.
3. Select a research workflow.
4. Launch an autonomous agent.
5. Monitor agent progress.
6. Review generated research artifacts.
7. Continue previous research sessions without losing context.

## 2. Core Design Philosophy

The system follows three principles.

### 2.1 Persistent Agent

Agents should maintain knowledge across sessions.

The system should support:

- project memory
- execution history
- progress tracking
- state recovery

### 2.2 Workflow-driven Research

Research tasks should be represented as reusable workflows.

Examples:

- Literature Search
- Idea Generation
- Paper Writing
- Paper Review
- Experiment Reproduction

### 2.3 Platform-oriented Architecture

The system should eventually become a deployable web platform.

The architecture should separate:

- Agent Runtime
- Workflow Engine
- Skill System
- Backend Services
- Frontend Interface

## 3. High-level Architecture

```text
                    Web Frontend
                         |
                  Backend Platform
                         |
        -------------------------------------
        |                  |                |
  Workflow Engine     Agent Manager    Skill Manager
        |                  |                |
        -------------------------------------
                         |
                   Agent Runtime
                         |
                LLM + Tools + Memory
```

## 4. Main Development Modules

### Module 1: Agent Runtime Core

Purpose:

Build the foundation that allows an AI agent to understand tasks and execute work.

Responsibilities:

- workspace management
- instruction loading
- context management
- memory management
- execution state

Expected structure:

```text
project/
├── AGENT.md
├── config.yaml
├── inputs/
├── outputs/
├── memory/
├── skills/
└── logs/
```

### Module 2: Workflow Engine

Purpose:

Transform research processes into executable workflows.

Responsibilities:

- workflow definition
- workflow execution
- task dependencies
- checkpoints

Example:

```text
Literature Search
        |
        v
Search Papers
        |
        v
Read Papers
        |
        v
Extract Knowledge
        |
        v
Generate Report
```

### Module 3: Skill System

Purpose:

Provide reusable capabilities for agents.

Examples:

- paper search
- PDF parsing
- citation management
- code execution
- experiment running

Each skill should contain:

- metadata
- implementation
- documentation

### Module 4: Memory and State System

Purpose:

Enable long-running research.

The system should support:

- Short-term state: current execution state
- Working memory: current task context
- Long-term memory: historical knowledge

### Module 5: Artifact Management

Purpose:

Manage research outputs.

Artifacts include:

- reports
- papers
- experiment results
- generated code

Requirements:

- version tracking
- metadata
- retrieval

### Module 6: Backend Platform

Purpose:

Provide cloud services.

Responsibilities:

- user management
- project management
- workflow management
- API management

Suggested technology:

- FastAPI
- PostgreSQL
- Redis

### Module 7: Web Frontend

Purpose:

Provide a user interface.

Main pages:

- dashboard
- project workspace
- workflow selection
- agent monitoring
- artifact viewer

Suggested technology:

- React
- Next.js

### Module 8: Monitoring and Evaluation

Purpose:

Make agent behavior observable.

Track:

- execution logs
- tool calls
- errors
- generated artifacts
- workflow status

## 5. Recommended Development Order

### Step 1: Define Architecture

Deliver:

- system architecture
- folder structure
- data models
- workflow specification

### Step 2: Implement Agent Runtime

Deliver:

- workspace parser
- agent context
- memory manager
- execution state

### Step 3: Implement Workflow Engine

Deliver:

- workflow schema
- workflow executor
- checkpoint system

### Step 4: Implement Skill System

Deliver:

- skill registry
- skill loading
- tool execution

### Step 5: Implement Artifact and Logging System

Deliver:

- artifact storage
- execution records

### Step 6: Build Backend API

Deliver:

- project API
- workflow API
- execution API

### Step 7: Build Web Interface

Deliver:

- user dashboard
- project management
- agent monitoring

## 6. Engineering Requirements

The project should prioritize:

- modular architecture
- clean interfaces
- testability
- documentation
- extensibility

The system should avoid:

- hard-coded workflows
- single-agent assumptions
- tightly coupled components

## 7. Current Development Goal

The first implementation goal is **not** the full web platform.

The first goal is to build a reliable Agent Runtime and Workflow foundation that can later be deployed as a web service.

Current priority:

1. Architecture design
2. Agent Runtime prototype
3. Workflow abstraction
4. Persistent memory system
