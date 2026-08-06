# ReAgent V0.1 Local Product Guide

ReAgent V0.1 is a localhost-only, single-user Literature Search product. The
server manages projects, Package delivery, bounded Proxy transport, automatic
Progress Report intake, and progress views. Codex performs planning, screening,
and synthesis in the downloaded local folder; the server does not execute,
rank, screen, synthesize, or resume the research task.

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
3. Extract the ZIP outside Git and run one complete round:

   ```bash
   python reagent_local.py run .
   ```

   The launcher prints six safe stages and opens Codex interactively in the
   current terminal. No graphical window opens. Codex first presents its topic
   interpretation, bounded query plan, screening rules, and metadata/abstract
   limitation. Search starts only after the owner confirms that plan. After
   retrieval, the owner can inspect candidate counts and themes, ask why a
   paper was included or excluded, revise a screening rule, or request one
   additional query when budget remains. Codex then describes the final local
   files and cloud summary and waits for the explicit command `finish`.

   Only after `finish` does Codex write final outputs, update context, and
   finalize one report draft. The launcher validates those machine-readable
   artifacts, closes the search session, creates exactly one Progress Report,
   and opens a fresh report-bound upload-only session. That new session uploads
   idempotently, verifies history/projection, stores a safe receipt, is revoked,
   and stops. The length of the interactive conversation cannot age this later
   upload authorization.
4. Refresh the project Progress page. It displays the round status, concise
   result summary, query/candidate/selection counts, evidence limitation,
   output names/checksums, warnings, next action, and immutable upload receipt.

The four local research outputs are:

- `outputs/search_plan.md`;
- `outputs/candidate_papers.json`;
- `outputs/selected_papers.json`;
- `outputs/literature_search_report.md`.

The complete libraries, query text, full report, and context stay local. The
cloud receives only the existing bounded Progress Report summary and artifact
names/checksums. V0.1 uses metadata and available abstracts; it never claims
that papers were read in full.

Press `Ctrl+C` to interrupt safely. The launcher forwards the signal, reaps
Codex, revokes the local session, preserves valid local files, and uploads
nothing incomplete. Run `python reagent_local.py run . --resume` to continue
partial round work. Use `--restart-round` only when intentionally discarding
round-scoped mutable files; it requires typing `restart-round` and never alters
immutable inputs, Workflow definitions, or uploaded history.

If a valid report exists without its receipt, run the same command again. It
opens a fresh upload-only session bound to that exact report, uploads it
idempotently, verifies the server receipt/history/projection, and does not rerun
search or Codex. Use the same Package; downloading another Package is neither
required nor appropriate for upload recovery. If
partial outputs exist without a valid report, the command stops without
overwriting them and prints the resume/restart choices. A completed round is
not repeated automatically.

## Provider boundary

OpenAlex is the only experimentally accepted live Provider and remains disabled
by default. Before `make dev`, an owner-authorized normal-mode session requires
the server process to receive both
`REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED=1` and
`REAGENT_OPENALEX_API_KEY`. The key stays server-side; it is never passed to
Codex or the Package. If that capability is absent, normal mode stops
fail-closed and explains the required startup step.

For a deterministic fictional demonstration, use:

```bash
python reagent_local.py run . --mode demo
```

Demo mode is explicit and every result is labelled fictional. Normal mode
never falls back to demo. Search sessions use literal loopback, last 15 minutes,
are scoped to the exact project/Package/Workflow, allow at most three
five-result searches, have no Progress capability, and close after research.
Post-round upload sessions last two minutes, bind the exact report round/ID/
content checksum, and have zero search calls or Provider budget. All token
plaintext remains process-local and is removed from the Codex subprocess
environment.

For explicitly unattended execution, add `--auto`:

```bash
python reagent_local.py run . --auto
python reagent_local.py run . --mode demo --auto
```

Auto mode preserves the same output, validation, report, upload, receipt, and
projection contracts, but uses the fixed bounded policy without owner input.
It is intended for CI, repeatable demonstrations, and explicitly requested
batch use; it is not the default owner experience.

## Terminal errors

Stage-labelled errors distinguish a missing or unauthenticated Codex CLI,
unsupported CLI version, missing interactive terminal, unavailable backend,
disabled normal-mode Provider, denied/expired local session, nonzero Codex
exit, invalid completion artifacts, and upload failure. The launcher never
prints credentials or complete sensitive URLs. A completed local report whose
upload fails remains pending for upload-only recovery.

## Known limits

Claude Code is Experimental / Untested. Only Literature Search exists. Public
deployment, production authentication, OAuth/SSO, multi-user authorization,
HTTPS termination, proof of possession, production secret management,
Hosted/cloud research execution and additional Providers or Workflows are
outside V0.1. Automatic upload is limited to the single locally produced
append-only report and never causes cloud research execution.
