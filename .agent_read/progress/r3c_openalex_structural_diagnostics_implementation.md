# R3C-N2-I OpenAlex Structural Diagnostics Implementation

Date: 2026-08-04

## Result

```text
R3C_N2_I_IMPLEMENTATION = PASS_WITH_WARNINGS
R3C_RECORD_LEVEL_POLICY = STRICT_COMPLETE_RESPONSE_FAILURE
R3C_STRUCTURAL_DIAGNOSTIC_CONTRACT = PASS
R3C_DIAGNOSTIC_PRIVACY_BOUNDARY = PASS
R3C_DIAGNOSTIC_SERVICE_WORK_DISTINCTION = PASS
R3C_NORMALIZATION_BEHAVIOR_UNCHANGED = PASS
R3C_PUBLIC_API_PERSISTENCE_UNCHANGED = PASS
R3C_SQL_REGRESSION = PASS
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
R3C_LIVE_PROVIDER_CALL_COUNT_THIS_PHASE = 0
R3C_DIAGNOSTIC_LIVE_CALL_GATE = READY_FOR_OWNER_AUTHORIZATION
R3C_I2_IMPLEMENTATION_GATE = CLOSED
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

Warnings are limited to the absence of a live diagnostic, the still-unknown
retry-1 root cause, unqualified real-response compatibility, the need for fresh
owner authorization/attestation/key for any future diagnostic, possible future
`UNCLASSIFIED_INTERNAL`, and the already deferred frontend/production security
and Claude Code work.

## Baseline and safety gate

The phase began from exact clean `main` commit
`f5bc017689e97fddbcfffad0581c7c391fb1f021`
(`R3C-N1: diagnose live OpenAlex normalization failure`). Required retry-1 and
R3C-I ancestors were present; status/porcelain were empty and diff check passed.

`REAGENT_OPENALEX_API_KEY` was absent. Owner key/attestation path variables were
present but ignored; no value or referenced file was opened. No `.env` was
read. No Provider API, OpenAlex documentation site, or other external service
was contacted. No live Provider call, key read, credential load, Uvicorn,
AgentRuntime, ExecutionDispatcher, Workflow, Hosted research Skill, LLM,
structured generation, Judge, or Progress Report generation/upload occurred.

All authority documents and the three-page teacher architecture PDF were read.
The teacher-aligned local-Harness/cloud-credential boundary remains unchanged.

## Owner decisions ratified

Accepted ADR 0013 ratifies strict complete-response failure. A malformed Work
fails the complete operation; no valid subset, partial result, warning-bearing
success, rejected-record count, quarantine, or raw record is returned or
persisted. This records existing behavior and does not infer that retry 1
contained a malformed Work.

No nullability, identity, DOI, title, authorship, abstract, year,
location/source, language, Unicode/control, safety, count/size, ordering, model,
or normalized result predicate changed. The pre-existing focused tests remained
green before the new diagnostic tests were added.

## Implemented internal boundary

`backend/cloud_api_proxy/openalex_diagnostics.py` implements internal contract
`reagent.openalex-structural-diagnostic/v0.1`, a closed failure-stage enum,
closed observed-kind enum, closed validator registry, closed approved-path
allowlist, immutable typed failure/diagnostic records, and the default-disabled
structured emitter.

The shape descriptor includes only approved-field presence, null/type state,
bounded structural counts, indices, path, and fixed classifications. It ignores
Provider string/numeric values and unknown key names, canonicalizes through the
existing JSON rules, and uses SHA-256. Tests prove determinism, equal checksum
for different values with the same shape, and inequality for a changed shape.

The adapter attaches a typed failure to every current response and per-Work
predicate. Sequential per-Work construction is used only to capture the first
record index and safe count; failure still discards the complete response.
Unexpected internal failures use a safe typed wrapper or
`UNCLASSIFIED_INTERNAL` with no raw exception text.

The service adds operation/request correlation after terminal persistence and
emits at most one event. Exact replay returns the stored operation before
adapter or emitter use. Service-level sensitive-content rejection is uniquely
`SERVICE_SAFETY / SENSITIVE_CONTENT / SERVICE_SENSITIVE_CONTENT` at
`/service_safety`; the scanner rule and match outcome are unchanged.

## Feature flag and logging

The sole flag is:

```text
REAGENT_EXPERIMENTAL_OPENALEX_STRUCTURAL_DIAGNOSTICS_ENABLED
```

Only exact `1` enables it. It is process-only, disabled by default, independent
of the OpenAlex Proxy feature flag, and cannot mount the Proxy or construct/read
a credential source by itself. Disabled mode emits no event. Enabled mode emits
one canonical JSON warning named `openalex_structural_diagnostic` without
exception interpolation, `exc_info`, stack trace, request/response object,
HTTPX representation, URL, header, query, key, token, or Provider value.

The future sink is a temporary owner-controlled mode-`0600` acceptance log
outside Git. No live log was created in this phase.

## API, identity, and persistence non-change

No request/submit/status/client field, Package template, Progress Report
contract, operation/checksum identity, query-retention rule, raw-body rule,
SQL model/repository schema, ORM model, or migration changed. The new result
shape checksum is internal adapter-to-service state only and is never
serialized into `ProxyOperation` data.

Historical fake/OpenAlex rows remain readable. SQL schema inspection found no
diagnostic/raw-error field. Existing exact replay, cost/call settlement,
uncertain reconciliation, query non-retention, and fake-adapter behavior remain
unchanged.

## Synthetic qualification

Wholly fictional scripted responses and runtime markers cover:

- diagnostic disabled/enabled behavior with the same external error;
- every current response and per-Work rejecting predicate with exact stage,
  approved path, observed kind, validator code, index, and safe count;
- approved nullable/sparse shapes that remain accepted;
- mixed valid/malformed/valid Works with complete failure and no partial data;
- service safety distinct from per-Work normalization and no matched value;
- canonical serialization, normalized size, domain-model, and unexpected
  internal failures without raw error text;
- value-independent structural checksum;
- query/key/Provider-value leakage canaries;
- exact 1,000-microusd post-cost failure settlement and one effective replay;
- unchanged uncertain reconciliation and fake-adapter isolation;
- hard DNS/socket/HTTP no-network canaries.

## PostgreSQL qualification and cleanup

A fresh PostgreSQL 18.1 cluster listened only on `127.0.0.1` at a non-default
port. Its dedicated database name contained `reagent_r3cn2i_tests`; it was not
ProjectDB. Existing migrations reached the single head `20260805_0005`, current
matched head, and `alembic check` reported no drift.

The two required Proxy/OpenAlex SQL files executed 13 tests with zero skip.
The full backend was then run with its SQL tests bound to a fresh dedicated
cluster/database of the same profile. An earlier full-suite command issued
after the first cluster had been removed failed closed at the required missing-
database configuration gate; it was rerun with the correct isolated URL and
passed. Both dedicated clusters were stopped, their loopback port release was
verified, and only their temporary directories were deleted.

## Verification

All commands used Conda environment `reagent-dev`.

| Command/suite | Result |
|---|---|
| OpenAlex adapter/diagnostic focused file | 133 passed |
| complete Cloud API Proxy suite | 195 passed |
| Proxy/OpenAlex PostgreSQL files | 13 passed, zero skipped |
| Workflow Package tests | 43 passed |
| Progress Report tests | 38 passed |
| complete backend with isolated SQL URL | 505 passed, 4 skipped |
| backend compileall | passed |
| Alembic heads/current/check | one head; `20260805_0005`; no drift |
| live Provider/documentation/key access | 0 / 0 / 0 |

The four full-suite skips are pre-existing separately gated integrations: the
destructive HTTP/PostgreSQL demo, historical 9B-1 isolated OpenAlex contract,
historical 9B-1 live OpenAlex, and historical 9A-2 research-v2. No Proxy or
OpenAlex PostgreSQL test skipped.

Green synthetic tests are not live compatibility acceptance. The future
at-most-one-call plan is documented in
`docs/acceptance/R3C_OPENALEX_STRUCTURAL_DIAGNOSTIC_LIVE_ACCEPTANCE.md` and
remains owner-gated.
