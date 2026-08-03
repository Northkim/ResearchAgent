# R3B API Proxy Implementation Acceptance Plan

Status: **FUTURE PLAN — NOT STARTED, GATE CLOSED**

Date: 2026-08-03

R3B purpose: implement and accept the provider-neutral proxy boundary using a
deterministic fake adapter only. This document is not evidence that R3B passed
and is not authorization to start while owner decisions remain open.

## Entry gate

R3B may start only after the owner records authoritative decisions for:

- authentication and credential issuance;
- authenticated project/Package authorization and multi-user isolation;
- the first capability (`paper.search/v0.1` or an owner-approved replacement);
- request/result/response size, timeout, attempt and concurrency limits;
- request-count/cost budgets;
- raw and normalized response retention/deletion;
- Package binding, token lifetime/revocation and any signing/nonce policy.

At R3A closure:

```text
R3B_IMPLEMENTATION_GATE = CLOSED
```

## Boundary under acceptance

```text
external fictional Workflow Package
  -> explicit local proxy client
  -> authenticated real loopback HTTP
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

## Required environment

1. Begin from the exact owner-approved R3A/R3B implementation baseline on a
   clean branch and clean working tree.
2. Create a wholly fictional Workflow Package outside Git. It must contain no
   credential, private research data, real R1 evidence or machine-specific path.
3. Use the repository’s real ASGI entrypoint and real HTTP over `127.0.0.1` on a
   unique port. TestClient/mocked HTTP cannot satisfy the core boundary.
4. Create a dedicated temporary PostgreSQL cluster or demonstrably isolated
   server/database, never `ProjectDB` or an existing user database. Use separate
   acceptance and automated-test databases.
5. Use persistent immutable artifact storage outside Git if the approved R3B
   policy stores normalized fake responses. If policy is metadata-only, prove
   no response artifact was silently created.
6. Use only a deterministic fake `PaperSearchProvider`. Do not configure or
   read a real provider credential and prevent external provider network access.
7. Use fictional auth material matching the approved authentication seam; no
   production credential or real account.

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

Verify exact Package, Workflow, capability, Harness and approved-limit binding.
Client-supplied principals/roles must be rejected or ignored in favor of
server-authenticated context.

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
2. Verify authorization, schema, identity and budget were durable before the
   fake adapter was invoked.
3. Verify exactly one fake adapter operation and no other capability ran.
4. Retrieve the operation by ID and by scoped idempotency identity.
5. Verify the normalized response matches the strict schema and labels all
   fake records as untrusted/synthetic.
6. Verify adapter identity, request/response checksums, latency, usage, budget,
   retry class, warnings, provenance and timestamps.
7. If response artifacts are approved, download and verify exact immutable
   bytes/checksum; otherwise prove metadata-only retention.
8. Verify no local Package file changed and no Progress Report was generated or
   amended.

## Idempotency and timeout reconciliation

Test sequential and concurrent exact replay using independent real HTTP
clients. Require one effective operation, one fake adapter invocation, one
budget reservation/settlement, stable response-content identity and no
duplicate artifact. Delivery receipts may report replay separately.

Use the same idempotency key with changed parameters, Package identity,
capability or declared limits. Require an identity conflict before fake-provider
invocation and no projection/local-state effect.

Simulate a client timeout after the server may have completed. The client must
report unknown outcome, perform no automatic retry and recover the durable
result through a status read using the same identity. Test process interruption
at `RESERVED`, `RUNNING`, response-persisted and settlement boundaries. Unknown
provider outcome must remain `RECONCILIATION_REQUIRED`, not trigger a second
fake call.

## Security rejection matrix

Use fictional canaries only. Each rejection must occur before provider use and
unsafe artifact retention where applicable.

- missing, expired, revoked, wrong-scope and malformed authentication;
- wrong project, Package ID/checksum or Workflow identity;
- unauthorized capability/provider preference;
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
- request-count, rate, concurrency and zero-cost budget exhaustion;
- malformed, timeout, 400/401/403/404/408/429/5xx and oversized fake responses.

Verify errors expose only safe codes, IDs/hashes/counts and retry
classification. No credential, query body, absolute path, traceback or other
tenant identity may leak.

## Persistence and restart recovery

Inspect PostgreSQL schema/rows to prove the application is not using an
in-memory repository and does not fabricate Hosted `WorkflowRun`/`StepRun`
records. Record accepted/rejected operation IDs, row counts, response checksums,
artifact manifests and budget settlement.

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
