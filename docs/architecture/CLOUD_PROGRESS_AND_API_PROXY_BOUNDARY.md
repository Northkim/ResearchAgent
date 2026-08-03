# Cloud Progress and API Proxy Boundary

Status: **Semantic boundary frozen; protocols remain experimental**

Date: 2026-08-03

Governing decision: ADR 0009

## Purpose

The teacher source assigns two important continuity services to the cloud:

- external provider credentials remain in the cloud while local execution uses
  the cloud to make calls (TMR-008, PDF page 1);
- each local round produces a Progress Report that the cloud collects into a
  unified project/workflow view and uses for continuity (TMR-007, TMR-016,
  TMR-018; PDF pages 1 and 3).

This document freezes those semantic responsibilities. It does not define or
implement endpoint paths, authentication, transport schemas, JSON/Markdown
formats, conflict algorithms, or frontend designs.

## Cloud API Proxy

### Intended path

```text
existing local Claude Code/Codex Agent Harness
  -> authenticated Cloud API Proxy request
  -> cloud policy and credential custody
  -> approved provider adapter
  -> normalized result or normalized failure
  -> local Agent Harness
  -> Local Task State update performed visibly by the Harness
```

The local folder may carry a proxy base URL, capability name, protocol version,
package/project identity, and non-secret caller configuration. It must not carry
the provider API key, authorization header, secret fragment, or reusable cloud
credential.

### Proxy-owned responsibilities

The Cloud API Proxy may own:

- authentication and authorization of the local caller;
- external provider credential custody and injection;
- provider endpoint and protocol translation;
- request-schema and size validation;
- approved provider/model/endpoint selection when already fixed by cloud
  project/package policy;
- request, token, monetary, concurrency, and runtime limits;
- rate-limit and bounded retry handling;
- `ProviderOperation` reservation, idempotency, attempt, usage, cost,
  settlement, and replay evidence;
- provider request identity and latency metadata;
- normalized response and failure envelopes;
- content-minimized, secret-safe diagnostics and audit history;
- explicit retention and attribution metadata.

The proxy may reject requests that exceed policy, lack authorization, request
an unapproved provider capability, or cannot be safely accounted.

### Responsibilities the proxy must not own

The proxy must not:

- decide the research question;
- silently expand or replace the local Harness's research method;
- choose sources on behalf of the Harness unless the request explicitly asks a
  narrowly defined provider operation under an approved Skill contract;
- execute the full research Workflow;
- advance local Workflow steps invisibly;
- maintain hidden server memory that replaces Local Task State;
- generate the final research report in teacher-aligned V1;
- write or mutate local outputs without an explicit Harness-visible response;
- treat a provider response as a completed research result without local
  Harness processing and file persistence.

### Current component reuse

| Current component | Reusable proxy role | Boundary correction required later |
|---|---|---|
| `PaperSearchProvider` and other provider ports | Normalized internal provider capability contracts | Expose through an authenticated local-Harness-facing use case rather than backend Workflow execution |
| `OpenAlexPaperSearchProvider` | OpenAlex transport/mapping behind the proxy | Remove research-method ownership from server Skill path; define approved request/response policy |
| `ProviderOperationService` and repository | Reservation, idempotency, limits, usage, settlement, replay, and failure audit | Associate operations with cloud project/package/caller identities rather than requiring hosted `WorkflowRun` execution |
| Provider budget evaluator | Fail-closed request/token/cost policy | Define proxy-specific budgets and owner approval; do not inherit hosted report budgets silently |
| Provider execution policy | Capability/mode guard | Define source-aligned proxy policies and caller scope |
| Artifact/checksum services | Optional normalized response or audit-evidence storage | Apply minimum-data and retention policy; never store keys or raw bodies by default |
| FastAPI/composition | Cloud transport and adapter composition boundary | Add new explicit proxy endpoints and server-only secret composition in R3, not R0 |

Current OpenAlex execution is a hosted research operation, not an implemented
proxy. Current ProviderOperation foreign keys and services do not by themselves
prove local-Harness proxy support.

### Proxy matters deliberately undecided

- endpoint paths and versioning;
- caller authentication and authorization;
- first capability/provider;
- generic versus capability-specific endpoints;
- request and normalized response schema;
- synchronous versus asynchronous response behavior;
- retry, rate, token, cost, and retention thresholds;
- result caching and replay exposure;
- region, tenancy, and credential rotation;
- whether a future LLM is ever exposed through the proxy.

These require R3 design and owner decisions. No proxy endpoint is implemented
in R0.

## Progress Report boundary

### Semantic round-trip

```text
local Harness executes one round
  -> writes local output/context updates
  -> writes a local Progress Report
  -> explicit upload to cloud
  -> cloud validates project/package/version/checksum identity
  -> cloud appends immutable report history
  -> cloud computes a project/workflow progress projection
  -> later package refresh, re-download, or local continuation
```

The folder's local report is part of Local Task State before upload. After a
successful upload, the immutable received record and derived cloud projection
are Cloud Project State. An upload must not silently rewrite newer unuploaded
local work.

### R2A contract realization

`progress-report/v0.2` now communicates:

- project and Workflow Package identity;
- Workflow type, identity, and version;
- Skill and template versions;
- execution round/session identity;
- status;
- completed work;
- current/incomplete work;
- next recommended action;
- output paths, identities, media types, and checksums as applicable;
- warnings, errors, and unresolved decisions;
- a context update or reference to the updated local context;
- Agent Harness identity and relevant compatibility version;
- creation and completion timestamps;
- report schema/version identity and checksum.

The exact v0.2 fields and non-cyclic hashing algorithm are frozen for this
experimental version in `PROGRESS_REPORT_V0_2_CONTRACT.md`. This remains an
engineering contract, not a claim that the teacher PDF specified field names.

### Cloud processing responsibilities

Cloud may:

- authenticate and associate the uploader;
- validate project/package/Workflow/Skill/template identities;
- validate size, structure, checksum, and allowed references;
- reject unknown or conflicting identity without destroying prior history;
- retain the received report immutably;
- associate explicitly uploaded outputs or artifact metadata;
- compute a human-readable project/workflow progress projection;
- expose history and current projection to the user;
- prepare information for a later refreshed package or continuation download.

Cloud must not present the report as proof of scientific correctness or silently
continue the research Workflow.

### Required distinctions

| Record | Meaning | Is it a Progress Report? |
|---|---|---|
| `ExecutionEvent` | Hosted AgentRuntime internal event such as step start or Skill result | No |
| server checkpoint | Hosted execution recovery snapshot/boundary | No |
| server memory revision | Hosted execution working-memory record | No |
| `.agent_read/progress/*` | Developer/agent repository-governance handoff | No; never product runtime memory |
| final research output | Deliverable produced by a Workflow | No; may be referenced by a Progress Report |
| local Harness-produced per-round report | Portable status/context/output handoff explicitly uploaded to cloud | Yes |

Existing hosted events/checkpoints must not be renamed or projected as if they
already satisfy TMR-007/TMR-016/TMR-018.

### Progress matters remaining deliberately undecided

- signing, caller identity, and trust model;
- context compression and package refresh algorithm;
- retention, deletion, and export policy;
- cross-machine concurrency behavior.

R2A selected explicit JSON upload, path/checksum artifact references,
append-only rejected-conflict retention, and no automatic merge for v0.2.
Authentication remains `SOURCE_UNDECIDED`; a supervised placeholder is not a
multi-user security decision.

R1 v0.1 remains historical. R2A owns the experimental v0.2 upload/projection
contract. Neither may claim the PDF finalized these details.

## Security invariants

- No provider key or authorization header enters the Workflow Package, Progress
  Report, prompt, output, log, diagnostic, or artifact.
- External content and Harness-provided fields are untrusted data.
- Proxy and upload requests are bounded and schema-validated.
- Raw provider responses are not retained by default.
- Audit metadata is content-minimized and secret-safe.
- Failed uploads or proxy calls do not mutate Local Task State invisibly.
- A partial or rejected Progress Report is never presented as accepted cloud
  progress.

## R2A implementation statement

R2A implements only the Progress Report side: explicit upload/read routes,
immutable originals, normalized records, chain/conflict validation, projection,
client and additive cloud metadata. It adds no proxy route, credential source,
provider configuration, research execution, context download, package merge,
or frontend run/resume behavior. R3 remains separately gated.
