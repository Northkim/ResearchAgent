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
| R3B-I | Fake-adapter API Proxy implementation and SQL qualification | **PASS_WITH_WARNINGS** — disabled-by-default `paper.search/v0.1`, digest-only scoped bearer, explicit client/CLI, separate Proxy ledger and migration `20260804_0004` |
| R3B-A | External fake-adapter API Proxy acceptance | **PASS_WITH_WARNINGS — FAKE_PROXY_ACCEPTED** — external Package, real loopback Uvicorn/HTTP, token lifecycle, isolated PostgreSQL restart and Package non-mutation passed |
| R3C-D | OpenAlex source qualification and owner decision | **PASS_WITH_CURRENT_SOURCE_WARNINGS** — ADR 0012 approves one supervised experimental OpenAlex Works metadata adapter; no key/API call/implementation |
| R3C-I | OpenAlex Proxy adapter implementation and mocked qualification | **PASS_WITH_WARNINGS — LIVE_ACCEPTANCE_PENDING** — fixed adapter, privacy-safe SQL, exact microusd, scripted transport and PostgreSQL qualification; zero key/Internet |
| R3C-A | Supervised live OpenAlex acceptance | **RETRY 4 BLOCKED — LIVE ACCEPTANCE EVIDENCE PRESERVED** — one HTTP-200/1,000-microusd call normalized five real Works; pre-restart recovery passed, but post-restart verification raised a value-free RuntimeError; no retry or repair occurred |
| R3C-N1 | Live normalization failure forensics | **INCONCLUSIVE** — exact live predicate not preserved; no approved failing shape reproduced offline; no source repair or Provider call |
| R3C-N2-I | Strict response policy and structural diagnostics | **PASS_WITH_WARNINGS** — strict whole-response failure ratified; default-disabled value-free internal diagnostics synthetic/SQL qualified; no live/key/docs call |
| R3C-I2 | Abstract formatting-control compatibility | **PASS_WITH_WARNINGS — LIVE_ACCEPTANCE_PENDING** — ADR 0014 maps only abstract-token TAB/LF/CR to safe spacing; fictional/SQL/backend qualification passed with zero key/network/Provider call |
| R3C-R1 | Post-restart recovery forensics | **PASS — DEFECT REPRODUCED OFFLINE** — both status routes passed; delayed exact replay deterministically failed freshness before durable idempotency; zero live call/key/docs access |
| R3C-R2 | Delayed replay ordering remediation | **PASS — OWNER ACCEPTED** — ADR 0015 resolves authorized existing replay/conflict before freshness, retains freshness for new admission, and passes real PostgreSQL/Uvicorn aged-replay restart qualification with zero live call |
| R3C-C | Composite experimental OpenAlex acceptance closure | **PASS_WITH_WARNINGS — LIVE_OPENALEX_ACCEPTED** — ADR 0016 composes immutable R3C-A-R4 live evidence with R3C-R1 diagnosis and owner-accepted R3C-R2 restart qualification; no historical blocked result changes |
| MVP-A0 | Local V0.1 product readiness audit | **BLOCKED — GAPS PRESERVED** — component backends passed, but project, Package, Progress UI, startup, typecheck, and teacher-aligned E2E product gaps prevented owner acceptance |
| MVP-I | Local V0.1 product integration | **PASS_WITH_WARNINGS — OWNER ACCEPTANCE PENDING** — local project persistence/API, deterministic Package download, existing Progress projection/history UI, primary local navigation, safe startup, and full-stack tests are integrated; no Hosted/cloud research execution |
| MVP-I1 | Persistent local dotenv startup | **PASS — OWNER ACCEPTANCE PENDING** — `make dev` safely resolves exported/custom/root dotenv database configuration without executing or printing values, while retaining loopback/ProjectDB safeguards and external PostgreSQL lifecycle |
| MVP-LS1 | Complete autonomous Literature Search round | **PASS_WITH_WARNINGS — READY FOR OWNER ACCEPTANCE** — one Package command runs one bounded local Codex round, normal OpenAlex-only or explicit fictional demo transport, four local outputs, one automatic idempotent report upload, verified projection, and guided UI; no Hosted/cloud research execution |
| MVP-LS2 | Interactive Codex Literature Search experience | **PASS_WITH_WARNINGS — READY FOR OWNER ACCEPTANCE** — default Package command attaches Codex to the current terminal, gates search/final writing on owner checkpoints, validates a versioned completion artifact, cleans up interrupts, preserves explicit auto/recovery modes, and retains the LS1 cloud/local boundary |
| MVP-LS2.1 | Fresh post-round upload authorization | **PASS_WITH_WARNINGS — OWNER ACCEPTANCE PENDING** — ADR 0021 separates search and exact-report upload sessions, safely reconciles expiry/response loss without rerunning Codex or search, and makes no-report cloud uncertainty explicit; zero live OpenAlex use |
| ARCH-D1 | Hybrid Project Workspace and Workflow Capsule design | **DESIGN COMPLETE; NIGHT-B4 PULL SYNC FOUNDATION IMPLEMENTED** — ADR 0022 defines one logical Workspace per Project and isolated versioned Capsules; B1/B2 provide persistence and desired state, ADR 0023/B3 provide identity/bootstrap/adoption, and ADR 0024/B4 add explicit pull sync, exact-instance acquisition, atomic installation, Installed Lock and acknowledgement recovery; later product slices remain owner-gated |
| NIGHT-B1 | Project Workspace persistence foundation | **PASS — OWNER REVIEW REQUIRED** — additive migration `20260806_0008`, local Workflow Definition/version, Capsule version, Project Workflow Instance, deterministic legacy Literature Search mapping, repository/UoW, isolated PostgreSQL restart and full backend regression; no API, frontend, Workspace/sync, Progress or new Workflow implementation |
| NIGHT-B2 | Workflow Catalog and Desired Project Manifest | **PASS — OWNER REVIEW REQUIRED** — additive migration `20260806_0009`, canonical Project/Manifest revision history, deterministic existing-Project backfill, repository-backed Catalog, multi-instance create/detail/list/retire APIs, PostgreSQL compare-and-swap revision safety, and an atomic Project-creation bridge; no Workspace files, sync/install, Progress aggregation, frontend or new Workflow execution |
| NIGHT-B3 | Workspace bootstrap and legacy Literature Search adoption | **PASS — OWNER REVIEW REQUIRED** — repository-backed bootstrap descriptor, promoted checksum-bound `project.json`, atomic minimal Workspace creation, safe directory/ZIP Package adoption into the frozen Capsule path, source/mutable-state preservation and standalone/adopted launcher compatibility; no database migration, sync, generic installation, Installed Lock, acknowledgement, frontend or new Workflow execution |
| NIGHT-B4 | Pull sync, Installed Lock and installation acknowledgement | **PASS — OWNER REVIEW REQUIRED** — additive migration `20260806_0010`, exact Workflow-Instance Capsule artifact binding, repository-driven sync plan/download/ack endpoints, explicit local `sync`, B3 registry migration, immutable-contract drift checks, atomic staging/publication, retained retired Capsules, OS write lock, checksummed Installed Lock, ACK_PENDING recovery and Manifest-race rejection; no Progress aggregation, frontend Workflow Board, Artifact handoff or new Workflow execution |
| R3D | Production/public Provider boundary | **PRODUCTION GATE CLOSED** — production auth, HTTPS, multi-user, secret management, paid use and retention remain unapproved |
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

ARCH-D1 ratifies the post-V0.1 design direction without implementation. The
future stable abstractions are Project, one logical Project Workspace,
Workflow Definition, project-owned Workflow Instance, and isolated versioned
Workflow Capsule. Cloud desired configuration is revisioned separately from a
local Installed Lock; pull-based sync stages and atomically installs only new
content. Existing Literature Search Packages, checksums, reports, projections,
sessions, and launch commands remain unchanged through V0.x compatibility.
Artifacts cross instances only by typed immutable reference and explicit
verified materialization. Initial Skills remain built-in/reviewed; external
Resources are metadata resolved with local credentials. Device tracking,
automatic cross-device sync/backup, general Artifact upload, imported Skill
execution, deep external connectors, and every new Workflow remain deferred.
NIGHT-B2 now adds the bounded cloud desired-state layer around the B1
foundation: repository-backed Workflow Catalog reads; project-scoped
Workflow Instance reads and atomic create/retire mutations; append-only full
Manifest snapshots; monotonic Project revisions; and PostgreSQL compare-and-
swap conflict rejection. Project creation establishes its canonical Project,
legacy-compatible Literature Search Instance, revision-1 Manifest and entry in
the existing transaction. At the B2 gate, all Workspace filesystem work and
later product expansion remained closed. The owner subsequently accepted B2
and authorized only the bounded B3 bootstrap/adoption slice recorded below.

NIGHT-B3 adds only the local identity/bootstrap compatibility layer around that
desired state. `GET /projects/{project_id}/workspace-bootstrap` exposes exact
Project/Workspace/Manifest/Instance/Capsule/legacy-Package bindings. The local
CLI atomically creates the minimal Workspace and can copy a verified existing
Literature Search Package without rewriting, moving, deleting or executing its
source. Package mutable state and the accepted `run .` behavior are preserved.
The Capsule registry records local adoption only and is explicitly not an
Installed Lock or sync acknowledgement. NIGHT-B4 now implements the explicit
pull path: a repository-derived sync plan binds each available Literature
Search instance to a unique artifact; the local CLI verifies/stages/publishes
missing Capsules, promotes a verified B3 registry entry into the canonical
Installed Lock without rewriting mutable state, and idempotently reports one
Manifest-aligned installation record. Retired Capsules remain local and a
stale acknowledgement never claims the newer revision. Progress aggregation,
Artifact handoff, new executable Workflows and frontend Workflow management
remain closed pending owner review.

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
real-provider and external-network use. R3B-I implements and SQL-qualifies that
profile in the separate `backend/cloud_api_proxy/` domain with feature flag
`REAGENT_EXPERIMENTAL_FAKE_PROXY_ENABLED` off by default and migration
`20260804_0004`. R3B-A accepted the external Package, real Uvicorn/loopback
HTTP, token lifecycle, SQL persistence/restart, idempotency, reconciliation and
Package immutability; `R3B_STATE = FAKE_PROXY_ACCEPTED`.

R3C-D retrieved and fingerprinted current official OpenAlex documentation,
Terms and Privacy sources without contacting the Provider API, audited the
existing Hosted adapter, and accepted ADR 0012. The only approved future live
operation is one keyed, single-page OpenAlex Works metadata search behind
`paper.search/v0.1`: unchanged query, at most 20 results, fixed fields, one
fixed HTTPS origin, zero automatic retry, maximum 20 calls and USD 0.05,
acceptance-lifetime normalized metadata only. R3C-I implemented that exact
adapter behind `backend/cloud_api_proxy/` with no key or Internet and with
feature flag `REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED` off by default.
Migration `20260805_0005` adds query-checksum/length evidence and integer
Provider call/microusd accounting without query text, key, raw body or Hosted
foreign keys. Scripted transport and a fresh isolated PostgreSQL 18.1 cluster
qualified request mapping, normalized metadata, safe errors, idempotency,
reconciliation and budget races with zero live Provider calls. R3C-A attempt 0
then stopped correctly at its owner-attestation prerequisite. Owner-authorized
retry 1 passed the owner/source/isolated-SQL/external-Package/composition gates
and made one live call. OpenAlex returned HTTP 200 and exact 1,000-microusd
cost/rate evidence, but the adapter settled `PROVIDER_INVALID_RESPONSE` without
an accepted normalized result. Retry 1 stopped fail-closed with no second call,
restart, regression run or production repair.

R3C-N1 then preserved the retry result and traced the response pipeline without
source changes or another call. It found no surviving field/path/type/validator
and no contract-approved synthetic shape that the adapter rejects, so root
cause remains `INSUFFICIENT_EVIDENCE`. R3C-N2-I records the owner's strict
complete-response decision in ADR 0013 and adds a default-disabled, log-only,
value-free structural diagnostic. Closed stage/path/kind/validator registries,
safe indices/counts and a canonical value-independent shape checksum now
distinguish per-Work normalization from service sensitive-content rejection.
The public API, SQL schema, operation/checksum identity, validation outcomes,
query/raw-body policy, Packages and Progress Reports remain unchanged.

R3C-N2-A then made one separately authorized call that succeeded with zero
records and no diagnostic, leaving evidence insufficient. Retry 2 stopped at
its owner-allowance gate before source/key/database/Provider use. Retry 3 passed
its owner/source/isolation/Package/composition gates and made exactly one call.
It returned HTTP 200 and exact 1,000-microusd cost; one Work normalized before
the next failed at `ABSTRACT_RECONSTRUCTION`, abstract inverted-index token
index `2`, with `CONTROL_CHARACTER / ABSTRACT_TOKEN_CONTROL`. Strict whole-
response failure retained no partial result or Provider value; replay and
conflict made no second call.

ADR 0014 now ratifies the minimal R3C-I2 compatibility rule: only TAB, LF, and
CR within abstract inverted-index tokens become ASCII SPACE, with adjacent
formatting-whitespace runs collapsed without concatenating words. Other
controls and every non-abstract field retain their existing rejection policy.
Fictional scripted tests, the unchanged Proxy/Package/Progress suites, a fresh
isolated PostgreSQL cluster at sole revision `20260805_0005`, and the full
backend regression qualify the correction offline. No Provider/documentation
call, key read, API/SQL schema change, retry, partial success, Hosted execution,
or Package mutation occurred. The exact retry-3 code point was not retained and
no real response has passed after remediation. `R3C_STATE` remains
`LIVE_ACCEPTANCE_PENDING`; a future live retry requires fresh owner
authorization, and R3D production/public deployment remains closed.

R3C-A-R4 subsequently made exactly one owner-authorized live call. It returned
HTTP 200, five normalized Works and exact 1,000-microusd cost; both status
routes, exact replay and changed-content conflict passed before restart. The
same PostgreSQL cluster and Uvicorn restarted successfully and SQL retained one
operation/call and exact cost, but the post-restart verification controller
raised a value-free `RuntimeError`. The phase stopped without a retry or source
repair, preserving the accepted normalization evidence.

R3C-R1 reproduced the recovery failure offline: status remained readable, but
exact POST replay older than five minutes returned
`CLIENT_TIMESTAMP_OUT_OF_RANGE` because freshness preceded durable
idempotency resolution. R3C-R2 accepts ADR 0015 and makes the minimum service
ordering correction. Strict structure/checksum, active-token and exact-scope
authorization remain mandatory; an existing matching checksum replays in any
status, changed content conflicts, and freshness still rejects stale/future new
admission. Focused, API/client, concurrent and PostgreSQL tests plus a physical
PostgreSQL/Uvicorn restart with fictional persisted success passed with one
unchanged operation/call, exact 1,000-microusd totals, no adapter reinvocation,
no diagnostic, no Package/Hosted mutation and zero external network/key/live
Provider use. No API, migration, checksum, retention, cost, normalization or
Provider contract changed.

The owner has now accepted R3C-R2 and ratified ADR 0016. R3C closes by
composite evidence: R3C-A-R4 supplies the immutable one-call live transport,
five-real-Work normalization, exact 1,000-microusd cost, privacy, pre-restart
idempotency, Package, and Hosted/runtime evidence; R3C-R1 supplies the
deterministic delayed-replay diagnosis; R3C-R2 supplies the corrected ordering,
real PostgreSQL/Uvicorn restart, both status routes, aged exact replay, stable
ledger, and complete regressions with zero additional live Provider use. No
single run on final HEAD exercised every gate, and R3C-A-R4 remains `BLOCKED`.
The owner accepts the conclusion compositionally because the changed service
ordering is before and independent from Provider transport and normalization.
No unresolved hard gate remains for the experimental R3C slice.

`R3C_STATE = LIVE_OPENALEX_ACCEPTED` and
`R3C_COMPLETE = PASS_WITH_WARNINGS`. This does not authorize public or
production deployment. OpenAlex is the only accepted Provider; production
authentication, multi-user authorization, HTTPS termination, proof of
possession, secret management, real-user third-party query disclosure, and
retention remain unresolved. R3D remains closed.

MVP-A0 then audited the first local product and correctly stopped on seven
integration gaps. MVP-I implements only those gaps. Accepted ADR 0017 adds an
independent `local_projects` Cloud Project State boundary at migration
`20260805_0006`, exposes project/list/detail and deterministic Package
generation/download APIs, aggregates the already accepted Progress Report
projection/history, and makes `/projects` the Next.js primary path. The old
Hosted pages remain labelled legacy/internal and absent from primary
navigation. `make dev`/`make stop` now provide a fail-closed loopback startup
sequence while leaving PostgreSQL under the owner's control.

The V0.1 implementation is qualified with real PostgreSQL, Uvicorn, Next.js,
browser-driven project/Package/report flow, physical restart continuity,
Package checksum/non-mutation evidence, and complete backend/frontend checks.
Project creation and Package generation produced no WorkflowRun, StepRun,
AgentRuntime, Hosted ProviderOperation, Provider/LLM call, server research
output, automatic resume, or automatic Progress Report. V0.1 remains
`OWNER_ACCEPTANCE_PENDING`; only the owner can accept it. R3D and public/
production deployment remain closed.

MVP-I1 corrects only persistent startup configuration. If the invoking process
does not already export `REAGENT_DATABASE_URL`, `make dev` safely parses the
file selected by `REAGENT_ENV_FILE` or the ignored repository-root `.env`.
Dotenv text is never sourced or evaluated, values are not logged, and malformed
input fails closed. Existing PostgreSQL-only, loopback-only and ProjectDB
rejection remains mandatory. The owner creates the database once; neither
startup nor shutdown creates, resets, deletes, starts, or stops PostgreSQL.

MVP-LS1 completes the first user-facing Literature Search round without moving
research execution into the cloud. Accepted ADR 0019 adds one Package command,
`python reagent_local.py run .`, that validates immutable identities, opens a
15-minute exact-Package loopback session, invokes Codex at fixed planning and
synthesis boundaries, issues two or three bounded provider-neutral searches,
writes four local output contracts, finalizes one native v0.2 Progress Report,
uploads it idempotently, verifies history/projection, revokes the session, and
stops after round 1.

Normal mode binds only to the accepted default-disabled OpenAlex adapter and
never falls back to fake results. Explicit demo mode binds only to the
deterministic fake adapter and requires fictional labels. A valid pending
report uses upload-only recovery with zero search allowance; a verified receipt
prevents repetition; partial outputs without a valid report fail closed without
overwrite. Token plaintext stays in launcher memory, is stripped from the Codex
environment and never enters the Package. Migration `20260806_0007` records
only local progress capability scope and permits zero-operation upload-only
tokens; it adds no concrete task state or Progress schema change.

The frontend is now task-oriented: project Start here/Quick Start, a dedicated
guide, action-first Package page, and a completed-result Progress view. Full
queries, candidates, selections, report and context remain local; cloud state
receives only the unchanged bounded report summary and artifact checksums.

Deterministic real-stack qualification used real PostgreSQL, Uvicorn, Next.js,
browser HTTP, an external Package, and fake Codex-equivalent stages, then
proved automatic upload, browser-visible completion, no repeat, and restart
continuity. The phase made zero live OpenAlex calls. Prior R3C evidence remains
authoritative for the adapter; a full real OpenAlex LS1 round requires separate
owner authorization. `LITERATURE_SEARCH_AUTONOMOUS_WORKFLOW =
READY_FOR_OWNER_ACCEPTANCE` and `V0_1_STATE = OWNER_ACCEPTANCE_PENDING`.
R3D and public/production deployment remain closed.

MVP-LS2 corrects the LS1 interaction model without changing its Provider,
output, upload, or cloud/local contracts. `python reagent_local.py run .` is now
interactive by default: the current terminal shows Codex output and accepts
owner input at search-plan, candidate-screening, and finalization checkpoints.
Search waits for a machine-recorded plan confirmation, and final artifacts wait
for explicit `finish`. A versioned round-control artifact binds plan, normalized
query results, outputs, context, report, and receipt; Codex exit alone cannot
signal success. The launcher retains tokens and transport in its parent process
and strips secrets from Codex.

`--auto` explicitly preserves the LS1 unattended path. `Ctrl+C` forwards the
signal, reaps Codex, revokes the session, preserves valid local work, and does
not upload. `--resume`, confirmed `--restart-round`, pending-upload recovery,
and verified-receipt no-repeat are explicit. Deterministic real-stack
interactive and auto demo qualification passed after physical PostgreSQL and
application restart. No live OpenAlex call or owner Demo artifact was used.
`MVP_LS2_INTERACTIVE_UX = READY_FOR_OWNER_ACCEPTANCE`,
`LITERATURE_SEARCH_AUTONOMOUS_WORKFLOW = READY_FOR_OWNER_ACCEPTANCE`, and
`V0_1_STATE = OWNER_ACCEPTANCE_PENDING`. Only the owner can accept V0.1.

MVP-LS2.1 corrects the post-round authorization lifetime without reusing the
failed owner Demo. Search tokens now carry no Progress capability and close
before report upload. After local output/context/round-control/report-chain
validation, a new two-minute session binds the exact round, report ID, and
report-content checksum, admits zero search operations/Provider budget, and
permits only upload plus scoped history/projection verification. Explicit
expiry or unknown response outcome may replace that upload session once;
revoked, unknown, malformed, scope/report/checksum, and unclassified failures
remain terminal. Exact response-loss replay retains one report and projection.
Real PostgreSQL/Uvicorn/Chromium qualification and physical restart passed with
zero live OpenAlex call. V0.1 remains owner-acceptance pending and R3D closed.

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
