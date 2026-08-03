# Teacher Design Realignment Plan

Audit date: 2026-08-03
Status: recommendation for owner review; no action is authorized

This plan does not introduce a new architecture. It restores the responsibility
split stated in the teacher PDF: cloud manages/supplies, a local workflow folder
holds task state, and an existing Agent Harness performs the work.

## Realignment principles

1. Teacher requirements TMR-003, TMR-004, TMR-009, and TMR-010 control the
   execution and state boundaries.
2. Existing code is preserved until the owner decides its long-term role.
3. Hosted technical quality does not make hosted task execution part of initial
   V1.
4. The PDF's sample folder tree guides an experiment; it is not silently frozen
   as a final schema (TMR-013, TMR-014).
5. No accepted ADR is edited or reinterpreted in this audit. Governance changes
   require explicit owner review and a subsequent decision record.

## 1. Immediate freeze

Pause further development of the following before owner review:

| Freeze item | Reason | Teacher IDs |
|---|---|---|
| Phase 9C-2B real hosted-LLM transport, composition, or execution | Would make cloud perform report research | TMR-004, TMR-010 |
| New server-side research Skills/providers and hosted workflow stages | Deepens responsibility inversion | TMR-003, TMR-004 |
| New browser actions that start/resume cloud research | Reinforces the wrong user journey | TMR-004, TMR-018 |
| New hosted AgentRuntime/worker/queue productionization | Source says use existing Harness | TMR-010 |
| Automated Judge/calibration/full-pool evaluation | Not source-defined initial core | TMR-005-TMR-008, TMR-018 |
| Expansion of hosted approval/event/artifact UX | Missing folder/progress core has higher source priority | TMR-006, TMR-007, TMR-018 |

“Freeze” means no further work, not deletion or runtime modification in this
audit.

## 2. Preserve

Keep the following untouched while realignment is reviewed:

- immutable workflow definitions and hashes as historical/test evidence
  (TMR-001);
- Domain, persistence, execution-event, approval, artifact, API, frontend, and
  test code (potential cloud-management reuse);
- Skill schemas/versioning and code registry (TMR-005 support);
- provider ports, OpenAlex adapter, ProviderOperation budget/accounting, and
  failure normalization (TMR-008 support);
- grounded-report contracts, prompts, provenance validators, synthetic fixtures,
  and acceptance evidence (potential local Literature Search package);
- PostgreSQL migrations and repositories for possible cloud metadata/report/
  proxy roles;
- Docker/Compose and existing tests for regression and optional hosted mode.

No removal is required to start source-aligned work.

## 3. Governance checkpoint

Before implementation, the owner should acknowledge:

1. The PDF supersedes the hosted product assumptions in the current derived
   plan for initial V1 (TMR-003, TMR-004, TMR-009, TMR-010).
2. ADR 0001's PostgreSQL task authority and project-owned AgentRuntime conflict
   with those requirements.
3. Current hosted execution is preserved but not the initial product path.
4. ADR 0007 remains limited synthetic evidence and ADR 0008 remains Proposed;
   neither authorizes the real hosted route.

A later governance task—not this audit—should decide whether to supersede ADR
0001 and update the development plan/context.

## 4. Recommended next milestone

### Experimental local workflow-folder package and Harness compatibility slice

This is the single recommended next milestone.

Goal: cloud-side code generates one synthetic, downloadable workflow folder;
Claude Code or Codex can open it and complete a bounded task using only folder
state, without `AgentRuntime` or PostgreSQL live execution; the Harness writes
an output and Progress Report that can be validated for later upload.

Direct support: TMR-002, TMR-006, TMR-010, TMR-013-TMR-018.

Owner decisions required before the slice:

- which one workflow to use; Literature Search is a reasonable repository reuse
  candidate but is not mandated by the PDF (TMR-011);
- Claude Code, Codex, or both as blocking Harnesses (TMR-010);
- initial experimental folder tree and prompt split (TMR-013, TMR-014);
- synthetic input/output and Progress Report acceptance fixture;
- archive format and download mechanism.

Minimum acceptance evidence:

1. Cloud package generation contains no provider credential.
2. Package records project/workflow/template/Skill versions and checksums.
3. The folder has harness-readable entry instructions, prompt/Skill material,
   memory/context, progress location, inputs, and outputs, with exact names
   explicitly marked experimental.
4. A fresh Harness session can determine the task and current state from files.
5. It writes the expected synthetic output and a Progress Report.
6. A second fresh session—or the other approved Harness—can continue from the
   folder without PostgreSQL or backend `AgentRuntime` execution.
7. No cloud endpoint performs the research task.

## 5. Reframe after the folder slice

### Cloud domain and PostgreSQL

Reframe toward cloud-owned project state rather than local task execution:

- project identity and workflow selection;
- template, prompt, Skill, and package versions;
- package/download history and checksums;
- uploaded Progress Report history and latest projection;
- external proxy policy, requests, usage, and cost;
- optional uploaded output metadata/snapshots.

Do not treat Step Runs, backend checkpoints, or DB memory as the only state from
which active local research can resume (TMR-009).

### Workflow definitions/engine

Reuse definition parsing, version pins, reference resolution, schema checks,
and handoff validation for package production (TMR-001, TMR-012). Keep the
server execution loop as an internal test tool or optional future mode, not the
default V1 workflow runner (TMR-004, TMR-010).

### Skill System

Evolve the model from an in-process implementation registry into AG Admin:

- persistent normalized Skill metadata;
- external source/import record;
- conversion/validation output;
- version/license/trust review;
- workflow compatibility and package contents;
- operator management UI/API.

The exact normalized format is an owner/teacher decision (TMR-005, TMR-013).

### API/frontend/artifacts

Reuse FastAPI, Next.js, PostgreSQL, and artifact storage for:

- project/workflow selection;
- AG Admin;
- package generation/download;
- Progress Report upload/history/aggregate progress;
- refreshed package download/continuation;
- proxy usage and policy views.

The hosted execution timeline can remain hidden/internal or later become an
optional-mode view. It is not a Progress Report history (TMR-007).

## 6. Build next after the folder slice

### Progress Report round-trip

Implement a versioned report contract and the flow:

```text
local Harness writes report
  -> authenticated upload/import
  -> project/workflow/version validation
  -> append-only history
  -> latest progress projection
  -> cloud project view
  -> refreshed folder/context for continuation
```

Decide conflict/merge semantics rather than treating server checkpoints as a
substitute (TMR-007, TMR-016, TMR-018).

### True cloud API proxy

Expose an authenticated, bounded endpoint used by a local Harness. The cloud
selects the approved provider, injects credentials, records ProviderOperation,
normalizes the response, and returns it. Reuse OpenAlex first only after owner
approval of endpoint, inputs, retention, attribution, limits, and output
contract (TMR-008).

### AG Admin and Skill packaging

Add operator workflows for importing/converting a synthetic external Skill,
reviewing normalized metadata/content, versioning it, and including it in the
folder package (TMR-005, TMR-006).

### Workflow composition

Represent all five teacher workflow types and define a versioned output/input
handoff. Do not require all five to be fully implemented until the owner chooses
priority (TMR-011, TMR-012, TMR-017).

## 7. Defer

Until the source-defined vertical slice and owner decisions pass, defer:

- Phase 9C-2B hosted real-LLM activation;
- hosted report generation from real abstracts;
- live hosted AgentRuntime as the default product mode;
- queue/worker scaling for hosted research execution;
- automated Judge, calibration, full-pool evaluation, and multilingual Judge;
- production hosted approval/execution monitoring expansion;
- full text/PDF and downstream Idea/Writing execution;
- deletion or broad refactoring of existing hosted code.

## 8. Phase 9C reuse path

- Package grounded prompts, schemas, abstract-only rules, and citation policy as
  local Literature Search Skill files.
- Run provenance checks as deterministic folder tooling and optionally repeat
  them cloud-side when outputs are uploaded.
- Reuse ProviderOperation only if the local Harness calls a cloud proxy.
- Preserve the inactive Anthropic mapper and cost/retention evidence for a later
  owner decision; do not read/configure a key now.
- Keep V3 hosted execution and synthetic tests as optional/internal evidence,
  not proof of teacher-design completion.

## 9. Stop conditions for future work

Stop and request owner review if a proposed milestone:

- makes FastAPI/AgentRuntime execute a research step in initial V1;
- makes PostgreSQL the only state needed to resume local work;
- puts a provider key in the downloaded folder;
- treats events/checkpoints as Progress Reports without a file round-trip;
- freezes the illustrative PDF folder tree without explicit experimentation;
- claims all five workflows must be production-complete despite the source's
  silence on priority;
- deletes current hosted infrastructure before the owner chooses its optional
  future role.
