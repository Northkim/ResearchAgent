# V0.1 Local MVP Readiness Audit

Date: 2026-08-05

Status: **BLOCKED — NOT READY FOR OWNER ACCEPTANCE**

Baseline: `fe4e68d82a393e9742a54d58e1a0836777aa30f8`
(`R3C-C: ratify composite live OpenAlex acceptance`) on clean `main`.

This was an acceptance-only audit. It changed no production or frontend source,
test, migration, fixture, Package template, contract, ADR, or Progress Report
schema. It made no live Provider call, read no real Provider key or `.env`, and
did not invoke Hosted execution, an LLM, a Judge, or automatic Progress Report
generation.

## 1. Frozen V0.1 scope

The audited target was a localhost-only, single-user Literature Search product
using Codex as the supported local Harness, OpenAlex as the sole previously
accepted live Provider, explicit Progress Report upload, local PostgreSQL, and a
minimal Next.js/FastAPI experience. Public deployment, production security,
multi-user operation, additional Providers or Workflows, automatic upload, and
Hosted/cloud research execution remain out of scope. Claude Code remains
Experimental / Untested.

The teacher-aligned boundary remains authoritative: the cloud manages projects,
Package supply, uploaded progress, and bounded Proxy capabilities; the external
local Package is authoritative for concrete research state; Codex performs the
research work; the cloud does not execute or resume it.

## 2. Current product inventory

| Required V0.1 function | Classification | Evidence |
|---|---|---|
| FastAPI backend entrypoint | COMPLETE_AND_CONNECTED | The committed ASGI app started on loopback and served health, Progress Report, and fake Proxy routes. |
| Next.js frontend entrypoint | PRESENT_BUT_HOSTED_MODE_ALIGNED | It started successfully, but its title, navigation, dashboard, and calls to action describe research runs, approvals, and the Phase 7B Hosted prototype. |
| Project list/create API | MISSING | The OpenAPI surface has no project collection/create endpoint; a frontend `/projects` request returned 404. |
| Project list/create frontend | MISSING | No project route, component, client method, or project model exists. |
| Literature Search selection | PRESENT_BUT_HOSTED_MODE_ALIGNED | `/workflows` selects a server Workflow definition and then creates and resumes a Hosted run. |
| Workflow Package generation | IMPLEMENTED_BACKEND_ONLY | The deterministic `backend.workflow_packages` CLI generated a valid external Literature Search Package. |
| Package ZIP download | IMPLEMENTED_BACKEND_ONLY | The CLI emitted a deterministic ZIP, but there is no Package API or frontend download action. |
| Package ID/checksum display | IMPLEMENTED_BACKEND_ONLY | CLI JSON exposes metadata; the frontend has no Package view. |
| Explicit Progress Report upload | COMPLETE_AND_CONNECTED | The committed local client validated and uploaded one fictional native report through real loopback FastAPI into PostgreSQL. |
| Progress Report history | IMPLEMENTED_BACKEND_ONLY | The backend history route returned the accepted record; no frontend consumer exists. |
| Project Progress Projection | IMPLEMENTED_BACKEND_ONLY | The backend projection returned round 1, `COMPLETED`, and `VALID_CHAIN`; no frontend consumer exists. |
| Proxy operation | COMPLETE_AND_CONNECTED | Operator CLI, provider-neutral client, fake adapter, API, and SQL persistence passed. |
| Proxy operation display | OUT_OF_SCOPE_FOR_V0_1 | A minimal display is optional; the existing frontend display is for Hosted `ProviderOperation`, not local Proxy operations. |
| Local startup scripts | PRESENT_BUT_HOSTED_MODE_ALIGNED | Make targets and Compose/Demo procedures launch or seed the preserved Hosted prototype. |
| Database migrations | COMPLETE_AND_CONNECTED | Fresh PostgreSQL upgraded to sole/current `20260805_0005`; Alembic detected no drift. |
| Sample configuration | PRESENT_BUT_HOSTED_MODE_ALIGNED | Examples primarily describe the Hosted demo; the frontend example only supplies the API rewrite target. |
| README/demo onboarding | PARTIALLY_CONNECTED | The root README contains no setup. `DEMO.md` and the frontend README provide Hosted or partial startup instructions, not one V0.1 local product sequence. |
| Local execution instructions | IMPLEMENTED_BACKEND_ONLY | The generated Package tells Codex to validate, work only in declared local state, finalize a Progress Report, and upload explicitly. The frontend does not surface these instructions. |

## 3. Isolated runtime evidence

A fresh loopback-only PostgreSQL 18.1 cluster used separate acceptance and test
databases. ProjectDB was not used. Both databases upgraded to
`20260805_0005`; `alembic current` and `alembic check` passed before and after
the physical database restart.

The committed FastAPI app and Next.js development server both started on
literal loopback addresses. Backend `/health` returned 200. Frontend `/`
returned 200 before and after restart. The available frontend routes were `/`,
`/workflows`, `/approvals`, and `/runs/[id]`; `/projects` and `/progress`
returned 404.

Direct interactive browser control was unavailable in the audit environment.
No API or database substitution was used to claim frontend acceptance. Runtime
HTML, route status, committed frontend source, client methods, and production
build route output independently established that the required project,
Package, and Progress surfaces do not exist.

## 4. Startup acceptance

`LOCAL_STARTUP_READINESS = FAIL`.

There is no one-command or short-sequence V0.1 startup procedure covering
environment setup, PostgreSQL, migration, backend, frontend, local URLs,
shutdown, and cleanup. The root README has no instructions. The comprehensive
demo procedure is explicitly the preserved Hosted prototype, and its primary
targets seed Hosted Workflow definitions and execution state. The frontend
README assumes an already configured backend and database.

The audit proved that the individual services can be started manually, but
that is diagnostic evidence rather than a supported new-developer V0.1 startup
experience.

## 5. Project, Package, and Progress flows

### Project creation and Package download

The required frontend flow stopped at its first step. There is no project list
or create surface. The visible dashboard instead offers `Start a research run`,
and the Workflow catalog describes launching through the backend execution
boundary. Its submit path creates and immediately resumes a Hosted run.

No direct API or SQL setup was used to claim frontend success. Consequently,
project creation and Package download fail product acceptance.

For component diagnosis only, the committed compiler generated an external
fictional Literature Search Package and ZIP. The folder, ZIP, bundled validator,
and repository validator passed. The Package contained Codex instructions,
explicit Progress Report steps, no credential or database URL, no private
repository path, and no Hosted Runtime dependency. This component result does
not substitute for the missing frontend generation/download flow.

### Progress Report upload and projection

The external Package helper created one fictional native v0.2 report. Offline
Package/report validation passed. The committed explicit client uploaded it via
real loopback HTTP. PostgreSQL retained one immutable report and one projection;
the downloaded original was byte-identical. History and projection reads
succeeded, and the projection exposed execution round, status, completed work,
current state, next action, outputs, and warning/error counts.

The frontend has no Progress Report client method, history view, project
projection view, or corresponding route. `/progress` returned 404. Therefore
backend upload passes, while Progress UI acceptance fails.

## 6. Deterministic fake Proxy flow

The operator issued one short-lived Package-bound fake-adapter capability to a
protected external file. The provider-neutral client submitted one fictional
request and received two normalized synthetic records. Exact replay returned
the same operation, both status read paths agreed, and request/response
checksums were stable. SQL held one Proxy operation. Fake-adapter Provider HTTP
calls and reserved/reported microusd were all zero.

The token plaintext stayed outside Git and the Package. The token was revoked
before cleanup. No live Provider or external network operation occurred.

## 7. Restart, Package, and Hosted boundary

The frontend, backend, and PostgreSQL cluster were physically stopped. The same
PostgreSQL data directory, artifact root, FastAPI app, and frontend were then
restarted. Backend history, projection, and original report bytes were exactly
unchanged; report/projection/Proxy row counts remained one. The frontend again
served `/`, while `/projects` remained 404.

The external Package had 28 files in its recursive pre/post content manifest.
The manifests were byte-identical. Cloud interaction did not mutate the
Package.

Hosted/runtime SQL counts remained zero for Workflow runs, step runs, agent
sessions, execution events, checkpoints, memory revisions, and Hosted Provider
operations. Nevertheless, the visible frontend still presents Hosted run
creation/resume as the primary product. That presentation violates the V0.1
product-boundary requirement even though the audit did not click it and no
Hosted row was created.

## 8. Verification matrix

Backend:

- Workflow Packages: 43 passed;
- Progress Reports: 38 passed;
- Cloud API Proxy: 231 passed;
- required PostgreSQL files: 32 passed, zero skipped;
- full backend: 545 passed, 4 skipped;
- compileall: passed;
- Alembic heads/current/check: `20260805_0005`, no drift.

The four full-backend skips were separately gated suites: destructive Hosted
demo integration, isolated Hosted research-v2 integration, offline OpenAlex
contract integration requiring a separate dedicated fixture, and live OpenAlex
integration. Running the Hosted suites or live Provider suite was prohibited in
this phase. All required Progress/Proxy/OpenAlex PostgreSQL tests executed with
zero skip.

Frontend:

- Vitest: 4 files, 5 tests passed;
- ESLint: passed;
- production build: passed;
- production route output confirmed only `/`, `/approvals`, `/runs/[id]`, and
  `/workflows`;
- standalone `tsc --noEmit`: failed with 23 diagnostics across four test files
  because Vitest globals (`test`, `vi`, and `expect`) are absent from the
  TypeScript configuration;
- Playwright: not run because both existing specifications execute the
  preserved Hosted demo/research path, which this phase expressly prohibited.

The successful production build does not override the required standalone
typecheck failure or the missing V0.1 pages.

## 9. Blocking gaps, in priority order

1. The primary frontend is the prohibited Hosted workflow-run product rather
   than the teacher-aligned local Package/Progress product.
2. Project list and project creation are absent from both API and frontend.
3. Workflow Package generation, metadata display, and ZIP download are absent
   from the frontend and public local API.
4. Uploaded Progress Report history and Project Progress Projection are absent
   from the frontend.
5. No supported end-to-end V0.1 local startup procedure exists.
6. Required standalone frontend typechecking fails.
7. Existing frontend end-to-end tests cover Hosted execution, not the local
   V0.1 owner flow.

No gap was repaired in this phase.

## 10. Acceptance states

```text
MVP_A0_ACCEPTANCE = BLOCKED
LOCAL_STARTUP_READINESS = FAIL
FRONTEND_RUNTIME_ACCEPTANCE = PASS
PROJECT_CREATION_ACCEPTANCE = FAIL
PACKAGE_DOWNLOAD_ACCEPTANCE = FAIL
EXTERNAL_PACKAGE_ACCEPTANCE = FAIL
PROGRESS_UPLOAD_ACCEPTANCE = PASS
PROGRESS_UI_ACCEPTANCE = FAIL
FAKE_PROXY_PRODUCT_ACCEPTANCE = PASS
RESTART_CONTINUITY_ACCEPTANCE = FAIL
PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
MVP_RUNTIME_HOSTED_BOUNDARY = FAIL
BACKEND_TEST_ACCEPTANCE = PASS
FRONTEND_TEST_ACCEPTANCE = FAIL
MVP_GIT_CLOSURE = PASS
V0_1_STATE = NOT_READY
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

The independently generated Package validated, but
`EXTERNAL_PACKAGE_ACCEPTANCE` is `FAIL` because no Package was generated and
downloaded through the required frontend flow. Restart continuity is likewise
`FAIL` because the required project, Package metadata, report history, and
progress cannot be observed through the frontend, despite exact backend data
continuity.
