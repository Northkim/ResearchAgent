# MVP-I Local V0.1 Product Integration

Date: 2026-08-05

Status: **PASS_WITH_WARNINGS — OWNER ACCEPTANCE PENDING**

## Baseline and scope

MVP-I began from clean `main` at exact commit
`97c8df4ca6c4d13c1c737721af12303b5a1e9e29`
(`MVP-A0: record local V0.1 readiness gaps`). It implemented only the seven
MVP-A0 integration gaps. It did not enable production deployment, R3D,
additional Providers/Workflows, public authentication, Hosted/cloud research
execution, an LLM, automatic Progress upload, or a live Provider call.

## Product implementation

Accepted ADR 0017 records the independent local project boundary. Additive
migration `20260805_0006` introduces `local_projects` for name,
fictional/public topic, the fixed Literature Search selection, timestamps, and
the current Package receipt. It has no Hosted execution foreign key.

FastAPI now provides project create/list/get and deterministic Package
generate/latest/download routes. Project responses aggregate the accepted
Progress Report projection and history rather than introducing a second model.
Package ZIP integrity is rechecked at download. Project creation and Package
generation have no Provider or execution side effect.

Next.js now redirects `/` to `/projects`. Primary routes cover project list,
creation, detail, Package generation/checksum/download, Progress projection and
report history, and local instructions. Hosted routes remain preserved but are
absent from primary navigation and display
`Legacy Hosted Mode — not part of V0.1`.

`make dev` and `make stop` provide the supported application lifecycle. Startup
requires a loopback PostgreSQL URL, verifies Conda/dependencies, rejects
ProjectDB, applies migrations, binds FastAPI/Next.js to literal loopback,
waits for readiness, and keeps logs/PIDs/Package artifacts outside Git. Stop
terminates only the application process trees it started and never stops or
deletes PostgreSQL. Scripts do not read `.env` and explicitly disable OpenAlex
and experimental Proxy routes.

## Real-stack qualification

A fresh PostgreSQL 18.x data directory used a unique loopback port and separate
`reagent_mvpi_local` and `reagent_mvpi_tests` databases. Both upgraded to sole
head `20260805_0006`; `alembic current` and `alembic check` passed. A downgrade
to `20260805_0005` followed by re-upgrade to `20260805_0006` passed.

The supported startup command brought up real Uvicorn and Next.js. A real
Playwright browser drove the V0.1 flow through the frontend and loopback APIs:
project creation, deterministic Package generation, ZIP download and manifest
inspection, construction/explicit upload of one fictional native v0.2 Progress
Report, and projection/history display. No API responses were mocked.

Before physical restart, SQL held one local project, one Progress Report, and
one projection, with zero WorkflowRun and zero Hosted ProviderOperation rows.
FastAPI and Next.js stopped; the same PostgreSQL data directory stopped and
restarted; the migration remained current; and new FastAPI/Next.js generations
became ready. The project response, Package tree manifest, Package metadata,
Progress history/projection, row counts, and browser-visible Progress page were
unchanged after restart. The downloaded Package pre/post recursive manifests
were identical.

## Verification

- focused local project/API/Package tests: 19 passed;
- Workflow Package tests: 44 passed;
- Progress Report tests: 38 passed;
- Cloud API Proxy tests: 231 passed;
- required selected PostgreSQL files: 33 passed, zero skipped;
- full backend: 556 passed, 4 separately gated integrations skipped;
- compileall: passed;
- Alembic heads/current/check and downgrade/re-upgrade: passed at
  `20260805_0006`, no drift;
- frontend TypeScript: passed;
- frontend Vitest: 8 files / 11 tests passed;
- frontend ESLint: passed;
- frontend production build: passed with nine application routes;
- teacher-aligned Playwright E2E: 1 passed through real HTTP/PostgreSQL;
- startup, shutdown, port release, and physical continuity: passed.

The four full-backend skips were the pre-existing separately gated destructive
Hosted demo, Hosted research-v2, isolated OpenAlex contract, and live OpenAlex
integration suites. All required local-project, Progress, Proxy, and OpenAlex
PostgreSQL tests executed with zero relevant skip. The production build needed
permission to bind Turbopack's local helper socket in the execution sandbox;
the identical build then passed.

## Product-boundary evidence

V0.1 primary actions caused zero AgentRuntime, ExecutionDispatcher,
WorkflowRun, StepRun, Hosted ProviderOperation, Provider/LLM/structured
generation, research output generation, automatic Workflow resume, Package
mutation, and automatic Progress Report generation/upload. No OpenAlex key,
`.env`, live Provider, or external documentation was read or contacted.

```text
MVP_I_IMPLEMENTATION = PASS_WITH_WARNINGS
LOCAL_PROJECT_IMPLEMENTATION = PASS
PROJECT_API_IMPLEMENTATION = PASS
PACKAGE_PRODUCT_FLOW_IMPLEMENTATION = PASS
PROGRESS_PRODUCT_FLOW_IMPLEMENTATION = PASS
TEACHER_ALIGNED_FRONTEND = PASS
LOCAL_STARTUP_IMPLEMENTATION = PASS
FRONTEND_TYPECHECK = PASS
FRONTEND_TESTS = PASS
BACKEND_TESTS = PASS
POSTGRESQL_QUALIFICATION = PASS
MVP_RUNTIME_HOSTED_BOUNDARY = PASS
V0_1_STATE = OWNER_ACCEPTANCE_PENDING
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

Allowed warnings remain: Claude Code is untested; OpenAlex is experimental and
disabled by default; Progress upload is explicit/manual; only Literature Search
exists; V0.1 is local/single-user; public deployment is unsupported. Wait for
owner review; do not claim V0.1 owner acceptance or begin R3D.
