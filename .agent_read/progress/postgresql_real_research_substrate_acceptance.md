# Phase 9A-1.5 PostgreSQL Real-Research Substrate Acceptance

- Date: 2026-07-21
- Status: `PASS`
- Scope: PostgreSQL migration and ProviderOperation persistence acceptance only
- PostgreSQL: 18.1 (Homebrew)
- Isolated database: `reagent_9a1_acceptance`
- Migration head: `20260721_0002`
- Frozen architecture contract changed: no
- New ADR: none

## Outcome

Alembic revision `20260721_0002`, the SQLAlchemy
`ProviderOperationRepository`, its UnitOfWork integration, and the already
accepted budget/provenance semantics now pass real PostgreSQL acceptance. The
complete backend suite ran with every PostgreSQL and isolated HTTP integration
test enabled: `123 passed`, `0 skipped`.

The complete Guided Literature Review v2 workflow was not implemented. No real
provider, network request, credential, dependency, Docker resource, or frontend
change was introduced.

## Database safety

Before creation, PostgreSQL catalog inspection showed only the non-template
databases `postgres` and the unrelated `ProjectDB`. The target name did not
exist. The local identity and server were:

- client: `psql (PostgreSQL) 18.1 (Homebrew)`;
- server: `18.1 (Homebrew)`;
- role: `lifengguang`;
- address/port: `127.0.0.1:5432`;
- service: Homebrew `postgresql@18`, pre-existing PID 1011.

Creation command:

```text
createdb --host=127.0.0.1 --port=5432 --username=lifengguang \
  --maintenance-db=postgres --owner=lifengguang reagent_9a1_acceptance
```

Redacted SQLAlchemy URL:

```text
postgresql+psycopg://lifengguang:<password-omitted>@127.0.0.1:5432/reagent_9a1_acceptance
```

Every migration, test, inspection, and application command targeted that exact
database. No command named, connected to, migrated, truncated, or dropped
`ProjectDB`. Final catalog inspection still showed `ProjectDB` at 8,552,975
bytes. The acceptance database is retained at head at 9,746,111 bytes
(approximately 9.3 MiB).

## Migration evidence

### First base to head

Command:

```text
REAGENT_DATABASE_URL=<isolated-url> \
  conda run --no-capture-output -n reagent-dev alembic upgrade head
```

Exit `0`. Alembic reported transactional PostgreSQL DDL and applied:

```text
-> 20260721_0001
20260721_0001 -> 20260721_0002
```

`alembic current` returned `20260721_0002 (head)`. Static `alembic heads`
returned the same single head.

### Schema inspection

Direct PostgreSQL catalog inspection found 30 `provider_operations` columns.
The database contains:

- primary key `id`;
- unique `(project_id, idempotency_key)`;
- composite project/run foreign key to
  `workflow_runs(project_id, id)` with cascade delete;
- composite run/StepRun foreign key to
  `workflow_step_runs(workflow_run_id, id)`;
- status, settlement-state, nonnegative reservation/retry/domain-version, and
  positive persistence-version checks;
- non-unique indexes for run/creation, status/update, and
  provider/failure/creation;
- the two revision-0002 artifact indexes for run/kind/creation and
  project/checksum.

PostgreSQL shortens the generated long check-constraint identifiers to its
63-byte identifier limit. This is naming-only: Alembic metadata comparison
matched the installed constraints exactly.

### First drift check

`alembic check` exited `0` with:

```text
No new upgrade operations detected.
```

### Head to base

`alembic downgrade base` exited `0`, applying `0002 -> 0001 -> base`.
Post-downgrade catalog inspection showed only an empty `alembic_version` table;
all application tables were removed.

### Base to head replay

The second `alembic upgrade head` exited `0` and reapplied both revisions in
order. The second `alembic check` also exited `0` with no new upgrade
operations.

Migration `20260721_0002` required no remediation. Migration `0001` was not
edited.

## Provider-operation contract evidence

The shared InMemory/SQL contract now verifies:

- create and reconstruct a `RESERVED / UNSETTLED` operation;
- persist reservation before simulated provider execution;
- exact idempotent replay returns the existing operation and does not reserve
  twice;
- conflicting project-scoped idempotency reuse raises
  `DuplicateEntityError`;
- `RESERVED -> RUNNING -> SUCCEEDED / SETTLED` with actual zero-cost usage;
- pre-call failure produces `FAILED / RELEASED` with no usage;
- post-call failure produces `FAILED / SETTLED` with actual usage;
- normalized diagnostic metadata persists without a raw response;
- hard request-budget overage raises `BudgetExceededError` before staging a
  second operation;
- a fresh UnitOfWork sees interrupted/unsettled operations;
- two independent sessions loading persistence version 1 race; the first
  update commits and the second raises normalized `StaleStateError`;
- an update that does not advance the logical `row_version` is rejected before
  commit;
- a provider transition plus a WorkflowRepository update both disappear on
  rollback;
- cross-project run association and cross-run StepRun association are rejected
  by PostgreSQL foreign keys and normalized at the UnitOfWork boundary;
- the final database reflects only the concurrency winner;
- a provenance manifest reconstructed with a persisted unsettled operation is
  non-publishable with `UNSETTLED_PROVIDER_OPERATION`.

One narrow defect was found in the application service: although the immutable
contract and repository already supported sanitized diagnostics,
`ProviderOperationService.settle_failure()` did not accept/pass them. An
optional `diagnostic_metadata` argument now forwards the normalized mapping to
the existing contract. This is backward compatible and does not alter any
status, settlement, repository, or persistence-port semantics.

## Test evidence

### Focused fast contract tests

```text
conda run --no-capture-output -n reagent-dev pytest -q \
  backend/persistence/tests backend/research/tests
```

- exit: `0`
- result: `47 passed in 0.11s`
- wall time: approximately 1.39 seconds
- PostgreSQL: not used by this command

### Focused real PostgreSQL adapter tests

```text
REAGENT_TEST_DATABASE_URL=<isolated-url> \
  conda run --no-capture-output -n reagent-dev pytest -q \
  backend/database/tests -rs
```

- exit: `0`
- result: `13 passed in 0.77s`
- skipped: `0`
- wall time: approximately 2.03 seconds
- fixture cleanup: each test truncates only the designated isolated schema

Before coverage remediation, the original suite also ran successfully as
`8 passed in 0.52s`; the 13-test result is authoritative for acceptance.

### Full backend with all PostgreSQL tests enabled

```text
REAGENT_DATABASE_URL=<isolated-url> \
REAGENT_TEST_DATABASE_URL=<isolated-url> \
REAGENT_E2E_DATABASE_URL=<isolated-url> \
REAGENT_ALLOW_DATABASE_RESET=1 \
  conda run --no-capture-output -n reagent-dev pytest -q backend -rs
```

- exit: `0`
- result: `123 passed in 1.59s`
- skipped: `0`
- wall time: approximately 2.75 seconds
- persistent effect: the explicitly destructive isolated HTTP integration test
  replayed migrations and retained one deterministic demo workflow/run

### Compile and migration commands

```text
conda run --no-capture-output -n reagent-dev python -m compileall -q backend
```

Exit `0`, no output, approximately 0.90 seconds.

```text
conda run --no-capture-output -n reagent-dev alembic heads
```

Exit `0`: `20260721_0002 (head)`.

Two real-database `alembic check` executions each exited `0` and reported no
pending operations. A third redundant post-suite launch was rejected by the
tool approval transport before the command process was created; it changed no
state and is not counted as validation evidence.

Frontend regressions were not run because no API/DTO, shared generated type,
frontend source, or Node dependency changed.

## Files changed in Phase 9A-1.5

Source:

- `backend/research/services/budget.py`

Tests:

- `backend/persistence/tests/adapter_contracts.py`
- `backend/persistence/tests/test_adapter_contracts.py`
- `backend/database/tests/test_postgresql_persistence.py`

Documentation:

- `.agent_read/context.md`
- `.agent_read/progress/postgresql_real_research_substrate_acceptance.md`

No migration, persistence port, ORM model, dependency file, frontend file, or
environment configuration was changed in this phase.

## Cleanup state

- no pytest, FastAPI/Uvicorn, Next.js, Playwright, Chromium, or acceptance
  process remains;
- no listener remains on ports 3000, 8000, or former temporary port 55439;
- only the pre-existing Homebrew PostgreSQL service listens on 5432;
- the acceptance database remains at `20260721_0002` for review;
- database test fixtures removed their ProviderOperation rows; the HTTP
  integration left one deterministic workflow definition and one completed
  run, as expected for retained acceptance evidence.

Optional destructive cleanup, not executed:

```text
dropdb --host=127.0.0.1 --port=5432 --username=lifengguang \
  reagent_9a1_acceptance
```

That command is appropriate only after the owner no longer needs the retained
acceptance database. It must never be changed to target `ProjectDB`.

## Architecture and readiness

No frozen ownership boundary, Domain lifecycle, Workflow Engine decision
ownership, Skill System ownership, ProviderOperationRepository port, or
settlement lifecycle changed. No ADR was created. The optional diagnostic
argument completes an already-accepted data path.

ReAgent is ready to enter **Phase 9A-2: Complete Deterministic Fake-Provider
Guided Literature Review v2 Vertical Slice**. Its PostgreSQL entry gate is now
satisfied. Phase 9A-2 must retain fake-only, zero-cost, no-network defaults and
keep real providers, credentials, workers, authentication, Docker remediation,
and production storage out of scope.
