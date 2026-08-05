# MVP-A0 Local V0.1 Product Readiness Audit

Date: 2026-08-05

Status: **BLOCKED**

## Baseline and boundary

MVP-A0 began from clean `main` at exact commit
`fe4e68d82a393e9742a54d58e1a0836777aa30f8`. It was acceptance-only: no
production/frontend source, test, migration, fixture, Package template,
contract, ADR, or Progress Report schema changed. No real Provider, key,
`.env`, Hosted execution, LLM, Judge, or automatic upload path was used.

## Outcome

Fresh PostgreSQL 18.1, committed FastAPI, and committed Next.js all started on
loopback. Migration `20260805_0005` was sole/current with no drift. The frontend
root served before and after restart.

The product acceptance is blocked because the frontend remains the preserved
Hosted research-operations prototype. Its primary action starts a research run,
its Workflow form creates and resumes a Hosted run, and its visible navigation
contains Overview, Workflows, and Approvals. There is no project list/create
API or UI, no Package generation/download UI, and no uploaded Progress Report
history or projection UI. `/projects` and `/progress` returned 404. The root
README supplies no setup and the available startup documentation is Hosted or
partial rather than a complete V0.1 local sequence.

Independent component qualification passed without being used to claim the
missing frontend flow. A fictional external Package and ZIP validated. One
native v0.2 report validated, uploaded through the explicit loopback client,
retained byte-identically, and produced one SQL projection. One fake Proxy
operation returned two normalized synthetic records; exact replay and both
status reads agreed, with zero external Provider HTTP call and zero cost. The
28-file Package pre/post manifests were byte-identical.

After physical frontend, backend, and PostgreSQL restart, backend report
history, projection, original bytes, and row counts were unchanged. The
frontend again served `/`, but still returned 404 for `/projects`. Hosted
Workflow/runtime/event/ProviderOperation counts remained zero because the
Hosted UI actions were not invoked. The visible Hosted-first product boundary
nevertheless fails V0.1 acceptance.

## Verification

- Workflow Package tests: 43 passed;
- Progress Report tests: 38 passed;
- Cloud API Proxy tests: 231 passed;
- required isolated PostgreSQL tests: 32 passed, zero skipped;
- full backend: 545 passed, 4 separately gated integrations skipped;
- compileall: passed;
- Alembic: `20260805_0005`, no drift;
- frontend unit tests: 4 files / 5 tests passed;
- frontend ESLint: passed;
- frontend production build: passed;
- standalone frontend typecheck: failed with 23 missing-Vitest-global
  diagnostics in four test files;
- Hosted Playwright specifications: not run because they invoke the prohibited
  Hosted product path.

The four backend skips were the separately gated destructive Hosted demo,
Hosted research-v2, isolated OpenAlex contract, and live OpenAlex integration
suites. All required PostgreSQL tests ran without skip.

## State

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

Detailed evidence is in
`docs/acceptance/V0_1_LOCAL_MVP_READINESS_AUDIT.md`. The owner checklist is
`docs/acceptance/V0_1_OWNER_MANUAL_ACCEPTANCE_CHECKLIST.md`. No gap was repaired.
