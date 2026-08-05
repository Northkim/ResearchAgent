# ReAgent

ReAgent V0.1 is a localhost-only, single-user research workspace. The cloud
application manages project metadata, downloadable Workflow Packages, explicit
Progress Report uploads, progress projections, and bounded API Proxy
capabilities. The downloaded folder remains authoritative for concrete
research state, and Codex performs the Literature Search work locally.

## Start the local V0.1 product

Prerequisites are Conda environment `reagent-dev`, Node/npm, and a running
loopback PostgreSQL database that is not ProjectDB. Export a SQLAlchemy URL;
the startup script never reads `.env`:

```bash
export REAGENT_DATABASE_URL='postgresql+psycopg://127.0.0.1:5432/reagent_local_v01'
make dev
```

Open <http://127.0.0.1:3000/projects>. The script verifies dependencies and
the loopback database, applies Alembic migrations, and starts FastAPI and
Next.js. Logs, generated Package artifacts, and PID files stay under
`/tmp/reagent-v0-1-$UID` by default.

Stop only the application processes started by that runtime directory:

```bash
make stop
```

PostgreSQL is a documented prerequisite and is never stopped or deleted by
these commands. Override ports or the runtime directory by exporting the
credential-free values shown in `config/local-v0.1.example`.

The complete owner flow and validation/upload commands are in
[`docs/getting-started/LOCAL_V0_1.md`](docs/getting-started/LOCAL_V0_1.md).

## V0.1 boundary

- Literature Search is the only selectable Workflow.
- Codex CLI is the supported Harness; Claude Code remains untested.
- Progress Report upload is explicit, never automatic.
- OpenAlex is experimental and disabled by default. The deterministic fake
  Provider is available for controlled demonstrations.
- Legacy Hosted pages are retained only as labelled internal history and are
  not linked from the V0.1 navigation.
- Public deployment, production authentication, multi-user authorization,
  HTTPS termination, and cloud research execution are unsupported.
