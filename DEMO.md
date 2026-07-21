# ReAgent reproducible demo

This guide runs the deterministic supervised research workflow through the real
Next.js UI, FastAPI application, Agent Runtime, SQL Unit of Work, and
PostgreSQL adapter. No LLM, external literature service, Redis, or worker queue
is used.

## 1. Prerequisites

- Git checkout of this repository.
- Conda with the `reagent-dev` environment created from `environment.yml`.
- Node.js and npm compatible with `frontend/package-lock.json`.
- A PostgreSQL database for the local workflow, or Docker with the Compose v2
  plugin for the container workflow.
- Google Chrome for the default Playwright project. A Playwright-managed
  browser can be used by installing Chromium and setting
  `REAGENT_PLAYWRIGHT_CHANNEL=chromium`.

Create or update the canonical Python environment without introducing another
local dependency source:

```bash
conda env create -f environment.yml
# If reagent-dev already exists:
conda env update -n reagent-dev -f environment.yml --prune
```

Install the locked frontend dependencies:

```bash
cd frontend
npm ci
cd ..
```

## 2. Local Conda workflow

Create a dedicated local PostgreSQL database and export its SQLAlchemy URL.
The example value below is a placeholder; use a local development credential:

```bash
export REAGENT_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/reagent'
```

Apply the schema and publish the immutable demo workflow:

```bash
conda run --no-capture-output -n reagent-dev alembic upgrade head
conda run --no-capture-output -n reagent-dev python -m backend.demo.seed
```

Start the backend from the repository root:

```bash
conda run --no-capture-output -n reagent-dev \
  uvicorn backend.api.app:app --host 127.0.0.1 --port 8000
```

In another terminal, start the frontend:

```bash
cd frontend
REAGENT_API_URL=http://127.0.0.1:8000 npm run dev
```

Open `http://127.0.0.1:3000`. Browser API requests remain same-origin under
`/backend/*`; the Next.js rewrite forwards them to `REAGENT_API_URL`.

## 3. Docker Compose workflow

Docker is an additional demo environment. The backend image creates the
`reagent-dev` Conda environment directly from `environment.yml`, so the image
does not maintain a second Python dependency manifest.

From the repository root:

```bash
make demo-configure
```

Review `.env` before startup. Its checked-in source, `.env.example`, contains
development-only placeholders and explicit internal service URLs. Do not use
the example password outside this local demo.

Validate and start the stack:

```bash
make demo-config-check
make demo-start
make demo-status
```

`demo-start` builds the images and waits for healthy services. PostgreSQL must
be healthy before the migration job runs; the seed job must complete before
FastAPI starts; the backend catalog health check must see
`guided-literature-review@1.0.0` before the frontend starts. Migration or seed
failure therefore prevents the serving stack from becoming ready.

The default endpoints are:

- frontend: `http://127.0.0.1:3000`
- backend: `http://127.0.0.1:8000`
- PostgreSQL: `127.0.0.1:5432`

## 4. Environment variables

| Variable | Purpose |
|---|---|
| `POSTGRES_USER` | Compose PostgreSQL role |
| `POSTGRES_PASSWORD` | Compose-only development password |
| `POSTGRES_DB` | Primary Compose database |
| `REAGENT_DATABASE_URL` | Backend, migration, and seed SQLAlchemy URL |
| `REAGENT_TEST_DATABASE_URL` | Isolated Compose integration-test URL |
| `REAGENT_API_URL` | Server-side Next.js rewrite destination |
| `REAGENT_POSTGRES_PORT` | Optional host PostgreSQL port override |
| `REAGENT_BACKEND_PORT` | Optional host FastAPI port override |
| `REAGENT_FRONTEND_PORT` | Optional host Next.js port override |
| `REAGENT_E2E_BASE_URL` | Optional Playwright frontend origin |
| `REAGENT_PLAYWRIGHT_CHANNEL` | Optional Playwright browser channel |

Do not expose the Compose-internal hostname `backend` to browser-side code.
Only the Next.js server uses `REAGENT_API_URL`; browser requests use the
same-origin rewrite.

## 5. Database migrations

Local migration commands must run through `reagent-dev`:

```bash
conda run --no-capture-output -n reagent-dev alembic upgrade head
conda run --no-capture-output -n reagent-dev alembic current
conda run --no-capture-output -n reagent-dev alembic check
```

Compose runs `alembic upgrade head` in the one-shot `migration` service on
every startup. Alembic is the schema authority; the application does not call
`create_all`.

## 6. Demo seeding

The fixture is `demo/workflows/guided_literature_review.v1.json`. Publish it
locally with:

```bash
conda run --no-capture-output -n reagent-dev python -m backend.demo.seed
```

Or publish it into the running Compose database with:

```bash
make demo-seed
```

Repeated runs return `status: unchanged`. The seed fails if the same immutable
identity exists with different content or if its canonical hash, version, DAG,
or pinned fake Skill references no longer match the frozen demo contract.

## 7. Full-stack lifecycle commands

The Makefile is the single repository-root command interface:

```bash
make demo-configure     # create .env once from the tracked template
make demo-config-check # validate the resolved Compose model
make demo-start         # build, migrate, seed, start, and wait for health
make demo-seed          # rerun the idempotent seed job
make demo-status        # show container and health state
make demo-logs          # follow the last 200 log lines per service
make demo-stop          # stop containers; preserve PostgreSQL volume
make demo-reset         # stop and delete the demo PostgreSQL volume
```

All targets are fail-fast and return the underlying non-zero exit status.

## 8. Manual walkthrough

1. Open `/workflows` and select **Guided literature review** version `1.0.0`.
2. Confirm the query `persistent research agents`, then choose **Create &
   execute run**.
3. On `/runs/{id}`, confirm Search is complete and the run is **Waiting for
   approval** at Approve Sources.
4. Follow **Review approval** to `/approvals`.
5. Optionally enter a decision note, then choose **Approve & continue**.
6. Return to the run ledger and confirm the run is **Completed** with all three
   steps complete.
7. Confirm the Research output is exactly:

   ```text
   Mock summary: Mock Foundations of persistent research agents; Mock Advances in persistent research agents
   ```

8. Confirm the ordered timeline includes workflow start, Search start and fake
   Skill execution, approval request, Summary start and fake Skill execution,
   and workflow completion. Checkpoint events appear between these semantic
   boundaries.
9. Reload the run page and confirm the same completed output and timeline remain.

Choosing **Reject & cancel** is the deterministic alternate path: the approval
is rejected and the run is cancelled instead of executing Summary.

## 9. Automated tests

Fast backend checks:

```bash
make test-backend
make compile-backend
```

Frontend checks:

```bash
make test-frontend
make lint-frontend
make build-frontend
```

The real PostgreSQL integration test uses the isolated `reagent_test` database
created by the Compose initialization script. It intentionally migrates and
resets only that database:

```bash
make test-integration
```

With the complete Compose stack healthy, run the real browser flow:

```bash
make test-e2e
```

The Playwright test does not mock HTTP. It retains traces, screenshots, and
video on failure and attaches screenshots of the workflow catalog, waiting run,
approval center, completed persisted run, and mobile dashboard to the HTML
report. Open `frontend/playwright-report/index.html` after a run.

To use an isolated local PostgreSQL database instead of Compose for the real
backend suite, explicitly opt into destructive reset of that database:

```bash
export REAGENT_TEST_DATABASE_URL="$REAGENT_DATABASE_URL"
export REAGENT_E2E_DATABASE_URL="$REAGENT_DATABASE_URL"
export REAGENT_ALLOW_DATABASE_RESET=1
conda run --no-capture-output -n reagent-dev python -m pytest -q backend
```

Never point those three variables at a shared or production database.

## 10. Reset and cleanup

Stop while preserving all demo runs:

```bash
make demo-stop
```

Delete the named PostgreSQL volume and replay from a clean database:

```bash
make demo-reset
make demo-start
```

The second command recreates the database, migrates it, and seeds exactly one
copy of the frozen workflow. Browser reports, traces, `.next`, and other build
artifacts are ignored by Git.

For a dedicated local test database only, a full schema reset is:

```bash
conda run --no-capture-output -n reagent-dev alembic downgrade base
conda run --no-capture-output -n reagent-dev alembic upgrade head
conda run --no-capture-output -n reagent-dev python -m backend.demo.seed
```

## 11. Troubleshooting

- `docker: command not found`: install Docker Desktop or another Docker Engine
  with the Compose v2 plugin; rerun `make demo-config-check` before startup.
- A port is occupied: edit `REAGENT_POSTGRES_PORT`,
  `REAGENT_BACKEND_PORT`, or `REAGENT_FRONTEND_PORT` in `.env`.
- The catalog is empty locally: run the migration, verify
  `REAGENT_DATABASE_URL`, and rerun `python -m backend.demo.seed` through Conda.
- Compose never becomes healthy: use `make demo-status` and `make demo-logs`.
  Migration and seed jobs are intentionally fail-closed.
- Playwright cannot launch Chrome: install Google Chrome, or run
  `npx playwright install chromium` in `frontend/` and set
  `REAGENT_PLAYWRIGHT_CHANNEL=chromium`.
- Playwright cannot reach the application: verify `/`, `/workflows`, and
  `/backend/workflows` return successfully on the configured frontend origin.
- A seed reports immutable-content conflict: do not overwrite the row. Reset a
  disposable demo database or publish a new workflow version and hash.

## 12. Known limitations

- The demo uses fixed prototype project and actor identities; there is no
  authentication, authorization, or approval-role enforcement.
- `SyncExecutionDispatcher` runs execution inline in HTTP requests; there is no
  durable queue, worker lease, clock scheduler, cancellation channel, or Redis.
- Approval expiry is enforced on a decision attempt, not by a background job.
- Research results and summaries are deterministic fake Skill outputs. There is
  no real LLM, literature provider, citation retrieval, or artifact byte store.
- Status updates use polling rather than server-sent events or WebSockets.
- The browser suite currently targets one Chrome-compatible desktop engine plus
  a mobile-width layout assertion; it is not a cross-browser accessibility or
  performance suite.
- Compose is a local demonstration topology, not production deployment
  configuration. Secrets management, TLS, backups, observability, resource
  limits, and high-availability behavior remain out of scope.
