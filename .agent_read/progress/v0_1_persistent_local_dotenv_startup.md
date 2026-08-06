# MVP-I1 Persistent Local Dotenv Startup

Date: 2026-08-06

Status: **PASS — OWNER ACCEPTANCE PENDING**

## Baseline and defect

MVP-I1 began from clean `main` at exact commit
`acbd91a24eefee1b7123eff4821b9ac3db7dee78`
(`MVP-I: integrate local Package and Progress product flow`). The ignored owner
`.env` existed, but `scripts/dev-start.sh` rejected a missing process-exported
`REAGENT_DATABASE_URL` before reading any persistent local configuration.

## Correction

Accepted ADR 0018 establishes exported value, custom `REAGENT_ENV_FILE`, then
repository `.env` precedence. `scripts/local_startup_config.py` parses a strict
dotenv subset without sourcing, evaluation, interpolation, or command
execution. It returns only the database URL to the startup process and never
logs it. Existing PostgreSQL, loopback and ProjectDB checks run after loading.

Startup now distinguishes configuration loading/validation failure from an
unavailable or nonexistent local database. It still performs no PostgreSQL
lifecycle management; the owner creates the persistent database once and
`make dev` only checks readiness and applies Alembic migrations.

## Qualification

- focused startup configuration tests: 14 passed;
- repository root `.env` loading: passed;
- exported-value precedence: passed without reading malformed `.env`;
- custom `REAGENT_ENV_FILE`: passed without reading repository `.env`;
- missing/malformed/duplicate/quoted/comment handling: passed;
- command substitution and backtick canaries: literal, zero marker files;
- non-loopback and ProjectDB rejection: passed;
- `.env` ignored and untracked: passed;
- Bash syntax and Python compile checks: passed;
- ShellCheck: unavailable in repository tooling/environment;
- `git diff --check`: passed.

A real smoke used `env -u REAGENT_DATABASE_URL -u REAGENT_ENV_FILE` so no
manual export or alternate file could satisfy startup. `make dev` reported only
that repository `.env` supplied local database configuration, applied the
current migrations to the already-created database, and brought FastAPI and
Next.js to readiness on unique loopback ports. `make stop` released both
application ports, reported PostgreSQL untouched, and the dedicated runtime
directory was removed. The owner `.env` value was never displayed, copied, or
recorded.

```text
MVP_I1_IMPLEMENTATION = PASS
REPOSITORY_DOTENV_LOADING = PASS
EXPORTED_ENV_PRECEDENCE = PASS
CUSTOM_ENV_FILE_SUPPORT = PASS
DOTENV_COMMAND_EXECUTION_SAFETY = PASS
DATABASE_SAFETY_CHECKS = PASS
MAKE_DEV_WITHOUT_MANUAL_EXPORT = PASS
DOTENV_GIT_EXCLUSION = PASS
V0_1_STATE = OWNER_ACCEPTANCE_PENDING
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

No backend/frontend product behavior, migration, schema, Package, Progress,
Provider, Proxy, Hosted Runtime, public deployment, production authentication,
or R3D change occurred. Wait for owner review.
