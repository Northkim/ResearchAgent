# R3B API Proxy Implementation Acceptance Plan

Status: **R3B-A EXTERNAL ACCEPTANCE PASSED WITH WARNINGS**

Date: 2026-08-04

R3B purpose: implement and accept the provider-neutral proxy boundary using a
deterministic fake adapter only. This document defines the gates; the completed
evidence is in `R3B_FAKE_PROXY_EXTERNAL_ACCEPTANCE_REPORT.md`. Neither document
authorizes R3C, a live provider or production deployment. ADR 0011 authorizes
only the disabled-by-default experimental profile specified here.

R3B-I created the disabled-by-default fake-only implementation, migration,
client/CLI and network-free/real-SQL qualification baseline at revision
`20260804_0004`. R3B-A subsequently ran the gates below with a fresh external
Package, real loopback Uvicorn server, isolated PostgreSQL and actual restart.
The detailed evidence and retained warnings are in
`R3B_FAKE_PROXY_EXTERNAL_ACCEPTANCE_REPORT.md`.

## Entry gate

ADR 0011 resolves the R3B-only authentication, exact authorization scope,
capability, limits/budget, idempotency/reconciliation, persistence separation,
retention/cleanup and Progress Report relationship. R3B-I implements those
decisions. After the clean R3B-A evidence commit:

```text
R3B_A_ACCEPTANCE = PASS_WITH_WARNINGS
R3B_STATE = FAKE_PROXY_ACCEPTED
R3C_LIVE_PROVIDER_GATE = CLOSED
```

R3B remains `EXPERIMENTAL_FAKE_PROVIDER_VERTICAL_SLICE`, disabled by default,
loopback-only and unsuitable for public/production deployment.

## Boundary under acceptance

```text
external fictional Workflow Package
  -> explicit local proxy client
  -> short-lived bearer-authenticated real loopback HTTP
  -> dedicated proxy application service
  -> isolated PostgreSQL operation metadata
  -> deterministic fake paper-search adapter
  -> normalized untrusted provider-data envelope
  -> local client result
```

The path must not import or invoke `AgentRuntime`, `ExecutionDispatcher`,
Workflow run/resume, research Skills, OpenAlex, LLM/structured generation,
Hosted Judge/approval execution, local Package mutation or Progress Report
generation.

## Ratified R3B profile

- Authentication: opaque bearer capability with at least 256 random bits;
  SHA-256 digest-only server storage and constant-time comparison.
- Issuance: operator CLI only; plaintext once to a new caller-selected `0600`
  file outside Git/Package, never stdout/logs/arguments; client reads only
  process environment `REAGENT_PROXY_TOKEN`; remove the file after acceptance.
- Lifetime: 60-minute default, 120-minute maximum/acceptance allowance, no
  refresh, explicit server-side revocation.
- Transport: server bound to `127.0.0.1`, loopback HTTP only, client timestamp
  skew at most plus or minus five minutes; no signature, nonce or proof of
  possession.
- Scope: server-bound token/tenant/subject/project, exact Package ID/checksum,
  exact Workflow ID/version/checksum, `paper.search/v0.1`, the deterministic
  fake adapter, maximum operation count, issue/expiry and revocation state.
- Parameters: `query` trimmed to 1–500 UTF-8 characters; `max_results` integer,
  default 10, range 1–20; unknown fields rejected.
- Limits: 16 KiB request, 512 KiB normalized result, 10-second operation
  timeout, two concurrent operations/token, 50 operations/token, zero money,
  zero real-provider calls and zero external-network calls.
- Idempotency: client UUIDv4; same scope/key/content replays; changed content
  under the key returns HTTP 409 `IDEMPOTENCY_CONFLICT` before adapter use.
- States: `RECEIVED`, `RUNNING`, `SUCCEEDED`, `FAILED`, and
  `RECONCILIATION_REQUIRED`; no ambiguous automatic client retry and no fake-
  adapter real-provider retry.
- Retention: safe normalized acceptance data for the isolated environment
  lifetime only; no raw body, credential, token plaintext, Authorization header,
  unsafe original payload or executable content.

## Required environment

1. Begin from the exact owner-approved R3A/R3B implementation baseline on a
   clean branch and clean working tree.
2. Create a wholly fictional Workflow Package outside Git. It must contain no
   credential, private research data, real R1 evidence or machine-specific path.
3. Use the repository’s real ASGI entrypoint and real HTTP over `127.0.0.1` on a
   unique port. Disable Uvicorn proxy-header parsing for this direct loopback
   profile so peer authorization uses the actual socket peer, not a forwarded
   header. TestClient/mocked HTTP cannot satisfy the core boundary.
4. Create a dedicated temporary PostgreSQL cluster or demonstrably isolated
   server/database, never `ProjectDB` or an existing user database. Use separate
   acceptance and automated-test databases.
5. Use persistent immutable artifact storage outside Git if the approved R3B
   policy stores normalized fake responses. If policy is metadata-only, prove
   no response artifact was silently created.
6. Use only the deterministic fake paper-search adapter. Prove it cannot make
   an external network call; do not configure or read a real credential.
7. Issue only a fictional acceptance token through the operator CLI and prove
   the full file-mode/non-overwrite/digest-only/redaction/revocation lifecycle.

## Contract and identity acceptance

Independently reconstruct and compare:

- canonical request bytes;
- request-content checksum;
- stable authorization-scope checksum from fictional accepted scope;
- version-namespaced operation ID;
- provider-data checksum;
- response-content checksum;
- delivery response checksum.

Prove the construction is non-cyclic and stable across processes/restarts.
Changed semantic content must change request checksum/operation identity; cloud
database surrogate IDs must not replace contract identity.

Verify exact tenant/subject/project, Package ID/checksum, Workflow ID/version/
checksum, capability, adapter, Harness and operation-count binding. Client-
supplied `actor_user_id`, role, tenant, owner or permission claims must never
be authorization. Prove token plaintext/digest is not canonical request
content and the UUIDv4 idempotency key is distinct from the request checksum.

## External Package and client acceptance

The Package remains outside Git and includes only non-secret proxy
configuration. Before client validation, compute a relative-path, size and
SHA-256 manifest for every file. Exercise:

```text
local validate
explicit proxy submit
status/reconciliation read
result retrieval
idempotent replay
security rejection cases
server/database restart
post-restart replay
```

Recompute the Package manifest after all operations. Paths, sizes and checksums
must be identical. The client must not write output, context, Progress Report,
configuration or credential files. It must make no ambiguous automatic retry
and print only safe operation metadata.

## Core success path

1. Submit one valid `paper.search/v0.1` request through real loopback HTTP.
2. Verify authorization, schema, identity and operation-count reservation were
   durable before the fake adapter was invoked.
3. Verify exactly one fake adapter operation and no other capability ran.
4. Retrieve the operation by ID and by scoped idempotency identity.
5. Verify the normalized response matches the strict schema and labels all
   fake records as untrusted/synthetic.
6. Verify adapter identity, request/response checksums, latency, zero-cost
   usage/budget, retry class, warnings, provenance and timestamps.
7. Verify any normalized fake-result artifact is immutable and checksum-bound;
   prove no raw-provider-body or unsafe-payload artifact exists.
8. Verify no local Package file changed and no Progress Report was generated or
   amended.

## Idempotency and timeout reconciliation

Test sequential and concurrent exact replay using independent real HTTP
clients. Require one effective operation, one fake adapter invocation, one
operation-count reservation/zero-cost settlement, stable response-content
identity and no duplicate artifact. Delivery receipts may report replay
separately.

Require client-generated UUIDv4 keys. Under the same authorization scope, use
the same key with changed canonical parameters and require HTTP 409
`IDEMPOTENCY_CONFLICT` before fake-adapter invocation. Test identity/scope
mismatches separately as authorization failures; do not conflate a scope
failure with changed request content.

Simulate a client timeout after the server may have completed. The client must
report unknown outcome, perform no automatic retry and recover the durable
result through a status read using the same identity. Test process interruption
at `RECEIVED`, `RUNNING`, response-persisted and settlement boundaries. Unknown
provider outcome must remain `RECONCILIATION_REQUIRED`, not trigger a second
fake call.

## Security rejection matrix

Use fictional canaries only. Each rejection must occur before provider use and
unsafe artifact retention where applicable.

- missing, expired, revoked, wrong-scope and malformed authentication;
- wrong project, Package ID/checksum or Workflow identity;
- unauthorized capability/adapter and any client-selected provider/endpoint;
- client-supplied principal/role/authorization claims;
- unknown contract/capability version or unknown field;
- arbitrary URL, scheme, host, method, header, redirect or provider filter;
- loopback/private/link-local/metadata address canary if any endpoint field can
  enter the adapter configuration path;
- idempotency key substitution and cross-project replay;
- oversized body, excessive nesting/list/string, record/result or response cap;
- invalid Unicode/control/log-injection canary;
- HTML/script/terminal-escape/provider prompt-injection text;
- secret-like provider response field;
- path traversal/absolute path/symlink local client input;
- 16 KiB request, 512 KiB result, 10-second timeout, 500-character query,
  20-result, two-concurrent, 50-operation and zero-cost/network limit breaches;
- malformed, timeout, 400/401/403/404/408/429/5xx and oversized fake responses.

Verify errors expose only safe codes, IDs/hashes/counts and retry
classification. No credential, query body, absolute path, traceback or other
tenant identity may leak.

## Persistence and restart recovery

Inspect PostgreSQL schema/rows to prove the application is not using an
in-memory repository and uses a separate Proxy operation domain. It must not
reuse or fabricate Hosted `ProviderOperation`, `WorkflowRun`, `StepRun`,
`ExecutionEvent`, `Checkpoint` or `MemoryRevision` records. Record accepted/
rejected operation IDs, row counts, response checksums, artifact manifests and
operation-count/zero-cost settlement.

Then:

1. stop FastAPI cleanly;
2. stop the isolated PostgreSQL cluster cleanly;
3. preserve its data directory and any persistent artifact directory;
4. restart the same PostgreSQL data;
5. restart FastAPI with the same stores;
6. retrieve every accepted/conflicting/reconciliation record over real HTTP;
7. compare canonical snapshots and checksums before/after;
8. replay the accepted operation and require no second fake call, reservation,
   settlement or artifact.

Restart acceptance fails on metadata loss, artifact loss, identity change,
budget corruption, duplicate execution or a `RUNNING` operation silently
becoming safe-to-retry.

## Runtime and provider boundary evidence

Add static forbidden-import checks and runtime canaries proving zero use of:

- `AgentRuntime`;
- `ExecutionDispatcher`;
- Workflow run/resume or Hosted approval execution;
- OpenAlex or any external provider transport;
- LLM or structured-generation provider;
- Hosted Judge/evaluation;
- server research ranking/synthesis/report Skills;
- local Package/context/output/Progress Report mutation.

Compare database counts before/after and require no proxy-caused
`WorkflowRun`, `StepRun`, `ExecutionEvent`, checkpoint or memory-revision row.
Provider operational provenance must use the approved proxy model, not relabel
an `ExecutionEvent` or checkpoint.

## Automated validation

R3B must define and run focused network-free contract, service, persistence,
API, client, security, boundary and restart tests using the isolated test
database. PostgreSQL coverage must execute rather than skip. Also run the full
backend regression and compilation checks required by repository policy.

Exact commands, counts, skips and exit codes belong in the R3B report. Any
PostgreSQL proxy test skipped for missing configuration is a hard failure.
Frontend tests are not required unless a separately authorized phase changes
frontend code.

## Git and evidence closure

- Keep external Package, database data, artifacts, credentials, logs and raw
  HTTP files outside Git or in approved ignored locations.
- Tracked evidence uses sanitized labels, relative paths and fictional data.
- Scan for credentials, absolute machine paths, real provider data and R1
  execution evidence.
- Confirm `.env` and `runtime_data/` remain ignored.
- Stop FastAPI and only the dedicated temporary PostgreSQL cluster.
- Remove the dedicated cluster, isolated artifact directory and plaintext
  token file only after restart/recovery evidence is complete; retain sanitized
  tracked evidence only.
- Do not use `git clean`, destructive resets or an existing database.
- Commit implementation and/or acceptance only under the scope explicitly
  authorized for R3B; end with a clean working tree.

## R3B pass gate

R3B passes only if the approved auth/authorization boundary, provider-neutral
contract, fake adapter, durable idempotency, reconciliation, budgets, security
rejections, real HTTP, isolated PostgreSQL, restart recovery, Package
non-mutation, forbidden-runtime/provider evidence, tests and clean Git closure
all pass.

R3B must not call a real provider. R3C remains a separate supervised milestone
requiring current provider terms, authentication, rate, cost and retention
verification plus explicit owner authorization.

R3B acceptance does not change `progress-report/v0.2`, create/upload/amend a
Progress Report, or mutate local context/outputs. A local output may record an
operation ID as ordinary provenance only.
