# R3C-I2 OpenAlex Abstract Formatting-Control Compatibility Remediation

Date: 2026-08-05

## Result

```text
R3C_I2_IMPLEMENTATION = PASS_WITH_WARNINGS
R3C_ABSTRACT_FORMATTING_CONTROL_POLICY = TAB_LF_CR_TO_SPACE
R3C_FORBIDDEN_CONTROL_REJECTION = PASS
R3C_STRICT_RESPONSE_POLICY = PASS
R3C_RETRY3_SYNTHETIC_REPRODUCTION = PASS
R3C_DIAGNOSTIC_PRIVACY_BOUNDARY = PASS
R3C_IDEMPOTENCY_RECONCILIATION = PASS
R3C_SQL_REGRESSION = PASS
R3C_RUNTIME_HOSTED_BOUNDARY = PASS
R3C_LIVE_PROVIDER_CALL_COUNT_THIS_PHASE = 0
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3C_NEXT_LIVE_RETRY_GATE = READY_FOR_FRESH_OWNER_AUTHORIZATION
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

Warnings are limited to the intentionally unretained exact Retry-3 code point,
the absence of a passing real OpenAlex response after remediation, Retry 1's
unexplained failure, the need for fresh owner authorization before any future
live retry, and the continued closure of production/R3D.

## Baseline and credential gate

The phase began from exact clean `main` commit
`a980acbc268ce96089bd93a2954a39b9491a3e94`
(`R3C-A-R3: record incomplete positive-result OpenAlex retry`). Required
ancestors were present, status/porcelain were empty, and diff check passed.

`REAGENT_OPENALEX_API_KEY` was absent. Legacy owner-input path variables were
present in the parent environment but were never dereferenced or used and were
explicitly removed from implementation/test subprocesses. No credential file
or `.env` was opened. No Provider API, OpenAlex documentation site, or other
external network endpoint was contacted. All authority came from committed
repository material and the local teacher architecture PDF.

## Owner-ratified policy and implementation

Accepted ADR 0014 records the narrow compatibility policy. Only string tokens
used to reconstruct `/results/*/abstract_inverted_index` receive preprocessing:
U+0009 TAB, U+000A LF, and U+000D CR become U+0020 SPACE. A contiguous run of
ASCII SPACE/TAB/LF/CR containing at least one permitted control becomes one
SPACE; a space-only run remains unchanged. Existing outer trimming and
position-ordered reconstruction then apply.

`backend/cloud_api_proxy/openalex_adapter.py` adds one pure token helper and
calls it immediately before the existing abstract-token `_safe_text` validator.
It does not log, persist, interpolate, or independently expose either token.
Non-control character order is preserved, words are not concatenated, and none
of the three formatting controls remains in normalized output. A narrow
abstract-only pre-trim check ensures forbidden whitespace-like controls such as
vertical tab and form feed cannot be removed by generic outer trimming before
they receive the required control classification.

U+0000 through U+0008, U+000B, U+000C, U+000E through U+001F, U+007F, and
other rejected control/format characters continue through the unchanged
validator and fail as `ABSTRACT_RECONSTRUCTION`,
`/results/*/abstract_inverted_index`, `CONTROL_CHARACTER`, and
`ABSTRACT_TOKEN_CONTROL`. Work ID, DOI, title, author, venue/source, language,
and all other field handling is unchanged.

## Strict response and privacy evidence

`STRICT_COMPLETE_RESPONSE_FAILURE` remains authoritative. A prohibited control
in the second fictional Work fails the complete result after one transiently
normalized Work. No partial paper array or Provider value is returned or
persisted, and no record is skipped or quarantined.

All privacy canaries are runtime-generated. Accepted formatting controls emit
no diagnostic. The prohibited-control equivalent emits exactly one event with
record index `1`, nested token index `2`, and the unchanged closed
classification. The event, submit/replay responses, and durable operation omit
the query marker, synthetic credential marker, bearer token, and Provider-value
marker. Structural checksums remain deterministic and equal across same-shape,
different-value responses. Public error and status contracts remain unchanged;
there is no diagnostic SQL field or raw response retention.

## Cost, idempotency, and boundaries

The Retry-3-equivalent fictional success settles exactly one scripted Provider
invocation and exactly 1,000 microusd. Exact replay returns the original
operation without another admission, reservation, call, cost, or event.
Changed canonical content under the same idempotency identity returns
`IDEMPOTENCY_CONFLICT` before adapter use. The prohibited-control failure also
settles 1,000 microusd once and replays without a second invocation or event.
Existing uncertain reconciliation tests remain green, and no automatic retry
was introduced.

Deterministic fake-adapter routing/authorization remains green. No Package,
Progress Report contract/behavior, Hosted ProviderOperation, WorkflowRun,
StepRun, ExecutionEvent, Checkpoint, MemoryRevision, AgentRuntime,
ExecutionDispatcher, Hosted Skill, LLM/structured-generation, Judge/evaluation,
or Workflow execution/resume path changed or ran. Cloud behavior remains
transport, normalization, safe provenance, and accounting only; local Packages
and Harnesses remain authoritative for research interpretation and state.

## PostgreSQL regression and cleanup

Two fresh PostgreSQL 18.1 clusters were used sequentially under the same
loopback-only, unique-non-default-port profile. The second reran the final SQL
and aggregate backend matrix after the abstract-only pre-trim rejection check
was added. Each dedicated database was `reagent_r3ci2_tests`, never ProjectDB.
The initial sandboxed `initdb` invocation stopped at the operating-system
shared-memory restriction before creating a usable cluster; approved host
execution then initialized the isolated clusters successfully.

Alembic reported one head/current revision `20260805_0005` and no drift before
and after testing. All 13 Proxy/OpenAlex PostgreSQL tests executed with zero
skip, covering exact call/cost settlement, query non-retention, replay, and
historical fake/OpenAlex readability. Direct schema inspection confirmed no
OpenAlex Proxy diagnostic, raw-body, or query-text column. The preserved
historical Hosted `provider_operations.diagnostic_metadata_json` column is
unrelated and unchanged.

After their respective verification runs, both dedicated clusters stopped
cleanly, their loopback port was released, and only their temporary data/socket/
log directories were deleted. ProjectDB and unrelated PostgreSQL services were
untouched.

## Verification

All commands used Conda environment `reagent-dev`, with the OpenAlex credential
and legacy owner-input path variables removed from subprocess environments.

| Command/suite | Result |
|---|---|
| focused OpenAlex adapter/remediation/diagnostic file | 154 passed |
| complete Cloud API Proxy suite | 216 passed |
| Proxy/OpenAlex PostgreSQL files | 13 passed, zero skipped |
| Workflow Package tests | 43 passed |
| Progress Report tests | 38 passed |
| complete backend with isolated SQL URL | 526 passed, 4 skipped |
| backend compileall | passed |
| Alembic heads/current/check | one head; `20260805_0005`; no drift |
| live Provider/documentation/key access | 0 / 0 / 0 |

The four aggregate skips are pre-existing separately gated integrations: the
destructive HTTP/PostgreSQL demo, historical 9B-1 isolated OpenAlex contract,
historical 9B-1 live OpenAlex, and historical 9A-2 research-v2. No Proxy or
OpenAlex PostgreSQL test skipped.

## Changed-file inventory

- `backend/cloud_api_proxy/openalex_adapter.py` — minimal abstract-token helper
  and one call site.
- `backend/cloud_api_proxy/tests/test_openalex_adapter.py` — focused wholly
  fictional formatting, rejection, privacy, strict-response, cost, replay, and
  conflict regressions.
- `.agent_read/decisions/0014-r3c-abstract-formatting-control-compatibility-policy.md`
  — accepted owner policy.
- `docs/architecture/OPENALEX_PAPER_SEARCH_V0_1_ADAPTER_CONTRACT.md` — exact
  abstract-only accepted-shape clarification.
- `docs/architecture/OPENALEX_STRUCTURAL_DIAGNOSTIC_V0_1.md` — unchanged event
  semantics for accepted/prohibited controls.
- `docs/security/R3C_OPENALEX_CREDENTIAL_PRIVACY_AND_COST_POLICY.md` — token-
  value/logging and continued rejection boundary.
- `docs/acceptance/R3C_OPENALEX_LIVE_ACCEPTANCE.md` — future retry requires a
  clean R3C-I2 baseline and fresh owner authorization.
- `docs/PROJECT_DEVELOPMENT_PLAN.md` — actual Retry-3 and offline I2 state.
- `.agent_read/context.md` — compressed current milestone and gates.
- `.agent_read/progress/r3c_openalex_abstract_control_compatibility_remediation.md`
  — this append-only phase record.

No migration, SQL/ORM, API schema, frontend, fixture, Package template, Package,
Progress Report contract, prior acceptance/forensic/progress record, ADR 0009-
0013, or private runtime/live evidence file changed.

## Remaining gates

Offline qualification does not prove live compatibility. The exact Retry-3
character was intentionally not retained and Retry 1 remains unexplained. Any
future live retry requires fresh owner authorization, current official-source
recheck, an owner-controlled key, and the complete supervised acceptance
boundary. R3C remains `LIVE_ACCEPTANCE_PENDING`; production and R3D remain
closed.
