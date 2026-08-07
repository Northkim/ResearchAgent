# NIGHT-H2 Deployment, Security, and Controlled Testing Readiness

Date: 2026-08-07

Status: **PASS_WITH_OWNER_DECISIONS_REQUIRED**

## Baseline and boundary

H2 started on clean `main` at accepted H1 final commit
`0fad50ae9262d3396ccc10c36d49d2aa15f1f947`. That commit remained an
ancestor, one worktree existed, and the sole Alembic head was
`20260806_0013`. Production Literature Search 0.4.0/Capsule 0.6.0, Idea
Discovery 0.1.0/Capsule 0.1.0, `selected-paper-library/v1`, H1 CLI discovery,
and next-action UI were reverified.

No `.env`, real credential, owner database, real Workspace/research data, live
Provider, or external service was read or called. Qualification used synthetic
Projects, temporary Workspaces, loopback processes, deterministic fixtures,
and a PostgreSQL 18.1 cluster under `/private/tmp`. H2 adds no Workflow and no
database migration.

## Readiness audit

The actual starting model was `LOCAL_SINGLE_USER`. FastAPI had no identity or
Project owner; Next.js used a same-origin rewrite; browser/Cloud/local Harness
boundaries were otherwise intact. Detailed findings are in
`docs/audits/CONTROLLED_TESTING_READINESS_AUDIT.md`:

- P0: 0;
- P1: 8 found, 7 fixed, 1 owner-level identity decision open;
- P2: 6;
- P3: 4.

The accepted controlled topology is one isolated process/database/runtime set
per tester, loopback-only, reached through an external authenticated private
tunnel/gateway. A shared mutually-untrusted API remains unsafe because no
caller identity or ownership exists.

## Hardening implemented

- `backend/api/deployment.py` validates local-development versus
  isolated-controlled-test profiles, exact empty CORS for controlled mode,
  64 KiB-8 MiB body bounds, loopback named PostgreSQL, fake-only Provider,
  disabled live flags/key, local mode, fake Proxy, and absolute roots.
- `backend/api/operations.py` adds correlation IDs, stable security headers,
  streaming/content-length limits, sanitized unhandled errors, and
  metadata-only JSON logs. Controlled startup disables Uvicorn access logs.
- `/ready` verifies SQL connectivity, exact sole revision, and B7 production
  Registry/dependency rows without Provider traffic. `/health` remains pure
  liveness.
- Controlled composition hides `/docs`, OpenAPI/Redoc, and legacy Hosted
  run/approval/workflow/artifact routers while development compatibility stays
  intact.
- Next.js emits corresponding frame/MIME/referrer/permissions headers and
  suppresses its powered-by header. Browser API remains same-origin.
- The fixed `/local-client/reagent_local.py` endpoint distributes the reviewed
  self-contained standard-library CLI with checksum/ETag and no supplied path.
- Help and Overview link the local tool and state that Cloud cannot restore a
  Workspace. `make controlled-start` builds/starts the standalone production
  frontend, checks readiness, and retains safe identity-aware stop behavior.
- Operator runbook, tester guide, threat model, readiness audit, and
  credential-free controlled config example were added.

Existing machine JSON error shapes were preserved. Request ID is carried in
the response header; new H2-only 413/500 responses also carry it in their new
error bodies. Cross-Project, checksum, archive, sync, materialization, and
immutable Capsule protections were not relaxed.

## Real controlled deployment and 25-step E2E

The following used real frontend, backend, CLI, filesystem, SQL, and product
paths. Only literature retrieval and representative Agent conversation were
the committed deterministic no-network fixtures:

1. initialize fresh isolated database; 2. upgrade to head; 3. start backend;
4. pass readiness; 5. build/start standalone frontend; 6. create Project in
browser; 7. download descriptor/bootstrap Workspace; 8. execute deterministic
Literature Search; 9. finish and create typed Artifact; 10. add Idea Discovery;
11. increment Manifest and sync its separate Capsule; 12. explicitly bind the
specific Artifact; 13. refresh/materialize with checksum receipt; 14. execute
two Idea sessions and upload Progress; 15. stop/restart backend; 16. stop/start
PostgreSQL; 17. stop/restart frontend; 18. verify state; 19. `pg_dump` custom
format; 20. drop/recreate only the isolated database; 21. `pg_restore`;
22. restart application and pass readiness; 23. verify original identities,
Manifest revision, histories, Artifact and binding; 24. rerun the complete H1
product journey to create new Progress after restore; 25. gracefully stop the
application while leaving PostgreSQL intact.

No product step used a direct DB insert, fake Lock, fake receipt, fake frontend
response, or internal JSON edit. Deterministic seed/migration setup remained
the declared fixture boundary.

## Backup/restore evidence

The representative dump was 129 KiB with recorded SHA-256, stored outside the
repository. After drop/recreate/restore:

- Alembic current/check returned sole `20260806_0013` and no drift;
- original Project ID, two Workflow Instance IDs, Progress report IDs/rounds,
  typed Artifact ID/checksum, binding ID/checksum, Manifest revision 2, and
  installation acknowledgements remained intact;
- Overview/Progress reads succeeded;
- a new full browser/API/CLI journey and new Progress mutations succeeded.

`CLOUD_DATABASE_RECOVERY = PASS`. Database recovery does not claim Local
Workspace or filesystem-content recovery.

## Failure and restart drills

- A backend restart: ready and persisted Project state after restart.
- B PostgreSQL restart: health stayed 200; ready returned 503; recovery was
  automatic through pool pre-ping.
- C database unavailable: business route returned sanitized 500 with Request
  ID; logs contained route/status/exception class, no traceback or URL value.
- D frontend restart: standalone production UI reloaded and reflected state.
- E migration mismatch: synthetic revision 0012 returned not-ready/mismatch.
- F fake Provider unavailable/configured off: controlled startup validation
  rejected the configuration; no silent fallback/live call.
- G acknowledgement retry: existing B4 idempotent ACK_PENDING recovery passed.
- H interrupted sync: B4 journal/lock/recovery tests passed.
- I interrupted materialization: B6 staging/publish/receipt recovery passed.
- J database backup/restore: destructive isolated drill passed as above.

SIGTERM-style supervised stop used existing identity records and stopped only
the application trees; PostgreSQL remained accepting connections.

## Tester/operator diagnostics

- `HOST_SETUP_STEPS = 8`
- `TESTER_SETUP_STEPS = 6`
- `TESTER_TERMINAL_COMMANDS = 8` for the full Literature-to-Idea journey
- `TESTER_SECRET_ACCESS_REQUIRED = 0` (tester-local Codex authentication is not
  a ReAgent Cloud/Provider secret)
- `TESTER_DB_ACCESS_REQUIRED = 0`
- `MANUAL_INTERNAL_JSON_EDITS = 0`
- `OPERATOR_INTERVENTIONS_REQUIRED = 2` scheduled classes: initial isolated
  instance/private-access provisioning and backup/incident recovery; routine
  Project/Workflow use needs none.

The local client is now downloadable without cloning the backend repository.
It remains unsigned and the supported H2 tester environment is Python 3.11+
on the existing Unix/macOS lock boundary.

## Qualification results

- targeted H2/API: 24 passed;
- full backend with all six historical migration DB gates, PostgreSQL suites,
  and offline integration DBs: **700 passed, 1 skipped**;
- the one skip is the pre-existing explicit live OpenAlex gate; no H2 skip was
  added;
- frontend Vitest: **16 files / 31 tests passed**;
- Playwright: **5 passed**, covering the current H1 journey, standalone
  interactive/auto Package, and retained Hosted deterministic compatibility;
- TypeScript, ESLint, production Next.js build, and Python compileall: passed;
- `pip check`: no broken requirements;
- `npm ci --dry-run --offline`: lock installation plan passed;
- `npm audit --offline --omit=dev`: zero advisories in available offline data;
  external vulnerability databases and Python `pip-audit` were not authorized/
  installed;
- Alembic heads/current/check: sole `20260806_0013`, no operations;
- `git diff --check`: passed.

The initial all-backend command exposed setup errors because freshly created
test and historical migration databases were not migrated/driver-qualified;
the authoritative rerun used explicit `postgresql+psycopg` safety-named
databases and executed every offline gate. The first frontend build was blocked
by the sandbox's Turbopack worker socket; the authorized loopback rerun passed.
The first full Playwright attempt lacked its retained Hosted seed; after using
the repository's deterministic idempotent seed, the authoritative full rerun
passed all five tests.

Scale regressions remain covered by the existing 1,000 Artifact/Progress and
multi-Workflow tests. H2 adds constant middleware/readiness work and no
per-card frontend request or N+1 database query.

## Readiness decision

- `ARCHITECTURE_READINESS = PASS`
- `CORE_USER_JOURNEY_READINESS = PASS`
- `ISOLATED_CONTROLLED_TEST_READINESS = READY`
- `CAN_SAFELY_RUN_SHARED_MULTI_USER_CONTROLLED_TEST = NO`
- `SHARED_MULTI_USER_TEST_READINESS = OWNER_DECISION_REQUIRED`
- `PUBLIC_PRODUCTION_READINESS = NOT_READY`
- `LIVE_PROVIDER_CONTROLLED_TEST = READY_BUT_NOT_EXECUTED`

The next evidence-supported action is a small 3-10 person test using one
isolated instance per tester. In parallel or before any shared deployment, the
owner must choose an application identity/Project ownership/session model. A
separate authorization is required before Provider-backed controlled testing.
