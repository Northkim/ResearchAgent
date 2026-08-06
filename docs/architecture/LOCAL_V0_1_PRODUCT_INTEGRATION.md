# Local V0.1 Product Integration

## Product flow

```text
Next.js project UI
  -> FastAPI local-project metadata
  -> deterministic Literature Search Package + ZIP
  -> downloaded external folder (authoritative task state)
  -> one-command launcher obtains an exact short-lived local session
  -> Codex plans, screens and synthesizes locally
  -> bounded provider-neutral searches through the ReAgent Proxy
  -> four local outputs + one Progress Report
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

Migration `20260806_0007` adds only the local-session capability tuple to the
existing Proxy token record and permits a zero-operation upload-only token. It
does not add task execution state, change Progress Report schemas, or link to a
Hosted Workflow. The token remains active, unexpired, unrevoked, and exactly
scoped to project, Package checksum, Workflow version/checksum, adapter, and
capability. Normal sessions use the accepted OpenAlex adapter; explicit demo
sessions use the fake adapter; upload-only sessions cannot submit Proxy
operations.

## Frontend

The primary navigation contains Projects, New project, and Local guide. The
root redirects to `/projects`. Project detail is task-oriented: Start here,
current step, primary action, four-step Quick Start, expected outputs, latest
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
local launcher, kept in process memory, stripped from the Codex environment,
and revoked after the round. Neither backend nor frontend invokes Codex or an
LLM.

## One-round state machine

- no report and no partial work: plan and execute round 1;
- valid report but no receipt: upload-only idempotent recovery;
- verified receipt: report already uploaded, no second round;
- partial outputs without a valid report: fail closed without overwrite.

The cloud receives a bounded summary through the unchanged Progress Report
v0.2 contract. Complete candidates, selections, query text, local context, and
full literature report remain in the Package.
