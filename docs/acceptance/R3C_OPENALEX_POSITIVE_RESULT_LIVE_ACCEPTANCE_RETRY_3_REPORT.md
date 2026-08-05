# R3C-A-R3 One-Call Positive-Result OpenAlex Live Acceptance Retry

Date: 2026-08-05

Status: **BLOCKED AFTER SPECIFIC LIVE STRUCTURAL DIAGNOSTIC**

Baseline: `a4041af136b673ed58708019f24f2be5dafc5351`
(`R3C-A-R2: record incomplete positive-result OpenAlex retry`), branch `main`,
with an initially clean worktree.

This is the immutable append-only retry-3 evidence record. It does not amend,
delete, replace, reinterpret, or supersede attempt 0, retry 1, R3C-N1,
R3C-N2-I, R3C-N2-A, or retry 2.

## 1. Phase Status

The Git, owner-authorization, official-source, isolated PostgreSQL, external
Package, feature-flag, credential, and token gates passed. The one authorized
Provider call returned HTTP 200 and exact USD 0.001 reported cost, but strict
whole-response normalization failed. The enabled value-free diagnostic emitted
exactly one specific event at `ABSTRACT_RECONSTRUCTION`; no partial result was
returned or retained. Production source was not changed and no remediation was
attempted.

```text
R3C_A_ATTEMPT = RETRY_3
R3C_A_RETRY_3_ACCEPTANCE = BLOCKED
BLOCKING_REASON = LIVE_RESPONSE_FAILED_STRICT_NORMALIZATION_WITH_SPECIFIC_STRUCTURAL_DIAGNOSTIC
```

## 2. Initial Git Baseline and Prior Attempt History

The initial gate passed exactly: repository root was ResearchAgent, HEAD was
`a4041af136b673ed58708019f24f2be5dafc5351`, branch was `main`, both status
commands were empty, there were no staged or untracked files, and
`git diff --check` passed. The seven-entry history contained the required
R3C-A-R2, R3C-N2-A, R3C-N2-I, R3C-N1, R3C-A-R1, attempt-0, and R3C-I commits.

The history remains distinct:

- attempt 0 stopped at its owner-attestation gate;
- retry 1 received HTTP 200 but failed approved normalization without enough
  evidence to identify the predicate;
- R3C-N1 was an offline forensic investigation and remained inconclusive;
- R3C-N2-I added the value-free diagnostic contract without changing strict
  normalization;
- R3C-N2-A made one live call, received zero records, and emitted no diagnostic;
- retry 2 stopped at the free-daily-allowance authorization gate with zero
  calls and zero cost;
- retry 3 made exactly one new call and produced the specific value-free
  diagnostic recorded below.

No reset, restore, checkout, rebase, clean, amend, squash, or history rewrite
was used.

## 3. Owner Authorization

Before either owner file was read, both runtime path variables existed and
their distinct targets were verified as regular, non-symlink, mode-`0600`
files with mode-`0700` non-symlink parents, outside Git, the repository,
`runtime_data`, and every detected Workflow Package.

The attestation was read first as strict UTF-8 JSON with duplicate-key
rejection. It had exactly the required field set and contract, exact baseline
and phase, one-call/1,000-microusd/five-result ceilings, test-only generic
public query declaration, no-overage declaration, deletion authority, and at
least USD 0.05 attested free daily allowance. It contained no credential,
command, executable content, or extension field. The key was not read before
this gate and the source recheck passed.

```text
R3C_OWNER_AUTHORIZATION = PASS
```

## 4. Official OpenAlex Source Recheck

The pre-key recheck contacted only the approved official documentation,
Terms, Privacy, and pricing-blog domains; it did not contact the Provider API.
Developer-document fingerprints below cover the official Markdown
representations, and Terms/Privacy fingerprints cover the retrieved PDFs.

| Retrieved UTC | Official source | Revision/publication | SHA-256 |
|---|---|---|---|
| 2026-08-05T04:46:20Z | [Overview](https://developers.openalex.org/) | 2026-08-03T18:32:01.465Z | `b9bdbf9a01e5dbbd55bd2d3cc89d68118b2725c70a73694641b30867f04e1c6f` |
| 2026-08-05T04:46:21Z | [Authentication & Pricing guide](https://developers.openalex.org/guides/authentication) | 2026-06-20T17:21:14.897Z | `3d26c9b0129ec4c688fd698b10511bcf976e12ba75a10e008984ee24f46cf8a2` |
| 2026-08-05T04:46:22Z | [Authentication & Pricing reference](https://developers.openalex.org/api-reference/authentication) | 2026-06-20T17:21:14.899Z | `1fe7b64818aba93b1a7902e27f96e692f484b2cc82b91fa60b42cdcfcdabc4bf` |
| 2026-08-05T04:46:22Z | [Search](https://developers.openalex.org/guides/searching) | 2026-06-25T02:18:03.099Z | `9c9a9fea46676c5fc4e1114d3a4dad8ad8327c2d8de793eb47b3338f1b7a9092` |
| 2026-08-05T04:46:23Z | [Deprecations](https://developers.openalex.org/guides/deprecations) | 2026-02-19T01:12:08.670Z | `2cdb6e3b0f13b95042fd801ff44c0ee91e79b1e0d191d6c50dd61571dae9f069` |
| 2026-08-05T04:46:23Z | [Works overview](https://developers.openalex.org/api-reference/works) | 2026-06-01T13:43:56.211Z | `c0ae79f3d57620271c77efd887ea810e3e7e4b25204fe8634b930f21c0609d79` |
| 2026-08-05T04:46:24Z | [List works](https://developers.openalex.org/api-reference/works/list-works) | 2026-08-03T18:31:54.210Z | `23c65f6a6af2a05bf2314e5c6e8db6eca5612cabe93c120c2f8e79e3a4a1f09a` |
| 2026-08-05T04:46:25Z | [Select fields](https://developers.openalex.org/guides/selecting-fields) | 2026-02-17T21:24:14.081Z | `1472eb466ee77c393a6861ed9ab1ab53d9c8212196376495e888a6ea9e42800d` |
| 2026-08-05T04:46:26Z | [Error handling](https://developers.openalex.org/api-reference/errors) | 2026-02-19T00:53:51.039Z | `dfb88b094ce704e85005e630962d1171295697f0a651231d9217d277c114d5b2` |
| 2026-08-05T04:46:26Z | [Rate-limit status](https://developers.openalex.org/api-reference/rate-limits/check-rate-limit-status) | 2026-08-03T18:31:54.190Z | `ec2eb8650f682b3b047b3e611eb4d700744c8fd2bd4afc2291a9dd2bf2a4f825` |
| 2026-08-05T04:44:52Z | [Terms of Service](https://openalex.org/OpenAlex_termsofservice.pdf) | revised 2024-02-07 | `b59bcbd2ed0fb550d35a989961c47b8fc29f22be89167e9c4789cdf1c4fa5fc4` |
| 2026-08-05T04:44:54Z | [Privacy Policy and Promise](https://openalex.org/OpenAlex_privacy_policy.pdf) | revised 2026-02-17 | `97b8eb0f03b06819f50d1b7b345eaad6847aa63283684f6535f1809fbdbfb67c` |
| 2026-08-05T04:44:57Z | [Usage-Based Pricing](https://blog.openalex.org/openalex-api-new-features-and-usage-based-pricing/) | published 2026-02-25T02:44:20Z; modified 2026-02-25T02:59:07Z | `67b53f76b6895b91c7491761f87db41d84b8614b1dfc05fa9b63715e7f67869e` |

Mintlify HTML wrapper bytes changed non-materially; the official Markdown
content and page revisions reconfirmed `api_key` authentication, fixed
`GET /works`, ordinary `search=`, the fixed selected fields, `per_page=5`,
exact USD 0.001 ordinary-search cost, `meta.cost_usd`, and the approved
X-RateLimit evidence names. No `/rate-limit` call was made. Terms and Privacy
remained compatible with the narrow supervised, non-sensitive experiment.
This engineering review is not legal advice.

```text
R3C_SOURCE_RECHECK = PASS
```

## 5. PostgreSQL Isolation and Migration

A fresh data-checksummed PostgreSQL 18.1 cluster listened only on a unique
loopback port. It contained separate `reagent_r3ca3_acceptance` and
`reagent_r3ca3_tests` databases and no unrelated database or service.
ProjectDB was never accessed.

The acceptance database upgraded from empty to the sole head
`20260805_0005`; final `heads`, `current`, and `check` confirmed one head and
no drift. Exact integer microusd and Provider-call counters, query checksum and
length columns were present. Schema inspection found no query-text, raw-body,
plaintext-key, credential-bearing-URL, authorization-header, or diagnostic
column, and no Hosted Workflow/step/provider foreign key.

The test database was independently upgraded to the same head before its final
zero-skip PostgreSQL suite.

```text
POSTGRESQL_ACCEPTANCE = PASS
```

## 6. External Package Evidence

The committed compiler produced and pristine-validated a fresh fictional
external Package:

- Package ID: `literature-search-fictional-r3ca3-positive-v0.2`;
- Package checksum:
  `sha256:90de8594205f25678f11ec9b821a06a1d111fd7e58eecede6e7ec185d7f13626`;
- manifest checksum:
  `sha256:4e9bcdbaa1878ab9a50dcc9c1e7b3db198434d3fcef21e8ef660961c0568feb3`;
- Workflow checksum:
  `sha256:8d25d7cd32a89e84ba8885454782cb923e93224df4637ddf6183af2a16f3980c`;
- compiler ZIP checksum:
  `sha256:963f7401e8aea23948b9fb90bd611d50d365a09e6438e7d7dcc86681db7fb12f`.

Its protected 34-entry recursive pre-manifest used only relative paths, file
type, size, and SHA-256 and had checksum
`sha256:93e9b474849f9de6c9c471c9a82a951e314db19ae85eb1438ce4420cb7592d89`.
The live request remained provider-neutral; the server-owned token scope alone
selected the adapter. No credential, token, private request, live Provider
evidence, or machine-specific path entered the Package.

```text
EXTERNAL_PACKAGE_ACCEPTANCE = PASS
```

## 7. Credential and Token Lifecycle

Only after the preceding gates passed, an outside-Git wrapper opened the key
copy as a regular non-symlink mode-`0600` file, trimmed at most one terminal
line ending, rejected empty/control/multiline content, set only
`REAGENT_OPENALEX_API_KEY`, removed the owner-path variables, and immediately
exec'd Uvicorn. It never printed, measured, hashed, or otherwise represented
the key. The key was never a command argument, `.env` entry, SQL value,
Package value, checksum, log field, response, or tracked evidence item.

The committed operator CLI issued one mode-`0600` OpenAlex-bound capability
token for the exact project, Package, Workflow, capability, and adapter. Its
operation and Provider-call maxima were one. The CLI exposes no narrow cost
argument, so the independent attested live ledger enforced the 1,000-microusd
ceiling. PostgreSQL retained only the token digest and safe scope metadata.
The local provider-neutral client received only `REAGENT_PROXY_TOKEN`.

After all checks the token was revoked with final counters of one admission,
one Provider call, 1,000 microusd reserved, and 1,000 microusd reported. Its
plaintext file was deleted. The exact authorized local key and attestation
copies were deleted; the owner's OpenAlex account key was not changed.

## 8. Feature Flags, Diagnostic Log and Uvicorn

Real committed-ASGI Uvicorn probes established:

1. OpenAlex was disabled by default;
2. the diagnostic flag alone did not mount the Proxy;
3. OpenAlex enabled without explicit SQL failed closed;
4. OpenAlex enabled with SQL but without the credential failed closed;
5. both flags plus the isolated SQL database and supervised credential started;
6. no fake, Hosted, or in-memory fallback became active; and
7. adapter selection came only from server-owned token scope.

The accepted process bound literal `127.0.0.1` on a unique non-default port
with access logging disabled. The dedicated structural-diagnostic log was
outside Git and the Package, mode `0600`, and contained one canonical JSON
line. No request body, query parameters, full Provider URL, HTTPX request
representation, authorization header, or value-bearing exception trace was
logged.

## 9. Single Provider Call Ledger

```text
new Proxy operations = 1
new admissions = 1
actual OpenAlex Provider calls = 1
reported cost = 1000 microusd
automatic retries = 0
/rate-limit calls = 0
pagination/content/PDF/full-text/other-Provider calls = 0
R3C_LIVE_PROVIDER_CALL_COUNT_THIS_PHASE = 1
R3C_REPORTED_COST_MICROUSD = 1000
```

The request used one UUIDv4 idempotency key, one valid client timestamp, the
owner-approved generic public acceptance query after normal outer trimming,
and `max_results=5`. It contained no marker, Boolean syntax, quotes, filters,
cursor, pagination, rewrite, or Provider selector. Its exact canonical bytes
were protected for the authorized replay and had request checksum
`sha256:5cf037e30b7f4cfdb4c80f6672a45e02d48181bb50b63be5b17863a483757a92`.

## 10. Live Operation Outcome

Operation
`proxyop-v1-0eeff83a6d1a767e4a5070e47e41b7d34aca0a7b38656460122a454a123869d7`
received Provider HTTP 200, then settled durably as
`FAILED / PROVIDER_INVALID_RESPONSE`. Strict normalization returned no
Provider data and no record. The immutable response-content checksum was
`sha256:79863e5232dcce30d5bcb1e57f12d8f0decdaee2eb9383f58bc1bfa3754d61bd`;
the Provider-response checksum was
`sha256:2966a934138c5a646e7dfad10eab47b222d461ba2ed4dd8dc1d9d137afa4ed7d`.

```text
LIVE_OPENALEX_HTTP_ACCEPTANCE = FAIL
R3C_LIVE_OPERATION_OUTCOME = FAILED_WITH_SPECIFIC_STRUCTURAL_DIAGNOSTIC
```

## 11. Real-Record Normalization

The diagnostic states that one record normalized before a later record failed,
but accepted policy is `STRICT_COMPLETE_RESPONSE_FAILURE`: no partial subset,
quarantine, or success body is permitted. Consequently the canonical returned
record count and size were both zero; no real Work was accepted, exposed, or
retained, and the positive-result requirements could not be evaluated as a
successful response. No title, author, DOI, abstract, venue, Provider/PDF URL,
or raw Provider body was placed in evidence.

```text
OPENALEX_NORMALIZATION_ACCEPTANCE = FAIL
```

## 12. Structural Diagnostic Event

Exactly one `reagent.openalex-structural-diagnostic/v0.1` event was emitted and
validated against the closed registry:

```text
failure_stage = ABSTRACT_RECONSTRUCTION
approved_json_path = /results/*/abstract_inverted_index
record_index = 1
nested_element_index = 2
observed_kind = CONTROL_CHARACTER
validator_code = ABSTRACT_TOKEN_CONTROL
normalized_records_before_failure = 1
structural_shape_checksum = sha256:7703adcdfe83743a838ab6201a72dab1d7e120e6933b29d799b76e2ab8b2ad18
diagnostic_log_checksum = sha256:47c99c4d74eefc30899381805ba38f802d5b70096a5f61f9db467f8091f8a753
```

The event correlated to the operation and request checksum, contained no
Provider field value, and did not appear in the public response or SQL. Replay
and conflict produced no second event. This identifies the rejected predicate
class for owner review without disclosing or retaining the rejected value. It
does not authorize remediation.

```text
R3C_STRUCTURAL_DIAGNOSTIC_EVENT = SPECIFIC
R3C_DIAGNOSTIC_EVIDENCE = SUFFICIENT_FOR_OWNER_REVIEW
```

## 13. Exact Cost and Privacy Audit

Provider HTTP category 200 and `meta.cost_usd=0.001` were accounted as exact
integer 1,000 microusd. The operation and token rows each settled one call,
1,000 microusd reserved, and 1,000 microusd reported. Provider credits remained
separate from USD and no binary float was used for persistence or comparison.

All 172 PostgreSQL text/JSON fields and the protected diagnostic, server,
client/operator-response, Package, and tracked-change surfaces were scanned.
Outside the authorized token and request source files there were zero matches
for token plaintext or the owner-approved generic public acceptance query.
There were also zero matches for authorization headers, full Provider URLs, or
API-key parameters. The query had zero matches in every PostgreSQL text/JSON
field, status/replay/conflict response, error field, diagnostic field, server
log, Package file, and tracked change. The key was not re-read for audit; the
single-read injection boundary and absence of any credential-bearing sink were
verified instead. No raw-body column/file or plaintext-key column existed, and
failed `provider_data` was null.

```text
OPENALEX_COST_USAGE_ACCEPTANCE = PASS
OPENALEX_QUERY_PRIVACY_ACCEPTANCE = PASS
```

## 14. Status, Replay and Conflict

Status by operation ID and by scoped Package/idempotency identity both returned
the same durable failed operation. Exact replay using the original stored bytes
returned `REPLAYED` with the same operation ID, status, request checksum,
response-content checksum, Provider-response checksum, error category, one
Provider-call count, and 1,000-microusd reported cost.

Changed canonical content under the same token/idempotency identity, with its
checksum recomputed correctly, returned HTTP 409 `IDEMPOTENCY_CONFLICT`. Final
SQL state remained one token row, one operation row, one admission, one call,
one reservation, one settlement, and one diagnostic event. There was no second
Provider call, operation, admission, cost reservation, or diagnostic event.

```text
R3C_IDEMPOTENCY_ACCEPTANCE = PASS
```

## 15. Backend and PostgreSQL Restart

The restart path was not run because it is authorized only for
`SUCCEEDED_WITH_REAL_RECORDS`. No restart acceptance is claimed for a failed
strict-normalization result.

```text
R3C_RESTART_ACCEPTANCE = NOT_RUN
```

## 16. Package Non-Mutation

The post-acceptance Package again validated pristine. Its recursive 34-entry
post-manifest was byte-identical to the pre-manifest and had the same
`sha256:93e9b474849f9de6c9c471c9a82a951e314db19ae85eb1438ce4420cb7592d89`
checksum. No input, output, memory/context, memory/progress, prompt, Skill,
instruction, manifest, or cloud-configuration byte changed.

```text
PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
```

## 17. Runtime and Hosted Boundary

Before and after the operation, Hosted ProviderOperation, WorkflowRun, StepRun,
ExecutionEvent, Checkpoint, checkpoint-record, MemoryRevision, uploaded
Progress Report, and progress-projection rows were zero. AgentRuntime,
ExecutionDispatcher, Hosted Skills, Workflow execution/resume, LLM/structured
generation, Judge/evaluation, and automatic Progress Report generation/upload
were never invoked. Only one Proxy token row and one Proxy operation row
existed in the isolated acceptance database before cleanup.

```text
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
```

## 18. Tests and Skips

Final qualification in Conda environment `reagent-dev` passed:

- focused OpenAlex adapter: 133 passed;
- complete Proxy suite: 195 passed;
- isolated Proxy/OpenAlex PostgreSQL files: 13 passed, zero skipped;
- Workflow Package suite: 43 passed;
- Progress Report suite: 38 passed;
- aggregate backend: 505 passed, four skipped;
- `compileall`: passed;
- acceptance Alembic `heads`, `current`, `check`: sole head
  `20260805_0005`, current, no drift;
- final pre-documentation `git diff --check`: passed.

The four aggregate skips were the separately gated destructive HTTP demo,
9B-1 contract integration, historical 9B-1 live OpenAlex integration, and 9A-2
research integration. The historical Hosted live test was not used as evidence.

Two setup invocations were corrected without source change: the initially
empty test database first reported 13 setup errors until the committed
migrations were applied, and an aggregate invocation without the isolated test
URL reported those 13 mandatory PostgreSQL tests as errors. The corrected
isolated invocations produced the zero-skip 13-test result and the final
505-pass aggregate result above.

## 19. Cleanup

The capability token was revoked before shutdown. Uvicorn stopped cleanly and
its loopback port was released. The dedicated PostgreSQL process identity was
verified, that cluster alone stopped cleanly, and its port was released.

The capability-token file, structural-diagnostic log, protected request and
response files, external fictional Package, server/configuration logs, source
downloads, temporary wrappers, and dedicated PostgreSQL data directory were
deleted. The exact authorized owner attestation and local key copies were
deleted and their owner directory was removed when empty. The account key,
ProjectDB, unrelated PostgreSQL services, and all unrelated files were
untouched. Both dedicated ports remained released after cleanup.

## 20. Append-Only Documentation

Only this new retry-3 report, the new retry-3 progress record, and
`.agent_read/context.md` are changed. All earlier acceptance/forensic/
implementation records, production/backend/frontend source, migrations,
tests, fixtures, Package templates, contracts, ADRs, and
`progress-report/v0.2` remain unchanged. The project plan required no vision or
goal change.

## 21. Commit Evidence

Exactly one documentation-only evidence commit is required with message
`R3C-A-R3: record incomplete positive-result OpenAlex retry`. Its identity is
reported in the final owner handoff because embedding a commit's own hash in
its contents would be self-referential. No push is authorized.

## 22. Final Git State

Before staging, scope, whitespace, secret, prohibited-query, and prohibited-
path checks must show only the three approved documentation paths. After the
sole evidence commit, the worktree must be clean.

## 23. Remaining Warnings

- Retry 3 did not produce an accepted positive result; R3C remains pending.
- Retry 1's unexplained normalization failure remains an explicit warning.
  Retry 3's specific diagnostic does not retrospectively identify retry 1's
  exact predicate because retry 1 preserved no structural event.
- The specific retry-3 event is owner-review evidence, not authorization to
  weaken normalization, add partial success/quarantine, or implement R3C-I2.
- Restart acceptance was correctly not run because no real record was accepted.
- R3C-I2 and R3D remain closed.

## 24. R3 Final Gate

```text
R3C_A_ATTEMPT = RETRY_3
R3C_A_RETRY_3_ACCEPTANCE = BLOCKED
R3C_OWNER_AUTHORIZATION = PASS
R3C_SOURCE_RECHECK = PASS
POSTGRESQL_ACCEPTANCE = PASS
EXTERNAL_PACKAGE_ACCEPTANCE = PASS
LIVE_OPENALEX_HTTP_ACCEPTANCE = FAIL
R3C_LIVE_OPERATION_OUTCOME = FAILED_WITH_SPECIFIC_STRUCTURAL_DIAGNOSTIC
OPENALEX_NORMALIZATION_ACCEPTANCE = FAIL
R3C_STRUCTURAL_DIAGNOSTIC_EVENT = SPECIFIC
R3C_DIAGNOSTIC_EVIDENCE = SUFFICIENT_FOR_OWNER_REVIEW
OPENALEX_COST_USAGE_ACCEPTANCE = PASS
OPENALEX_QUERY_PRIVACY_ACCEPTANCE = PASS
R3C_IDEMPOTENCY_ACCEPTANCE = PASS
R3C_RESTART_ACCEPTANCE = NOT_RUN
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

Do not begin R3D. Wait for owner review.
