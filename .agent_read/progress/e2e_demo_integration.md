# Phase 8B — Reproducible End-to-End Demo Integration

- Date: 2026-07-21
- Status: PASS_WITH_WARNINGS
- Canonical local Python environment: `reagent-dev`
- Frozen contract changed: no
- ADR added: no

## Outcome

Phase 8B connects the existing backend and frontend into one deterministic,
supervised research demonstration:

```text
Next.js browser UI
        |
        v
FastAPI application services
        |
        v
SyncExecutionDispatcher -> AgentRuntime
        |
        v
Workflow Engine + deterministic fake Skills
        |
        v
SQLAlchemy UnitOfWork -> PostgreSQL
```

The full real local path was executed successfully through system Chrome:
create run -> execute Search -> wait for approval -> approve -> execute Summary
-> complete -> inspect ordered timeline and output -> reload persisted state.

The warning is environmental: Docker is not installed on the validation host.
The Compose topology was implemented and its YAML/shell syntax checked, but the
resolved Compose model, image builds, clean Compose startup/health, volume reset,
and second Compose replay could not be executed.

## Frozen demo contract

The source of truth is `.agent_read/progress/e2e_demo_contract.md`.

- Identity: `guided-literature-review@1.0.0`
- Name: `Guided literature review`
- Canonical SHA-256: `2e58bc1702f0393230c7f0e76d64f4b35684b709abf0597352498d508f45457f`
- Input: required string `query`; deterministic default `persistent research agents`
- Steps: `search` -> `approve_sources` -> `summarize`
- Skills: `mock_paper_search@1.0.0` and `mock_summary@1.0.0`
- Approval policy: `project_reviewer`
- Approval reason: `Approval required for workflow step approve_sources`
- Expected output: `Mock summary: Mock Foundations of persistent research agents; Mock Advances in persistent research agents`

The semantic event order is Workflow Started; Search Step Started; Search Skill
Executed; Approval Requested; Summary Step Started; Summary Skill Executed;
Workflow Completed. Runtime checkpoint events remain visible between these
semantic boundaries. The verified completed stream contained 19 contiguous
events numbered 1 through 19.

## Seed design

The JSON fixture lives under `demo/workflows/` because it is a repository-level
demo asset consumed by local Conda, integration tests, and containers. The
publisher lives at `backend/demo/seed.py` because it validates backend Domain,
Workflow Engine, serialization, and Skill Registry contracts.

The frozen `WorkflowRepository` has no definition-only publication operation.
Changing that port solely for bootstrap would violate the phase constraints, so
the seed is an explicit administrative PostgreSQL adapter entrypoint. It:

1. reconstructs the Domain Workflow through existing serializers;
2. validates the DAG with `WorkflowValidator`;
3. registers and resolves the existing deterministic fake Skills;
4. verifies identity, version, and the frozen canonical hash;
5. inserts through the existing SQLAlchemy workflow-definition mapping in one
   database transaction;
6. returns unchanged for an identical row; and
7. fails closed if the immutable identity already has different content.

No router invokes the seed, no ORM model owns seed logic, no demo run is created,
and repeated invocations do not duplicate definitions. Two consecutive CLI
invocations after the PostgreSQL suite both returned the same hash and
`status: unchanged`.

## Startup architecture

`compose.yaml` defines:

1. PostgreSQL with the named `reagent_postgres_data` volume and health check;
2. a one-shot Alembic migration service gated on healthy PostgreSQL;
3. a one-shot idempotent seed service gated on successful migration;
4. FastAPI gated on successful seed, with a catalog-aware health check; and
5. standalone Next.js gated on healthy FastAPI.

The separate `integration-test` profile targets the isolated `reagent_test`
database created only when the PostgreSQL volume is first initialized. Test
reset requires both the isolated URL and `REAGENT_ALLOW_DATABASE_RESET=1`.

The backend container uses Micromamba to create `reagent-dev` directly from
`environment.yml`. There is no requirements.txt, pyproject dependency copy, or
other Python dependency authority. The frontend uses its npm lockfile and the
Next.js standalone production output. `.env.example` contains only documented
development placeholders.

The root Makefile is the only lifecycle interface. Commands are fail-fast and
cover configure, Compose validation, start/wait, seed, status, logs, reset,
stop, backend tests/compilation, frontend unit/lint/build, PostgreSQL integration,
and Playwright E2E.

## Database and HTTP integration behavior

`backend/integration/tests/test_http_postgresql_demo.py` performs the required
real adapter path:

1. downgrade an explicitly isolated database to Alembic base and upgrade head;
2. seed twice and assert one definition;
3. reconstruct FastAPI with the SQLAlchemy Unit of Work;
4. create and resume a run over HTTP;
5. assert `WAITING_FOR_APPROVAL` and query the pending ApprovalRequest;
6. approve over HTTP;
7. assert `COMPLETED`, exact output, and ordered event semantics;
8. dispose and recreate the application/engine; and
9. query and resume the completed run, asserting no duplicate events/execution.

The test cannot silently fall back to the InMemory adapter. Without both the
dedicated database URL and explicit reset opt-in, it skips instead of touching
an ambiguous database.

## Frontend and Playwright integration

The frontend no longer invents a workflow when the catalog is empty. The seed
is now the single demo-definition authority and empty/error states remain
honest. The catalog guards against duplicate create/execute submissions with a
synchronous ref, and the run ledger renders final output from the durable run.

`frontend/tests/e2e/demo.spec.ts` uses accessible headings, links, groups,
labels, buttons, regions, and list semantics. It performs no route interception
or response mocking. It asserts:

- seeded workflow visibility and default input;
- run-detail navigation and approval wait;
- pending approval visibility and decision submission;
- completion and exact deterministic summary;
- contiguous sequence numbers and required semantic event order;
- persisted completion/output after page reload; and
- no horizontal overflow at 390-pixel dashboard width.

Playwright retains trace, screenshot, and video on failure. The successful HTML
report also contains five attached screenshots: selected workflow catalog,
waiting run, pending approval, completed/reloaded run, and mobile dashboard.
Generated reports and failure artifacts are ignored by Git.

## Visual and functional QA

The five real Chrome screenshots were inspected. Verified qualities:

- desktop and mobile navigation remain usable;
- long run identities are truncated without overflow and remain linkable;
- pending, waiting, and completed badges are visually distinct;
- approval controls and decision note are legible and enabled only in the
  pending state;
- step ordering, event sequence labels, and completion output are visible;
- the full event stream is vertically long but correctly ordered;
- the completed output persists after reload; and
- the 390-pixel dashboard has no horizontal overflow.

Loading, empty, and error components remain present and unit/implementation
checked. No independent in-app browser instance was available, so those states
were not manually forced in a second interactive browser session. No broad
visual redesign was performed.

## Validation evidence

Executed from the repository root unless noted:

- `conda run --no-capture-output -n reagent-dev pytest -q backend`
  - passed: 67
  - skipped: 8 PostgreSQL-gated tests
- `conda run --no-capture-output -n reagent-dev python -m compileall -q backend`
  - passed
- full backend suite with both isolated PostgreSQL URLs and reset opt-in
  - passed: 75
  - skipped: 0
- two `conda run ... python -m backend.demo.seed` invocations
  - both passed with the frozen hash and `status: unchanged`
- `npm test` from `frontend/`
  - 4 files passed; 5 tests passed
- `npm run lint` from `frontend/`
  - passed with no ESLint errors
- `npm run build` from `frontend/`
  - passed; 4 product routes plus `_not-found` generated
- `npm run test:e2e` from `frontend/` against real local services
  - 1 test passed in 3.9 seconds after final screenshot additions
- local HTTP health
  - frontend `/` and backend `/workflows` returned successfully
- `compose.yaml` Ruby YAML parse and `sh -n demo/postgres/init-test-db.sh`
  - passed
- `make demo-config-check`
  - not executed successfully: `docker: No such file or directory`
- Compose build/start/health/reset/replay and Compose-hosted browser test
  - not executed because Docker/Compose is unavailable

The first final build attempt inside the filesystem sandbox was blocked when
Turbopack tried to bind an internal process port; the required production build
was rerun in the approved local context and passed. Similarly, the final E2E
screenshot rerun was performed only after the real services were confirmed
available and system Chrome was allowed to start.

## Files created

### Demo infrastructure

- `.env.example`
- `.dockerignore`
- `compose.yaml`
- `Makefile`
- `docker/backend.Dockerfile`
- `docker/frontend.Dockerfile`
- `demo/postgres/init-test-db.sh`
- `demo/workflows/guided_literature_review.v1.json`

### Backend and tests

- `backend/demo/__init__.py`
- `backend/demo/seed.py`
- `backend/demo/tests/__init__.py`
- `backend/demo/tests/test_demo_workflow.py`
- `backend/integration/tests/__init__.py`
- `backend/integration/tests/test_http_postgresql_demo.py`

### Frontend and tests

- `frontend/playwright.config.ts`
- `frontend/tests/e2e/demo.spec.ts`

### Documentation

- `DEMO.md`
- `.agent_read/progress/e2e_demo_contract.md`
- `.agent_read/progress/e2e_demo_integration.md`

## Files modified

- `frontend/api/hooks.ts`
- `frontend/app/globals.css`
- `frontend/components/run-status-panel.tsx`
- `frontend/components/workflow-catalog.tsx`
- `frontend/components/workflow-list.tsx`
- `frontend/next.config.ts`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/tests/run-status.test.tsx`
- `frontend/vitest.config.mts`
- `frontend/.gitignore`
- `frontend/README.md`
- `.agent_read/context.md`

`frontend/lib/demo-workflow.ts` was removed because a frontend-owned fallback
duplicated the new persisted catalog authority.

## Unresolved limitations and risks

- Docker-specific evidence is missing on this host; Compose readiness and reset
  repeatability require execution on a Docker-capable machine.
- Fixed prototype project/actor identities and absent authorization make the
  environment single-demo only.
- Runtime still executes inline through `SyncExecutionDispatcher`; there is no
  durable queue, worker claim/lease, retry clock, or cancellation signal.
- Approval expiry has no proactive scheduler.
- PostgreSQL repositories are synchronous in async HTTP routes.
- Fake Skills, polling, metadata-only artifacts, and absence of real citations
  are deliberate demo shortcuts.
- There is no TLS, production secret management, backup policy, metrics/tracing,
  resource limit, load test, cross-browser suite, or formal accessibility audit.
- The repository Git index contains only `LICENSE` and `README.md` in this
  workspace; all implementation/source paths, including `.agent_read`, appear
  untracked. `.agent_read` is not ignored and remains eligible to track, but no
  `git add` or commit was performed.

## Recommendation

ReAgent is ready for the supervised end-to-end product flow on the verified
local Conda/real-PostgreSQL/system-Chrome path. Overall Phase 8B remains
PASS_WITH_WARNINGS until the same lifecycle is executed from a clean Docker
volume and repeated after reset.

Next milestone: **remediation of demo integration**. Run the Compose validation,
clean startup, health inspection, integration suite, browser suite, volume reset,
and second startup on a Docker-capable machine. If all pass, proceed to the
first real research vertical slice without changing the frozen architecture.
