# R2A Progress Report Upload and Aggregation

Date: 2026-08-03
Status: **PASS_WITH_WARNINGS**
R2 state: **UPLOAD_ACCEPTANCE_PENDING**

## Outcome

R2A adds native immutable `progress-report/v0.2`, deterministic non-cyclic
identity, explicit raw context-before/context-after digests, safe v0.1
normalization, explicit upload envelopes, exact original-byte retention,
append-only cloud history, deterministic chain/conflict validation, project
progress projection, FastAPI upload/read endpoints, an explicit offline/upload
client, additive PostgreSQL migration, a v0.2 future package template/helper,
and network-free synthetic acceptance tests.

The application service and upload router contain no local research execution
hook. Uploaded content remains unexecuted data. The path cannot run/resume a
Workflow, call AgentRuntime/ExecutionDispatcher, call OpenAlex/LLM/structured
generation, create research outputs, or mutate local context.

## Identity and compatibility

The content checksum excludes all three identity fields. `report_id` is
`prv2-<SHA-256>` over package, Workflow/version, round, predecessor ID, and
content checksum. The final report checksum includes the ID/content checksum
and excludes only itself by canonicalizing it as null. Exact uploaded bytes
also receive a separate digest.

v0.1 bytes are retained and normalized with explicit assumptions,
unavailable fields, and evidence limitations. Its single context checksum is
kept only as legacy-ambiguous; no before/after values are fabricated. Executed
R1 evidence is not modified. Future generator output is package-template v0.2
and embeds v0.2 schema, deterministic helper, dynamic chain validation, and
`UPLOAD_ACCEPTANCE_PENDING`.

## Persistence and API

Migration `20260803_0003_progress_reports` adds append-only report receipt/
normalized metadata and a reconstructible projection table. Exact bytes use
existing `ArtifactContentStorage`. Progress metadata is separate from hosted
events/checkpoints.

Endpoints: explicit upload, history list, report read, original-byte download,
and project progress read under `/projects/{project_id}`. There is no
continue/run/resume route.

## Verification

- `python -m pytest -q backend/progress_reports/tests`: 38 passed, exit 0;
- `python -m pytest -q backend/workflow_packages/tests`: 43 passed, exit 0;
- `python -m pytest -q backend`: 282 passed, 19 skipped, exit 0;
- `python -m compileall -q backend`: exit 0;
- `alembic heads`: `20260803_0003 (head)`, exit 0;
- PostgreSQL progress/reload and mapping tests: collected but skipped because
  `REAGENT_TEST_DATABASE_URL` was not configured; no database was created or
  used;
- frontend: unchanged and untested; the optional local-progress view is the
  documented warning.

All 19 backend skips are environment-gated PostgreSQL/live acceptance tests.
The one new R2A PostgreSQL restart/reload test is among them. In-memory restart/
reconstruction and API persistence-boundary tests pass.

The optional Next.js display was deferred to avoid mixing uploaded local
progress with the preserved Hosted Mode UI. R2B must perform the external live
upload/idempotency/conflict/restart procedure in
`docs/acceptance/R2B_PROGRESS_UPLOAD_ACCEPTANCE.md`; it has not passed yet.

## R2A-C closure audit

The complete R2A working change set was reviewed from baseline `0c51f63`: 25
modified tracked files and 28 new files. Every file belongs to the approved R2A
contracts/normalization, ingestion/security/chain/projection, API, repository/
UoW, SQL mapping/migration, explicit client, future package v0.2, fictional-test
or documentation categories. No frontend file, real R1B report/package,
database file, credential or private execution evidence is part of the change
set.

The implementation audit confirms that native content identity removes only
the three identity fields, derives a version-namespaced deterministic report
ID, and computes the final checksum with only `report_checksum` represented as
null. Context checksums use exact `memory/context.md` bytes; equality represents
a locally asserted no-op and is not missing data, while the cloud does not
claim byte verification without a supplied snapshot. Missing predecessors are
retained as rejected `INCOMPLETE_CHAIN` evidence and remain an explicit R2B
acceptance case. Rejected/conflicting evidence never enters projection.

Closure regression results are unchanged: 38 focused Progress Report tests, 43
Workflow Package tests, and 282 full-backend tests passed; 19 environment-gated
tests skipped. Compilation succeeded and Alembic reports the single head
`20260803_0003`. PostgreSQL was not configured, so its persistence/restart tests
were not executed and must pass in R2B against a new isolated database. The
optional frontend remains deferred, Claude Code remains untested, R2B has not
started, and R2 remains `UPLOAD_ACCEPTANCE_PENDING`.

## Next milestone

**R2B — external Progress Report upload, idempotency, conflict and restart acceptance.**
