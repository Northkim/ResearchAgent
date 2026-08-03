# R3A-D Owner Decision Ratification

Date: 2026-08-04

Status: **PASS — DOCUMENTATION-ONLY OWNER RATIFICATION**

Initial baseline: `e598fac2d996004b5d545f4c4558fc74954165a9`
(`R3A: define local-Harness cloud API proxy contract`) on clean `main`.

## Purpose and scope

R3A-D ratifies the owner decisions needed for the experimental R3B
fake-provider slice. It changes architecture, security, acceptance, planning,
ADR and `.agent_read` documentation only. It does not implement or run R3B,
change production source/tests/migrations/Package runtime behavior, start a
server/database, read `.env`/credentials, call a provider/network, execute a
Workflow, or invoke AgentRuntime, ExecutionDispatcher, OpenAlex, an LLM or
structured generation.

The teacher-aligned boundary remains unchanged: the local Workflow Package is
authoritative for concrete research-task state; Codex/Claude Code performs the
research; the cloud may expose an explicitly requested bounded API capability
but does not choose or interpret the research task.

## Ratified R3B decisions

Accepted ADR 0011 records all owner-authorized controls:

1. R3B is `EXPERIMENTAL_FAKE_PROVIDER_VERTICAL_SLICE`, disabled by default,
   deterministic-fake-adapter-only, external-network/real-provider/real-
   credential disabled, and not public/production suitable.
2. Authentication is a short-lived opaque bearer with at least 256 random
   bits, SHA-256 digest-only server storage, constant-time comparison,
   operator-only file issuance, 60-minute default/120-minute maximum lifetime,
   no refresh and explicit revocation.
3. The server token record binds token/tenant/subject/project, exact Package
   and Workflow identity/checksums, `paper.search/v0.1`, the deterministic fake
   adapter, maximum operation count, issue/expiry and revocation. Client roles,
   ownership and permission claims are never authorization.
4. Acceptance is loopback HTTP on `127.0.0.1` with plus or minus five minutes
   of client timestamp skew. R3B has no detached signature, nonce or proof of
   possession; non-loopback use requires HTTPS and separate approval.
5. The only capability is `paper.search/v0.1`, accepting exactly a trimmed
   1–500-character UTF-8 `query` and `max_results` default 10/range 1–20.
6. Limits are 16 KiB request, 512 KiB normalized result, 10-second timeout, two
   concurrent and 50 total operations per token, and zero monetary,
   real-provider and external-network use.
7. Client idempotency keys are UUIDv4. Same scope/key/canonical content returns
   one existing Proxy operation; changed content returns HTTP 409
   `IDEMPOTENCY_CONFLICT` before adapter use. Timeouts use explicit status reads
   and `RECONCILIATION_REQUIRED`, never ambiguous automatic retry.
8. R3B receives a separate Proxy operation domain/repository/persistence
   boundary. It does not reuse/fabricate Hosted provider/run/step/event/
   checkpoint/memory identity and cannot import Hosted research execution.
9. Retention is limited to the isolated acceptance environment and safe
   normalized fake data. Raw bodies, credentials, token plaintext,
   Authorization headers, unsafe payloads and executable content are forbidden;
   isolated database/artifacts/token file are removed after acceptance.
10. R3B does not change `progress-report/v0.2`, automatically create/upload/
    amend Progress Reports, or mutate local context/outputs.
11. `R3C_LIVE_PROVIDER_GATE` remains closed pending separate owner decisions on
    production authentication/UX/HTTPS, provider terms/credentials/rates/cost/
    retry, live retention/deletion/logging and public-network security.

## Identity and consistency result

The contract now makes the construction explicitly one-way:

```text
canonical semantic request -> request_content_checksum
request_content_checksum + UUIDv4 idempotency key + stable server-derived scope
  -> version-namespaced operation_id
operation outcome -> response-content and delivery checksums
```

The idempotency key is distinct from the request-content checksum. Token
plaintext/digest is neither canonical request content nor operation identity.
Authorization context comes from the server token record and is not accepted
from the request. Exact replay, 409 conflict and status/reconciliation behavior
are deterministic. The Proxy operation ledger is independent of Hosted
`WorkflowRun` and `ProviderOperation` persistence. The fake adapter has a
zero-network policy, the cloud performs no research interpretation, and no
Progress Report contract change is implied.

## Documentation changed

- Added accepted ADR 0011 for all R3B owner decisions.
- Reconciled the Cloud API Proxy contract from candidate parameters/limits to
  the exact ratified R3B profile.
- Reconciled the threat model with the digest-only bearer lifecycle, exact
  scopes/limits, acceptance-lifetime cleanup and R3C residual decisions.
- Opened the future R3B implementation plan under the fake-only controls while
  leaving its runtime acceptance unstarted.
- Updated the project plan, compressed context and original R3A progress record
  without rewriting the historical pre-ratification decision packet.

## Validation

- The initial baseline gate passed at the exact required commit on clean
  `main`; initial `git diff --check` exited 0.
- The changed-file inventory is restricted to the approved architecture,
  security, acceptance, planning, ADR and `.agent_read` documentation paths.
- `git diff --check` exited 0 after the documentation changes. Targeted text
  audits found no newly added machine-specific absolute path, credential/key/
  token example, real R1B path/evidence marker, production-ready claim, R3C-open
  claim or real-provider authorization claim. The sole path-related hit was the
  explicit fictional rejection-canary category in the future acceptance plan.
- `.env` and `runtime_data/` remain ignored. No `.env`, runtime-data path,
  database file, production source, frontend, migration, test, fixture or
  Workflow Package runtime file is in the changed-file inventory.
- No repository-provided documentation/link check was found by the targeted
  configuration/script search.
- Backend tests are intentionally not run because no source may change. Static
  documentation inspection is not R3B runtime acceptance.
- No server, PostgreSQL/database, Workflow, provider, network request, `.env`,
  real credential, AgentRuntime, ExecutionDispatcher, OpenAlex, LLM or
  structured generation was used.

## Gate

```text
R3A_OWNER_DECISION_RATIFICATION = PASS
R3A_OWNER_DECISIONS = RATIFIED_FOR_R3B
R3B_AUTH_MODEL = APPROVED_FOR_EXPERIMENTAL_R3B
R3B_AUTHORIZATION_MODEL = APPROVED_FOR_EXPERIMENTAL_R3B
R3B_CAPABILITY = PAPER_SEARCH_V0_1_APPROVED
R3B_LIMITS_AND_BUDGET = APPROVED
R3B_RETENTION = ACCEPTANCE_LIFETIME_ONLY
R3B_IMPLEMENTATION_GATE = OPEN
R3C_LIVE_PROVIDER_GATE = CLOSED
R2_STATE = UPLOAD_ACCEPTED
```

R3B has not started. Wait for owner review; do not begin R3C.
