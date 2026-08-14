# Qualification levels and non-substitution rules

Status: Owner-ratified policy; implementation not authorized

These are the labels that an engineering verification packet and the future
requirement-to-test ledger must use. The evidence level is a ceiling achieved
by the concrete test, not a property inferred from its directory name.

| Qualification label | Typical evidence | Required disclosure |
|---|---:|---|
| `UNIT` | E1 | isolated symbols, mocks, negative cases |
| `SCHEMA` | E1 | schema/version, valid and invalid golden inputs |
| `CONTRACT` | E1-E2 | authoritative source and compatibility surface |
| `SERVICE_INTEGRATION` | E3 | real collaborators versus mocks |
| `POSTGRESQL_INTEGRATION` | E4 | disposable DB identity and isolation proof |
| `MIGRATION` | E4 | upgrade path, sole head, data/schema assertions |
| `PUBLIC_API` | E4 | real route, auth profile, request/response/errors |
| `PUBLIC_WORKSPACE_COMMAND` | E5 | exact root command and durable file effects |
| `PTY` | E5 | terminal transport and first meaningful output |
| `FAKE_HARNESS` | E5 maximum | fake behavior and what it does not qualify |
| `CONTROLLED_BROWSER` | E6 | real controlled API, disposable dataset, viewport |
| `REAL_CODEX` | E7 | installed CLI, startup or full completion explicitly |
| `LONG_LIVED_WORKSPACE` | E8 | version history, preserved bytes, recovery path |
| `OWNER_MANUAL_UX` | E9 | bounded owner observation without private payloads |

## Entry conditions

- The test names its contract requirement and versioned surface.
- Data is disposable unless the level explicitly requires owner evidence.
- Database, Workspace, Provider, Harness, and network use are explicit.
- Required dependencies are already installed; qualification does not silently
  install tools or browsers.
- Expected negative, retry, and compatibility cases are selected from risk.

## Exit conditions

- The exact public or internal path exercised is recorded.
- Assertions cover externally meaningful state, not only implementation calls.
- Skips, timeouts, mocks, fake executables, and early termination are reported.
- Side effects and cleanup are verified.
- The result is attached to ledger test IDs and a highest evidence level.

## Non-substitution examples

```text
FAKE_HARNESS completion PASS != REAL_CODEX completion PASS
REAL_CODEX startup PASS != REAL_CODEX finalization PASS
internal readiness helper PASS != PUBLIC_WORKSPACE_COMMAND recovery PASS
synthetic legacy fixture PASS != LONG_LIVED_WORKSPACE compatibility PASS
frontend component mock PASS != CONTROLLED_BROWSER real-API PASS
SQLite or repository fake PASS != POSTGRESQL_INTEGRATION PASS
declared Playwright package != installed browser binary
```

Release reports must name both achieved and unachieved levels. A skipped
release-blocking level makes the claim `BLOCKED` rather than implicitly PASS.
