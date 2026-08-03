# R2B External Progress Upload Acceptance Report

Date: 2026-08-03
Baseline: `6fa19476c6effe58f58ade2cd294a89b77df8807` on `main`
Result: **PASS_WITH_WARNINGS**
R2 state: **UPLOAD_ACCEPTED**

## Scope and authority

This acceptance exercised the committed R2A path and made no production-code,
frontend, migration, contract, repository, or package-generator change. The
teacher architecture, ADR 0009, R1 evidence, and committed R2A documents remain
the authority: a local folder and external Agent Harness own concrete research
execution and state; cloud code may receive, retain, validate, and aggregate
Progress Reports but may not continue the research task.

All acceptance content was fictional. No research Workflow, AgentRuntime,
ExecutionDispatcher, OpenAlex client, research provider, LLM, structured
generation, hosted judge, approval execution, or external research API was
invoked. Only loopback HTTP was used.

## Initial Git gate

- `git rev-parse HEAD`: exact required baseline
  `6fa19476c6effe58f58ade2cd294a89b77df8807`.
- `git branch --show-current`: `main`.
- `git status --short` and `git status --porcelain=v1`: empty.
- `git diff --check`: exit 0.
- Baseline message: `R2A: add progress report ingestion and projection infrastructure`.

The gate passed before any runtime material was created. All package, database,
artifact, log, response, and fixture material remained outside Git.

## Isolated PostgreSQL qualification

PostgreSQL `18.1 (Homebrew)` on `aarch64-apple-darwin25.0.0` was initialized as
a new disposable cluster under `<isolated-postgresql-data-dir>`. It used data
page checksums, UTF-8, locale-independent initialization, trust authentication
inside the isolated cluster, loopback binding only, a unique high port `50769`,
and its own `pg_ctl` process. It did not use or contact an existing PostgreSQL
service.

Two fresh databases were created:

- live HTTP acceptance: `reagent_r2b_acceptance_20260803_50769`;
- automated PostgreSQL tests: `reagent_r2b_tests_20260803_50769`.

Sanitized URLs are
`postgresql+psycopg://127.0.0.1:50769/reagent_r2b_acceptance_20260803_50769`
and
`postgresql+psycopg://127.0.0.1:50769/reagent_r2b_tests_20260803_50769`.
They contained no password. Catalog inspection returned zero databases named
`ProjectDB`; ProjectDB was not accessed.

Migration evidence against the live acceptance database:

- `alembic heads` -> one head, `20260803_0003 (head)`;
- `alembic upgrade head` -> `20260420_0001` -> `20260420_0002` ->
  `20260803_0003`, exit 0;
- `alembic current` -> `20260803_0003 (head)`, exit 0;
- `alembic check` -> `No new upgrade operations detected.`, exit 0.

Direct schema inspection found `uploaded_progress_reports`,
`project_progress_projections`, artifact metadata and all preserved Hosted Mode
tables. Initial progress, projection, execution-event, checkpoint,
memory-revision and provider-operation row counts were zero. This proves the
live server used PostgreSQL metadata persistence rather than an in-memory
repository.

## External Workflow Package

The committed package compiler generated a fresh package under
`<external-package-root>`, outside the repository. A first untouched trial
build was not used. The acceptance build was validated and captured its first
context-before checksum before task-state consumption.

- fictional project: `fictional-r2b-native-20260803`;
- package ID: `literature-search-fictional-r2b-native-20260803-v0.2`;
- package schema: `workflow-package/v0.1`;
- package-template version: `0.2.0`;
- package checksum:
  `sha256:0818f17646d2176b1f900b030db8e5d424160261e591c34abc233d67c7bb6a62`;
- manifest checksum:
  `sha256:73102913c71a3a50c8e45191bebb848b7cd289507c17368427b241390820e6bf`;
- ZIP checksum:
  `sha256:38ad71c8e10d2735a819cfbad14c70372a199cd3b8f77a211ab18dd40dfc9f7a`.

The bundled validator and repository validator both returned `PASS`. The four
minimal output files explicitly stated that they were synthetic transport
evidence and that no external search occurred. No real R1B report, output,
path, or private data was copied.

The package helper generated this native chain:

| Field | Round 1 | Round 2 |
|---|---|---|
| report ID | `prv2-50feb4cab24d390c3936c6889022355ce46d39a11a45613fdba73cf5c86441c6` | `prv2-4e6cc5ca382c505c55cf13f8dd0700e70731f8019154c00d949cc9b73c7c2800` |
| content checksum | `sha256:b1c2b2b18d35186981e07fdfa94efa9c162a42966fee7f2cd7b9d235f8206577` | `sha256:5d11078854719a9f383a5bdbfe419968a8c4f0916835405127a22b65959bfbdd` |
| report checksum | `sha256:155efad67cb3dbd430801f2b80f760b6aa8fa388136c9c6ca043e34adf9caf91` | `sha256:22c86028290c721a5272f734ea2aa811ce6ff45be3ca98e7de6179e8e66ba169` |
| original-byte checksum | `sha256:25c369996f925995a376dfad73d01cf11f31d171aaf8fca1b0fe2c77aeb6f462` | `sha256:bae2df98d8c696f07ccf3643b8f8cff205cebe6d094477931881a05b8c020f77` |
| context before | `sha256:13f38bbdc2bdd138d6ef36caeec188470a511197de28a711eb10b8fb839204b5` | `sha256:ef2272b6639e3f1c0e22c0a541ee63ab339f0326f6a3a082e046b7bf250535d1` |
| context after | `sha256:ef2272b6639e3f1c0e22c0a541ee63ab339f0326f6a3a082e046b7bf250535d1` | `sha256:f90a1be8b0403d345dc151dac74b257c71ad3e780fcf0f13924f75638bd8e327` |
| status | `IN_PROGRESS` | `COMPLETED` |

Round 2 names the exact round-1 report ID/checksum, and its context-before
checksum equals round 1 context-after. Both committed offline-client validation
commands returned `validation=PASS` and `upload_ready=true`.

`PACKAGE_PRE_UPLOAD_MANIFEST` bound 29 relative paths, byte sizes, and content
SHA-256 values. Its canonical digest was
`sha256:e07b471a2bf818e3ee7ba7e4207169becb8f87ab369635f915f932f13af62927`.

## Live HTTP and persistent artifact storage

The committed ASGI entrypoint ran through Uvicorn on `127.0.0.1:51719`. Its
environment selected the live acceptance database, the fake paper-search
adapter, no provider credentials, and `<persistent-artifact-root>` outside Git.
The same artifact root was reused without alteration across restart.

The committed CLI performed explicit `validate` and `upload` commands. The
core path used actual HTTP requests; no FastAPI TestClient, mock transport, or
in-memory repository was used. Direct PostgreSQL row inspection confirmed that
each retained upload created SQL metadata. Server logs contained loopback
method/path/status lines only; they contained no request bodies, credential,
secret canary, package absolute path, or private content.

## Native v0.2 upload and projection

Round 1 returned HTTP 201, `VALID_CHAIN`, and receipt
`progress-receipt-fc8824b2fb56ef63357cfdf18c61368ef3ce833f56d843b1eea2f54016ef5e50`.
Its normalized read, list read, original read, and projection read succeeded.
The downloaded original was byte-identical at 3291 bytes.

Round 2 returned HTTP 201, `VALID_CHAIN`, and receipt
`progress-receipt-8dcc0036c11a1f6e49a83b8696229247ff0b20d42e5f67c56ded6faecb6fe4dc`.
Its original was byte-identical at 3400 bytes. History advanced from one to two
accepted reports, and the deterministic projection advanced to round 2 with
checksum
`sha256:8313cd40459aa9ba4fd40df353f4ff5818dbe8285f088e5e15569748cd50b52b`.
Normalized records remained linked metadata and did not replace original
bytes.

After the two native uploads, PostgreSQL held two report rows, one projection,
and exactly one accepted native round-2 record. Artifact storage held two
content-addressed originals.

## Package non-mutation

After validation, native uploads, replay, legacy upload, conflict/rejection
tests, both process restarts, retrievals, and post-restart replay,
`PACKAGE_POST_UPLOAD_MANIFEST` again contained the same 29 paths, sizes, and
hashes. Its canonical digest remained
`sha256:e07b471a2bf818e3ee7ba7e4207169becb8f87ab369635f915f932f13af62927`.

`PACKAGE_PRE_UPLOAD_MANIFEST == PACKAGE_POST_UPLOAD_MANIFEST` was true. No
instruction, manifest, input, context, draft, report, output, or checksum file
was changed by cloud interaction.

## Sequential and concurrent idempotency

Sequential exact replay of round 2 returned HTTP 200,
`idempotent_replay=true`, the original receipt, original timestamps, and the
same receipt checksum. Two concurrent independent real HTTP requests also both
returned HTTP 200, `idempotent_replay=true`, and that same receipt.

Before and after the replay checks, the native scope retained two rows, one
accepted round-2 row, two artifact objects, and the same projection checksum.
No duplicate accepted history, artifact, effective round, or projection was
created.

Post-restart exact replay produced the same result. At final observation there
were nine total retained reports, four accepted reports, three projections,
and one accepted native round-2 row; replay changed none of those counts.

## Legacy v0.1 compatibility

A separate wholly fictional legacy report was created outside Git and uploaded
over the same live HTTP server under a separate project/package identity. It
used the committed v0.1 self-checksum convention.

- report ID: `round-001`;
- report checksum:
  `sha256:415c8b333dd372a327dd6d35669905b8415506b9998637ade8c6e02862dd3b12`;
- original-byte checksum:
  `sha256:b90489b3deb94c813bef775fd05e4b0c856c8dfe1a6f91ae0c44b16148291f6a`;
- receipt:
  `progress-receipt-306fcc04dc0aa4a28ba09e6b8d2644b9ccdb15590e3e56b80457268492b57ca0`;
- result: HTTP 201, `LEGACY_CHAIN_WITH_WARNINGS`, accepted projection, seven
  compatibility/evidence warnings.

The original bytes were exact. Source schema remained `progress-report/v0.1`
and normalizer version remained `reagent-progress-normalizer/0.2.0`. The
ambiguous checksum appeared only as `legacy_context_checksum`. The normalized
record left `context_before_checksum`, `context_after_checksum`, Workflow
checksum, Harness version/session, report-content checksum, Skill pins, and
template pins absent or empty. It was not represented as native v0.2. The
separate legacy projection correctly carried its warning state.

## Conflict and rejection matrix

Each safe retained conflict was read by its receipt ID, returned exact original
bytes, remained `REJECTED`, and left native projection checksum
`sha256:8313cd40459aa9ba4fd40df353f4ff5818dbe8285f088e5e15569748cd50b52b`
unchanged.

| Case | HTTP / state | Receipt and observed SQL effect |
|---|---|---|
| Same report ID, different safe bytes | 409 `IDENTITY_CONFLICT` | `progress-receipt-641b683d47a35e02f4823aa55a7dd40e5d306b171e6b25e6e9bd490988401dcd`; first pass changed total rows 3 -> 4, accepted count stayed 3. A temporary evidence-runner response parser then failed; exact replay retrieved the same retained row and added nothing. |
| Different valid identity in round 2 | 409 `BRANCHED_HISTORY` | `progress-receipt-63192b926e4bef22456eed472387d1378812f45a48f4b8a1bae4d3c7728f69b8`; rows 4 -> 5, accepted unchanged. |
| Existing predecessor ID, wrong checksum | 409 `IDENTITY_CONFLICT` | `progress-receipt-d7b67c9d04c1404c4fca7b715a8e3ad08286fb441f99e9dcd2ee1e8e690ee6ed`; rows 5 -> 6, accepted unchanged. |
| Context discontinuity | 409 `CONTINUITY_CONFLICT` | `progress-receipt-765ab99038217bccc3a116a3c0984d5620d1b736844c05b36252bcd6a16d0aa6`; rows 6 -> 7, accepted unchanged. |
| Missing predecessor child | 422 `INCOMPLETE_CHAIN` | `progress-receipt-9134b62036612a36e3aaacefb25e6288edde620a3f448826e819769cd60bc8c7`; rows 7 -> 8, accepted unchanged, no projection. |
| Unsafe fictional secret-like canary | 422 security rejection | rows remained 9, no receipt, no artifact, no projection. The canary value is intentionally omitted from this report. |

The valid missing-case predecessor then returned HTTP 201 with receipt
`progress-receipt-4827aad148f8333b2d683027c7ed2d79c0d39ad518c31fa2de23122e9b4959b4`.
That separate project changed from one rejected row to two total/one accepted
row and gained a round-1 projection with checksum
`sha256:9c03b449d6da6ab9f736046bbe8b00b0e01733346162427ee51de65db074a042`.

The earlier child was not automatically re-evaluated. Exact child replay
returned the same receipt and HTTP 422 `INCOMPLETE_CHAIN`, added no row, and
did not advance the projection. No explicit recovery endpoint exists. This is
the committed permanent non-reevaluation behavior and remains a warning; it did
not corrupt accepted progress.

Final progress storage held nine immutable originals. Before and after restart,
their aggregate relative-path/size/content manifest was
`sha256:a7a4836bc62761fa5ee07e4ec829a051162b2b96f3acd1b1f7c469e344e06f4c`.

## Restart recovery

Before restart, a canonical HTTP snapshot captured all accepted report IDs and
receipts, all rejected receipts, original checksums, normalized-record
checksums, validation/chain states, complete projection JSON, projection
checksums, row counts, and latest native round. The snapshot was 11,306 bytes.

The FastAPI server stopped cleanly. The dedicated PostgreSQL cluster then
stopped cleanly and `pg_ctl status` reported no server. The same cluster was
restarted from the retained data directory; the same acceptance database and
unchanged artifact root were reused; FastAPI was restarted on the same
loopback port.

The post-restart canonical HTTP snapshot was exactly equal to the pre-restart
snapshot, including all normalized checksums, history, rejected receipts,
projection JSON, and projection checksums. All nine originals were fetched by
receipt after restart; every size and SHA-256 matched. The legacy record and
warning projection were unchanged. No rejected report entered a projection.
The artifact manifest was unchanged. Post-restart accepted-report replay
remained idempotent.

## Runtime and provider boundary evidence

The focused boundary suite statically asserts that the upload service has no
AgentRuntime, ExecutionDispatcher, OpenAlex, or structured-generation import;
the router has no run/resume/dispatch call; and projection has no LLM/provider
hook. It passed 3 tests.

Direct isolated PostgreSQL counts after all uploads were:

- `uploaded_progress_reports=9` and accepted reports `=4`;
- `project_progress_projections=3`;
- `execution_events=0`;
- `checkpoints=0` and `checkpoint_records=0`;
- `memory_revisions=0`;
- `workflow_runs=0` and `workflow_step_runs=0`;
- `provider_operations=0`.

The external package manifest was unchanged. Progress Reports therefore stayed
separate from ExecutionEvent/Checkpoint semantics and uploaded bytes remained
unexecuted data.

## Tests and skips

All commands used Conda environment `reagent-dev`.

- `python -m pytest -q backend/database/tests/test_progress_report_postgresql.py`:
  **1 passed**, 0 skipped, exit 0.
- `python -m pytest -q backend/database/tests/test_postgresql_persistence.py`:
  **13 passed**, 0 skipped, exit 0.
- `python -m pytest -q backend/progress_reports/tests`: **38 passed**, exit 0.
- `python -m pytest -q backend/progress_reports/tests/test_boundary.py`:
  **3 passed**, exit 0.
- `python -m pytest -q backend/workflow_packages/tests`: **43 passed**, exit 0.
- `python -m pytest -q -rs backend` with the isolated test database:
  **297 passed, 4 skipped**, exit 0.
- `python -m compileall -q backend`: exit 0, no output.
- post-restart `alembic heads`, `current`, and `check`: exit 0, sole current
  head `20260803_0003`, no model drift.

The four full-suite skips are unrelated opt-in integration gates:

1. destructive isolated HTTP/PostgreSQL demo requires
   `REAGENT_E2E_DATABASE_URL` and explicit reset permission;
2. 9B-1 OpenAlex contract requires its isolated database/artifact root;
3. 9B-1 live OpenAlex requires explicit live authorization and a narrow query;
4. 9A-2 hosted research v2 requires its isolated database/artifact variables.

No R2B PostgreSQL test skipped. Frontend tests were not required because no
frontend source changed.

## Security, cleanup, and retained warnings

Unsafe content was rejected before artifact retention. All evidence is
fictional. Tracked evidence contains no credential, API key, password, real R1B
package/report/output, private research content, local home path, PostgreSQL
data path, artifact path, or package absolute path. Runtime paths are represented
only by `<external-package-root>`, `<isolated-postgresql-data-dir>`, and
`<persistent-artifact-root>`.

After verification, FastAPI shut down cleanly and its port was bindable again.
The dedicated cluster shut down cleanly and `pg_ctl status` reported no server.
No existing PostgreSQL service or database was modified or stopped.

Warnings retained after successful acceptance:

- optional frontend view remains deferred;
- Claude Code compatibility remains untested;
- production authentication/signing is `SOURCE_UNDECIDED`;
- multi-user authorization is `SOURCE_UNDECIDED`;
- without a supplied context snapshot, cloud cannot independently verify that
  equal before/after checksums describe a true no-op;
- missing-predecessor evidence is not automatically re-evaluated and has no
  explicit recovery route.

## Final gate

```text
R2B_ACCEPTANCE = PASS_WITH_WARNINGS
POSTGRESQL_ACCEPTANCE = PASS
EXTERNAL_HTTP_UPLOAD_ACCEPTANCE = PASS
ORIGINAL_BYTE_RETENTION_ACCEPTANCE = PASS
PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
IDEMPOTENCY_ACCEPTANCE = PASS
CONFLICT_RETENTION_ACCEPTANCE = PASS
RESTART_ACCEPTANCE = PASS
RUNTIME_PROVIDER_BOUNDARY = PASS
R2B_GIT_CLOSURE = PASS
R2_STATE = UPLOAD_ACCEPTED
R2_COMPLETE = PASS_WITH_WARNINGS
```

R2B is complete with the listed warnings. R3 was not begun or recommended.
The next action is owner review.
