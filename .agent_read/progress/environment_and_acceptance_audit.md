# Environment, Dependency, Storage, and Acceptance Audit

- Date: 2026-07-21
- Scope: post-Phase-8B audit only
- Verdict: `PASS_WITH_WARNINGS`
- Repository root: `/Volumes/tb/个人资料/暑研/UCInspire26/MetaResearchAgent/ResearchAgent`
- Mutating cleanup performed: none

## Executive summary

The tracked source tree is healthy and the current Conda/backend and
Node/frontend installations pass every validation that does not require a
database reset. The repository has 892 GiB free and occupies 665 MiB, almost
entirely due to the project-local `frontend/node_modules` and `.next` output.

The audit has three warnings:

1. The current npm installation tree is usable but not pristine:
   `npm ls --all` reports five optional WASM packages as extraneous and a
   hoisted `fsevents@2.3.3` that does not satisfy Playwright's nested `2.3.2`
   request. Unit tests, lint, and the production build still pass.
2. The Conda environment contains an orphaned explicit `httpx` install from an
   earlier `environment.yml` revision. The current file declares `httpx2` and
   no project source imports `httpx` directly. There are no pip-installed
   packages, but there is no exact Conda lock file.
3. Docker is unavailable. No isolated ReAgent PostgreSQL database currently
   exists, and this audit forbids creating or resetting one. Consequently the
   destructive PostgreSQL integration test, real-stack Playwright rerun, and
   all Compose acceptance work were not executed in this audit.

## Git safety

### Observed state before creating this report

- `git status --short`: no output; tracked working tree clean.
- `git ls-files | wc -l`: `248`.
- All backend, frontend, demo, Docker, documentation, and `.agent_read` source
  files are tracked.
- `git check-ignore -v .agent_read/context.md`: no match; `.agent_read` is
  trackable and currently tracked.
- There were no untracked files before this report was created.

### Ignored state

`git status --ignored --short` showed only generated/local material:

- `.pytest_cache/`
- Python `__pycache__/` directories
- `frontend/node_modules/`
- `frontend/.next/`
- `frontend/playwright-report/`
- `frontend/test-results/`
- `frontend/next-env.d.ts`

Root and frontend ignore files also cover local `.env*` values while explicitly
allowing `.env.example`, private keys, logs, SQLite data, runtime data,
uploads/artifacts, coverage, and standard package/build outputs. Compose
PostgreSQL data is stored in a Docker named volume outside the Git worktree.

After this report is created, this report itself is intentionally untracked
because the audit did not run `git add`. Tracked source would survive
`git clean`, but this report would not. `git clean -fdx` would additionally
delete ignored dependencies, build evidence, and local environment files.
Therefore no Git clean/reset operation should be run before the owner reviews
and commits or separately backs up this report.

## Storage baseline

Filesystem `/dev/disk4s1`:

- capacity: 935 GiB
- used: 42 GiB
- available: 892 GiB
- utilization: 5%

Repository totals:

| Path | Disk usage |
|---|---:|
| repository | 665 MiB |
| `frontend/` | 661 MiB |
| `frontend/node_modules/` | 543 MiB |
| `frontend/.next/` | 115 MiB after acceptance build |
| `frontend/playwright-report/` | 1.2 MiB |
| `backend/` | 2.6 MiB |
| backend `__pycache__` files/directories | 1.7 MiB, 191 `.pyc` files |
| `.agent_read/` | 248 KiB before this report |
| `.pytest_cache/` | 24 KiB |
| `demo/` | 8 KiB |
| `docker/` | 8 KiB |

The repository size is persistent disk usage. It does not imply equivalent RAM
use: dependency trees, build output, reports, and caches consume effectively no
process RAM while idle, aside from reclaimable operating-system file cache.

## Resource inventory

| Resource | Management | Location | Disk usage | Current RAM | Regenerable | Cleanup risk |
|---|---|---|---:|---:|---|---|
| `reagent-dev` | Conda | `/Users/lifengguang/miniconda3/envs/reagent-dev` | 297 MiB | none while commands are stopped | yes, from `environment.yml` | high: reinstall required |
| Conda package cache | Conda shared cache | `/Users/lifengguang/miniconda3/pkgs` | 8.8 GiB apparent | none | yes, by redownload | medium/high: shared by all environments |
| pip cache | pip shared cache | `/Users/lifengguang/Library/Caches/pip` | 2.0 GiB | none | yes | medium: unrelated projects may reuse it |
| `node_modules` | npm local install | `frontend/node_modules` | 543 MiB | none while Node is stopped | yes, `npm ci` | medium: reinstall/download required |
| npm cache | npm shared cache | `/Users/lifengguang/.npm` | 881 MiB | none | yes | medium: shared download cache |
| Next build | Next.js | `frontend/.next` | 115 MiB | none while server is stopped | yes, `npm run build` | low |
| Playwright browser cache | Playwright shared cache | `/Users/lifengguang/Library/Caches/ms-playwright` | 346 MiB | none while browser is stopped | yes, browser download required | medium: may be shared by projects |
| system Chrome | Homebrew/system application | `/Applications/Google Chrome.app` | about 2.0 GiB | about 2.55 GiB RSS across 18 user Chrome processes during audit | reinstallable, but not project-owned | very high: do not treat as project cache |
| Playwright reports/results | Playwright | `frontend/playwright-report`, `frontend/test-results` | 1.2 MiB + 4 KiB | none | yes, by E2E rerun | low |
| PostgreSQL software | Homebrew | `/opt/homebrew/Cellar/postgresql@18` | 82 MiB | included below when server runs | reinstallable | high: shared system tool |
| PostgreSQL data | Homebrew service | `/opt/homebrew/var/postgresql@18` | 63 MiB | about 18 MiB RSS; approximately 0% CPU | not generally regenerable | destructive/state-losing |
| Docker images/volumes | Docker | unavailable | not measurable/none inspected | none | images yes; database volume no | unknown until Docker exists |

The shared Conda/npm/pip/Playwright caches and Homebrew Node/PostgreSQL/Chrome
installations are outside the repository. Global npm contains `npm@11.6.4` and
`azurite@3.35.0`; Azurite is unrelated and not required by ReAgent. The
Homebrew Node Cellar uses 84 MiB and `/opt/homebrew/lib/node_modules` uses
194 MiB. No globally installed Python distribution is required by ReAgent.

Three Next.js sandbox panic logs exist outside the repository under the current
macOS temporary directory, each 1.3 KiB. One was produced by this audit's first
sandboxed build attempt; none was removed.

## Conda and Python audit

### Current installation

- Conda executable: `/Users/lifengguang/miniconda3/bin/conda`
- Conda version: 25.5.1
- active shell environment: `base`
- project environment: `/Users/lifengguang/miniconda3/envs/reagent-dev`
- Python: 3.11.15
- all `conda list` entries report the `conda-forge` channel
- pip-installed distributions inside `reagent-dev`: none

Declared direct dependencies in `environment.yml`:

- `python=3.11`
- `pytest=8.4`
- `sqlalchemy=2`
- `alembic`
- `psycopg=3`
- `fastapi`
- `pydantic=2`
- `uvicorn`
- `httpx2`

`environment.yml` is the only Python dependency manifest in the repository.
There is no `requirements.txt`, `pyproject.toml`, Pipfile, Poetry lock, or Conda
lock file. The backend Dockerfile copies this file and runs
`micromamba create --file /tmp/environment.yml`; Docker therefore derives from
the same canonical dependency definition.

### Drift and reproducibility

`conda-meta/history` shows that a prior environment revision explicitly
declared `httpx`; the next update switched to `httpx2` without `--prune`.
`conda env export --from-history` consequently still emits both. The current
source file is the intended dependency authority; the installed environment is
a small superset.

The user's global Conda configuration uses flexible channel priority with a
Tsinghua PyTorch mirror and defaults. The environment file declares
`conda-forge`, and all current packages resolved from conda-forge, but an exact
cross-machine build is not guaranteed because only major/minor constraints are
pinned and no explicit/conda-lock file is committed.

An exact lock is not required to keep this prototype functional—the validation
suite passes—but it is recommended before CI/production acceptance or whenever
identical transitive builds across time/platforms are required.

## Node.js, npm, and lockfile audit

### Current installation

- Node executable: `/opt/homebrew/bin/node`
- Node version: 25.2.1
- npm executable: `/opt/homebrew/bin/npm`
- npm version: 11.6.4
- project package root: `frontend/node_modules`
- npm cache: `/Users/lifengguang/.npm`
- npm lock format: lockfile version 3
- lock package records: 550 including the root
- 549 resolved registry entries, all from `registry.npmjs.org`
- resolved entries missing integrity: zero

The project selects npm through `package-lock.json`; it has no yarn/pnpm lock.
`package.json` has neither an `engines` nor `packageManager` field, and there is
no `.nvmrc`/`.node-version`. Docker pins Node `24.14.1`, whereas this audit used
local Node `25.2.1`. This is a local/Docker runtime-version inconsistency even
though the current suite passes on Node 25.

`package-lock.json` records exact transitive versions, download locations,
integrity digests, dependency relationships, and platform/optional metadata.
`npm ci` uses it to replace a local installation with the locked graph; optional
native packages can still differ by operating system/CPU.

### Installed-tree integrity warning

- `npm ls --depth=0 --json`: exit 0, but reports five optional WASM packages as
  extraneous.
- `npm ls --all --json`: exit 1 (`ELSPROBLEMS`), with the same extraneous
  packages plus `fsevents@2.3.3` invalid for Playwright's nested `2.3.2` request.
- The affected packages do exist in the lock file as optional packages; the
  issue is the current hoisted/deduplicated installation tree, not missing lock
  metadata.

No install/reconciliation was attempted. `npm cache verify` was intentionally
not run because npm documents verification as potentially garbage-collecting
cache content, which conflicts with the audit-only rule.

No global npm application package is required. A clean clone consumes about
543 MiB for `node_modules`, up to 115 MiB for `.next`, and browser/download
caches outside the repository.

## Playwright audit

- package and CLI version: 1.61.1, locked by `package-lock.json`
- default configured browser channel: system `chrome`
- system Chrome bundle version on disk: 150.0.7871.129
- running user Chrome processes still showed a 149 framework path, consistent
  with an application updated while already open; these are not ReAgent test
  processes
- Playwright-managed cache contains `chromium-1228` and `ffmpeg-1011`
- cache location: `/Users/lifengguang/Library/Caches/ms-playwright`
- cache size: 346 MiB
- report: six files, consisting of `index.html` and five prior success PNGs
- current `test-results`: empty

The successful report is evidence from Phase 8B, not a browser run performed by
this audit. Browser binaries live outside the repository and can be large.
Reports, traces, screenshots, videos, test results, and `.next` are correctly
ignored by both root/frontend Git rules and the Docker build context.

## Docker and Compose audit

Every attempted Docker inspection command returned `command not found`:

- `docker --version`
- `docker compose version`
- `docker info`
- `docker system df`
- image, volume, and container listings

Docker was not installed, no installation was attempted, and no Docker runtime
validation was performed.

Static topology:

- pulled base/service images would include
  `postgres:18.4-alpine3.23`,
  `mambaorg/micromamba:2.8.1-debian13-slim`, and
  `node:24.14.1-alpine3.23`
- built images would be `reagent-demo-backend:local` and
  `reagent-demo-frontend:local`
- services are `db`, one-shot `migration`, one-shot `seed`, `backend`,
  `frontend`, and profile-only `integration-test`
- PostgreSQL data would persist in named volume `reagent_postgres_data`, mounted
  at `/var/lib/postgresql` in the container
- `make demo-stop` preserves the volume
- `make demo-reset` executes `docker compose down --volumes` and deletes it

Future Docker disk categories are pulled images, built images, layer/build
cache, stopped/running container writable layers, logs, and the named PostgreSQL
volume. None are measurable until Docker is installed.

## PostgreSQL audit

- client/server tooling: Homebrew PostgreSQL 18.1
- Homebrew service status: started
- server PID: 1011, data directory `/opt/homebrew/var/postgresql@18`
- listening: `127.0.0.1:5432` and `[::1]:5432`
- 5432 accepted connections outside the filesystem/network sandbox
- prior temporary port 55439: closed/no response
- temporary directories matching `reagent-phase8b-pg.*`: none under
  `/private/tmp` or `/tmp`
- remaining database names: `ProjectDB`, `postgres`, `template0`, `template1`
- databases named `reagent`, `reagent_test`, or `reagent_e2e`: zero
- catalog sizes: `ProjectDB` about 8.2 MiB; `postgres` and templates about
  7.4–7.6 MiB each; complete cluster directory 63 MiB

The Phase 8B disposable cluster/data is gone and no ReAgent database remains.
`ProjectDB` is treated as unrelated user data and was neither inspected beyond
catalog name/size nor used for tests.

## Running process and RAM audit

No ReAgent Next.js server, Node application server, FastAPI/Uvicorn process,
pytest process, Python backend process, Playwright process, managed Chromium
process, or temporary PostgreSQL server was running.

The long-running Homebrew PostgreSQL service uses about 18 MiB summed RSS and
approximately 0% CPU. The user's normal Chrome session used about 2.55 GiB
summed RSS across 18 processes; it predates this audit and is not a leaked E2E
browser. The ChatGPT/Codex tooling itself has Node processes, but they are not
ReAgent services.

RAM/RSS is released when a test/server/browser process exits. Conda/npm/browser
caches, PostgreSQL rows, `.next`, reports, and dependencies remain on disk after
shutdown until explicitly removed.

## Dependency source-of-truth table

| Concern | Source of truth | Current observation |
|---|---|---|
| Python runtime | `environment.yml` (`python=3.11`) | local 3.11.15; container resolves from same file |
| Python dependencies | `environment.yml` | only Python manifest; installed orphan `httpx`; no pip installs |
| Python environment | Conda `reagent-dev` | local prefix outside repo; range-pinned, not exactly locked |
| frontend direct dependencies/scripts | `frontend/package.json` | valid; no Node/npm version declaration |
| npm resolution | `frontend/package-lock.json` v3 | authoritative for `npm ci`; current `node_modules` has optional-tree drift |
| Playwright package | package/lock files | 1.61.1 |
| Playwright browser | system Chrome by config; optional managed cache | external and not cryptographically pinned by repo |
| Docker topology | `compose.yaml` + Dockerfiles | statically coherent; runtime unverified |
| PostgreSQL schema | Alembic revision `20260721_0001` | no current ReAgent DB to inspect |
| migrations | `alembic.ini`, `backend/database/migrations/` | sole schema migration source |
| environment variables | `.env.example`, `frontend/.env.example` | templates tracked; no local `.env` exists |
| demo commands | root `Makefile`, documented in `DEMO.md` | one command interface; Docker targets unavailable here |

Direct answers:

1. `environment.yml` is the only Python dependency definition: **yes**.
2. Docker derives its Python environment from it: **yes**.
3. `package-lock.json` is authoritative for npm resolution: **yes**, when using
   `npm ci`.
4. Global npm packages required: **none**; only the Node/npm toolchain is needed.
5. Global Python packages required: **none**; use Conda or the backend image.
6. Reproduction without the current shell: **the Docker demo is designed to do
   so once `.env`, Docker, host Node/npm, and a browser for E2E are supplied**.
   Local development also needs Conda and PostgreSQL. Exact transitive Python
   and local Node versions are not fully pinned.
7. Unverified without Docker: resolved Compose config, image pulls/builds,
   health-gated migration/seed/startup, actual image/cache/volume sizes,
   Compose integration/E2E, volume deletion, second clean startup, and
   container-restart persistence.

## Acceptance evidence from current installations

| Command | Exit | Result/duration | Persistent effect | Cleanup |
|---|---:|---|---|---|
| `conda run --no-capture-output -n reagent-dev pytest -q backend` | 0 | 67 passed, 8 PostgreSQL-gated skipped; pytest 0.79s, wall 2.40s | may refresh ignored pytest/bytecode caches; no DB | processes exited; caches retained by audit rule |
| `conda run --no-capture-output -n reagent-dev python -m compileall -q backend` | 0 | passed; wall 0.93s | refreshes ignored `.pyc` as needed | no process/service remains; bytecode retained |
| `npm test` | 0 | 4 files/5 tests passed; Vitest 1.10s, wall 1.40s | no tracked change | process exited |
| `npm run lint` | 0 | passed; wall 1.77s | no tracked change | process exited |
| `npm run build` inside sandbox | 1 | Turbopack blocked from binding internal local port | partially refreshed ignored `.next`; wrote one 1.3 KiB temp panic log | retained; no cleanup permitted |
| `npm run build` in approved local context | 0 | compiled/typed/generated 6 pages; wall 4.01s | refreshed ignored `.next` to 115 MiB | build process exited; output retained |
| isolated PostgreSQL integration | not run | no isolated ReAgent DB and test intentionally resets schema | none | not applicable |
| real-stack Playwright E2E | not run | safe stack required creating/migrating a DB and new run data | none | not applicable |
| Docker validation | not run | Docker command unavailable | none | not applicable |

## Acceptance level A — current machine

### Current audit status

Passed now: Git safety, backend fast tests, backend compilation, frontend unit
tests, lint, production build, and no ReAgent service leaks.

Pending explicit authorization: creating a disposable database, running the
destructive PostgreSQL integration test, seeding it, starting FastAPI/Next.js,
and running Playwright. Do not use existing `ProjectDB`.

### Prerequisites

- existing `reagent-dev`, Node/npm, local packages, system Chrome
- running Homebrew PostgreSQL 18 on 127.0.0.1:5432
- explicit permission to create and later drop database `reagent_acceptance`
- terminals for backend and frontend services

### Safe owner-operated commands after authorization

```bash
cd /Volumes/tb/个人资料/暑研/UCInspire26/MetaResearchAgent/ResearchAgent

/opt/homebrew/Cellar/postgresql@18/18.1/bin/createdb reagent_acceptance
export REAGENT_DATABASE_URL='postgresql+psycopg://lifengguang@127.0.0.1:5432/reagent_acceptance'
export REAGENT_TEST_DATABASE_URL="$REAGENT_DATABASE_URL"
export REAGENT_E2E_DATABASE_URL="$REAGENT_DATABASE_URL"
export REAGENT_ALLOW_DATABASE_RESET=1

conda run --no-capture-output -n reagent-dev pytest -q backend
conda run --no-capture-output -n reagent-dev python -m compileall -q backend
conda run --no-capture-output -n reagent-dev python -m backend.demo.seed

cd frontend
npm test
npm run lint
npm run build
cd ..
```

Start in terminal 1:

```bash
REAGENT_DATABASE_URL="$REAGENT_DATABASE_URL" \
  conda run --no-capture-output -n reagent-dev \
  uvicorn backend.api.app:app --host 127.0.0.1 --port 8000
```

Start in terminal 2:

```bash
cd frontend
REAGENT_API_URL=http://127.0.0.1:8000 npm run dev
```

Run in terminal 3:

```bash
cd frontend
REAGENT_E2E_BASE_URL=http://127.0.0.1:3000 npm run test:e2e
```

Expected acceptance: all 75 backend tests pass with no skip; Playwright reports
one complete approval flow passed; reload retains the deterministic summary.
Any migration/seed failure, missing approval wait, event-order error, or reload
loss is an acceptance failure rather than an infrastructure warning.

Stop only the two foreground application commands with Ctrl-C. Verify:

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

Both should return no application listener. The pre-existing Homebrew
PostgreSQL service may remain. Optional destructive database cleanup is listed
later and must be separately approved.

## Acceptance level B — clean Docker-capable machine

### Prerequisites

- clean clone with this report committed
- Docker Engine/Desktop with Compose v2
- Make
- Node/npm matching the frontend lock; preferably Node 24.14.1 to match Docker
- Google Chrome, or a Playwright-managed Chromium installed for the matching
  Playwright version
- enough disk for pulled/build images, build cache, `node_modules`, browser
  binaries, and the named PostgreSQL volume

### Exact sequence

```bash
git clone <repository-url> ResearchAgent
cd ResearchAgent

cp .env.example .env
# Review every value in .env; keep it local and never commit credentials.

cd frontend
npm ci
cd ..

docker --version
docker compose version
make demo-config-check
make demo-start
make demo-status

curl --fail http://127.0.0.1:8000/workflows
curl --fail http://127.0.0.1:3000/

make test-integration
make test-e2e
curl --fail 'http://127.0.0.1:8000/runs?offset=0&limit=1'

make demo-stop
make demo-start
make demo-status
curl --fail 'http://127.0.0.1:8000/runs?offset=0&limit=1'

make demo-reset
make demo-start
make demo-status
curl --fail http://127.0.0.1:8000/workflows
curl --fail 'http://127.0.0.1:8000/runs?offset=0&limit=1'
make test-e2e

make demo-stop
```

Expected behavior:

- config resolves without warnings/errors
- database health precedes migration; migration precedes seed; seed precedes
  backend; backend health precedes frontend
- catalog contains exactly the immutable demo identity/version
- integration and E2E pass against real PostgreSQL
- stop/start without `--volumes` preserves run state
- reset/start removes prior runs, recreates schema, and re-seeds one workflow
- second E2E passes from the new volume

Failure of image build, dependency resolution, health ordering, migration,
seed, persistence, or either test is a Level B rejection. Inspect
`make demo-status` and `make demo-logs`; do not prune resources until evidence
is captured.

## Optional cleanup plan — not executed

Measure again immediately before any cleanup because sizes can change.

### A. Safe and regenerable

| Proposed command | Target/current size | Recoverability | Reinstall | Risk |
|---|---|---|---|---|
| `rm -r -- frontend/.next` | exact Next output, 115 MiB | `npm run build` | no dependency reinstall | low |
| `rm -r -- frontend/playwright-report frontend/test-results` | 1.2 MiB | rerun E2E | no | low; deletes evidence |
| `rm -r -- .pytest_cache` | 24 KiB | next pytest run | no | low |
| `find backend -type d -name __pycache__ -prune -exec rm -r -- {} +` | backend bytecode, 1.7 MiB | import/compileall | no | low; verify working directory first |
| `rm -- /var/folders/qh/p9wkbjmx2h10swnjtps84fg40000gn/T/next-panic-246f5fc5d62fa922820ea877389cdbea.log` | audit panic log, 1.3 KiB | not needed | no | low |

### B. Regenerable but expensive/shared

| Proposed command | Maximum apparent recovery | Recoverability | Reinstall/download | Risk |
|---|---:|---|---|---|
| `rm -r -- frontend/node_modules` | 543 MiB | `cd frontend && npm ci` | yes | medium; frontend unusable until install |
| `rm -r -- /Users/lifengguang/Library/Caches/ms-playwright` | 346 MiB | matching Playwright browser install | yes | medium; shared by projects |
| `npm cache clean --force` | up to 881 MiB | npm redownloads | yes | medium; shared cache |
| `conda clean --packages --tarballs` | up to 8.8 GiB apparent, actual reclaim may be lower due package linking | Conda redownloads | yes | medium/high; shared by all Conda envs |
| `/Users/lifengguang/miniconda3/bin/python -m pip cache purge` | up to 2.0 GiB | pip redownloads | yes | medium; unrelated projects may use it |

Use each tool's dry-run/listing mode where available and inspect scope before
approval. Do not combine these into a broad home-directory cleanup.

### C. Destructive or state-losing

| Proposed command | Recovery | Risk |
|---|---|---|
| `conda env remove -n reagent-dev` | recreate from `environment.yml`; exact current transitive set not locked | high |
| `docker volume rm reagent_postgres_data` | no recovery without backup; deletes demo runs | critical |
| `/opt/homebrew/Cellar/postgresql@18/18.1/bin/dropdb reagent_acceptance` | no recovery without database backup | critical; only if that exact disposable DB was owner-created |
| deleting `.env`/`frontend/.env.local` | reconstruct manually from templates; local secrets/ports lost | high |
| `git clean -fd` | deletes this untracked report; no recovery unless copied | high |
| `git clean -fdx` | additionally deletes dependencies, reports, builds, and local env files | critical |
| `git reset --hard` | discards tracked edits not committed elsewhere | critical |

Never target the repository root, home directory, `/opt/homebrew/var/postgresql@18`,
or `ProjectDB` with a broad delete/reset command.

## Remaining risks and recommendation

- Conda is range-pinned rather than locked and has an orphan `httpx` install.
- Local Node 25 differs from Docker Node 24; no local Node/npm version pin exists.
- Current `node_modules` has optional dependency-tree drift.
- Shared caches can grow independently of the repository: Conda 8.8 GiB, pip
  2.0 GiB, npm 881 MiB, Playwright 346 MiB.
- Docker behavior and Docker storage are wholly unverified.
- Current PostgreSQL has no ReAgent DB, so current-audit database/E2E acceptance
  is incomplete.
- No ReAgent services leaked; the existing PostgreSQL and Chrome processes are
  pre-existing user services.
- No local `.env` exists now. Future `.env` files are ignored, which protects
  secrets from normal Git adds but also makes them vulnerable to broad cleanup.

The current machine is healthy for the verified fast backend and frontend
workflow. The project is reproducible at compatible-version level from
`environment.yml` and exact npm graph level from `package-lock.json`, but exact
Python/Node/browser and Docker clean-machine reproduction remains unproven.

Before cleanup, the owner should review and commit or separately back up this
audit report, then complete Level A database/E2E acceptance under explicit
authorization. The single immediate next action is to review and commit
`.agent_read/progress/environment_and_acceptance_audit.md`; do not clean caches
or environment state first.
