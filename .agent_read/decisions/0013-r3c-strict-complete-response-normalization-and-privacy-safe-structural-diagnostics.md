# ADR 0013: R3C Strict Complete-Response Normalization and Privacy-Safe Structural Diagnostics

- **Status:** Accepted
- **Date:** 2026-08-04
- **Scope:** Experimental R3C OpenAlex Proxy only
- **Governing decisions:** ADR 0009, ADR 0010, ADR 0011, and ADR 0012

## Context

R3C-A retry 1 received one successful HTTP response and exact cost evidence but
settled `PROVIDER_INVALID_RESPONSE`. The response body was correctly not
retained. R3C-N1 could not recover the field, structural kind, record index, or
validator that rejected the response, and no contract-approved failing shape
could be reproduced offline. The remaining safe possibilities included both a
per-Work normalization predicate and the service-level sensitive-content
canary.

The frozen implementation already fails the complete response when any Work
fails normalization. ADR 0012 and the adapter contract did not explicitly
resolve mixed valid/malformed record handling, so owner ratification and a
privacy-safe diagnostic boundary were required before another separately gated
live diagnostic could be considered.

## Decision

### 1. Complete-response failure

R3C uses `STRICT_COMPLETE_RESPONSE_FAILURE`. If any Work in `results` fails the
approved normalization contract, the complete Proxy operation fails. No valid
subset, partial result, warning-bearing success, rejected-record count, raw
record, or record quarantine is returned or persisted.

This ratifies the existing fail-closed behavior. It does not prove that retry 1
contained a malformed Work and does not change which Provider shapes are
accepted or rejected.

### 2. Internal structural diagnostic

The internal contract is
`reagent.openalex-structural-diagnostic/v0.1`. It may contain only:

- fixed contract, adapter, stage, observed-kind, and validator identities;
- operation ID and request-content checksum for safe correlation;
- one path from the closed approved-field path registry;
- record and nested-element indices where applicable;
- the number of records normalized before terminal failure;
- a canonical SHA-256 checksum of a value-free structural descriptor.

It never contains a Provider value, unknown Provider key name, query, runtime
marker, API key, capability token, title, author information, DOI value,
abstract token, venue, language value, raw JSON, URL, header, exception text,
stack trace, or request/response object.

### 3. Structural descriptor

The structural descriptor may encode selected-field presence, missing/null
state, JSON primitive/container kind, bounded array/object counts, approved
path, indices, and fixed validator classification only. It uses the existing
canonical JSON/hash rules. Provider values and unknown key names cannot affect
the descriptor. Equal structural shapes therefore have equal checksums even
when all field values differ.

### 4. Activation and sink

Diagnostics are disabled by default. The only activation is the server-side
process flag:

```text
REAGENT_EXPERIMENTAL_OPENALEX_STRUCTURAL_DIAGNOSTICS_ENABLED
```

Only exact value `1` enables emission. The flag does not mount the Proxy, load
a credential or query, change request mapping, authorize a Provider call, or
change success/failure behavior. When enabled alongside the experimental
OpenAlex Proxy, one terminal normalization or safety failure emits exactly one
canonical structured event named `openalex_structural_diagnostic`.

The approved live sink is an owner-controlled temporary mode-`0600` log outside
Git. No diagnostic is written to normal request/result payloads,
`ProxyOperation` data, Package files, Progress Reports, or public client output.

### 5. Public and durable non-change

The public request, submit response, status response, operation identity,
checksums, idempotency, cost settlement, reconciliation, SQL schema, ORM model,
Package format, and Progress Report contracts are unchanged. No migration or
diagnostic database field is authorized. Historical fake and OpenAlex
operations remain readable.

### 6. Gate boundary

This decision authorizes instrumentation and synthetic/SQL qualification only.
It does not authorize a live Provider call, a key read, a normalization
compatibility repair, or R3D. Any live diagnostic remains separately
owner-gated, limited to at most one call, and subject to a fresh attestation,
credential file, official-source recheck, isolated environment, temporary log,
cleanup, and append-only evidence.

## Consequences

- Mixed valid/malformed arrays deterministically fail as a whole and reveal
  only safe index/count structure when diagnostics are enabled.
- Per-Work normalization, abstract, domain-model, response, size, serialization,
  and service-safety failures are distinguishable without Provider values.
- The service sensitive-content canary remains unchanged and is distinguishable
  from per-Work structural normalization.
- Exact replay of a failed operation does not call the adapter, reserve cost,
  or emit another event.
- Retry-1 root cause and live compatibility remain unknown until a separately
  authorized diagnostic is executed.
- `R3C_I2_IMPLEMENTATION_GATE` and `R3D_PRODUCTION_PROVIDER_GATE` remain closed.

## Alternatives considered

- Record-level quarantine was rejected because it creates partial-success,
  warning, checksum, and API-policy semantics not justified by current evidence.
- Accepting a valid subset without warnings was rejected because it hides data
  loss and weakens provenance.
- Persisting raw responses or detailed exceptions was rejected because it
  violates the query, credential, Provider-value, and raw-body boundaries.
- Adding SQL diagnostic columns was rejected because a temporary structured
  acceptance log is sufficient and minimizes retention.
- Changing nullability or other normalization predicates was rejected because
  R3C-N1 found no approved failing shape and this phase is diagnostic-only.
