# Phase 9A-1 Real Research Contract Substrate

- Date: 2026-07-21
- Status: `PASS_WITH_WARNINGS`
- Target workflow: `guided-literature-review@2.0.0`
- Scope: provider-independent contracts, persistence, and local artifacts
- Real network/provider calls: none
- Dependency changes: none

## Outcome

Phase 9A-1 implements the provider-independent foundation approved by ADR 0003.
The backend can now represent, validate, store, budget, audit, and inject the
building blocks of a grounded literature review without choosing or contacting
a real paper-search or LLM vendor.

The milestone is `PASS_WITH_WARNINGS`, rather than an unconditional pass,
because the new PostgreSQL migration and shared SQL provider-operation contract
could not be executed without an explicitly designated isolated database. All
non-PostgreSQL tests and the full fast backend regression suite pass.

## Accepted ADR scope

ADR `.agent_read/decisions/0003-real-research-provider-and-artifact-boundaries.md`
is now Accepted only for these additive changes:

1. `UnitOfWork.provider_operations` exposes a
   `ProviderOperationRepository`.
2. `WaitingApproval.resolved_inputs` carries values resolved by Workflow
   Engine.
3. Artifact bytes cross an `ArtifactContentStorage` port; database records hold
   metadata and relative keys.
4. Provider SDK/client construction remains in infrastructure adapters and
   composition; Skills receive explicitly granted ports.
5. Provider usage and budget reservation/settlement state are durable and
   auditable.

Acceptance does not choose a paper provider, LLM provider/model, price, key,
live mode, S3 backend, or retention policy. Domain lifecycle legality and the
frozen ownership boundaries did not change.

## Research contracts

`backend/research/contracts/` contains frozen dataclasses with deterministic
JSON serialization and `sha256:` canonical hashing:

- `ResearchQuery`;
- `PaperAuthor` and normalized `PaperRecord`;
- `SourceContent`, including explicit metadata/abstract/full-text scope and
  access limitation;
- `RankedPaper` and inclusion status;
- `CitationReference` using `[P1]`, `[P2]`, ... labels;
- `EvidenceUnit` and `GroundedClaim`;
- `ResearchReport`;
- `ProviderUsage`, `ProviderReservation`, and `ProviderBudget`;
- `ProviderOperation` and its lifecycle enums;
- `ProviderVersion` and `ProvenanceManifest`.

All persistent mappings are recursively frozen, timestamp fields require
timezone awareness, DOI values are normalized, SHA-256 values are shape
validated, and no contract imports SQLAlchemy, FastAPI, provider SDKs, or local
absolute paths. Monetary limits use integer minor units and one explicit
currency (`USD` by the milestone defaults), never binary floating point.

## Provenance validation

`ProvenanceValidator` is a pure fail-closed service. A manifest is publishable
only when all error-level issues are absent. It verifies:

- every provenance and report citation resolves to a selected `PaperRecord`;
- every evidence unit resolves to a paper and checksum-matched source object;
- substantive claims contain existing, bidirectionally linked evidence;
- normalized DOI values, paper IDs, citation IDs/labels, evidence IDs, and
  claim IDs are not duplicated;
- abstract evidence/report scope is never represented as full-text review;
- report labels and reference objects match canonical citations;
- workflow, Skill, prompt, provider, adapter, and model/endpoint versions are
  recorded;
- report/provenance artifact IDs have checksum links and point to one another;
- reserved, running, or otherwise unsettled provider operations block
  publication;
- at least three ranked papers are selected under the approved default.

Validation returns immutable typed issues and an explicit publishable result;
it does not mutate `WorkflowRun` or invoke Domain transitions.

## Provider ports and deterministic adapters

`backend/research/ports/` defines asynchronous, vendor-neutral interfaces:

- `PaperSearchProvider` returns normalized papers, identity, request
  fingerprint, timestamp, warnings, and usage;
- `SourceContentProvider` returns permitted content with source provenance and
  explicit limitations;
- `LLMProvider` separates text and structured generation, carries prompt and
  response-schema identity, deadline/cancellation context, normalized errors,
  actual provider identity, request reference, and usage;
- `ArtifactContentStorage` writes/reads/opens immutable bytes and verifies
  checksums and sizes.

No embedding port was added. Ports do not read environment variables.

`backend/research/adapters/fake_providers.py` implements stable synthetic
search, abstract retrieval, and LLM adapters. They use no network or
credentials, expose fixed versions, return zero-cost usage, support
configurable normalized failures and cancellation, replay identically for the
same request, and never call abstract-only content full text. All paper titles,
authors, abstracts, and generated statements are synthetic.

## Local artifact storage and application gateway

`LocalFilesystemArtifactStorage` takes an injected root. The default intended
composition root is the exported `runtime_data/artifacts`; tests inject
isolated temporary roots.

The adapter:

- accepts only clean relative POSIX keys;
- rejects absolute keys, `..`, backslashes, and symbolic-link traversal;
- creates a same-directory temporary file, flushes/fsyncs it, verifies its
  checksum, and atomically claims a new immutable path with a hard link;
- treats replay of identical bytes as idempotent;
- rejects a different body at the same immutable key;
- calculates and verifies SHA-256 and byte length;
- survives adapter recreation/process restart;
- never returns an absolute root path as a storage reference.

`ArtifactApplicationGateway` writes content first, then stages the existing
`ArtifactMetadata` through the caller's Unit of Work. It lists metadata by run,
gets metadata, and verifies checksum/size before content reads. There are no
artifact HTTP endpoints in this milestone. Future transport mapping remains:

- `GET /runs/{run_id}/artifacts` -> `list_for_run`;
- `GET /artifacts/{artifact_id}` -> `get_metadata`;
- `GET /artifacts/{artifact_id}/content` -> `read_verified`/stream.

Filesystem writes cannot be part of the PostgreSQL transaction. A database
rollback after a successful byte write can leave an unreferenced immutable
object; later idempotent replay is safe, but garbage collection/lifecycle
cleanup is deferred.

## Provider-operation lifecycle and budget semantics

The immutable lifecycle is:

```text
RESERVED / UNSETTLED
    -> RUNNING / UNSETTLED
    -> SUCCEEDED / SETTLED
    -> FAILED / SETTLED|RELEASED
    -> CANCELLED / SETTLED|RELEASED
```

Each record binds operation, project, run, logical step, optional StepRun,
provider category/identity/adapter/model-or-endpoint, operation kind,
idempotency key, request fingerprint, reservation, actual usage, normalized
failure, retry count, timestamps, row version, settlement state, and sanitized
diagnostic metadata.

`ProviderOperationService` checks the persisted run ledger before staging a
reservation. It rejects total request, LLM-call, token, cost, and currency
overages, reuses an exact
idempotent operation without reserving twice, rejects conflicting idempotency
reuse, exposes unsettled operations after UoW reconstruction, settles actual
zero-cost fake usage, and releases a reservation when failure occurs before a
provider call. Unknown or interrupted calls remain conservatively reserved.

The milestone live-provider budget is zero. Fake providers may reserve one
request but zero tokens and cost. No exchange rates or billing service were
added.

## Persistence and migration

`ProviderOperationRepository` is implemented by both
`InMemoryUnitOfWork` and `SQLAlchemyUnitOfWork`. Both provide insert/update,
lookup by operation/idempotency key, ordered run listing, unsettled listing,
rollback, and expected-version checks. The reusable adapter contract exercises
reservation, idempotent replay, restart visibility, stale concurrent update,
settlement, and reconstruction against both adapter factories.

Alembic revision: `20260721_0002` (down revision `20260721_0001`).

New table: `provider_operations`.

Important columns:

- identity/scope: `id`, `project_id`, `workflow_run_id`, `logical_step_id`,
  `step_run_id`;
- provider: category, operation kind, provider identity, adapter version,
  model/endpoint;
- request: idempotency key and request fingerprint;
- reservation: request/input/output/cost values, currency, and explicit
  fake/live-provider classification;
- result: status, settlement state, actual-usage JSONB, failure category,
  retry count, sanitized diagnostic JSONB;
- lifecycle: created/updated/started/finished timestamps, domain row version,
  repository persistence version.

Constraints and indexes:

- globally unique primary operation ID;
- composite project/run and run/StepRun foreign keys;
- unique `(project_id, idempotency_key)`;
- check constraints for valid status/settlement, nonnegative reservations,
  retry/domain row version, and positive persistence version;
- run/creation, status/update, and provider/failure/creation indexes;
- additive artifact indexes on run/kind/creation and project/checksum.

SQLAlchemy mapper versioning uses `persistence_version`; stale commits map to
`StaleStateError`. Domain `row_version` separately records logical operation
transitions.

## Approval-input extension

For approval steps, Workflow Engine now resolves the declared input mapping
before returning `WaitingApproval`. The integration coordinator persists those
resolved inputs when it marks the approval StepRun ready. Runtime constructs a
canonical action containing:

- project, workflow ID/version, run, approval step and StepRun/attempt;
- policy/approval role and expiration;
- exact Engine-resolved values, including query hash, selected paper IDs,
  selected-papers artifact checksum, and ranker version when declared;
- all pinned Skill references from the immutable workflow.

Runtime derives the ApprovalRequest fingerprint from that complete canonical
action. Tests prove that changing either selected paper IDs or the artifact
checksum creates a different fingerprint and Domain approval rejects it.
Existing approval-only, approve, reject, expiry, recovery, and API behavior
remain compatible. No research-specific logic was added to FastAPI routers.

## Skill substrate additions

`SkillExecutionContext` now carries a frozen `SkillCapabilities` bundle with
explicit optional paper-search, source-content, LLM, artifact-storage, and
provider-operation services. Every capability is absent by default and
`require_*` fails with `CAPABILITY_DENIED` when not granted.

Existing Skills may continue returning a plain output mapping. New Skills may
return `SkillExecutionOutput`, which carries output data, immutable emitted
artifact metadata, and `ProviderUsage`. `SkillExecutor` validates the output
schema and propagates the additional data into `SkillResult`. Normalized
`ProviderError` values cross the execution boundary as safe typed Skill errors;
raw SDK objects never do.

This is additive and backward compatible. Existing fake Skills, definitions,
registrations, and tests still use their former contracts unchanged.

## Test evidence

Executed in the existing `reagent-dev` environment:

```text
conda run --no-capture-output -n reagent-dev pytest -q backend
106 passed, 9 skipped in 0.73s
exit 0

conda run --no-capture-output -n reagent-dev python -m compileall -q backend
no output
exit 0

conda run --no-capture-output -n reagent-dev pytest -q \
  backend/database/tests backend/integration/tests -rs
9 skipped in 0.22s
exit 0
```

The skip report is explicit:

- 8 PostgreSQL repository/schema/runtime tests require
  `REAGENT_TEST_DATABASE_URL`;
- 1 destructive HTTP/PostgreSQL integration test requires
  `REAGENT_E2E_DATABASE_URL` and `REAGENT_ALLOW_DATABASE_RESET=1`.

No isolated ReAgent PostgreSQL database was designated, and the unrelated
`ProjectDB` was not used. Consequently migration 0002 and the PostgreSQL
provider-operation shared contract are implemented but **not executed** here.
Alembic static head discovery reports `20260721_0002 (head)`.
Importing SQLAlchemy metadata reports 30 provider-operation columns, 10
constraints, and 3 table indexes, matching the declared adapter model.

Frontend tests were not run because no frontend source, HTTP endpoint,
`package.json`, lockfile, or generated/shared API type changed.

Validation also confirmed:

- no Domain source changed;
- no environment, npm, Compose, Make, or credential file changed;
- no SQLAlchemy/FastAPI/environment-variable/provider-SDK import exists in
  research contracts/ports, Workflow Engine, Agent Runtime, or Skill contracts;
- `runtime_data/` is ignored by Git;
- `.agent_read` remains trackable;
- no staged changes, generated artifact bodies, database data, credentials, or
  provider responses exist.

## Remaining risks and exclusions

- Paper-search provider, LLM provider/model, real API behavior, price, rate
  limit, terms, key availability, and secret configuration remain undecided.
- Live-provider mode remains disabled with zero monetary budget. Settlement
  policies must be reviewed with the selected vendor's actual usage semantics.
- Only a local filesystem content adapter exists. S3-compatible storage,
  cross-resource atomicity, orphan cleanup, retention enforcement, and artifact
  authorization are deferred.
- The complete `guided-literature-review@2.0.0` workflow and real research
  Skills are not implemented or seeded. There is no full fake research run yet.
- Artifact list/content APIs and report/approval frontend views are deferred.
- There is no authentication, multi-user authorization, worker/lease queue,
  durable cancellation signal, or production secret manager.
- The SQL migration/adapter contract needs a real isolated PostgreSQL execution.
- Docker clean-machine behavior remains unverified and is a separate remediation
  stream.
- Existing environment drift documented by the environment audit is unchanged;
  no dependency or cache remediation was attempted.

## First fake research evidence

This milestone did **not** execute a complete fake Guided Literature Review v2.
It executed contract-level synthetic provider calls, provenance validation,
artifact persistence/restart checks, provider-operation lifecycle checks,
Skill injection/error propagation, and Runtime approval binding. The next
milestone can now compose these verified components into the full deterministic
DAG.

## Exact next milestone

Implement exactly **Phase 9A-2: Complete Deterministic Fake-Provider Guided
Literature Review v2 Vertical Slice**.

Entry conditions:

1. migrate an explicitly isolated PostgreSQL test database to
   `20260721_0002` and pass the shared provider-operation contract;
2. retain all accepted ADR 0003 boundaries and zero-cost/no-network defaults;
3. keep provider/model selection, credentials, live adapters, worker queue,
   authentication, S3, and Docker remediation out of scope.

The milestone should implement the immutable workflow definition/seeder,
provider-independent research Skills, operation reservations and settlement at
each fake provider call, all planned artifact bodies/metadata, provenance-gated
completion, artifact application/API reads, minimal approval/report frontend
presentation, and backend/frontend/browser acceptance using only deterministic
synthetic data.

Completion gate: one real UI -> FastAPI -> Runtime -> SQL UoW -> PostgreSQL ->
local ArtifactContentStorage run must complete
topic -> search -> rank -> approval -> source retrieval -> synthesis -> report,
with citation/evidence validation, artifact download/read, ordered events, and
reload persistence. No provider SDK or network call may be present.
