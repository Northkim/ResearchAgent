# ADR 0018: Safe Persistent Local Dotenv Startup

- **Status:** Accepted
- **Date:** 2026-08-06
- **Scope:** ReAgent V0.1 local database configuration only
- **Supersedes:** the no-dotenv startup detail in ADR 0017
- **Governing decisions:** ADR 0009 and ADR 0017

## Context

MVP-I introduced `make dev` and correctly kept PostgreSQL lifecycle outside the
application. Its startup script required `REAGENT_DATABASE_URL` only from the
invoking process environment, even though the repository-root `.env` is already
ignored and is the intended persistent local configuration. Owners therefore
had to export or source the same value in every terminal session.

Blindly sourcing `.env` would make arbitrary shell syntax executable and would
unnecessarily load unrelated credential-bearing variables. The correction must
retain PostgreSQL-only, loopback-only and ProjectDB rejection and must not print
the selected URL.

## Decision

Local V0.1 startup resolves only `REAGENT_DATABASE_URL` with this precedence:

1. an existing invoking-process environment value;
2. the file selected by `REAGENT_ENV_FILE`;
3. the ignored repository-root `.env`.

An exported value prevents any dotenv read. Otherwise, a small Python parser
reads a strict non-interpolating assignment subset: blank and comment-only
lines, `KEY=value`, `KEY="value"`, and `KEY='value'`. It validates every line,
rejects duplicates, malformed quoting and control characters, and treats shell
command syntax as literal data. It does not source, evaluate, interpolate, or
invoke dotenv content. Only the database URL is returned to the startup shell;
unrelated dotenv keys are not imported.

The startup shell does not log the URL. After resolution it retains the
existing SQLAlchemy validation for PostgreSQL scheme, literal loopback host and
non-ProjectDB identity. It verifies that the already-created database is
reachable before running Alembic. Missing/malformed configuration and database
unavailability are distinct fail-closed errors.

## Consequences

- One-time local setup is database creation plus an ignored root `.env`.
- Normal use is `make dev` and `make stop` without repeated shell exports.
- Explicit exported configuration remains available for automation and has
  highest priority.
- `REAGENT_ENV_FILE` supports an alternate local configuration file without a
  global shell-profile dependency.
- The application still never creates, resets, deletes, starts, or stops
  PostgreSQL.
- Owner `.env` contents remain ignored, untracked, unprinted, and absent from
  evidence and commits.
- No backend/frontend product logic, migration, schema, Package, Progress,
  Provider, Proxy, Hosted Runtime, or production boundary changes.

## Alternatives considered

- Require repeated `export` or `source` commands: rejected as the usability
  defect this decision corrects.
- Use unrestricted `source .env`: rejected because dotenv data would become
  executable shell code.
- Add `python-dotenv`: rejected because the repository has no such dependency
  and this single-key boundary needs only a small strict parser.
- Put configuration in `~/.zshrc`: rejected because project configuration must
  remain local, explicit, and shell-independent.
- Manage PostgreSQL automatically: rejected because application scripts cannot
  safely own or identify unrelated local database services.
