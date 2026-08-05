# R3C Composite OpenAlex Acceptance Report

Date: 2026-08-05

Status: **PASS_WITH_WARNINGS — EXPERIMENTAL R3C ACCEPTED BY COMPOSITE EVIDENCE**

Baseline: `5b44b3f868566a4deef45b664385f16df92f6e11`
(`R3C-R2: permit delayed exact replay after restart`), branch `main`, with an
initially clean worktree.

This is a documentation-only owner-ratification record. It made no live
Provider call, read no credential or `.env`, retrieved no external source,
started no database or server, and changed no production source, test,
migration, fixture, frontend, Package template, API contract, or Progress
Report contract.

## 1. Composite acceptance decision

The owner accepts R3C by composing the immutable Provider-specific live
evidence from R3C-A-R4 with the deterministic recovery diagnosis from R3C-R1
and the owner-accepted remediation/restart qualification from R3C-R2.

No single run on final HEAD exercised every gate. The conclusion is explicitly
compositional. R3C-A-R4 itself remains `BLOCKED`; this report does not alter,
supersede, or reinterpret any historical result.

## 2. Provider-specific live evidence matrix

| Experimental gate | Authoritative evidence | Accepted fact | Composite result |
|---|---|---|---|
| Owner authorization | R3C-A-R4 sections 3 and 24 | Exact-baseline, one-call, five-result, cost, query-class, and cleanup authorization passed before credential use | PASS |
| Current official-source recheck | R3C-A-R4 sections 4 and 24 | Approved documentation-only recheck passed before credential access | PASS |
| Real credential injection | R3C-A-R4 section 7 | Credential was injected only into supervised Uvicorn children; the provider-neutral client received only its scoped capability | PASS |
| Fixed OpenAlex Works origin | R3C-A-R4 sections 4 and 8 | The committed fixed HTTPS Works transport was used; no arbitrary Provider endpoint or fallback was used | PASS |
| Real HTTP response | R3C-A-R4 sections 9 and 10 | Exactly one Provider call returned HTTP 200 with zero retry | PASS |
| Real normalized records | R3C-A-R4 sections 10 and 11 | Five real Works normalized in Provider order with approved metadata only | PASS |
| Canonical normalized size | R3C-A-R4 sections 10 and 11 | Canonical normalized body was exactly 8,726 bytes and within the 512-KiB bound | PASS |
| Exact cost | R3C-A-R4 sections 9 and 13 | One call settled exactly 1,000 integer microusd with Provider credits separate from USD | PASS |
| Rate-limit evidence | R3C-A-R4 sections 4 and 13 | Approved bounded rate evidence was present and validated without a separate rate-limit call | PASS |
| Query/key/raw-body privacy | R3C-A-R4 sections 7, 8, 11, and 13 | No prohibited durable query request, credential, token, authorization header, full Provider URL, raw body, or arbitrary exception was found | PASS |
| Pre-restart status | R3C-A-R4 section 14 | Status by operation ID and scoped idempotency identity returned the same success | PASS |
| Pre-restart exact replay | R3C-A-R4 section 14 | Exact request replay returned the same operation with no second call, cost, operation, or diagnostic | PASS |
| Changed-content conflict | R3C-A-R4 section 14 | Changed content under the same key returned `IDEMPOTENCY_CONFLICT` before Provider use | PASS |
| Package non-mutation | R3C-A-R4 sections 6 and 16 | Recursive pre/post manifests were byte-identical | PASS |
| Hosted/runtime/LLM isolation | R3C-A-R4 section 17 | Hosted, Runtime, Workflow, LLM, Judge, and Progress Report activity remained zero | PASS |

The live operation settled `SUCCEEDED` with no structural diagnostic. R3C-A-R4
nonetheless remains blocked because its post-restart verification controller
failed before producing the required safe recovery artifact.

## 3. Recovery and remediation evidence matrix

| Recovery gate | Authoritative evidence | Accepted fact | Composite result |
|---|---|---|---|
| Delayed replay reproduction | R3C-R1 sections 7 and 8 | The original-equivalent controller deterministically reproduced the value-free failure after timestamp aging | PASS |
| Root cause | R3C-R1 sections 4, 8, and 11 | Exact replay reached timestamp freshness before durable scoped idempotency resolution | PASS |
| Existing operation before freshness | ADR 0015; R3C-R2 sections 2 and 3 | A matching existing checksum now replays in every operation status regardless of timestamp age | PASS |
| Existing-key conflict before freshness | ADR 0015; R3C-R2 sections 2 and 3 | Existing changed content returns HTTP 409 / `IDEMPOTENCY_CONFLICT` before freshness | PASS |
| Stale new admission | ADR 0015; R3C-R2 sections 2, 3, and 5 | The unchanged freshness window still rejects stale or future new keys with no operation, call, or cost | PASS |
| Authentication/authorization | ADR 0015; R3C-R2 sections 2 and 3 | Expired, revoked, and wrong-scope capabilities cannot replay or probe an operation | PASS |
| Real PostgreSQL restart | R3C-R2 sections 4 and 5 | The same isolated data directory restarted at sole/current revision `20260805_0005` with no drift | PASS |
| Real Uvicorn restart | R3C-R2 section 5 | A second committed-ASGI Uvicorn generation became healthy under equivalent configuration | PASS |
| Status by operation ID | R3C-R2 section 5 | The same successful operation was retrieved after restart | PASS |
| Status by scoped idempotency identity | R3C-R2 section 5 | The same successful operation was retrieved through the second read path | PASS |
| Delayed exact replay | R3C-R2 sections 3 and 5 | The aged original bytes returned the existing operation as `REPLAYED` after restart | PASS |
| Result and checksum stability | R3C-R2 section 5 | Operation ID, normalized result, stable checksums, count, and canonical size were unchanged | PASS |
| Call and cost stability | R3C-R2 sections 4 and 5 | Ledger remained one operation, one call, 1,000 reserved microusd, and 1,000 reported microusd | PASS |
| SQL regression | R3C-R2 sections 4 and 7 | Seventeen required Proxy/OpenAlex PostgreSQL tests passed with zero skip | PASS |
| Full regression | R3C-R2 section 7 | Focused, Proxy, Package, Progress Report, and full backend suites passed; only four separately gated integrations skipped | PASS |
| Additional live use | R3C-R1 and R3C-R2 gate states | Both phases made zero live Provider calls and used no real key or external documentation | PASS |

## 4. Composite-evidence rationale

The service correction is orthogonal to live Provider transport and
normalization. R3C-R2 moved only the existing timestamp-freshness check so that,
after structural validation, authentication, and exact scope authorization, a
durable existing operation is resolved as replay or conflict before freshness
is applied to a new admission. It changed no adapter mapping, Provider fields,
normalization predicate, response shape, request or result checksum semantic,
SQL schema, credential source, privacy/retention rule, call/cost arithmetic,
diagnostic, Package behavior, or Hosted boundary.

R3C-A-R4 proves the unchanged Provider-facing behavior with one real response.
R3C-R1 locates the failure before transport, and R3C-R2 exercises the corrected
branch using real PostgreSQL and Uvicorn, an aged request, a stable ledger, and
zero adapter invocation on replay. Requiring another Provider call would not
exercise a changed Provider-facing path.

Accordingly, no unresolved hard gate remains for the experimental R3C slice.
This conclusion is not a claim that R3C-A-R4 passed as a single run, and it is
not production acceptance.

## 5. Immutable historical attempts

| Historical phase | Immutable result | Preserved meaning |
|---|---|---|
| Attempt 0 | BLOCKED | Owner attestation was absent; zero Provider calls |
| Retry 1 | BLOCKED | One HTTP-200 response failed normalization for an unpreserved reason; remains historically unexplained |
| R3C-N1 | INCONCLUSIVE | No exact live failure path or approved failing synthetic shape was available |
| R3C-N2-A | PASS_WITH_WARNINGS | One zero-record live success emitted no diagnostic and supplied no positive-record evidence |
| Retry 2 | BLOCKED | Owner free-allowance prerequisite failed; zero Provider calls |
| Retry 3 | BLOCKED | One call produced the specific value-free abstract-token control diagnostic under strict whole-response failure |
| Retry 4 | BLOCKED | Live normalization succeeded, but mandatory post-restart verification failed closed |
| R3C-R1 | PASS | Delayed exact-replay ordering defect reproduced deterministically offline |
| R3C-R2 | PASS | Ordering remediation and real PostgreSQL/Uvicorn delayed-replay qualification passed offline |

No historical `BLOCKED`, `FAIL`, or `INCONCLUSIVE` state is changed to `PASS`.
Composite closure is a new higher-level owner decision.

## 6. Security and product boundary

The teacher-aligned boundary remains unchanged: cloud supplies bounded
credentialed transport, normalization, provenance, and accounting; the local
Harness chooses and interprets research requests; the local Package remains
authoritative for concrete research state. Cloud performed no research
synthesis, Workflow continuation, Package mutation, or automatic Progress
Report action.

This ratification phase made zero Provider or external-documentation calls,
read zero credentials and zero `.env` files, and started zero PostgreSQL or
Uvicorn processes. It invoked no AgentRuntime, ExecutionDispatcher, Workflow,
Hosted Skill, LLM, structured generation, Judge, or Progress Report path.

## 7. Remaining warnings

- No single end-to-end live run occurred on final HEAD.
- R3C-A-R4 remains an immutable blocked attempt.
- Retry 1 remains historically unexplained.
- Only OpenAlex was accepted.
- Only limited fictional public acceptance queries were used.
- Live Provider error conditions were not intentionally induced.
- Official Provider behavior, pricing, Terms, and Privacy may change.
- Claude Code remains untested and frontend work remains deferred.
- Real-user third-party query disclosure remains unimplemented.
- Production authentication, multi-user authorization, HTTPS termination,
  proof of possession, secret management, and retention remain unresolved.
- This acceptance does not authorize public or production deployment.

## 8. Final states

```text
R3C_COMPOSITE_CLOSURE = PASS
R3C_COMPOSITE_OWNER_REVIEW = ACCEPTED
R3C_COMPOSITE_ACCEPTANCE = PASS_WITH_WARNINGS
R3C_PROVIDER = OPENALEX_PAPER_SEARCH_ACCEPTED_FOR_EXPERIMENTAL_R3C
R3C_LIVE_TRANSPORT_ACCEPTANCE = PASS
R3C_LIVE_NORMALIZATION_ACCEPTANCE = PASS
R3C_COST_USAGE_ACCEPTANCE = PASS
R3C_QUERY_CREDENTIAL_PRIVACY_ACCEPTANCE = PASS
R3C_PRE_RESTART_IDEMPOTENCY_ACCEPTANCE = PASS
R3C_FINAL_RESTART_ACCEPTANCE = PASS_BY_COMPOSITE_EVIDENCE
R3C_DELAYED_REPLAY_ACCEPTANCE = PASS
R3C_PACKAGE_IMMUTABILITY_ACCEPTANCE = PASS
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
R3C_STATE = LIVE_OPENALEX_ACCEPTED
R3C_COMPLETE = PASS_WITH_WARNINGS
R3C_GIT_CLOSURE = PASS
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
R2_STATE = UPLOAD_ACCEPTED
R3B_STATE = FAKE_PROXY_ACCEPTED
```

Do not begin R3D. A separate owner decision is required for any production or
public Provider work.
