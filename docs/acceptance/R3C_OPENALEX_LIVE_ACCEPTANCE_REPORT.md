# R3C-A Supervised OpenAlex Live Acceptance Report

Status: **BLOCKED AT OWNER AUTHORIZATION GATE**

Date: 2026-08-04

Baseline: `6ba48416b4936060298b9e5fd9ce197b782b2bb1`
(`R3C-I: implement mocked OpenAlex proxy adapter`), branch `main`, with an
initially clean working tree.

This is a documentation-only blocked acceptance record. It does not claim a
live OpenAlex, PostgreSQL, Uvicorn, external Package, credential-lifecycle,
idempotency, restart, or cleanup acceptance result.

## 1. Blocking gate

R3C-A requires a separate owner-created, credential-free attestation file
outside Git and outside the Workflow Package. The phase request supplied
neither that file nor a location from which it could be read. The request also
prohibits Codex from authoring the attestation on the owner's behalf.

Consequently the owner authorization and free-allowance attestation could not
be verified. The phase stopped at Section C before reading or loading any
OpenAlex key and before contacting any OpenAlex documentation or API origin.

```text
R3C_A_ACCEPTANCE = BLOCKED
R3C_OWNER_AUTHORIZATION = FAIL
BLOCKING_REASON = OWNER_AUTHORIZATION_OR_FREE_ALLOWANCE_NOT_ATTESTED
```

The phase may be retried only after the owner supplies the path to a
credential-free `0600` attestation outside Git and the Package whose values
exactly authorize this acceptance. The OpenAlex key must remain separate and
must not be placed in the attestation.

## 2. Initial Git baseline

The initial gate passed:

- `git rev-parse HEAD` returned the exact required commit
  `6ba48416b4936060298b9e5fd9ce197b782b2bb1`;
- `git branch --show-current` returned `main`;
- both status commands returned no entries;
- `git diff --check` exited successfully;
- the latest commit was `R3C-I: implement mocked OpenAlex proxy adapter`.

No existing file was discarded, cleaned, restored or reset.

## 3. Authority and product boundary

The repository instructions, current project context, ADRs 0009 through 0012,
R3B/R3C progress records, Proxy and OpenAlex architecture/security contracts,
implementation/live-acceptance plans, R3B external acceptance evidence,
development plan and the complete three-page teacher architecture were read.

The teacher boundary remains unchanged: the cloud may hold credentials and
perform one bounded authorized API operation, while the local Harness chooses
and interprets the query and owns local research state. No cloud research
interpretation, Hosted Workflow continuation or Progress Report mutation was
performed.

## 4. Official-source recheck

The official-source recheck was **not started**. Section C is an explicit
precondition to Section D, so no request was made to an OpenAlex documentation
domain. `R3C_SOURCE_RECHECK = FAIL` below means unqualified due to the upstream
authorization blocker; it does not assert that a current official source
contradicted the committed adapter.

## 5. Acceptance environment and runtime

No acceptance environment was created:

- no PostgreSQL cluster or database was created, connected to, migrated,
  started or stopped;
- ProjectDB was not accessed;
- no external Workflow Package or manifest was created;
- no capability token was issued;
- no Uvicorn/FastAPI process was started;
- no OpenAlex credential source, `.env` file or process credential was read;
- no live Provider, API or other network request was made;
- no Provider result, query, raw response, log, database file or secret file
  was created.

Accordingly the live Provider-call ledger is exactly zero calls and zero
reported/reserved live cost.

```text
R3C_LIVE_PROVIDER_CALL_COUNT = 0
R3C_REPORTED_COST_MICROUSD = 0
```

## 6. Downstream acceptance gates

Because the phase stopped before source recheck and environment setup, the
following required runtime gates were not exercised and cannot be accepted:

- PostgreSQL migration/schema qualification;
- external Package creation and non-mutation comparison;
- OpenAlex credential and capability-token lifecycles;
- feature-disabled, missing-key and enabled composition;
- real loopback Uvicorn/HTTP and fixed-origin Provider transport;
- real Work normalization, exact cost and rate-limit evidence;
- query/key/URL/raw-body leakage audit;
- exact replay, conflict and status reads;
- backend/PostgreSQL restart recovery;
- focused, SQL and full-backend acceptance reruns;
- acceptance-runtime cleanup.

No failure in those implementation paths was observed; they remain
unqualified because the prerequisite owner authorization was absent.

## 7. Safety evidence

The fail-closed stop preserved these facts:

- no real or synthetic key was read or recorded;
- no live or private query was constructed or transmitted;
- no key, token, Authorization header, full Provider URL or raw body entered
  Git;
- no production, frontend, migration, test, fixture, Package, contract or ADR
  source changed;
- AgentRuntime, ExecutionDispatcher, Hosted Skills, Workflow execution, LLM,
  Judge and Progress Report activity remained zero;
- R3D production/public-provider authorization remains closed.

The temporary rendered teacher-PDF pages used for local authority review were
outside Git and are removed during documentation closure.

## 8. Final states

```text
R3C_A_ACCEPTANCE = BLOCKED
R3C_OWNER_AUTHORIZATION = FAIL
R3C_SOURCE_RECHECK = FAIL
POSTGRESQL_ACCEPTANCE = FAIL
EXTERNAL_PACKAGE_ACCEPTANCE = FAIL
LIVE_OPENALEX_HTTP_ACCEPTANCE = FAIL
OPENALEX_CREDENTIAL_LIFECYCLE = FAIL
OPENALEX_FIXED_ORIGIN_ACCEPTANCE = FAIL
OPENALEX_NORMALIZATION_ACCEPTANCE = FAIL
OPENALEX_COST_USAGE_ACCEPTANCE = FAIL
OPENALEX_QUERY_PRIVACY_ACCEPTANCE = FAIL
R3C_IDEMPOTENCY_ACCEPTANCE = FAIL
R3C_RESTART_ACCEPTANCE = FAIL
PACKAGE_IMMUTABILITY_ACCEPTANCE = FAIL
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
R3C_LIVE_PROVIDER_CALL_COUNT = 0
R3C_REPORTED_COST_MICROUSD = 0
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3C_COMPLETE = NOT_COMPLETE
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
R3B_STATE = FAKE_PROXY_ACCEPTED
R2_STATE = UPLOAD_ACCEPTED
```

`FAIL` for an unexecuted downstream acceptance denotes “not qualified in this
blocked phase,” not an observed implementation defect. Git closure is recorded
after the documentation-only evidence commit.
