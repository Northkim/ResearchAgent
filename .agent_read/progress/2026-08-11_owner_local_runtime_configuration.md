# Owner local runtime configuration and secure startup

Date: 2026-08-11

The owner-local real-research gate now has product-level local startup UX
without changing Workflow, Artifact, Skill, Resource, Progress, Provider, or
database contracts. `make owner-setup` validates the passwordless loopback
PostgreSQL identity and sole migration, writes strict owner-only versioned TOML
to the user config directory, and invokes a secure macOS Keychain prompt for a
ReAgent-specific OpenAlex item. The config cannot contain the Provider key,
database passwords, Cloud/Workspace identities, or research state.

`make owner-start` uses that config plus Keychain inside a trusted helper,
gives the OpenAlex credential only to the Backend child, starts the existing
local-development/NORMAL-capable Backend and a scrubbed Frontend, waits for
readiness, and reports bounded URLs. It neither loads repository `.env` as
owner authority nor migrates the database. `make owner-doctor` safely reports
config/database/migration/Keychain/port readiness. `make stop` also stops the
separate owner PID/identity records but never PostgreSQL, config, Keychain, or
database state. `make dev` and `make controlled-start` retain their previous,
separate semantics; Provider credential availability still does not replace
per-run `continue-real-search` consent.

Unit qualification covers atomic/safe config, invalid versions/fields,
symlinks and permissions, Keychain prompt argv, initial/replace/remove flows,
missing setup/key/migration/ports, Backend-only sentinel isolation, doctor,
runtime mode separation and process identity. A fresh-shell smoke test used a
fake Keychain command and marker-guarded disposable PostgreSQL database to run
`make owner-start`, `make stop`, then `make owner-start` again with no ReAgent
exports. Backend/Frontend reached readiness, only Backend held the sentinel,
config/logs did not, and the generated database was dropped.

Final qualification passed the focused startup/security/NORMAL/Workspace set
`276 passed`, complete Backend `799 passed, 14 existing skips`, frontend Vitest
`17 files / 34 tests`, TypeScript, ESLint, scrubbed production build,
controlled Playwright `4 passed`, compileall, shell syntax, diff check and sole
Alembic head. No new skips were added. The owner database was queried read-only
before and after: eight Projects and the exact owner Project present both
times, delta zero. Every generated qualification database was dropped.

Migration remains `20260806_0017`; no migration is required. `project1` and
the owner Workspace were neither read nor modified. The owner may now perform
one-time `make owner-setup`, then use `make owner-start`, browse `/projects`,
and create a separate real-research Project.
