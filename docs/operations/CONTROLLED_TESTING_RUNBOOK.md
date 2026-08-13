# Controlled Testing Runbook

This runbook operates one **isolated ReAgent instance for one controlled
tester**. ReAgent currently has no user identity, Project ownership, or tenant
authorization. Do not put mutually untrusted testers on one API or database,
and do not expose FastAPI or Next.js directly to the public Internet.

The controlled profile keeps backend and frontend on loopback, uses a dedicated
PostgreSQL database, disables live Providers, API documentation, and legacy
Hosted AgentRuntime routes, and serves browser API calls through the same-origin
Next.js rewrite. Remote access needs an operator-managed, authenticated private
tunnel or access gateway with TLS. That layer is outside this repository and
must not forward the backend port separately.

## Prerequisites and instance isolation

The host needs this reviewed repository revision, Conda environment
`reagent-dev`, Node.js/npm, loopback PostgreSQL, and PostgreSQL client tools
from the server's major version. Allocate one database, runtime directory,
frontend port, and backend port per tester.

The tester needs Python 3.11 or later, a locally authenticated supported Codex
CLI, and disk space for the Local Workspace. The downloaded
`reagent_local.py` uses only the Python standard library. A tester receives no
ReAgent Provider or database credential.

Keep owner/manual testing and automated qualification databases separate:

- `REAGENT_DATABASE_URL` selects the persistent database for one manually
  operated controlled instance. It may intentionally be an owner continuity
  database such as `reagent_local_v01`.
- Automated H1/F1F qualification must use `make test-controlled-e2e`. That
  harness creates a uniquely named temporary database, writes an exact
  per-execution disposable marker, migrates it, starts controlled services
  with an explicit database override, runs the browser tests, and drops only
  that verified database afterward.
- `REAGENT_TEST_DATABASE_URL` is destructive-test configuration, never a
  fallback for an owner database. PostgreSQL fixtures reject protected names,
  merely test-looking names, missing markers, and marker/identity mismatches
  before `TRUNCATE`, downgrade, or other destructive setup.

Do not run mutating Playwright product journeys against an already running
manual instance. Stop that application's frontend/backend first; automated
qualification fails closed if the frozen loopback ports are occupied and
never stops a manual instance automatically. For local automated qualification, supply only a loopback
administrative connection to PostgreSQL's `postgres` or `template1` database;
the harness generates the test database URL itself:

```bash
export REAGENT_TEST_ADMIN_DATABASE_URL=postgresql+psycopg://operator@127.0.0.1:5432/postgres
make test-controlled-e2e
```

The same generated marker lifecycle protects the complete PostgreSQL backend
suite:

```bash
make test-backend-postgres
```

Do not manually copy `REAGENT_DATABASE_URL` into
`REAGENT_TEST_DATABASE_URL`. The generated identity marker is intentionally
not present in persistent owner/manual databases.

Example operator allocation (replace names and paths; do not copy secrets into
Git):

```bash
createdb --host=127.0.0.1 --port=5432 reagent_controlled_tester_01
export REAGENT_DATABASE_URL=postgresql://127.0.0.1:5432/reagent_controlled_tester_01
export REAGENT_LOCAL_RUNTIME_DIR=/var/lib/reagent/tester-01
export REAGENT_BACKEND_PORT=18101
export REAGENT_FRONTEND_PORT=17101
```

Use peer authentication, `.pgpass` with mode `0600`, or an operator-managed
secret injection mechanism. Never put a password in tracked configuration, a
tester guide, a browser environment variable, or a command transcript.

## Migrate, start, and inspect

Only one operator process may migrate or start an instance. The existing
startup contract validates database connectivity, runs `alembic upgrade head`
before serving traffic, builds the production frontend, and waits for
readiness:

```bash
make controlled-start
curl --fail http://127.0.0.1:18101/health
curl --fail http://127.0.0.1:18101/ready
```

This owner/manual command remains valid with an explicitly supplied persistent
`REAGENT_DATABASE_URL`; it is not the automated qualification entry point.

`/health` is liveness only. `/ready` succeeds only when PostgreSQL is
reachable, the sole revision is `20260813_0020`, and the reviewed Workflow,
Skill, Artifact-dependency, Experiment Resource-requirement, and current
interactive Experiment Capsule records exist.
It never calls a live Provider or Resource resolver. A gateway should send user
traffic only while readiness passes.

The controlled process writes mode-`0600` logs and PID identity records under
`$REAGENT_LOCAL_RUNTIME_DIR`. Backend request events contain request ID,
matched route template, status, duration, and bounded Project/Workflow IDs.
They omit request bodies, query values, Provider credentials, Artifact bytes,
and research text. Give operators the user-visible error code and Request ID;
do not send research outputs without a separate data-handling authorization.

```bash
tail -f "$REAGENT_LOCAL_RUNTIME_DIR/backend.log"
tail -f "$REAGENT_LOCAL_RUNTIME_DIR/frontend.log"
curl -i http://127.0.0.1:18101/docs  # expected 404
curl -i http://127.0.0.1:18101/runs  # expected 404
```

## Tester access and onboarding

Give each tester only an authenticated private URL or tunnel to the assigned
frontend port. One private-host pattern is a per-user SSH account and local
port forwarding:

```bash
ssh -N -L 3000:127.0.0.1:17101 tester-host-alias
```

The tester opens `http://127.0.0.1:3000/projects`. Do not expose or forward the
backend or PostgreSQL port. Follow
[`CONTROLLED_TESTER_GUIDE.md`](../getting-started/CONTROLLED_TESTER_GUIDE.md).
The Help page provides the fixed local-client download and Project-specific
Workspace setup descriptor.

Controlled H2 runs use the deterministic fake Provider. Results from that
boundary are test fixtures, not real literature evidence. A live Provider
requires separate owner authorization and qualification.

## Restart and shutdown

```bash
REAGENT_LOCAL_RUNTIME_DIR=/var/lib/reagent/tester-01 make stop
make controlled-start
```

`make stop` validates process identity, stops only the assigned
frontend/backend process trees, and never stops or alters PostgreSQL. During a
database restart, liveness remains up, readiness fails, API mutations return a
safe Request-ID-bearing error, and the SQLAlchemy pool reconnects after the
database returns.

Stop application traffic before a planned migration or restore. If migration
fails, do not serve traffic against an uncertain schema. Restore the pre-change
database dump and matching application revision; do not run an automatic
Alembic downgrade on user data.

## Database backup and restore

These credential-free commands are the H2-qualified shape. Use the actual
loopback port and database, store dumps outside Git and the runtime tree,
restrict permissions, and encrypt them according to host policy.

```bash
pg_dump --format=custom --no-owner --no-privileges \
  --host=127.0.0.1 --port=5432 \
  --file=/secure-backups/reagent_controlled_tester_01.dump \
  reagent_controlled_tester_01
chmod 600 /secure-backups/reagent_controlled_tester_01.dump
```

Restore with the application stopped:

```bash
dropdb --host=127.0.0.1 --port=5432 reagent_controlled_tester_01
createdb --host=127.0.0.1 --port=5432 reagent_controlled_tester_01
pg_restore --exit-on-error --no-owner --no-privileges \
  --host=127.0.0.1 --port=5432 \
  --dbname=reagent_controlled_tester_01 \
  /secure-backups/reagent_controlled_tester_01.dump
python -m alembic current
python -m alembic check
make controlled-start
curl --fail http://127.0.0.1:18101/ready
```

Verify Project, Workflow Instance, Progress, Artifact, dependency, Workspace,
Capsule, and Manifest identities; then execute a new normal API mutation to
prove constraints and transaction state remain usable.

PostgreSQL backup preserves Cloud metadata and provenance. It does **not**
back up a tester's Local Workspace, research bytes, Capsule outputs, local
memory, Artifact Index, or materialization receipts. The operator must also
back up configured Cloud Package/Progress content roots when those bytes are
required; the database contains references, not a filesystem snapshot.
Testers must retain and protect their Local Workspace.

## Common failures

- `ready: database unavailable`: restore PostgreSQL connectivity; do not
  delete or recreate a Workspace. The application reconnects automatically.
- `ready: migration mismatch`: stop traffic and run the reviewed migration
  from one operator process.
- `ACK_PENDING`: keep installed Capsules and retry the same explicit sync;
  acknowledgement is idempotent.
- interrupted sync or materialization: rerun the same command. Journals,
  staging, checksums, and receipts recover without overwriting user files.
- `LOCAL_ARTIFACT_DRIFT`: restore the exact producer output or select and bind
  a newly produced Artifact; never rewrite Cloud checksum metadata.
- `MATERIALIZATION_CONFLICT`: preserve the existing input and resolve it
  explicitly; no force overwrite exists.
- provider fixture unavailable: Cloud metadata operations remain available;
  retry after the operator restores the fixture boundary.
- user-visible 500: collect the stable error code and Request ID, then locate
  its metadata-only event in `backend.log`.

## Security boundary

The controlled profile is not multi-user authorization. CORS and loopback are
network boundaries, not identity. API mutations remain unauthenticated inside
the instance. Use one isolated database/process set per tester plus an
authenticated private access layer. Public deployment, shared
mutually-untrusted use, live Provider use, and automatic Workspace backup are
not authorized by H2.
