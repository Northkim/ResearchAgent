# R3C-A-R4 Post-Remediation One-Call OpenAlex Live Acceptance

Date: 2026-08-05
Status: **BLOCKED AT RESTART STATUS/REPLAY VERIFICATION**

## Result

Retry 4 began from exact clean `main` commit
`110f54ac7c87453a08e61ae26a5d5afbd6b77bb2`. Git, strict owner authorization,
official-only source recheck, fresh PostgreSQL isolation/migrations, pristine
external fictional Package, feature-flag fail-closed probes, supervised key
injection, and one-call token issuance passed.

The provider-neutral client submitted the owner-approved generic public
acceptance query through real loopback Uvicorn and the committed Proxy. The
one OpenAlex call succeeded with five normalized Works, no diagnostic, an
8,726-byte canonical normalized body, zero retries, and exactly 1,000
microusd. Coverage passed for identifier/title/author/DOI/year/venue/language/
abstract mapping, order preservation code paths, unknown-field discard,
constructed links, PDF exclusion, and the canonical size limit. Abstract
TAB/LF/CR were absent after normalization and forbidden controls remained
absent.

Both initial status paths, exact replay, and changed-content conflict passed
without another call, operation, reservation, cost, or diagnostic. SQL,
runtime, Package, response, and Git privacy scans found no retained query
request, plaintext token, credential parameter, authorization header, full
Provider URL, raw body, or arbitrary exception. Query-phrase occurrences were
confined to ordinary normalized Provider-result content. The Package's
34-entry pre/post manifests were byte-identical, and every Hosted/runtime/
Workflow/LLM/Judge/Progress Report row and invocation remained zero.

The same PostgreSQL cluster restarted at sole/current migration
`20260805_0005` with no drift, and the second supervised Uvicorn child became
healthy. The required post-restart provider-neutral status/replay controller
then failed with a value-free `RuntimeError` before producing a safe recovery
artifact. The token was active and the durable ledger remained exactly one
successful operation, one Provider call, and 1,000 microusd. Per owner
instruction, the step was not retried, no replacement token was issued, no
source repair or further acceptance execution occurred, and the required test
matrix was not run.

The token was revoked, both services stopped and released their ports, and all
dedicated database, Package, diagnostic, request/response, token, wrapper, PDF
render, and owner-input material was deleted. ProjectDB, unrelated services,
the account key, repository source, Package bytes, and prior audit history were
untouched.

```text
R3C_A_ATTEMPT = RETRY_4
R3C_A_RETRY_4_ACCEPTANCE = BLOCKED
BLOCKING_REASON = RESTART_STATUS_REPLAY_VERIFICATION_FAILED
R3C_OWNER_AUTHORIZATION = PASS
R3C_SOURCE_RECHECK = PASS
POSTGRESQL_ACCEPTANCE = PASS
EXTERNAL_PACKAGE_ACCEPTANCE = PASS
LIVE_OPENALEX_HTTP_ACCEPTANCE = PASS
R3C_LIVE_OPERATION_OUTCOME = SUCCEEDED_WITH_REAL_RECORDS
OPENALEX_NORMALIZATION_ACCEPTANCE = PASS
R3C_STRUCTURAL_DIAGNOSTIC_EVENT = NOT_TRIGGERED_SUCCESS
OPENALEX_COST_USAGE_ACCEPTANCE = PASS
OPENALEX_QUERY_PRIVACY_ACCEPTANCE = PASS
R3C_IDEMPOTENCY_ACCEPTANCE = PASS
R3C_RESTART_ACCEPTANCE = FAIL
PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
R3C_GIT_CLOSURE = PASS
R3C_LIVE_PROVIDER_CALL_COUNT_THIS_PHASE = 1
R3C_REPORTED_COST_MICROUSD = 1000
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3C_COMPLETE = NOT_COMPLETE
R3C_I2_IMPLEMENTATION_GATE = CLOSED
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

Detailed evidence is in
`docs/acceptance/R3C_OPENALEX_POST_REMEDIATION_LIVE_ACCEPTANCE_RETRY_4_REPORT.md`.
Do not begin R3D. Wait for owner review.
