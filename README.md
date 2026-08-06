# ReAgent

ReAgent V0.1 is a localhost-only, single-user research workspace. The cloud
application manages project metadata, downloadable Workflow Packages, explicit
Progress Report uploads, progress projections, and bounded API Proxy
capabilities. The downloaded folder remains authoritative for concrete
research state, and Codex performs the Literature Search work locally.

## Start the local V0.1 product

Prerequisites are Conda environment `reagent-dev`, Node/npm, and a running
loopback PostgreSQL database that is not ProjectDB. One time only, create that
database and copy the credential-free local template to the ignored root
`.env`:

```bash
cp config/local-v0.1.example .env
# Edit .env and set REAGENT_DATABASE_URL for the persistent local database.
```

Normal startup and shutdown then require only:

```bash
make dev
make stop
```

Open <http://127.0.0.1:3000/projects>. The script verifies dependencies and
the loopback database, applies Alembic migrations, and starts FastAPI and
Next.js. Logs, generated Package artifacts, and PID files stay under
`/tmp/reagent-v0-1-$UID` by default.

`make dev` reuses the database and applies migrations; it never creates,
deletes, resets, or recreates the database. `make stop` stops only the
application processes recorded in the runtime directory and never stops or
deletes PostgreSQL.

An already exported `REAGENT_DATABASE_URL` overrides `.env`. Set
`REAGENT_ENV_FILE` to select a different local dotenv file instead. The loader
parses assignments without executing shell syntax and never prints the URL.
Tracked `.env.example` and `config/local-v0.1.example` contain no real
credential. Do not put project-specific configuration in `~/.zshrc`.

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
