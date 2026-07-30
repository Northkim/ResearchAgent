# ReAgent reproducible demo

This guide runs the deterministic supervised research workflows through the real
Next.js UI, FastAPI application, Agent Runtime, SQL Unit of Work, and
PostgreSQL adapter and local artifact storage. No real LLM, external literature
service, credential, Redis, or worker queue is used.

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
export REAGENT_ARTIFACT_ROOT='runtime_data/artifacts'
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
| `REAGENT_ARTIFACT_ROOT` | Immutable local artifact root; default `runtime_data/artifacts` |
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

The seed publishes both immutable fixtures:

- `guided-literature-review@1.0.0` from
  `demo/workflows/guided_literature_review.v1.json`
- `guided-literature-review@2.0.0` from
  `demo/workflows/guided_literature_review.v2.json`, canonical hash
  `af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`

Publish them locally with:

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

### Guided Literature Review v2

1. Select **Guided Literature Review v2 (deterministic synthetic)** `2.0.0`.
2. Enter topic, year range, and `max_papers >= 3`; create and execute.
3. At **Waiting for approval**, confirm `papers.json` and
   `selected_papers.json` already exist.
4. Review the three synthetic titles, authors, years, venues, abstracts,
   relevance scores, ranking explanations, provider identities, and the
   abstract-only notice.
5. Approve the exact set. The fingerprint binds project/run/workflow/step,
   query hash, paper IDs, selected artifact checksum, ranker, Skills, role and
   expiry; mutation or corruption fails closed.
6. Confirm completion, `[P1]`–`[P3]`, eight artifacts, nine settled fake
   provider operations, zero cost, and reload persistence.

All content is invented; `example.invalid` citation URLs are synthetic
identifiers and are not fetched. No source is full text.

### Legacy v1 walkthrough

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

Local 9A-2 acceptance must use an isolated database, never `ProjectDB`:

```bash
export REAGENT_9A2_DATABASE_URL='postgresql+psycopg:///reagent_9a2_acceptance'
export REAGENT_9A2_ARTIFACT_ROOT='/private/tmp/reagent_9a2_artifacts'
conda run --no-capture-output -n reagent-dev pytest -q \
  backend/integration/tests/test_http_postgresql_research_v2.py
```

To use an isolated local PostgreSQL database instead of Compose for the real
backend suite, explicitly opt into destructive reset of that database:

```bash
export REAGENT_TEST_DATABASE_URL="$REAGENT_DATABASE_URL"
export REAGENT_E2E_DATABASE_URL="$REAGENT_DATABASE_URL"
export REAGENT_ALLOW_DATABASE_RESET=1
conda run --no-capture-output -n reagent-dev python -m pytest -q backend
```

Never point those three variables at a shared or production database.

## 10. Phase 9B-1 supervised OpenAlex discovery

The normal demo remains deterministic and network-free:

```bash
export REAGENT_PAPER_SEARCH_PROVIDER=fake
export REAGENT_OPENALEX_LIVE_ENABLED=false
```

`guided-literature-review@2.0.0` was not mutated. Composition chooses the
adapter, so its canonical hash remains
`af3dd76540cfb7b08a73a7fbffda76679375a8170f0099611016c57d4c9d856a`.

OpenAlex mode requires three explicit server-side values:

```bash
export REAGENT_PAPER_SEARCH_PROVIDER=openalex
export REAGENT_OPENALEX_LIVE_ENABLED=true
export REAGENT_OPENALEX_API_KEY='<owner-supplied free key>'
```

The key is required by ReAgent—not because anonymous trial calls are impossible,
but because the official `/rate-limit` endpoint requires a key and ReAgent must
verify remaining free daily credit before the search. The value must never be
placed in source control, logs, screenshots or commands copied into reports.

Supervised limits are max 20 discovery candidates, selected-paper input 3–5,
one cursor page, one preflight plus at
most three Works attempts, 15 seconds per request, 90 seconds total provider
operation, max 12 full-workflow provider request units, and zero out-of-pocket
monetary cost. Search output is discovery-only/unverified. SourceContent and LLM
providers remain deterministic fakes; no PDF/full text, Semantic Scholar,
Crossref or real LLM is invoked.

OpenAlex runs add three immutable artifacts before approval:

- `search_plan.json`: exact query, filters/policies, adapter/contract identity,
  planned maximum and one-page cursor policy;
- `search_execution.json`: sanitized endpoint/fields, timestamps, actual
  request/retry count, completeness, provider-reported credit cost and
  discovery-only identity status;
- `search_statistics.json`: received/normalized/rejected/missing/dedup/advisory
  cluster counts.

They appear alongside the existing eight research artifacts. Raw provider
responses and credentials are never artifact content. Reports include an
OpenAlex attribution and explicitly say that identity is unverified and
downstream providers are fake.

Network-free verification against an isolated Phase 9B-1 database:

```bash
createdb reagent_9b1_acceptance
export REAGENT_TEST_DATABASE_URL='postgresql+psycopg:///reagent_9b1_acceptance'
export REAGENT_9B1_DATABASE_URL="$REAGENT_TEST_DATABASE_URL"
export REAGENT_9B1_ARTIFACT_ROOT='/tmp/reagent_9b1_artifacts'
conda run --no-capture-output -n reagent-dev alembic upgrade head
conda run --no-capture-output -n reagent-dev python -m pytest -q \
  backend/database/tests \
  backend/integration/tests/test_http_postgresql_openalex_contract.py
```

The opt-in real-provider test additionally requires
`REAGENT_9B1_LIVE=true`, `REAGENT_9B1_QUERY`, and
`REAGENT_OPENALEX_API_KEY`:

```bash
conda run --no-capture-output -n reagent-dev python -m pytest -q \
  backend/integration/tests/test_http_postgresql_openalex_live.py
```

It is skipped by default. Phase 9B-1 implementation did **not** execute it
because no owner-authorized key/query/real-data retention configuration was
provided. Do not interpret the network-free OpenAlex-shaped contract test as a
live API result.

## 11. Reset and cleanup

Stop while preserving all demo runs:

```bash
make demo-stop
```

Delete the named PostgreSQL volume and replay from a clean database:

```bash
make demo-reset
make demo-start
```

The second command recreates the database, migrates it, and seeds the frozen
workflow catalog. Browser reports, traces, `.next`, `runtime_data/`, and other
generated artifacts are ignored by Git.

Filesystem and PostgreSQL cannot share one transaction, so a failed DB commit
can leave immutable orphan bytes. Inspect before cleanup; ReAgent does not
silently delete unknown files. Optional cleanup for explicitly disposable
acceptance resources is:

```bash
dropdb reagent_9a2_acceptance
rm -rf /private/tmp/reagent_9a2_artifacts
```

Phase 9B-1 acceptance resources are retained for review. Optional cleanup:

```bash
dropdb reagent_9b1_acceptance
rm -rf /tmp/reagent_9b1_pg_artifacts.Xo4fgn
```

Do not substitute `ProjectDB`, `reagent_9a1_acceptance`, or
`reagent_9a2_acceptance` in those commands.

For a dedicated local test database only, a full schema reset is:

```bash
conda run --no-capture-output -n reagent-dev alembic downgrade base
conda run --no-capture-output -n reagent-dev alembic upgrade head
conda run --no-capture-output -n reagent-dev python -m backend.demo.seed
```

## 11A. Phase 9B-2A OpenAlex evaluation harness

The evaluation harness is separate from Agent Runtime and the frontend. Its
default tests remain network-free.

Initialize an ignored evaluation directory and bind the tracked topic-set hash:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  initialize openalex-eval-example
```

Live candidate generation is never implicit. It requires an owner-authorized
key plus explicit `--live`, and one invocation is capped at three topics:

```bash
set -a
source .env
set +a

conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  generate openalex-eval-example \
  --live \
  --topic cs-persistent-agents \
  --topic biomed-long-covid-cognition \
  --topic nonenglish-chinese-digital-humanities
```

Default output root is `runtime_data/evaluations/openalex/`, which is ignored
by Git. The generator stores normalized candidates, SearchPlan/Execution/
Statistics, tracked evaluation-topic context, per-topic immutable manifests,
checksums and sanitized usage. It
stores no raw response and creates no relevance labels. Abstract preview is
off by default; explicit `--include-abstract-preview` makes the resulting
ignored data subject to `OPENALEX_DATA_RETENTION_POLICY.md`.

The CLI also stores a private mode-`0600`, append-only
`provider_operations.journal.jsonl` inside that evaluation ID. It implements
the existing ProviderOperation port for this Runtime-independent harness:
reservation, RUNNING, and settlement are fsynced before the next boundary;
restart validates the checksum chain and refuses missing/unsettled/stale
operations. It is not a raw-response log and must not be committed.

Export review sheets:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  export openalex-eval-example --format json

conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  export openalex-eval-example --format csv
```

Import a human-completed sheet:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  import openalex-eval-example /path/to/reviewer-a.json \
  --format json --require-complete
```

The `adjudicate` and `report` commands accept human-produced reviewer and
adjudication files. They reject unknown candidates, changed identity hashes,
duplicate judgments and unknown source-judgment hashes:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  adjudicate openalex-eval-example /path/to/adjudicated.json \
  /path/to/reviewer-a-import.json /path/to/reviewer-b-import.json

conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  report openalex-eval-example /path/to/adjudicated.json \
  /path/to/reviewer-a-import.json /path/to/reviewer-b-import.json
```

Inspect state without mutation:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  status openalex-eval-example
```

Cleanup is explicit and scoped:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  clean openalex-eval-example --confirm openalex-eval-example
```

Do not execute cleanup before owner review. Phase 9B-2A did not run a live
pilot; these commands document the future owner-supervised path.

## 11B. Phase 9B-2B-1 retained three-topic review packet

The owner-authorized pilot uses:

```bash
set -a
source .env
set +a

conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  initialize openalex-three-topic-pilot-v1

conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  generate openalex-three-topic-pilot-v1 \
  --live \
  --include-abstract-preview \
  --topic cs-machine-unlearning \
  --topic social-algorithmic-management \
  --topic nonenglish-chinese-digital-humanities

conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  packets openalex-three-topic-pilot-v1 \
  --reviewer reviewer_A \
  --reviewer reviewer_B
```

The actual retained private root is:

```text
runtime_data/evaluations/openalex/openalex-three-topic-pilot-v1/
```

It contains three immutable topic manifests, a mode-`0600` operation journal,
reviewer_A/reviewer_B JSON and CSV packets, a blank adjudication template and a
packet checksum manifest. It is ignored and must not be committed.

Reviewers must follow
`docs/evidence/OPENALEX_THREE_TOPIC_PILOT_REVIEW_GUIDE.md`. No judgment file has
been imported. Do not run `adjudicate` or `report` before two independent human
files are returned.

Retention deadlines:

- abstract previews: 2026-08-11 UTC or adjudication, whichever is earlier;
- normalized pools and operation journal: 2026-08-27 UTC.

Optional owner-authorized cleanup after review/cancellation:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  clean openalex-three-topic-pilot-v1 \
  --confirm openalex-three-topic-pilot-v1
```

This command deletes only the named ignored evaluation root. Do not execute it
before preserving approved aggregate evidence.

### Multilingual Chinese-topic acceptance

Phase 9B-2C-1 adds an evaluation-only command; it does not change
`guided-literature-review@2.0.0` or enable multilingual expansion by default.
The immutable plan is
`evaluation/topics/openalex_chinese_multilingual_v1.json`.

Initialize a new isolated ignored evaluation:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  initialize openalex-chinese-multilingual-v1
```

An owner-supervised live run, if free OpenAlex credit and the repository-root
key are available, is:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  generate-multilingual openalex-chinese-multilingual-v1 \
  --plan evaluation/topics/openalex_chinese_multilingual_v1.json \
  --live
```

The command runs exactly four manual variants in definition order, disables
Works retries, caps each variant at one free-credit preflight plus one Works
request, retains no raw response, and generates no relevance label. Each variant
has a separate ProviderOperation. Re-running a completed evaluation verifies
immutable artifacts and performs no provider call.

Optional cleanup, never automatic:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  clean openalex-chinese-multilingual-v1 \
  --confirm openalex-chinese-multilingual-v1
```

### Synthetic Fake Judge acceptance

Phase 9B-2C-2 adds a network-free evaluation command. It never reads the live
OpenAlex candidate pools and accepts only the source-marked synthetic fixture:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  judge-synthetic synthetic-silver-v1
```

The command runs fixture-defined pointwise A/B judgments and one mirrored
pairwise check, settles zero-cost ProviderOperations, builds a pending audit
queue, reports raw synthetic silver metrics, and verifies replay with zero
additional Fake Judge calls. Audited metrics remain unavailable because no
human result is auto-filled. The `0.80` confidence threshold, 10% sample, and
20-item cap are `TEST_POLICY_ONLY`; output is architecture evidence, not model
quality or expert ground truth.

Generated evidence stays below the ignored evaluation root. Optional cleanup:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.evaluation \
  clean synthetic-silver-v1 \
  --confirm synthetic-silver-v1
```

### Synthetic grounded-report V3 acceptance

Phase 9C-1 adds immutable `guided-literature-review@3.0.0` while preserving V2.
Run the isolated, network-free, fictional-paper acceptance with:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.synthetic_grounded_acceptance
```

The command pauses for an internal exact synthetic approval, resumes through
three summary/evidence calls, one claims call, one report call, validates
provenance, persists thirteen artifacts under the ignored
`runtime_data/grounded_v3_synthetic_acceptance` root, reconstructs through a new
in-memory process graph, and verifies zero duplicate generation calls. It
performs no socket/HTTP call, key lookup, OpenAlex call, real model call, or
spend.

Optional cleanup after review:

```bash
rm -rf runtime_data/grounded_v3_synthetic_acceptance
```

The acceptance output is architecture evidence only. It is not a real
literature report and does not authorize Phase 9C-2.

## 12. Troubleshooting

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

## 13. Known limitations

- The demo uses fixed prototype project and actor identities; there is no
  authentication, authorization, or approval-role enforcement.
- `SyncExecutionDispatcher` runs execution inline in HTTP requests; there is no
  durable queue, worker lease, clock scheduler, cancellation channel, or Redis.
- Approval expiry is enforced on a decision attempt, not by a background job.
- Fake mode remains wholly deterministic. OpenAlex live mode exists only for
  supervised discovery and was not live-verified in Phase 9B-1; SourceContent
  and LLM processing remain deterministic fakes, identity is unverified, and
  there is no full text or live citation verification. Artifact bytes use local
  filesystem storage only; remote storage and retention remain future.
- Status updates use polling rather than server-sent events or WebSockets.
- The browser suite currently targets one Chrome-compatible desktop engine plus
  a mobile-width layout assertion; it is not a cross-browser accessibility or
  performance suite.
- Compose is a local demonstration topology, not production deployment
  configuration. Secrets management, TLS, backups, observability, resource
  limits, and high-availability behavior remain out of scope.
