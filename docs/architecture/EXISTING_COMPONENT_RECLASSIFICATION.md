# Existing Component Reclassification

Status: **Frozen planning classification under ADR 0009**

Date: 2026-08-03

## Purpose

This document preserves the existing implementation while assigning each major
component one primary treatment under the teacher-aligned V1 boundary. A
classification is a product-role decision, not an instruction to delete,
disable, refactor, or modify code in R0.

Allowed primary treatments:

- `KEEP_AS_CLOUD_V1`
- `KEEP_BUT_REFRAME`
- `KEEP_AS_INTERNAL_TEST_TOOL`
- `KEEP_AS_OPTIONAL_HOSTED_MODE`
- `DEFER`
- `NEEDS_LATER_OWNER_DECISION`

Teacher requirement IDs are defined in the committed requirement ledger.

## Component matrix

| Component | Primary treatment | Current role | Teacher-aligned V1 role | User-facing behavior later changes? | Future code-action phase | Teacher IDs |
|---|---|---|---|---|---|---|
| Domain Core | `KEEP_BUT_REFRAME` | Models hosted Workflow Runs, sessions, steps, approvals, checkpoints, and artifacts | Reuse pure identities, versions, checksums, lifecycle invariants, and validation for Cloud Project State and package/report records; hosted lifecycle remains qualified | Yes: project/package/progress concepts replace hosted execution as mainline | R1+ domain spike; state separation no earlier than the relevant feature | TMR-001-TMR-003, TMR-006-TMR-009 |
| Workflow definitions | `KEEP_BUT_REFRAME` | Immutable static DAGs consumed by backend execution | Source material for versioned Workflow templates/packages, pins, dependency and handoff validation | Yes: catalog selection should generate/download a package rather than launch server execution | R1 package definition; R6 handoff | TMR-001, TMR-006, TMR-012, TMR-017 |
| Workflow Engine | `KEEP_AS_INTERNAL_TEST_TOOL` | Resolves references, schedules steps, applies retry/approval decisions through hosted execution coordination | Preserve deterministic validators/reference logic as internal evidence; extract only explicitly useful validation for packages later | Yes: it must not be the default V1 research executor | R1 may reuse validators; optional Hosted Mode only otherwise | TMR-004, TMR-010, TMR-015 |
| Skill System | `KEEP_BUT_REFRAME` | Defines typed versioned Skills and executes registered Python implementations | Basis for normalized Skill identity, validation, compatibility metadata, package contents, and Harness-readable capability instructions | Yes: portable Skill packages replace Python-only hosted invocation as the primary product view | R1 package subset; R4 administration/import | TMR-005, TMR-006, TMR-014 |
| Skill Registry | `KEEP_BUT_REFRAME` | In-process explicit allow-list with no dynamic import | Validation/reference prototype for a persistent normalized Skill catalog and package registry | Yes: operators eventually manage/import/package Skills | R4 | TMR-005, TMR-006 |
| Hosted AgentRuntime | `KEEP_AS_OPTIONAL_HOSTED_MODE` | Restores PostgreSQL state, schedules via Workflow Engine, invokes Skills, writes checkpoints/memory/events/artifacts | Preserved optional future Hosted Mode and internal deterministic test Harness; never the teacher-defined Agent Harness | Yes: hidden/disabled from teacher-aligned default after later implementation authorization | Later owner-authorized mode boundary; not R0 | TMR-003, TMR-004, TMR-009, TMR-010 |
| ExecutionDispatcher | `KEEP_AS_OPTIONAL_HOSTED_MODE` | Submits resume/approval execution to `AgentRuntime`; sync adapter runs inline | Hosted-mode submission boundary only; not part of local Harness execution | Yes: default cloud UI must not submit research execution | Later teacher-aligned mode separation; hosted scaling deferred | TMR-004, TMR-010, TMR-018 |
| PostgreSQL repositories | `KEEP_BUT_REFRAME` | Authoritative hosted run/session/step/checkpoint/memory/event/provider storage | Cloud authority for projects, packages, Skill/template versions, downloads, uploaded Progress Reports, proxy accounting, and returned metadata | Yes: cloud views must distinguish management state from Local Task State | R1+ additive cloud models; R2/R3/R4 by feature | TMR-005-TMR-009, TMR-016, TMR-018 |
| Checkpoints | `KEEP_AS_OPTIONAL_HOSTED_MODE` | Hosted execution recovery boundaries | Hosted/internal recovery evidence only; not a Progress Report or portable continuation contract | Yes: must not be shown as local continuity | Optional Hosted Mode; no R0 action | TMR-007, TMR-009, TMR-016 |
| Memory revisions | `KEEP_AS_OPTIONAL_HOSTED_MODE` | Hosted server working-memory history | Hosted/internal state only; not authoritative V1 local context | Yes: local folder context becomes the V1 continuation source | Optional Hosted Mode; local context experiment in R1 | TMR-009, TMR-016 |
| ExecutionEvents | `KEEP_AS_OPTIONAL_HOSTED_MODE` | Append-only hosted runtime event timeline | Preserve hosted trace; build a separate uploaded Progress Report history/projection | Yes: server timeline must not be presented as V1 progress continuity | R2 adds the distinct progress model; hosted event UI later hidden/qualified | TMR-007, TMR-016, TMR-018 |
| Approval system | `NEEDS_LATER_OWNER_DECISION` | Pauses and resumes hosted steps from the browser | Potential future approval of packages, proxy scopes, uploads, or optional hosted actions; no source mandate for hosted step approval | Yes if reused; current approve/resume path is outside default V1 | Decide with the first package/proxy approval need; not R0 | TMR-004, TMR-006, TMR-008, TMR-010 |
| ProviderOperation | `KEEP_AS_CLOUD_V1` | Durable reservation, settlement, usage, cost, idempotency, and replay for hosted providers | Cloud API Proxy ledger for bounded provider calls requested by local Harnesses | Yes: operations become proxy records rather than evidence that cloud ran the Workflow | R3 | TMR-008 |
| OpenAlex adapter | `KEEP_BUT_REFRAME` | Backend research Skill directly performs discovery | Provider adapter behind a local-Harness-facing Cloud API Proxy with normalized results | Yes: local Harness initiates bounded proxy requests; cloud does not own search methodology | R3 after endpoint/policy approval | TMR-004, TMR-008 |
| Grounded-report contracts | `KEEP_BUT_REFRAME` | Hosted V3 summary/evidence/claim/citation/report operation schemas | Candidate portable Literature Search Skill contracts, prompts, package files, handoff artifacts, and upload validation | Yes: existing hosted generation is not the default consumer | R1 experiment may package a bounded subset; later owner review | TMR-001, TMR-006, TMR-010, TMR-012, TMR-017 |
| Grounded provenance validator | `KEEP_BUT_REFRAME` | Blocks publication of unsupported hosted V3 output | Deterministic folder-side validation under the Harness and/or cloud-side validation of uploaded outputs, without cloud generation | Possibly: validation results may appear in package or progress views | R1 local validator experiment or later upload validation | TMR-006, TMR-007, TMR-015-TMR-018 |
| Anthropic adapter substrate | `DEFER` | Inactive structured-output mapper targeting future hosted generation | No V1 hosted generation role; preserve for separately approved proxy or Hosted Mode study | No current exposure; must remain inactive | After teacher-aligned V1 and a new owner provider/data decision | TMR-004, TMR-008, TMR-010 |
| Fake/Synthetic providers | `KEEP_AS_INTERNAL_TEST_TOOL` | Network-free deterministic provider behavior and fixtures | Test package generation, schemas, proxy normalization, validation, and replay without credentials or real content | No production exposure required | R1+ tests | TMR-006, TMR-008, TMR-010, TMR-015 |
| Artifact storage | `KEEP_AS_CLOUD_V1` | Stores immutable hosted output bytes and metadata | Store Workflow Packages, Skill/template payloads, uploads, Progress Reports, returned artifact snapshots, checksums, and archives | Yes: package/report/upload views become mainline; hosted artifacts remain qualified | R1 package archives; R2 reports; later returned outputs | TMR-006, TMR-007, TMR-018 |
| FastAPI | `KEEP_AS_CLOUD_V1` | Run/resume/approval/event/artifact/provider HTTP API | Cloud project, AG Admin, package/download, Progress Report, progress projection, artifact, and proxy APIs | Yes: management/download/upload/proxy becomes default; hosted execution routes become optional/hidden later | R1-R4 incrementally | TMR-005-TMR-008, TMR-018 |
| Next.js | `KEEP_BUT_REFRAME` | Creates/executes hosted runs and displays approvals/events/artifacts | Cloud project/Skill/package management, download, Progress Report history, progress projection, and continuation UI | Yes, materially | R1 package UI, R2 progress UI, R4 AG Admin; hosted UI preserved as optional | TMR-005-TMR-007, TMR-018 |
| Docker/Compose | `KEEP_AS_CLOUD_V1` | Local topology for PostgreSQL, migrations, seed, FastAPI, and Next.js hosted demo | Reproducible development environment for cloud management/storage/proxy services; preserved hosted demo profile | Later service purpose/labels may change; no R0 change | As needed by R1-R4; hosted demo preserved | TMR-005-TMR-008 |
| Optional evaluation module | `DEFER` | Fake/synthetic automated silver relevance evaluation and proposed real Judge calibration | Preserved optional evaluation evidence; not teacher-aligned initial core | No default V1 exposure | New owner decision after core V1 or evaluation claim need | TMR-005-TMR-008, TMR-018 |
| Existing tests | `KEEP_AS_INTERNAL_TEST_TOOL` | Verify hosted domain/runtime/persistence/API/UI/provider behavior | Preserve regressions and optional hosted evidence; reuse fakes/contracts; add distinct package/Harness/progress/proxy tests later | No direct user behavior | R1 onward adds source-aligned suites; do not weaken existing tests without scoped review | TMR-001-TMR-018 as applicable |

## Treatment summaries

### KEEP_AS_CLOUD_V1

- ProviderOperation
- Artifact storage
- FastAPI
- Docker/Compose

Their current hosted consumers do not define their future authority. New
teacher-aligned use cases are additive and require later implementation.

### KEEP_BUT_REFRAME

- Domain Core
- Workflow definitions
- Skill System and Skill Registry
- PostgreSQL repositories
- OpenAlex adapter
- grounded-report contracts and provenance validator
- Next.js

Reframing changes product ownership and consumer paths. It does not assert that
the current code already serves the new role.

### KEEP_AS_INTERNAL_TEST_TOOL

- Workflow Engine
- Fake/Synthetic providers
- existing tests

The Workflow Engine may supply validators, but its backend scheduler is not V1
research execution.

### KEEP_AS_OPTIONAL_HOSTED_MODE

- Hosted AgentRuntime
- ExecutionDispatcher
- checkpoints
- memory revisions
- ExecutionEvents

They remain non-default, preserved, and frozen from V1 product expansion.

### DEFER

- Anthropic adapter substrate activation
- Optional Evaluation Module

### NEEDS_LATER_OWNER_DECISION

- Approval system, if repurposed beyond the preserved hosted prototype

## R0 code-change answer

No component requires or receives a code change in R0. “Future code-action
phase” records the earliest relevant planning point; it is not implementation
authorization. No deletion is recommended by this document.
