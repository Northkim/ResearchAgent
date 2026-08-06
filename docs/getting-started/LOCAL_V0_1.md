# ReAgent V0.1 Local Product Guide

ReAgent V0.1 is a localhost-only, single-user Literature Search product. The
server manages projects, Package delivery, explicit Progress Report uploads,
progress views, and bounded Proxy metadata. Codex performs the research in the
downloaded local folder; the server does not execute or resume the task.

## Prerequisites

- Conda environment `reagent-dev` with the backend dependencies;
- Node.js and npm with `frontend/node_modules` installed;
- a running PostgreSQL database reachable only through loopback;
- the current repository checkout.

## One-time database configuration

Create a persistent dedicated local database using your normal PostgreSQL
tooling. Do not use ProjectDB. The application never creates, deletes, resets,
or recreates this database.

Copy the credential-free local template to the ignored repository-root `.env`
and set its database URL once:

```bash
cp config/local-v0.1.example .env
# Edit .env:
# REAGENT_DATABASE_URL=postgresql+psycopg://user@127.0.0.1:5432/reagent_local_v01
```

The root `.env` is ignored and must remain local. The tracked examples contain
no real credential. Do not put this project-specific setting in `~/.zshrc`.

Configuration precedence is:

1. an already exported `REAGENT_DATABASE_URL`;
2. the file selected by `REAGENT_ENV_FILE`;
3. the repository-root `.env`.

The dotenv parser accepts unquoted, single-quoted, and double-quoted values,
ignores blank/comment-only lines, and never sources or executes file contents.
It does not print the database URL. An explicit exported URL overrides any file
value. `REAGENT_ENV_FILE` is useful for selecting a separate local
configuration file without changing global shell startup files.

## Start and stop

```bash
make dev
```

Startup verifies Conda and required commands, rejects non-loopback or ProjectDB
URLs, checks that the application ports are unused, upgrades the database to
the current Alembic head, waits for FastAPI and Next.js readiness, and prints:

- frontend: `http://127.0.0.1:3000/projects`;
- backend health: `http://127.0.0.1:8000/health`;
- the external runtime directory containing logs, PID files, and server-side
  Package artifacts.

Stop only those application processes:

```bash
make stop
```

Normal use is simply `make dev` and `make stop`. Startup reuses the same
persistent database and applies pending migrations. The stop command does not
stop PostgreSQL, delete a database, or remove a downloaded Package.

## Product workflow

1. Open `/projects` and create a project with a name and fictional or public
   research topic. Literature Search is fixed; creation starts no execution.
2. Open the project Package page, generate a Package, inspect its Package,
   Workflow, and checksum identities, then download the ZIP outside Git.
3. Extract the ZIP, read `AGENT.md`, and run:

   ```bash
   python validate_package.py --root .
   ```

4. Open that extracted folder with Codex. Codex is the supported Harness. It
   owns the local research task, outputs, context, and append-only Progress
   Reports; the cloud does not perform the research.
5. At a completion boundary, use the bundled `progress_report.py` helper to
   finalize a report and validate the Package again.
6. Explicitly upload the finalized report with the committed client:

   ```bash
   conda run --no-capture-output -n reagent-dev \
     python -m backend.progress_reports.client upload \
     --package-root /absolute/path/to/extracted-package \
     --report-file memory/progress/reports/<report-file>.json \
     --base-url http://127.0.0.1:8000
   ```

7. Refresh the project Progress page to view the latest execution round,
   status, completed work, current state, next action, outputs,
   warnings/errors, and immutable report-history receipts.

Upload is always an explicit owner action. The server never generates a report
or mutates the downloaded Package.

## Provider boundary

OpenAlex is the only experimentally accepted live Provider, remains disabled
by default, and is not needed for the basic local product flow. A deterministic
fake Provider may be used for controlled demonstrations through the existing
operator-issued capability and provider-neutral client. Credentials and token
plaintext must stay outside Git and outside the Package.

## Known limits

Claude Code is Experimental / Untested. Only Literature Search exists. Public
deployment, production authentication, OAuth/SSO, multi-user authorization,
HTTPS termination, proof of possession, production secret management,
automatic upload, Hosted/cloud research execution, and additional Providers or
Workflows are outside V0.1.
