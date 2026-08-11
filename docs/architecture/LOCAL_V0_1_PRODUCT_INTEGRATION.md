# Local V0.1 Product Integration

## Product flow

```text
Next.js project UI
  -> FastAPI local-project metadata
  -> deterministic Literature Search Package + ZIP
  -> downloaded external folder (authoritative task state)
  -> one-command launcher obtains an exact short-lived local session
  -> interactive Codex plans, screens and synthesizes locally
  -> owner confirms plan, reviews candidates and explicitly finalizes
  -> bounded provider-neutral searches through the ReAgent Proxy
  -> four local outputs + one Progress Report
  -> search session closes
  -> fresh exact-report upload session
  -> automatic idempotent upload and receipt/projection verification
  -> immutable report history + Project Progress Projection
  -> Next.js progress UI
```

Project creation and Package generation are metadata/artifact operations. They
do not create a `WorkflowRun`, invoke `AgentRuntime` or
`ExecutionDispatcher`, contact a Provider or LLM, generate research output, or
resume local work.

## Persistence

Migration `20260805_0006` adds `local_projects`, an independent Cloud Project
State table. It stores the project identity, display name, owner-declared
fictional/public topic, the fixed Literature Search selection, timestamps, and
the current deterministic Package receipt. It has no Hosted Workflow foreign
key. Concrete task state remains in the downloaded folder.

The project API derives current progress and history from the existing
Progress Report repository and `ProjectProgressService`; it does not introduce
a second progress model. Package ZIPs are stored under an externally configured
artifact root, and their stored checksum is revalidated before download.

Migration `20260806_0007` adds only local-session capability JSON to the
existing Proxy token record and permits a zero-operation upload-only token. The
same JSON column now stores an optional exact round/report/content-checksum
binding while retaining backward-compatible list-form decoding. It
does not add task execution state, change Progress Report schemas, or link to a
Hosted Workflow. The token remains active, unexpired, unrevoked, and exactly
scoped to project, Package checksum, Workflow version/checksum, adapter, and
capability. Normal sessions use the accepted OpenAlex adapter; explicit demo
sessions use the fake adapter; neither has Progress capabilities. A separate
two-minute upload session uses a neutral local-progress capability, exact
report binding, and zero search operation/Provider budget.

## Frontend

The primary navigation contains Projects, New project, and Local guide. The
root redirects to `/projects`. Project detail is task-oriented: Start here,
current step, primary action, an eight-step interactive Quick Start, expected outputs, latest
summary, and links to dedicated Package, Progress, and project Guide pages.

Historical Hosted routes remain source-compatible but are absent from primary
navigation and display `Legacy Hosted Mode — not part of V0.1`. They are not a
path from project creation.

## Runtime

`make dev` and `make stop` manage only FastAPI and Next.js. PostgreSQL is a
manual loopback prerequisite so the scripts cannot stop or delete unrelated
database services. When no database URL is already exported, startup safely
parses `REAGENT_ENV_FILE` or the ignored repository-root `.env` without
executing it; exported configuration has precedence. Runtime files live outside
Git. Local-session endpoints mount only under explicit V0.1 local mode and
require literal loopback. The fake Proxy is enabled for explicit demonstration;
OpenAlex remains disabled unless the owner explicitly enables it and supplies
the key to the backend process. Capability plaintext is returned once to the
local launcher, kept in parent-process memory, stripped from the Codex
environment, and revoked after its phase. The launcher executes the installed
Codex CLI attached directly to the owner's current terminal; neither backend
nor frontend invokes Codex or an LLM.

The parent launcher, not Codex, owns the bearer token and Proxy transport. A
versioned `memory/round-control.json` binds the exact project, Package,
Workflow, round, confirmed plan, normalized query-result checksums, final
output/context/report-draft checksums, and receipt. Codex first records
`PLAN_CONFIRMED`; only then may the parent issue bounded Proxy calls. Codex
records `FINALIZED` only after the owner's explicit `finish`. Process exit is
never sufficient evidence of completion.

## One-round state machine

- no report and no partial work: launch interactive round 1;
- valid report but no receipt: upload-only idempotent recovery;
- verified receipt: report already uploaded, no second round;
- interrupted/partial outputs without a valid report: fail closed without
  overwrite; the Capsule requires explicit `--resume`, while the verified
  Workspace generic launcher selects that existing path when local
  round-control proves a resumable checkpoint. Direct Package recovery still
  requires explicit `--resume` or confirmed `--restart-round`.

Default and explicit `--auto` paths converge at the same artifact validation,
report-chain finalization, fresh upload-session issuance, receipt/projection
verification, and session-revocation boundary. Signals are forwarded to the child; bounded cleanup reaps
it, marks an interruption safely, revokes the session, and performs no upload.
For the Workspace product route, a nonzero attached Harness exit also records a
bounded interruption around the last Capsule-validator-approved state. The
Workspace list combines Cloud readiness with that local state and presents
Resume without uploading local research bytes.

The cloud receives a bounded summary through the unchanged Progress Report
v0.2 contract. Complete candidates, selections, query text, local context, and
full literature report remain in the Package.
