# R3C-A-R1 Supervised OpenAlex Live Acceptance Retry 1 Report

Status: **BLOCKED AFTER ONE FAIL-CLOSED LIVE PROVIDER CALL**

Date: 2026-08-04

Baseline: `e381e74dac017f2466ac80b77a582ccc10cf6e78`
(`R3C-A: record blocked live OpenAlex acceptance`), branch `main`, initially
clean. Required implementation ancestor:
`6ba48416b4936060298b9e5fd9ce197b782b2bb1`.

This is the separate retry-1 evidence record. It does not overwrite, weaken or
reinterpret `R3C_OPENALEX_LIVE_ACCEPTANCE_REPORT.md`, which remains immutable
attempt-0 evidence for the correct stop at the owner-attestation gate.

## 1. Phase status

Retry 1 passed the Git, owner authorization, current-source, isolated
PostgreSQL, external Package, feature-composition, credential-injection,
capability-token, exact cost, query-privacy, Package non-mutation and Hosted
boundary gates reached before the blocker.

The first and only Provider request received HTTP 200 and exact current cost
evidence, but the committed adapter settled the durable operation as
`FAILED / PROVIDER_INVALID_RESPONSE`. It produced no accepted normalized
result. This was an unexpected live Provider/adapter contract outcome, so the
retry stopped immediately. No second Provider call, production repair,
idempotency replay, conflict request, restart acceptance or required regression
suite was attempted after the blocker.

```text
R3C_A_ATTEMPT = RETRY_1
R3C_A_RETRY_1_ACCEPTANCE = BLOCKED
R3C_A_ACCEPTANCE = BLOCKED
BLOCKING_REASON = LIVE_PROVIDER_RESPONSE_FAILED_APPROVED_NORMALIZATION
```

## 2. Initial Git baseline and previous attempt

The initial gate returned the exact required HEAD and `main`; both status
commands were empty, `git diff --check` passed and the required R3C-I commit was
an ancestor. The latest two commits were the immutable blocked attempt and the
mocked OpenAlex implementation.

Attempt 0 remains `BLOCKED_AT_OWNER_ATTESTATION` with zero calls and zero cost.
It is prerequisite/audit evidence, not an implementation failure. Retry 1 is
the separate result in this file.

## 3. Owner authorization and attestation

Both owner path variables were present. Metadata-only validation established
that both targets were regular, non-symlink `0600` files, their parent
directories denied group/world access, and both were outside Git, every
detected Workflow Package, `.env` and `runtime_data/`.

Only the attestation was read at this stage. It was an exact JSON object with
contract `reagent-r3ca-owner-attestation/v0.1`, no extra fields, no credential
or executable content, and these exact authorizations:

- key use, fictional public queries, and no prepaid/paid overage: true;
- free daily allowance remaining: at least USD 0.05;
- maximum Provider calls: 20;
- maximum reported cost: USD 0.05;
- planned acceptance Provider calls: 2.

The key content remained unread until the source recheck passed.

```text
R3C_OWNER_AUTHORIZATION = PASS
```

## 4. Official OpenAlex source recheck

No Provider API endpoint was contacted during this gate. Thirteen required
objects were retrieved only from `developers.openalex.org`, `openalex.org` and
`blog.openalex.org`, between 2026-08-04T07:23:06Z and
2026-08-04T07:25:27Z. Twelve exact-byte fingerprints matched the committed
ledger. The Authentication & Pricing reference had a new complete-byte
fingerprint and now exposed a 2026-06-20 revision marker, but its substance
still matched the guide and the committed adapter.

| Title / official domain | Revision/publication where present | SHA-256 | Affected decision |
|---|---|---|---|
| Overview / developers.openalex.org | 2026-08-03T18:32:01.465Z | `1c55bb3e20ca204fbf2b5b1f41e315de56127cf312df97664efa669e1baf4aa2` | keyed access/free allowance |
| Authentication & Pricing guide / developers.openalex.org | 2026-06-20T17:21:14.897Z | `25b949ab879de50b77a6d8f5b8fc1eb71462be3498a7d5b173c6b886f5efe03d` | key/pricing/usage evidence |
| Authentication & Pricing reference / developers.openalex.org | 2026-06-20T17:21:14.899Z | `b563fb62b3360d6b300f516237a8c6d34be1929a2f987563c027129ddfeb1baa` | key/pricing/usage evidence; non-material byte change |
| Search / developers.openalex.org | 2026-06-25T02:18:03.099Z | `5de66b5769cac8d7804c3d5c733d0ab149d7796bd8ad7fbf7977932d1ea0a681` | ordinary `search=` mapping |
| Deprecations / developers.openalex.org | 2026-02-19T01:12:08.670Z | `7b8bde5192ee1cad731ed3ee06830fc467c4d4994ddd3eaa745de083517c9772` | excludes legacy search forms |
| Works Overview / developers.openalex.org | 2026-06-01T13:43:56.211Z | `e056e251f0450fe965f030604205b7dd1971935bf48e4f323cabad134e5a3fa3` | selected Work fields |
| List works / developers.openalex.org | 2026-08-03T18:31:54.210Z | `6a06ea78b37116a11daed7132371cb30f39ae4c9004a8765b3ac5d0e57add8ec` | `/works`, `per_page`, `meta.cost_usd` |
| Select Fields / developers.openalex.org | 2026-02-17T21:24:14.081Z | `7ebf3f06729e0d53ecee57ebd05a925be7d277271959387be8b3fc5cbfc7e9fc` | fixed top-level select list |
| Error Handling / developers.openalex.org | 2026-02-19T00:53:51.039Z | `a837a68a5dde561430f1d5dfe0c673bed2de9821a369c50ce1517b59dd448cd1` | error/rate header semantics |
| Check rate limit status / developers.openalex.org | 2026-08-03T18:31:54.190Z | `1ed0893395fb24d37619967a0883f01ed06f9466bffd6349259e91bb75f08f0b` | safe rate evidence names; endpoint not called |
| Terms of Service / openalex.org | last revised 2024-02-07 | `b59bcbd2ed0fb550d35a989961c47b8fc29f22be89167e9c4789cdf1c4fa5fc4` | eligibility/third-party rights |
| Privacy Policy and Promise / openalex.org | last revised 2026-02-17 | `97b8eb0f03b06819f50d1b7b345eaad6847aa63283684f6535f1809fbdbfb67c` | key/query/technical metadata disclosure |
| New Features and Usage-Based Pricing / blog.openalex.org | published 2026-02-25T02:44:20Z; modified 2026-02-25T02:59:07Z | `47e4430d6e738b6177f377bffa1b5c716ae5c103ecf8aaa07f598b889cd3ef4b` | rollout context |

The recheck confirmed key-based `api_key` access, one Works `/works` search,
ordinary `search=`, the eight fixed selected fields, `per_page=5` eligibility,
USD 0.001 per search, `meta.cost_usd`, and the four approved rate-limit header
names. Current Terms and Privacy remained byte-identical to the previously
fully inspected PDFs and did not materially contradict this narrow fictional,
temporary engineering acceptance. This is not legal advice.

```text
R3C_SOURCE_RECHECK = PASS
```

## 5. PostgreSQL isolation and migration

A fresh PostgreSQL 18.1 data-checksummed cluster listened only on
`127.0.0.1:55491`. It contained only PostgreSQL defaults plus separate
`reagent_r3ca` acceptance and test databases; `ProjectDB` was absent.

The acceptance database upgraded from empty to the sole head
`20260805_0005`; `alembic current` returned that head and `alembic check`
reported no drift. Catalog inspection confirmed exact query checksum/length,
Provider-call, reservation and reported integer-microusd fields. The only
Proxy-operation foreign key targeted `proxy_capability_tokens`. There was no
query-text, plaintext-key, raw-body, credential-URL or Authorization-header
column.

```text
POSTGRESQL_ACCEPTANCE = PASS
```

## 6. External Package evidence

A fresh fictional Package was compiled and pristine-validated outside Git:

- Package ID: `literature-search-fictional-r3ca-retry1-20260804-v0.2`;
- Package checksum:
  `sha256:37365611543350045354fa54a4dcdfb047a2df4787762ba0c699bc974e9bb1e2`;
- manifest checksum:
  `sha256:62e62c1d3be410669179a2ee6aa2db3571364f0bb77a6728decec4bd213e37a3`;
- Workflow checksum:
  `sha256:8d25d7cd32a89e84ba8885454782cb923e93224df4637ddf6183af2a16f3980c`;
- recursive manifest: 34 entries, SHA-256
  `35855c814d34a65340f0fc2f2db294acbe76fddd6527be012d4872f0a54fd74d`.

It contained fictional inputs and no key, token plaintext, private research or
machine path. Its Proxy declaration remained provider-neutral and disabled by
default.

```text
EXTERNAL_PACKAGE_ACCEPTANCE = PASS
```

## 7. OpenAlex credential lifecycle

After authorization and source gates passed, a wrapper read the protected key
file, removed at most one terminal line ending, rejected empty/control/
multiline/non-ASCII content without printing any property, injected only
`REAGENT_OPENALEX_API_KEY` into the supervised Uvicorn child, removed both
owner-path variables from that child, and immediately executed Uvicorn. The
key was never a command argument, Package value, `.env` entry, SQL value,
response, or tracked evidence item.

Uvicorn logs contained zero matches for the Provider host, `api_key`, an
Authorization header or raw response markers. Exact key comparison was not
repeated because the key-read boundary permitted reading only for child
injection.

The cleanup attempt to delete the owner key file was rejected by the execution
safety reviewer as requiring fresh explicit approval for that exact external
owner file. It remained a protected regular `0600` file at closure. The
OpenAlex account key was not rotated or deleted.

```text
OPENALEX_CREDENTIAL_LIFECYCLE = FAIL
```

## 8. Capability-token lifecycle

The operator CLI issued one 120-minute OpenAlex-bound token capped at two
admitted operations and two Provider calls. SQL stored only its digest and
scope. The plaintext existed only in one external `0600` file and the
client's transient environment/header. A private comparison found zero token
matches outside the token file.

After the blocker the token was explicitly revoked; SQL read-back showed
`revoked=true`, one admission, one Provider call and 1,000 reported microusd.
The token file was removed with the dedicated temporary root.

## 9. Feature flag and composition

Three real-process gates passed:

- feature absent: health returned 200 and the Proxy route returned 404;
- OpenAlex enabled without SQL: startup terminated fail-closed;
- OpenAlex enabled with SQL but without the key: startup terminated
  fail-closed;
- OpenAlex enabled with dedicated SQL and wrapper-injected key: Uvicorn started
  successfully.

The fake flag was absent and no in-memory or Hosted fallback was configured.

## 10. Live Uvicorn and outbound network boundary

The accepted process used the committed `backend.api.app:app` entrypoint,
literal `127.0.0.1:58441`, proxy-header parsing disabled, and the dedicated SQL
database. The local client used literal loopback HTTP and received no Provider
credential.

The committed transport fixed the sole outbound domain and `/works` path,
verified TLS, disabled redirects and ambient proxies, bounded the complete
operation at 10 seconds/512 KiB, and contained no retry. A 500-sample socket
monitor observed the Uvicorn listener and PostgreSQL connections; the brief
external HTTPS connection was not captured, so the monitor is not represented
as packet-capture proof. No other outbound operation was initiated.

```text
OPENALEX_FIXED_ORIGIN_ACCEPTANCE = PASS
```

## 11. Live Provider call ledger

```text
admitted operations = 1
actual Provider HTTP calls = 1
reserved cost = 1000 microusd
reported cost = 1000 microusd
remaining retry-specific call allowance = 1 (unused and prohibited after blocker)
```

The pre-call controller parse error occurred before imports or request
construction; SQL verified zero admissions/calls afterward. The corrected
controller caused the only Provider request. No direct Provider client,
`/rate-limit`, retry, second query or diagnostic Provider request was used.

```text
R3C_LIVE_PROVIDER_CALL_COUNT = 1
R3C_REPORTED_COST_MICROUSD = 1000
```

## 12. Successful OpenAlex search

The sole fictional public request used `max_results=5`. The Provider returned
HTTP 200, but the adapter settled `FAILED / PROVIDER_INVALID_RESPONSE`. Because
the first call exposed an unexpected response/normalization contract, the
second authorized call was not used.

No successful Work result was accepted.

```text
LIVE_OPENALEX_HTTP_ACCEPTANCE = FAIL
```

## 13. Response normalization

The operation retained no accepted normalized result and the controller
stopped before inspecting or printing paper metadata. No paper title, abstract
or author was copied into evidence. No Provider/PDF/content link was followed.

The failure could not be diagnosed further without prohibited raw-body
retention or another Provider call. Production source was not repaired.

```text
OPENALEX_NORMALIZATION_ACCEPTANCE = FAIL
```

## 14. Exact cost and rate-limit evidence

The HTTP 200 response passed the cost and approved rate-header parsing stage:
the durable operation contained non-null safe rate evidence and reported
exactly 1,000 microusd against the 1,000-microusd reservation. The token totals
were exactly one call, 1,000 reserved and 1,000 reported microusd. Provider
credits remained separate from USD. No binary-float persistence/comparison was
used.

```text
OPENALEX_COST_USAGE_ACCEPTANCE = PASS
```

## 15. Query, key, URL and raw-body privacy audit

The query and its unique runtime marker were assembled only in process memory
and are intentionally absent from this report. A private exact comparison over
Git-tracked files, the full dedicated acceptance tree (including PostgreSQL
files), and logical Proxy token/operation rows returned:

```text
exact query durable matches = 0
runtime marker durable matches = 0
capability-token matches outside its token file = 0
```

The Proxy operation used `CHECKSUM_ONLY` retention with query byte/character
length evidence. Runtime logs contained zero complete Provider host,
credential-parameter, Authorization-header or raw-body markers. The schema had
no raw-body or credential-URL column. All dedicated database/log/runtime
material was deleted.

The owner key itself was not reread for an exact-value comparison, in order to
preserve the key-read-only-for-injection rule. The key file cleanup exception
is recorded in section 21.

```text
OPENALEX_QUERY_PRIVACY_ACCEPTANCE = PASS
```

## 16. Idempotency, conflict and status

The controller was designed to run exact replay, status by operation ID,
status by scoped idempotency identity and changed-content conflict only after a
successful result. It stopped at the Provider-invalid terminal state as
required. No replay or conflict POST occurred and no second Provider call was
made.

Historical R3C-I scripted/SQL evidence remains valid but is not substituted for
the unexecuted live retry gate.

```text
R3C_IDEMPOTENCY_ACCEPTANCE = FAIL
```

## 17. Backend and PostgreSQL restart

Restart acceptance was not started after the unexpected live contract result.
Uvicorn and PostgreSQL were stopped once for fail-closed cleanup; the database
was not restarted and the failed operation was not replayed.

```text
R3C_RESTART_ACCEPTANCE = FAIL
```

## 18. Package non-mutation

The external Package passed pristine validation after the blocked call. Its
post-attempt recursive manifest remained 34 entries, had the same SHA-256 as
the pre-attempt manifest and was byte-identical to the pre-attempt manifest.

```text
PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
```

## 19. Runtime and Hosted boundary

Before and after the one live operation, counts remained zero for Hosted
`provider_operations`, Workflow runs/steps, execution events, checkpoints,
checkpoint records, memory revisions and uploaded Progress Reports. No
AgentRuntime, ExecutionDispatcher, research Skill, Workflow execution/resume,
LLM, structured generation, Judge/evaluation or automatic Progress Report path
was invoked.

```text
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
```

## 20. Tests and skips

Before the live call, the dedicated acceptance database passed `alembic heads`,
empty upgrade, `current` and `check`. The required pytest/compileall regression
matrix was not started after the live blocker, because the phase mandate
required an immediate fail-closed stop and prohibited production repair.

No new Proxy/OpenAlex PostgreSQL test was reported as skipped; the retry test
matrix is unqualified rather than represented as passing. The immutable R3C-I
results remain historical implementation evidence only.

## 21. Cleanup

Completed:

- capability token revoked;
- Uvicorn stopped and port released;
- dedicated PostgreSQL stopped and port released;
- token file, Package, logs, source downloads, request/controller material and
  only the dedicated PostgreSQL directory deleted;
- no dedicated process or temporary root remained;
- `.env` and `runtime_data/` remained ignored;
- ProjectDB and unrelated PostgreSQL services were untouched.

Not completed:

- the safety reviewer rejected deletion of the two exact external owner files
  pending fresh explicit owner approval;
- the key and attestation therefore remained regular `0600` files outside Git
  at closure.

This cleanup exception is an independent hard blocker even though the retry
was already blocked by the Provider-invalid response.

## 22. Retry documentation and commit evidence

This separate report, a separate retry progress record, compressed context and
the R3C-A project-plan status are the only intended tracked changes. The
attempt-0 report, production/backend/frontend source, migrations, tests,
fixtures, Package templates, contracts, ADRs and Progress Report v0.2 remain
unchanged.

The single documentation-only commit uses message
`R3C-A-R1: record blocked supervised OpenAlex retry`. Its resulting hash and
`git show` evidence are reported in the final owner handoff; embedding a
commit's own hash in its content would be self-referential.

## 23. Final Git state

Before staging, status/name/stat/untracked and whitespace checks are required to
show only these four approved documentation/handoff paths. After the single
retry-evidence commit, final HEAD/status/show evidence is collected for the
owner handoff and the worktree must be clean.

## 24. Remaining warnings

- The Provider-invalid response was intentionally not diagnosed with a second
  call or raw-body retention.
- Live 401/403/429/5xx and timeout were not intentionally induced.
- Only one fictional public query was used.
- The external HTTPS socket was too brief for the supporting socket sampler.
- The two owner input files require owner deletion approval/action.
- Real-user disclosure UX, Claude Code, frontend, production authentication,
  multi-user authorization, public HTTPS/proof-of-possession, production secret
  management, production retention/deletion and additional Providers remain
  unresolved.

## 25. R3 final gate

```text
R3C_A_ATTEMPT = RETRY_1
R3C_A_RETRY_1_ACCEPTANCE = BLOCKED
R3C_A_ACCEPTANCE = BLOCKED
R3C_OWNER_AUTHORIZATION = PASS
R3C_SOURCE_RECHECK = PASS
POSTGRESQL_ACCEPTANCE = PASS
EXTERNAL_PACKAGE_ACCEPTANCE = PASS
LIVE_OPENALEX_HTTP_ACCEPTANCE = FAIL
OPENALEX_CREDENTIAL_LIFECYCLE = FAIL
OPENALEX_FIXED_ORIGIN_ACCEPTANCE = PASS
OPENALEX_NORMALIZATION_ACCEPTANCE = FAIL
OPENALEX_COST_USAGE_ACCEPTANCE = PASS
OPENALEX_QUERY_PRIVACY_ACCEPTANCE = PASS
R3C_IDEMPOTENCY_ACCEPTANCE = FAIL
R3C_RESTART_ACCEPTANCE = FAIL
PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
R3C_GIT_CLOSURE = PASS
R3C_LIVE_PROVIDER_CALL_COUNT = 1
R3C_REPORTED_COST_MICROUSD = 1000
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3C_COMPLETE = NOT_COMPLETE
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
R3B_STATE = FAKE_PROXY_ACCEPTED
R2_STATE = UPLOAD_ACCEPTED
```

Do not begin R3D. Wait for owner review.
