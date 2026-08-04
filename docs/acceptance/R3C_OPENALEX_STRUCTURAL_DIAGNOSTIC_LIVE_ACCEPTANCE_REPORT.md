# R3C-N2-A Owner-Authorized Live OpenAlex Structural Diagnostic Acceptance

Date: 2026-08-04

Status: **PASS_WITH_WARNINGS — SINGLE OPERATION SUCCEEDED; DIAGNOSTIC NOT TRIGGERED**

This is a diagnostic-only acceptance record. It is not R3C-I2, a complete
R3C-A retry, normalization remediation, or production Provider acceptance.

## 1. Phase status

One owner-authorized Provider operation traversed the external Package
identity, provider-neutral local Proxy client, real loopback Uvicorn/FastAPI,
the separate Proxy ledger in isolated PostgreSQL, and the committed fixed
OpenAlex Works adapter. It succeeded with an empty normalized paper list and
emitted no structural diagnostic. Exact replay and both status reads caused no
second admission, call, reservation, cost, operation, or diagnostic event.

The prior retry-1 normalization failure was not reproduced. No root cause is
inferred and no source remediation is authorized.

```text
R3C_N2_A_ACCEPTANCE = PASS_WITH_WARNINGS
R3C_LIVE_OPERATION_OUTCOME = SUCCEEDED_WITH_NO_DIAGNOSTIC
R3C_STRUCTURAL_DIAGNOSTIC_EVENT = NOT_TRIGGERED_SUCCESS
R3C_DIAGNOSTIC_EVIDENCE = INSUFFICIENT
```

## 2. Initial Git baseline

The phase began on clean `main` at exact commit
`45ef6b500c61a484bd6d4b569b3d4233ab6146a2`
(`R3C-N2-I: add privacy-safe OpenAlex structural diagnostics`). Both status
commands were empty, `git diff --check` passed, and required ancestors
`f5bc017689e97fddbcfffad0581c7c391fb1f021`,
`f78f145b2506400931247d8a669de0ff33367aec`, and
`6ba48416b4936060298b9e5fd9ce197b782b2bb1` were present.

All required repository instructions, context, ADRs 0009 through 0013,
progress/acceptance/audit/architecture/security records, and all three pages of
the teacher architecture PDF were read before execution.

## 3. Owner authorization and attestation

Metadata qualification established that both runtime-only owner paths named
distinct regular, non-symlink mode-`0600` files outside Git, the repository,
`runtime_data`, and every detected Workflow Package. Their parent directories
were mode `0700`.

Only the attestation was read first. It was strict UTF-8 JSON with no duplicate,
unknown, secret-like, executable, or command field. Contract
`reagent-r3cn2-live-structural-diagnostic-owner-attestation/v0.1` bound the exact
baseline and phase and authorized key use, privacy-safe diagnostics, fictional
public queries, one Provider call, 1,000 microusd, at most five results, no
paid/prepaid overage, no Provider-value/raw-response retention, and deletion of
the dedicated local acceptance copies. The attested free daily allowance was
at least USD 0.05.

```text
R3C_OWNER_AUTHORIZATION = PASS
```

## 4. Official OpenAlex source recheck

The recheck completed before key access and contacted only
`developers.openalex.org`, `openalex.org`, and `blog.openalex.org`. It did not
contact the Provider API. SHA-256 covers exact retrieved bytes.

| Retrieved UTC | Official domain and title | Revision/publication | Exact-byte SHA-256 | Affected decision |
|---|---|---|---|---|
| 2026-08-04T15:08:34Z | developers.openalex.org — Overview | 2026-08-03T18:32:01.465Z | `1c55bb3e20ca204fbf2b5b1f41e315de56127cf312df97664efa669e1baf4aa2` | keyed access/free allowance |
| 2026-08-04T15:08:37Z | developers.openalex.org — Authentication & Pricing guide | 2026-06-20T17:21:14.897Z | `25b949ab879de50b77a6d8f5b8fc1eb71462be3498a7d5b173c6b886f5efe03d` | key/pricing/cost/rate evidence |
| 2026-08-04T15:08:48Z | developers.openalex.org — Authentication & Pricing reference | 2026-06-20T17:21:14.899Z | `b563fb62b3360d6b300f516237a8c6d34be1929a2f987563c027129ddfeb1baa` | key/pricing/cost/rate evidence |
| 2026-08-04T15:08:59Z | developers.openalex.org — Search | 2026-06-25T02:18:03.099Z | `5de66b5769cac8d7804c3d5c733d0ab149d7796bd8ad7fbf7977932d1ea0a681` | ordinary `search=` mapping |
| 2026-08-04T15:09:41Z | developers.openalex.org — Deprecations | 2026-02-19T01:12:08.670Z | `7b8bde5192ee1cad731ed3ee06830fc467c4d4994ddd3eaa745de083517c9772` | legacy search exclusion |
| 2026-08-04T15:08:57Z | developers.openalex.org — Works Overview | 2026-06-01T13:43:56.211Z | `e056e251f0450fe965f030604205b7dd1971935bf48e4f323cabad134e5a3fa3` | selected Work fields |
| 2026-08-04T15:10:05Z | developers.openalex.org — List works | 2026-08-03T18:31:54.210Z | `6a06ea78b37116a11daed7132371cb30f39ae4c9004a8765b3ac5d0e57add8ec` | `/works`, `per_page`, `meta.cost_usd` |
| 2026-08-04T15:08:51Z | developers.openalex.org — Select Fields | 2026-02-17T21:24:14.081Z | `7ebf3f06729e0d53ecee57ebd05a925be7d277271959387be8b3fc5cbfc7e9fc` | fixed top-level select list |
| 2026-08-04T15:08:48Z | developers.openalex.org — Error Handling | 2026-02-19T00:53:51.039Z | `a837a68a5dde561430f1d5dfe0c673bed2de9821a369c50ce1517b59dd448cd1` | rate/error semantics |
| 2026-08-04T15:08:59Z | developers.openalex.org — Check rate limit status | 2026-08-03T18:31:54.190Z | `1ed0893395fb24d37619967a0883f01ed06f9466bffd6349259e91bb75f08f0b` | safe rate evidence names only; endpoint not called |
| 2026-08-04T15:09:29Z | openalex.org — Terms of Service | last revised 2024-02-07 | `b59bcbd2ed0fb550d35a989961c47b8fc29f22be89167e9c4789cdf1c4fa5fc4` | eligibility/third-party rights |
| 2026-08-04T15:09:29Z | openalex.org — Privacy Policy and Promise | last revised 2026-02-17 | `97b8eb0f03b06819f50d1b7b345eaad6847aa63283684f6535f1809fbdbfb67c` | key/query/technical metadata disclosure |
| 2026-08-04T15:08:36Z | blog.openalex.org — New Features and Usage-Based Pricing | published 2026-02-25T02:44:20Z; modified 2026-02-25T02:59:07Z | `6aa69b43415a2bf1588a4e599ead1a4a2cfeae3fd410ff9ee75dfca10a9dcc7d` | pricing rollout context |

Twelve objects matched the committed/retry ledger exactly. The pricing blog
changed bytes non-materially; its title, publication metadata, API-key/free-
allowance explanation, ordinary-search price, and `search=` direction remained
compatible. The gate reconfirmed API-key authentication and the committed
`api_key` mechanism, fixed Works path, ordinary `search=`, all eight selected
fields, `per_page=5`, exact USD 0.001 search price, `meta.cost_usd`, and the four
approved X-RateLimit fields. Terms and Privacy were byte-identical to their
previous complete reviews and did not materially contradict the narrow
fictional supervised diagnostic. This engineering review is not legal advice.

```text
R3C_SOURCE_RECHECK = PASS
```

## 5. PostgreSQL isolation and migration

A fresh data-checksummed PostgreSQL 18.1 cluster listened only on
`127.0.0.1:53129`. It contained separate databases
`reagent_r3cn2a_acceptance` and `reagent_r3cn2a_tests`; ProjectDB was absent and
untouched.

Both databases upgraded from empty to the sole head `20260805_0005`. Final
`alembic heads`, `current`, and `check` confirmed one head, current at head, and
no drift. Proxy schema inspection found no diagnostic, query-text, raw-body,
plaintext-key, credential-URL, or Authorization-header column. OpenAlex
`request_json` remained checksum-only. The only Proxy-operation foreign key
targeted `proxy_capability_tokens`, not Hosted run/step/provider state.

```text
POSTGRESQL_ACCEPTANCE = PASS
```

## 6. External Package evidence

The committed compiler produced and pristine-validated a fresh external
fictional Package:

- Package ID: `literature-search-fictional-r3cn2a-observatory-v0.2`;
- Package checksum:
  `sha256:9fdb3fcf4eefd36a463b7dacc670dd43d22dba94b388022fa25b95ff4cc68314`;
- manifest checksum:
  `sha256:10a5a6a30b950b4e6db8a598f78ea2dc9c3434e2925e8224f052b05c28b6cac7`;
- Workflow checksum:
  `sha256:8d25d7cd32a89e84ba8885454782cb923e93224df4637ddf6183af2a16f3980c`;
- compiler ZIP checksum:
  `sha256:08cbc22b604f7ef54dee6013650690d07388c618c3a612d1e09f5af68679bd50`.

The protected pre-manifest bound 34 relative entries by type, size, and SHA-256
and had checksum
`sha256:50350465f6646986e68aed397b5d53b72131e91e93243bbc965a07c940df99eb`.
The Package contained only fictional inputs, no credential/token, no live
Provider configuration, and no machine-specific path. Its disabled compiler-
supplied Proxy example remained outside the live runtime authority; the token
scope selected the adapter server-side.

```text
EXTERNAL_PACKAGE_ACCEPTANCE = PASS
```

## 7. Credential and capability-token lifecycle

Only after owner and source gates passed, an outside-Git wrapper opened the key
copy as a regular non-symlink file, trimmed at most one terminal line ending,
rejected empty/control/multiline content without printing any property, set
only `REAGENT_OPENALEX_API_KEY`, removed the owner path variables, and
immediately exec'd the Uvicorn child. The key was never a command argument,
`.env` entry, Package value, SQL value, checksum, log field, response, or
tracked evidence item.

The committed operator CLI issued one mode-`0600` OpenAlex-bound token for the
exact project/Package/Workflow/capability/adapter scope. Its operation and
Provider-call maxima were both one. The committed token cost field remained
50,000 microusd because the CLI has no narrower cost option; the independent
phase ledger enforced exactly 1,000 microusd. PostgreSQL retained only its
digest and safe metadata. The local client received token plaintext only from
`REAGENT_PROXY_TOKEN`. The token was revoked with final counters one admission,
one call, 1,000 reserved, and 1,000 reported microusd.

## 8. Feature flags and diagnostic log

Diagnostics and the OpenAlex Proxy were default-off. Exact `1` enabled each
independently. A real diagnostic-flag-only Uvicorn probe returned health 200 and
Proxy-route 404 without SQL or credential loading. OpenAlex-enabled composition
failed closed without SQL and failed closed without a credential.

The accepted process explicitly enabled:

```text
REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED=1
REAGENT_EXPERIMENTAL_OPENALEX_STRUCTURAL_DIAGNOSTICS_ENABLED=1
```

The fake Proxy flag was absent. One new mode-`0600` log received only the
dedicated canonical logger and remained zero bytes before the call, after the
operation, after status/replay, and after server shutdown. Access logging was
disabled; free-form exception traces and outbound request-line logging were not
enabled.

## 9. Live Uvicorn and fixed-origin network

The committed `backend.api.app:app` entrypoint ran under real Uvicorn on
literal `127.0.0.1:53130` with proxy-header parsing and access logging disabled.
Health returned 200. The provider-neutral client used only loopback HTTP.

The committed adapter fixed the sole outbound host and `/works` path, required
TLS verification, disabled redirects and ambient proxies, applied the ten-
second/512-KiB bounds, and had zero retry, pagination, `/rate-limit`, content,
PDF, fallback-Provider, or secondary-endpoint path. The independent SQL ledger
recorded exactly one Provider request.

```text
LIVE_OPENALEX_DIAGNOSTIC_HTTP_ACCEPTANCE = PASS
```

## 10. Single live Provider-call ledger

```text
newly admitted Proxy operations = 1
actual Provider HTTP calls = 1
reserved cost = 1000 microusd
reported cost = 1000 microusd
automatic retries = 0
rate-limit endpoint calls = 0
pagination/content/PDF/other-Provider calls = 0
```

The request used one UUIDv4 idempotency key, a valid client timestamp, exact
canonical content checksum, `max_results=5`, and one runtime-only fictional
public query. The exact request bytes existed only in a protected temporary
mode-`0600` file and were deleted after exact replay and leakage scanning.

## 11. Live operation outcome

The operation succeeded with zero normalized paper records. It did not
reproduce retry 1's `PROVIDER_INVALID_RESPONSE`, so no diagnostic path was
executed and no root cause can be inferred.

Safe operation evidence:

- operation ID:
  `proxyop-v1-20c2c51b359135170f851a9e3ae6f94e2ccb87b3a17ce41ac08e340d1a4ce864`;
- request-content checksum:
  `sha256:39eb9cb0a0232fae72987dac6d9a26d4cd959d922e4a7ec78dd95da351fdb437`;
- provider-data checksum:
  `sha256:5ccd7f755a1f1d2b2bbebfedcf30750841cef4540db124487ff011619ae73f20`;
- response-content checksum:
  `sha256:895fae7545cb4b9bf9a2c8a33b00fb06a8b9ca376dfc74747c97ac0c920eed88`;
- Provider-response checksum:
  `sha256:ff3cb16bb1b617ae7d8b2498aeb38efb2cd538fc92bfdb8383a9eaf1e1067c35`.

```text
R3C_LIVE_OPERATION_OUTCOME = SUCCEEDED_WITH_NO_DIAGNOSTIC
```

## 12. Structural diagnostic event

The temporary diagnostic sink contained zero nonempty lines. No event was
expected for a successful operation. Normal submit/status/replay responses
contained no diagnostic field.

```text
event count = 0
R3C_STRUCTURAL_DIAGNOSTIC_EVENT = NOT_TRIGGERED_SUCCESS
R3C_DIAGNOSTIC_EVIDENCE = INSUFFICIENT
```

## 13. Cost and rate-limit evidence

The Provider response was HTTP 200 and reported exact USD 0.001, persisted and
compared as 1,000 integer microusd without binary float. Safe rate evidence was
`rate_limit_limit=10000`, `rate_limit_remaining=9980`,
`provider_credits_used="10"`, and `rate_limit_reset="30985"`. Provider credits
remained a separate decimal string and were not interpreted as USD.

## 14. Status and exact replay

Status by operation ID and by scoped idempotency identity returned the same
terminal operation. The replay read and resubmitted the exact protected request
bytes. It returned `REPLAYED`; the original returned `CREATED`.

Across create, both status reads, and replay, operation status, operation ID,
request checksum, provider-data checksum, response-content checksum, and safe
error state were identical. SQL remained one operation, one admission, one
call, one reservation, and one cost settlement. The diagnostic event count
remained zero.

```text
R3C_STATUS_AND_REPLAY = PASS
```

## 15. Query, key, token, URL, raw-body and value privacy audit

Private scans covered every SQL text/JSON value through a protected data dump,
the complete dedicated PostgreSQL files, structured/server/client/operator
logs, submit/status/replay responses, Package files, temporary non-secret
evidence, and tracked Git state.

Results:

- exact query matches outside the protected request file: zero;
- query-marker matches outside the protected request file: zero;
- capability-token plaintext matches outside its token file/transient header:
  zero;
- credential-bearing URL or Authorization-header runtime matches: zero;
- raw Provider-body artifacts: zero;
- normalized Provider paper records/values: zero;
- diagnostic events/values: zero;
- normal response diagnostic fields: zero.

The key file was not reread after injection, preserving the key-read boundary.
Every possible sink was instead exhaustively inspected: the diagnostic/server
logs were empty of credential/query material, SQL had no credential/raw-body
column or value, requests/responses never carried the key, and the wrapper's
only post-read action was environment injection followed by exec. The exact
key copy and all transient process/runtime material were then deleted.

```text
R3C_DIAGNOSTIC_PRIVACY_BOUNDARY = PASS
```

## 16. Package non-mutation

The post-manifest again contained 34 entries and had the same
`sha256:50350465f6646986e68aed397b5d53b72131e91e93243bbc965a07c940df99eb`
checksum. Its bytes were exactly equal to the pre-manifest, and pristine
Package validation passed after replay.

```text
PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
```

## 17. Runtime and Hosted boundary

Before and after counts remained zero for Hosted `provider_operations`,
WorkflowRun, StepRun, ExecutionEvent, Checkpoint, checkpoint-boundary records,
MemoryRevision, and uploaded Progress Reports. No AgentRuntime,
ExecutionDispatcher, Workflow execution/resume, Hosted research Skill, LLM,
structured generation, Judge/evaluation, automatic Progress Report operation,
Package/context/output mutation, fallback Provider, retry, or pagination ran.

```text
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
```

## 18. Tests and skips

All commands used Conda environment `reagent-dev`.

| Suite/check | Result |
|---|---|
| focused OpenAlex adapter/diagnostic | 133 passed |
| complete Cloud API Proxy | 195 passed |
| Proxy/OpenAlex PostgreSQL files | 13 passed, zero skipped |
| Workflow Package | 43 passed |
| Progress Report | 38 passed |
| complete backend | 505 passed, 4 skipped |
| compileall | passed |
| Alembic heads/current/check | one head; `20260805_0005`; no drift |
| final `git diff --check` before documentation | passed |

The four backend skips are pre-existing, separately gated integrations: the
destructive demo database, historical 9B-1 isolated OpenAlex contract,
historical 9B-1 live OpenAlex, and historical 9A-2 research-v2. No Proxy or
OpenAlex PostgreSQL test skipped. Synthetic tests are not represented as live
compatibility acceptance.

## 19. Cleanup

The capability token was revoked. Uvicorn and dedicated PostgreSQL stopped,
and both loopback ports were released. The token file, diagnostic/server/client
logs, request bytes, response/dump evidence, wrappers/config, artifact root,
external Package/build receipts/ZIP, source downloads, teacher-PDF render,
database cluster, exact owner attestation copy, and exact owner key copy were
deleted. Empty owner directories were removed where applicable.

Post-cleanup checks proved absence of both owner copies, all dedicated
temporary roots, the token, diagnostic log, Package, Uvicorn listener,
PostgreSQL listener, and tracked runtime material. ProjectDB and unrelated
PostgreSQL services were untouched. The OpenAlex account and account key were
not rotated or deleted.

## 20. Append-only documentation

This new report and
`.agent_read/progress/r3c_openalex_structural_diagnostic_live_acceptance.md`
are append-only. `.agent_read/context.md` is updated only with the current
result and next gate. Earlier attempt, retry, forensic, implementation, ADR,
contract, Package-template, test, migration, frontend, backend, and Progress
Report evidence remains unchanged.

## 21. Commit evidence

Exactly one documentation evidence commit is required with message
`R3C-N2-A: record live OpenAlex structural diagnostic`. The resulting hash is
reported in the final owner handoff because embedding a commit's own identity
inside its contents would be self-referential. No push is authorized.

## 22. Final Git state

Before staging, the only intended paths are this report, the new progress
record, and `.agent_read/context.md`. Final status/porcelain, whitespace, and
`git show` evidence are collected after the single commit; the worktree must be
clean.

## 23. Remaining uncertainty

- Retry 1's exact live failure path remains unknown.
- This operation returned zero normalized records, so none of the per-Work,
  authorship, abstract, model, serialization, result-size, or service-safety
  diagnostic branches was exercised live.
- A successful empty result does not prove compatibility for arbitrary current
  OpenAlex Works records and does not justify a normalization change.
- Production authentication, multi-user authorization, public HTTPS, proof of
  possession, paid/prepaid use, production secret management/retention,
  frontend work, and Claude Code remain outside this acceptance.

The next action is owner review only. Do not open R3C-I2 or start another live
call from this evidence.

## 24. R3 gates

```text
R3C_N2_A_ACCEPTANCE = PASS_WITH_WARNINGS
R3C_OWNER_AUTHORIZATION = PASS
R3C_SOURCE_RECHECK = PASS
POSTGRESQL_ACCEPTANCE = PASS
EXTERNAL_PACKAGE_ACCEPTANCE = PASS
LIVE_OPENALEX_DIAGNOSTIC_HTTP_ACCEPTANCE = PASS
R3C_LIVE_OPERATION_OUTCOME = SUCCEEDED_WITH_NO_DIAGNOSTIC
R3C_STRUCTURAL_DIAGNOSTIC_EVENT = NOT_TRIGGERED_SUCCESS
R3C_DIAGNOSTIC_PRIVACY_BOUNDARY = PASS
R3C_DIAGNOSTIC_EVIDENCE = INSUFFICIENT
R3C_STATUS_AND_REPLAY = PASS
PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
R3C_LIVE_PROVIDER_CALL_COUNT_THIS_PHASE = 1
R3C_REPORTED_COST_MICROUSD = 1000
R3C_DIAGNOSTIC_LIVE_CALL_GATE = CLOSED_AFTER_ATTEMPT
R3C_I2_IMPLEMENTATION_GATE = CLOSED
R3C_FULL_LIVE_ACCEPTANCE_GATE = CLOSED
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```
