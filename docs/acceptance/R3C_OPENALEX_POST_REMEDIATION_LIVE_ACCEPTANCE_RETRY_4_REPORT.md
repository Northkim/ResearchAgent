# R3C-A-R4 Post-Remediation One-Call OpenAlex Live Acceptance

Date: 2026-08-05

Status: **BLOCKED AT RESTART STATUS/REPLAY VERIFICATION**

Baseline: `110f54ac7c87453a08e61ae26a5d5afbd6b77bb2`
(`R3C-I2: normalize abstract formatting controls safely`), branch `main`,
with an initially clean worktree.

This is an immutable append-only retry-4 evidence record. It preserves every
earlier R3C record and does not reinterpret or supersede retry 1, retry 3, or
the committed R3C-I2 remediation.

## 1. Phase Status

Git, owner authorization, current-source review, PostgreSQL isolation,
Package, feature-flag, credential, token, one-call, live normalization, cost,
privacy, initial status/replay/conflict, Package-immutability, and
Hosted/runtime-boundary gates passed. The one authorized Provider call
returned five normalized Works at exactly 1,000 microusd with no structural
diagnostic.

The same PostgreSQL cluster restarted at the sole migration head and the
second supervised Uvicorn child became healthy. The mandatory post-restart
provider-neutral status/replay controller then returned a value-free
`RuntimeError` before it could create the safe recovery artifact. The durable
ledger remained one successful operation, one Provider call, and 1,000
microusd. Per the owner instruction, no retry, replacement token, source
repair, or further acceptance execution was attempted.

```text
R3C_A_ATTEMPT = RETRY_4
R3C_A_RETRY_4_ACCEPTANCE = BLOCKED
BLOCKING_REASON = RESTART_STATUS_REPLAY_VERIFICATION_FAILED
```

## 2. Initial Git Baseline and History

The initial gate passed exactly. The repository root was ResearchAgent; HEAD
was `110f54ac7c87453a08e61ae26a5d5afbd6b77bb2`; branch was `main`; both status
commands were empty; there were no staged or untracked files; and
`git diff --check` passed.

The nine-entry log contained the required R3C-I2 baseline and ancestors
`a980acbc268ce96089bd93a2954a39b9491a3e94`,
`45ef6b500c61a484bd6d4b569b3d4233ab6146a2`, and
`6ba48416b4936060298b9e5fd9ce197b782b2bb1`. No reset, restore, checkout,
rebase, clean, amend, squash, or history rewrite was used.

## 3. Owner Authorization

Before either owner file was read, both runtime variables and their distinct
targets were verified. Each target was a regular non-symlink mode-`0600` file
with a mode-`0700` parent outside Git, the repository, `runtime_data`, and all
Packages.

The attestation was read first as strict JSON with duplicate- and unknown-field
rejection. It matched contract
`reagent-r3ca-post-remediation-owner-attestation/v0.1`, the exact baseline and
phase, the generic-public/test-only declaration, the one-call,
1,000-microusd, and five-result limits, the no-paid-overage declaration, the
minimum free-allowance threshold, and local-file deletion authority. It
contained no credential, token, password, executable content, or command.

```text
R3C_OWNER_AUTHORIZATION = PASS
```

## 4. Official OpenAlex Source Recheck

Before key access, the current recheck contacted only approved official
documentation domains and did not contact the Provider API. The official
[authentication and pricing guide](https://developers.openalex.org/guides/authentication),
[list-works reference](https://developers.openalex.org/api-reference/works/list-works),
[search guide](https://developers.openalex.org/guides/searching),
[field-selection guide](https://developers.openalex.org/guides/selecting-fields),
and [error/rate-limit reference](https://developers.openalex.org/api-reference/errors)
confirmed `api_key`, fixed `GET /works`, ordinary `search=`, the committed
selected fields, five-result requests, exact USD 0.001 ordinary-search cost,
`meta.cost_usd`, and the approved X-RateLimit evidence.

The current [Terms](https://openalex.org/OpenAlex_termsofservice.pdf),
[Privacy Policy](https://openalex.org/OpenAlex_privacy_policy.pdf), and
[usage-based pricing notice](https://blog.openalex.org/openalex-api-new-features-and-usage-based-pricing/)
remained compatible with this supervised, non-sensitive experiment. This is
an engineering compatibility review, not legal advice.

```text
R3C_SOURCE_RECHECK = PASS
```

## 5. PostgreSQL Isolation and Migration

A fresh data-checksummed PostgreSQL 18.1 cluster listened only on a unique
loopback port and contained separate `reagent_r3ca4_acceptance` and
`reagent_r3ca4_tests` databases. ProjectDB and unrelated services were never
accessed.

Both databases upgraded from empty to sole head `20260805_0005`. Acceptance
`alembic heads`, `current`, and `check` passed before use. After the physical
database restart, the same three checks again showed sole/current
`20260805_0005` and no drift.

Schema inspection confirmed exact integer call/microusd accounting and query
checksum/length metadata, with no query-text, raw-body, plaintext-key,
credential-URL, authorization-header, or diagnostic column and no Hosted
Workflow/ProviderOperation foreign key. An initial `initdb` attempt stopped
before a usable cluster because of an inherited locale; the dedicated cluster
was then initialized explicitly with locale `C`. No source changed.

```text
POSTGRESQL_ACCEPTANCE = PASS
```

## 6. External Package Evidence

The committed compiler produced and pristine-validated a fresh fictional
external Package with Package checksum
`sha256:2469f45546d87d14e13d9ee921311f05e257e113b3b0e93543a85a4073caeb61`,
manifest checksum
`sha256:141cc06c0d009039c4fcf6249de49f4b0eecef2455dc57ec055494fff49283d2`,
and compiler ZIP checksum
`sha256:2e373eba13d47eb3953e8461144c6df0763fb1d8cf3562b97e805efa7d848b9d`.

Its protected recursive pre-manifest contained 34 entries and checksum
`sha256:9238f7a49b49d6447273d694d5b0b4882d82396bf1a9b681d5a396194610b8ca`.
The Package contained only its disabled provider-neutral placeholder: no
credential, token, live Provider selector, private research request, or prior
acceptance data.

```text
EXTERNAL_PACKAGE_ACCEPTANCE = PASS
```

## 7. Credential and Token Lifecycle

Only after all preceding gates passed, an outside-Git wrapper opened the key
copy and injected it solely as `REAGENT_OPENALEX_API_KEY` into each supervised
Uvicorn child environment. The wrapper removed owner-path variables before
exec and never printed, hashed, measured, logged, persisted, or passed the key
as an argument. The provider-neutral client received only
`REAGENT_PROXY_TOKEN`.

The committed operator CLI issued one mode-`0600`, short-lived,
OpenAlex-bound capability for the exact external Package and Workflow, with
one operation and one Provider-call maximum. PostgreSQL stored only its digest
and safe scope metadata. After the blocked restart check, the token was
revoked and its plaintext file was deleted. The exact authorized attestation
and local key copies were deleted; the OpenAlex account key itself was not
changed.

## 8. Feature Flags, Diagnostic Log and Uvicorn

Probes verified that OpenAlex remained disabled by default, diagnostics alone
did not activate the route, and enabled mode without explicit SQL or without
the credential failed closed. Enabled mode with isolated SQL and the
supervised key started without fake, Hosted, or in-memory fallback. One probe
controller initially expected an overly specific failure string; its
value-free expectation was corrected without source change before live use.

Both committed-ASGI Uvicorn generations bound literal `127.0.0.1` with access
logging and proxy-header trust disabled. The mode-`0600` diagnostic log was
outside Git and the Package and remained empty. No body, query parameter, full
Provider URL, authorization header, request representation, or free-form
exception trace was logged.

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

The request used exact outer trimming, `max_results=5`, one UUIDv4
idempotency key, one valid timestamp, and exact canonical checksum
`sha256:d98aee19339128911978425794a42229eccddd669a31d5ac9587eb7cf0a09aee`.
Tracked evidence refers to it only as the owner-approved generic public
acceptance query.

## 10. Live Operation Outcome

Operation
`proxyop-v1-c4ae3c4a26ac24ae40d11f994f194f735bcfaa89ccf92a74b7b46b25ed1c47ff`
settled `SUCCEEDED` with five real normalized Works and canonical normalized
body size 8,726 bytes. Its value-free checksums were:

- provider data:
  `sha256:2452eb3f187a28a6e432abaa26a0cd0211fddcd6a5470677f976065323f6b8f0`;
- Provider response:
  `sha256:b0b091371d723ecdc3a5922c858e01ea0ee2e927ca090b5899f591cde1c249a1`;
- response content:
  `sha256:77731cc871a43db8ef43fe2de800771066836cd527a1c900e7ac739588d8ed3b`.

No ranking, relevance, summary, synthesis, or research interpretation was
produced.

```text
LIVE_OPENALEX_HTTP_ACCEPTANCE = PASS
R3C_LIVE_OPERATION_OUTCOME = SUCCEEDED_WITH_REAL_RECORDS
```

## 11. Real-Record Normalization

The five-record result passed Work-ID mapping, unrewritten title mapping,
author-list handling, DOI handling, integer publication-year typing, optional
source/language handling, bounded abstract reconstruction, result-order and
author-order code paths, unknown-field discard, and the 512-KiB canonical
bound. Coverage established that abstracts, authors, DOI, year, venue, and
language were represented in the accepted set.

No TAB/LF/CR remained after abstract-token normalization; no forbidden control
remained. Only constructed public record links were exposed, no Provider/PDF
URL was followed or returned, and no raw Provider body was retained. Tracked
evidence contains only counts, coverage flags, checksums, and canonical size,
not Provider field values.

```text
OPENALEX_NORMALIZATION_ACCEPTANCE = PASS
```

## 12. Structural Diagnostic Event

The success path produced zero diagnostic events before restart and after the
failed restart controller attempt. The protected diagnostic log remained
empty, as required for a successful real-record response.

```text
R3C_STRUCTURAL_DIAGNOSTIC_EVENT = NOT_TRIGGERED_SUCCESS
```

## 13. Exact Cost and Privacy Audit

Provider `meta.cost_usd=0.001` was converted and persisted as exact integer
1,000 microusd. The token and operation ledgers each showed one call, 1,000
microusd reserved, and 1,000 microusd reported. Provider credits and approved
rate-limit evidence remained separate from USD; no binary float was persisted
or compared.

Private scans covered SQL text/JSON fields, PostgreSQL files, protected logs,
responses, the external Package, and Git. The approved phrase occurred only
as ordinary content within normalized Provider results; request JSON retained
only checksum/length metadata and did not retain query text. Outside the
authorized transient sources, there were zero plaintext-token matches and zero
query matches other than ordinary normalized Provider-result content. There
were also zero authorization-header, credential-parameter, full Provider-URL,
raw-body, or arbitrary-exception markers. The key was not reread for audit.

```text
OPENALEX_COST_USAGE_ACCEPTANCE = PASS
OPENALEX_QUERY_PRIVACY_ACCEPTANCE = PASS
```

## 14. Status, Replay and Conflict

Before restart, status by operation ID and by scoped idempotency identity
returned the same durable success. Exact replay of the original bytes returned
the same operation with zero additional call, reservation, cost, operation,
or diagnostic. Changed canonical content under the same key, with a recomputed
checksum, returned `IDEMPOTENCY_CONFLICT` with zero Provider calls.

```text
R3C_IDEMPOTENCY_ACCEPTANCE = PASS
```

## 15. Backend and PostgreSQL Restart

The initial safe operation/result/checksum/cost evidence was snapshotted.
Uvicorn and the dedicated PostgreSQL cluster stopped; both loopback ports were
released. The same cluster restarted, retained sole/current migration
`20260805_0005` with no drift, and the second supervised Uvicorn child became
healthy with the same flags and key-source boundary.

The required provider-neutral post-restart status/status/replay controller
then failed with a value-free `RuntimeError` before producing the safe restart
artifact. The token had not expired or been revoked at that point. SQL still
showed one successful operation, one Provider call, and exactly 1,000
microusd, so no second live call occurred. The phase stopped immediately; the
failing read/replay step was not retried and its precise substep remains
unclassified.

```text
R3C_RESTART_ACCEPTANCE = FAIL
```

## 16. Package Non-Mutation

The post-acceptance Package pristine/safety scan passed. Its recursive
34-entry post-manifest was byte-identical to the pre-manifest and retained
checksum
`sha256:9238f7a49b49d6447273d694d5b0b4882d82396bf1a9b681d5a396194610b8ca`.
No Package instruction, input, output, context, memory, progress, prompt,
Skill, manifest, or cloud configuration changed.

```text
PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
```

## 17. Runtime and Hosted Boundary

Before and after live settlement, Hosted ProviderOperation, WorkflowRun,
StepRun, ExecutionEvent, Checkpoint, checkpoint-record, MemoryRevision,
uploaded Progress Report, progress projection, artifact, approval, and agent
session rows remained zero. AgentRuntime, ExecutionDispatcher, Hosted Skills,
Workflow execution/resume, LLM/structured generation, Judge/evaluation, and
automatic Progress Report generation/upload were never invoked. Cloud work
remained bounded credentialed transport, normalization, provenance, and
accounting; no research synthesis or continuation occurred.

```text
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
```

## 18. Tests and Skips

The acceptance and test databases both migrated to sole head
`20260805_0005`; acceptance Alembic head/current/drift checks also passed after
the physical restart. The requested pytest, aggregate backend, compileall, and
final database-test matrix were **not run** because the owner instruction
required an immediate fail-closed stop after a restart failure. No passing
test claim or skip count is made for retry 4, and no Proxy/OpenAlex SQL test
was reported as skipped—it was not invoked.

## 19. Cleanup

The capability token was revoked. Both Uvicorn generations and the dedicated
PostgreSQL cluster stopped, and both loopback ports were confirmed released.
The token file, diagnostic log, protected request/response evidence, external
Package, temporary wrappers/scripts/logs, rendered teacher-PDF pages, and both
dedicated PostgreSQL data areas were deleted.

The exact authorized owner attestation and local key copies were deleted and
their empty owner directory was removed. The account key, ProjectDB, unrelated
PostgreSQL services, repository source, and all earlier audit records were
untouched.

## 20. Append-Only Documentation

Only this new retry-4 report, the new retry-4 progress record, and
`.agent_read/context.md` change. Production/backend/frontend source,
migrations, tests, fixtures, Package templates, API/architecture contracts,
ADRs, the project plan, and `progress-report/v0.2` remain unchanged. No repair
was attempted and no R3D work began.

## 21. Commit Evidence

Exactly one documentation-only evidence commit is required with message
`R3C-A-R4: record incomplete post-remediation OpenAlex retry`. Its identity is
reported in the final owner handoff because embedding a commit's own hash in
its contents would be self-referential. No push is authorized.

## 22. Final Git State

Before staging, scope, whitespace, credential, query, Provider-value,
temporary-path, and prohibited-change checks must show only the three approved
documentation paths. After the sole evidence commit, the worktree must be
clean.

## 23. Remaining Warnings

- The live response is the first positive real-record evidence after R3C-I2,
  but the mandatory restart recovery gate is incomplete and failed closed.
- The exact restart controller substep that raised the value-free
  `RuntimeError` is intentionally unclassified; this phase did not retry or
  investigate by changing behavior.
- The required final test matrix was not run after the stop condition.
- Retry 1 remains an unresolved historical normalization warning.
- R3C remains pending; R3C-I2 and R3D gates remain closed.

## 24. R3 Final Gate

```text
R3C_A_ATTEMPT = RETRY_4
R3C_A_RETRY_4_ACCEPTANCE = BLOCKED
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

Do not begin R3D. Wait for owner review.
