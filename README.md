# ReAgent

ReAgent V0.1 is a localhost-only, single-user research workspace. The cloud
application manages project metadata, downloadable Workflow Packages, bounded
API Proxy capabilities, automatic Progress Report uploads, and progress
projections. A short-lived local session connects one exact Package to those
capabilities. The downloaded folder remains authoritative for concrete
research state, and Codex performs Literature Search or Idea Discovery work
locally.

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

The complete owner flow, one-round command, and recovery behavior are in
[`docs/getting-started/LOCAL_V0_1.md`](docs/getting-started/LOCAL_V0_1.md).

## Optional long-lived Project Workspace

The existing downloaded Literature Search Package remains directly runnable.
NIGHT-B3 also permits a Project to initialize its canonical long-lived local
Workspace and non-destructively copy the same verified Package into its frozen
Workflow Capsule path:

```bash
python reagent_local.py bootstrap "$WORKSPACE_DIR" --descriptor workspace-bootstrap.json
python reagent_local.py adopt "$LEGACY_PACKAGE" "$WORKSPACE_DIR"
python reagent_local.py sync "$WORKSPACE_DIR"
```

Obtain `workspace-bootstrap.json` from the repository-backed
`GET /projects/{project_id}/workspace-bootstrap` endpoint after generating the
Package. The source Package is not moved, rewritten, deleted, or executed during
adoption; declared outputs, memory, Progress and receipts are preserved. The
adopted Capsule retains the original `python reagent_local.py run .` command.

See the [Workspace bootstrap, adoption, and sync guide](docs/getting-started/PROJECT_WORKSPACE_BOOTSTRAP.md)
for layout, integrity checks, recovery and exit codes. Sync is always an
explicit local command: the web service never writes the Workspace. It installs
only exact available Capsule pins, preserves retired and mutable research
state, and reports checksum-bound installation metadata. The acknowledgement
is not a cloud backup. The [Idea Discovery and Artifact handoff guide](docs/getting-started/IDEA_DISCOVERY.md)
documents explicit typed input selection, local materialization, and execution.

## V0.1 boundary

- New Projects start with Literature Search 0.4.0 / Capsule 0.6.0. Its explicit
  successful finish creates the production `selected-paper-library/v1`
  Artifact. Idea Discovery 0.1.0 is the second available Workflow and consumes
  one explicitly selected, checksum-bound library.
- Existing Literature Search 0.3.0 / Capsule 0.5.0 remains byte-stable and
  supported. It is never silently upgraded or promoted to the new Artifact
  contract.
- Codex CLI is the supported Harness; Claude Code remains untested.
- From an extracted Package, `python reagent_local.py run .` opens Codex in the
  current terminal. The owner reviews the search plan and candidate screening,
  types `finish` to finalize exactly one round, and the launcher then validates,
  closes the search session, and opens a fresh report-bound upload-only session
  to upload and verify its Progress Report. A pending upload is retried from the
  same Package without rerunning research or Provider search.
- `--auto` is the explicit unattended mode for bounded batch use and tests; it
  is never selected implicitly.
- OpenAlex is experimental and disabled by default. The deterministic fake
  Provider is available only through explicit `--mode demo`; normal mode never
  silently falls back to fictional evidence.
- Legacy Hosted pages are retained only as labelled internal history and are
  not linked from the V0.1 navigation.
- Public deployment, production authentication, multi-user authorization,
  HTTPS termination, and cloud research execution are unsupported.
