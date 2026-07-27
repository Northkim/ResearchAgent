# 0003: Add real-provider operation and artifact-content boundaries

- Status: Accepted
- Date: 2026-07-21
- Accepted: 2026-07-21 for the limited Phase 9A-1 scope below
- Supersedes: None

## Context

The first real literature-review slice needs external paper search, permitted
source retrieval, structured LLM generation, immutable artifact content,
provider usage/cost controls, and source-grounded approval previews.

The current architecture already requires provider-neutral LLM and file/object
storage ports, but the implementation currently has:

- `SkillExecutionContext` with correlation identity only;
- `SkillResult` with output data and generic execution metadata only;
- an `ArtifactRepository` that stores metadata but no artifact bytes;
- no durable provider-operation reservation/usage ledger;
- a `WaitingApproval` decision without Engine-resolved approval inputs;
- approval fingerprints based on workflow inputs rather than the selected-paper
  artifact and candidate identities.

An external provider call cannot be atomically committed with PostgreSQL. A
process may fail after a billable request succeeds but before the Step result
and checkpoint commit. Without a durable pre-call reservation, recovery cannot
reliably enforce budget or determine whether a logical provider operation was
already attempted. Resolving approval input mappings inside Runtime would also
move reference-resolution behavior out of Workflow Engine ownership.

## Decision

The owner accepted only these additive architecture changes:

1. `UnitOfWork` may expose `ProviderOperationRepository` so provider budget
   reservation, status, usage, failure, and settlement share the caller's
   persistence transaction.
2. `WaitingApproval` may carry Workflow-Engine-resolved approval inputs.
   Workflow Engine still owns reference resolution; Runtime only fingerprints
   and persists the exact resolved action.
3. Artifact bytes must be read and written through
   `ArtifactContentStorage`. PostgreSQL retains metadata and relative storage
   keys, not absolute host paths or artifact bodies.
4. Provider SDKs and vendor clients must remain in infrastructure adapters and
   composition boundaries. Skills receive explicitly granted provider ports
   and remain deny-by-default.
5. Provider usage and budget reservation/settlement state must be durable and
   auditable, including interrupted/unsettled operations.

This acceptance does **not** select a paper-search vendor, LLM vendor, model,
price, credential, live-provider mode, production artifact backend, or broader
retention policy. It does not approve a Domain lifecycle change, worker queue,
authentication system, or real network access.

Add the following framework-independent outbound ports:

- `PaperSearchProvider`;
- `SourceContentProvider`;
- `LLMProvider` with separate text and structured generation;
- `ArtifactContentStorage`;
- `ProviderOperationRepository`.

Add `ProviderOperationRepository` to the Unit of Work as an additive persistence
contract. Implement durable request-hash/idempotency identity, pre-call budget
reservation, normalized completion/failure usage, and optimistic versioning in
both InMemory and PostgreSQL adapters.

Add a budgeted provider-operation application gateway. Skills receive only
scoped provider interfaces from composition and never instantiate SDK clients,
read secrets, or access SQLAlchemy.

Introduce an additive Skill API version supporting:

- scoped provider/artifact-read capabilities in `SkillExecutionContext`;
- immutable artifact write requests in `SkillResult`;
- normalized ProviderUsage in `SkillResult`.
- minimal enum, string-length, and numeric-range schema constraints required by
  the research contracts, without claiming full JSON Schema support.

An application Artifact Service writes and verifies immutable bytes through
`ArtifactContentStorage`, then stages existing `ArtifactMetadata` in the Runtime
Unit of Work. Database records contain relative storage keys, never absolute
paths.

Extend Workflow Engine approval decisions so `WaitingApproval` carries the
Engine-resolved approval input mapping. Runtime fingerprints that immutable
selection preview and artifact checksum. Workflow Engine continues to own
reference resolution; Runtime continues to own approval creation and
transactional orchestration.

Provider and model vendors, credentials, pricing, production storage product,
and retention policy remain separate owner decisions.

## Consequences

- Domain lifecycle states and legal transitions do not change.
- Workflow Engine, Skill System, Runtime, application, and adapter ownership
  remain in their frozen modules.
- Existing persistence repository methods remain; the Unit of Work gains one
  additive repository.
- Every real provider operation can be budgeted, audited, normalized, and
  recovered independently of raw SDK objects.
- Exactly-once external billing still cannot be guaranteed when a provider
  offers neither idempotency nor request reconciliation. The system reserves
  budget conservatively and exposes interrupted operations.
- Artifact content survives process restart and can later move from a local
  filesystem adapter to S3-compatible storage without changing artifact IDs or
  API contracts.
- Skills and Runtime require additive contract/test updates; existing fake
  Skills must remain compatible or be explicitly migrated to the new Skill API
  version.
- One Alembic migration and matching InMemory/SQL adapter contract tests are
  required for provider operations.
- Real provider adapters remain subject to separate owner decisions and current
  official-document verification.

## Alternatives considered

- Put provider SDK clients directly inside Skills: rejected because it couples
  capability logic to vendors, secrets, retries, and environment variables.
- Store provider usage only in execution events or final `usage.json`: rejected
  because neither can reserve budget before a billable call or reconcile a
  crash between provider response and Step commit.
- Let provider adapters use the Workflow Unit of Work directly: rejected
  because it leaks persistence coordination into infrastructure adapters and
  cannot span external I/O atomically.
- Persist artifact bodies in PostgreSQL JSONB/Text: rejected because the frozen
  architecture assigns large content to file/object storage and requires
  storage references.
- Add local filesystem paths to `ArtifactMetadata.storage_ref`: rejected because
  host/container paths are not stable or portable and can leak system layout.
- Build the approval preview in Runtime from prior Step outputs: rejected
  because Workflow Engine owns reference validation and resolution.
- Change the Workflow DAG dynamically per paper: rejected because V1 remains a
  versioned static DAG with sequential execution.
