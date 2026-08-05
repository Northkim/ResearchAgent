# Local V0.1 Product Integration

## Product flow

```text
Next.js project UI
  -> FastAPI local-project metadata
  -> deterministic Literature Search Package + ZIP
  -> downloaded external folder (authoritative task state)
  -> Codex performs local work and finalizes a Progress Report
  -> explicit Progress Report client upload
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

## Frontend

The primary navigation contains Projects, New project, and Local guide. The
root redirects to `/projects`. Project detail links to dedicated Package and
Progress pages and explains the Codex/local-folder boundary.

Historical Hosted routes remain source-compatible but are absent from primary
navigation and display `Legacy Hosted Mode — not part of V0.1`. They are not a
path from project creation.

## Runtime

`make dev` and `make stop` manage only FastAPI and Next.js. PostgreSQL is a
manual loopback prerequisite so the scripts cannot stop or delete unrelated
database services. Runtime files live outside Git. OpenAlex and fake Proxy
routes are explicitly disabled by the startup script; an operator must enable
a bounded capability separately.
