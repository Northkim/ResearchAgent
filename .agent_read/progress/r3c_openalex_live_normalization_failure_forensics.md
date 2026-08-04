# R3C-N1 Live OpenAlex Normalization Failure Forensics

Date: 2026-08-04

## Result

R3C-N1 completed as an inconclusive documentation-only forensic phase. It made
zero live Provider calls, did not read an OpenAlex key or `.env`, did not use a
database or Runtime path, and did not modify production source, tests,
migrations, contracts, ADRs, or either immutable acceptance report.

The exact retry-1 live failure path was not preserved. Safe durable evidence
shows HTTP 200, successful exact 1,000-microusd cost and rate parsing, terminal
`PROVIDER_INVALID_RESPONSE`, and no accepted normalized result. Source ordering
excludes failures before cost parsing, the direct top-level results predicates,
and normalized-size overflow. It cannot distinguish a per-Work predicate from
the service-level sensitive-content canary.

An offline, network-disabled synthetic matrix exercised the committed adapter
with one shape variation at a time. All unambiguously approved nullable and
sparse shapes were accepted. Malformed and sensitive-canary shapes reproduced
the generic durable error/cost signature, but no approved Provider shape was
deterministically rejected.

```text
EXACT_LIVE_FAILURE_PATH = NOT_PRESERVED
OFFLINE_FAILURE_REPRODUCTION = NOT_REPRODUCED
ROOT_CAUSE_CLASSIFICATION = INSUFFICIENT_EVIDENCE
ROOT_CAUSE_CONFIDENCE = HIGH
```

## Policy and gates

ADR 0012 and the adapter contract do not unambiguously specify treatment of one
malformed Work among otherwise valid Works. A separate owner-decision packet
recommends retaining strict complete-response failure (Option A) until better
evidence exists. This recommendation is not owner approval.

Because neither the exact live path nor an approved offline reproducer exists,
no R3C-I2 patch is authorized. A future privacy-safe structural diagnostic may
use at most one separately owner-authorized live call. It may retain only field
presence, missing/null/type classes, an approved-field pointer, record index, a
safe validator code, and a structural checksum—never field values, query, key,
paper metadata, raw JSON, or full Provider URL.

```text
R3C_NORMALIZATION_FORENSICS = INCONCLUSIVE
R3C_RECORD_LEVEL_POLICY = OWNER_DECISION_REQUIRED
R3C_I2_IMPLEMENTATION_GATE = CLOSED
R3C_DIAGNOSTIC_LIVE_CALL_GATE = OWNER_AUTHORIZATION_REQUIRED
R3C_LIVE_PROVIDER_CALL_COUNT_THIS_PHASE = 0
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

## Validation

- Focused OpenAlex adapter suite: 54 passed.
- Complete Cloud API Proxy suite: 110 passed.
- Backend compileall: passed.
- Offline synthetic probe: completed with hard network canaries and no network
  attempt.
- No PostgreSQL was created or used.
