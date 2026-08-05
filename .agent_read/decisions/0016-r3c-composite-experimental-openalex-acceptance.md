# ADR 0016: R3C Composite Experimental OpenAlex Acceptance

- **Status:** Accepted
- **Date:** 2026-08-05
- **Scope:** Experimental R3C OpenAlex Proxy closure only
- **Governing decisions:** ADR 0009 through ADR 0015

## Context

R3C-A-R4 made the only post-remediation live OpenAlex call. It returned HTTP
200, normalized five real Works into an 8,726-byte canonical body, settled
exactly 1,000 microusd, and passed the pre-restart status, replay, conflict,
privacy, Package, and Hosted/runtime gates. The same PostgreSQL cluster and a
new Uvicorn generation restarted successfully, but the post-restart controller
raised a value-free `RuntimeError`. R3C-A-R4 therefore remains an immutable
`BLOCKED` attempt and is not reclassified as a pass.

R3C-R1 reproduced the recovery symptom deterministically with fictional data
and no live Provider use. It established that an aged exact replay reached
`CLIENT_TIMESTAMP_OUT_OF_RANGE` because timestamp freshness preceded durable
idempotency resolution. R3C-R2 then implemented the owner-ratified ordering in
ADR 0015 and qualified it through focused, API/client, concurrent, PostgreSQL,
and physical PostgreSQL/Uvicorn restart regressions. The owner has accepted the
R3C-R2 implementation and results.

No single run on the final R3C-R2 HEAD exercised every live and recovery gate.
The owner therefore had to decide whether the immutable live evidence and the
subsequent offline recovery evidence could be composed without another live
Provider call.

## Decision

The owner accepts the R3C evidence composition with warnings.

Provider-specific gates are supplied by R3C-A-R4: owner authorization,
current-source qualification, supervised credential injection, the fixed
Works origin, one real HTTP-200 call, five real normalized Works, the
8,726-byte canonical normalized result, exact 1,000-microusd accounting,
approved rate evidence, query/credential/raw-body privacy, pre-restart status
and replay, changed-content conflict, Package non-mutation, and Hosted/runtime/
LLM isolation.

Recovery and remediation gates are supplied by R3C-R1 and R3C-R2: deterministic
delayed-replay reproduction, the exact ordering root cause, authorized durable
operation resolution before freshness, conflict before freshness, continued
stale-new-admission rejection, expired/revoked/wrong-scope protection, real
PostgreSQL and Uvicorn restart, both status routes, delayed exact replay, a
stable result/checksum/call/cost ledger, complete backend and zero-skip Proxy/
OpenAlex SQL regressions, and zero additional live Provider calls.

This composition is accepted because ADR 0015 changes only service admission
ordering after request validation, authentication, and authorization. It does
not change OpenAlex transport, selected fields, normalization, result order,
request or result schemas, checksums, SQL models, cost accounting, retention,
credential handling, query privacy, diagnostics, Package behavior, or Hosted
boundaries. The corrected branch is exercised before any adapter invocation,
and R3C-R2 proved zero transport invocation on replay. The evidence sets are
therefore orthogonal at the changed boundary.

Historical attempt outcomes remain immutable. In particular, R3C-A-R4 remains
`BLOCKED`; retry 1 remains unexplained; and no earlier `BLOCKED`, `FAIL`, or
`INCONCLUSIVE` state is converted into `PASS`. Composite closure is a new
higher-level owner decision.

The accepted final experimental state is:

```text
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
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
R2_STATE = UPLOAD_ACCEPTED
R3B_STATE = FAKE_PROXY_ACCEPTED
```

No unresolved hard gate remains for the experimental R3C slice. This decision
does not authorize a public or production deployment, another Provider, or
R3D.

## Consequences

- R3C closes as `LIVE_OPENALEX_ACCEPTED` with warnings by composite evidence.
- A further live OpenAlex call is neither required nor authorized for R3C
  closure.
- R3C-A-R4 remains a blocked historical attempt, while its safe live sub-gate
  evidence remains the live component of the composite decision.
- The final restart acceptance is explicitly compositional, not a claim that
  the live R3C-A-R4 operation was successfully replayed after restart.
- The experimental OpenAlex adapter remains disabled by default and
  non-production.
- OpenAlex is the only accepted Provider and `paper.search/v0.1` remains the
  only accepted experimental capability.
- Production authentication, multi-user authorization, public HTTPS, proof of
  possession, secret management, real-user disclosure, and production
  retention remain unresolved.
- R3D remains closed pending a separate owner decision.

## Remaining warnings

- No single end-to-end live run occurred on the final R3C-R2 HEAD.
- R3C-A-R4 remains an immutable blocked attempt.
- Retry 1 remains historically unexplained.
- Only limited fictional public acceptance queries were used, and live
  Provider error conditions were not intentionally induced.
- Official Provider behavior, pricing, Terms, and Privacy may change.
- Claude Code remains untested and frontend work remains deferred.
- Real-user third-party query disclosure is not implemented.
- This acceptance does not authorize public or production deployment.

## Alternatives considered

- Require another end-to-end live call on final HEAD: rejected for R3C closure
  because the only changed behavior is a pre-transport recovery ordering that
  R3C-R2 qualified with real processes, stable persistence, and hard zero-
  transport evidence. Another live call would add cost and disclosure without
  testing a Provider-facing change.
- Reclassify R3C-A-R4 as passing: rejected because its mandatory post-restart
  controller gate failed and immutable audit outcomes must not be rewritten.
- Treat R3C-R2 as production acceptance: rejected because its qualification is
  experimental, synthetic, loopback-only, and leaves the production security
  and retention decisions unresolved.
