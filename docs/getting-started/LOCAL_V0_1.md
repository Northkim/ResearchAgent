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

Create a dedicated local database using your normal PostgreSQL tooling. Do not
use ProjectDB. Then export its SQLAlchemy URL. The product scripts deliberately
do not read `.env`:

```bash
export REAGENT_DATABASE_URL='postgresql+psycopg://127.0.0.1:5432/reagent_local_v01'
```

Optional non-secret overrides are documented in `config/local-v0.1.example`.

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

The stop command does not stop PostgreSQL, delete a database, or remove a
downloaded Package.

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
