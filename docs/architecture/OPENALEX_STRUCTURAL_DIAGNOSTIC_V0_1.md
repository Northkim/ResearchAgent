# OpenAlex Structural Diagnostic v0.1

Status: **R3C-N2-I IMPLEMENTED AND SYNTHETIC/SQL QUALIFIED; LIVE DIAGNOSTIC OWNER-GATED**

Date: 2026-08-04

Governing ADRs: 0012 and 0013

## 1. Purpose and boundary

`reagent.openalex-structural-diagnostic/v0.1` identifies the structural point
at which an experimental OpenAlex response failed without retaining or exposing
Provider values. It is internal observability, not a client API, a compatibility
repair, or acceptance evidence by itself.

Strict complete-response failure remains authoritative. Diagnostics do not
change request mapping, validation, normalization, cost, idempotency,
reconciliation, persistence, or the public error category.

## 2. Activation

The process-only flag is:

```text
REAGENT_EXPERIMENTAL_OPENALEX_STRUCTURAL_DIAGNOSTICS_ENABLED
```

Only exact value `1` enables emission. It is false by default and is independent
of `REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED`. The diagnostic flag alone
does not mount a route, construct a credential source, read a query or key, or
authorize network activity.

## 3. Event schema

One enabled terminal OpenAlex normalization or safety failure emits one event
named `openalex_structural_diagnostic` with exactly these diagnostic fields:

| Field | Type | Rule |
|---|---|---|
| `diagnostic_contract_version` | string | fixed contract identity |
| `adapter_id` | string | fixed OpenAlex Proxy adapter ID |
| `adapter_version` | string | configured adapter version |
| `operation_id` | string | public `proxyop-v1-` identity |
| `request_content_checksum` | string | canonical SHA-256; never request text |
| `failure_stage` | enum | closed registry below |
| `approved_json_path` | enum | closed path registry below |
| `record_index` | non-negative integer or null | structural array index only |
| `nested_element_index` | non-negative integer or null | structural nested index only |
| `observed_kind` | enum | value-free structural class |
| `validator_code` | enum | closed fixed predicate identity |
| `normalized_records_before_failure` | non-negative integer | safe count only |
| `structural_shape_checksum` | string | canonical SHA-256 of value-free shape |

The log envelope additionally contains fixed `event` value
`openalex_structural_diagnostic`. No arbitrary exception string is a field.

## 4. Closed failure-stage registry

```text
RESPONSE_BYTES
JSON_ROOT
COST_USAGE
RESULTS_ARRAY
WORK_NORMALIZATION
AUTHORSHIP_NORMALIZATION
ABSTRACT_RECONSTRUCTION
PAPER_MODEL_VALIDATION
NORMALIZED_SERIALIZATION
SERVICE_SAFETY
RESULT_SIZE
UNCLASSIFIED_INTERNAL
```

## 5. Closed observed-kind registry

```text
MISSING
NULL
WRONG_TYPE
EMPTY
INVALID_VALUE
INVALID_POSITION
LIMIT_EXCEEDED
CONTROL_CHARACTER
SENSITIVE_CONTENT
MODEL_VALIDATION
UNKNOWN
```

## 6. Closed approved-path registry

```text
/
/meta
/meta/cost_usd
/results
/results/*
/results/*/id
/results/*/doi
/results/*/display_name
/results/*/authorships
/results/*/authorships/*
/results/*/authorships/*/author
/results/*/authorships/*/author/id
/results/*/authorships/*/author/display_name
/results/*/authorships/*/author/orcid
/results/*/abstract_inverted_index
/results/*/publication_year
/results/*/primary_location
/results/*/primary_location/source
/results/*/primary_location/source/display_name
/results/*/language
/normalized_results
/service_safety
```

Unknown Provider key names cannot become paths. Validator codes are the closed
`ValidatorCode` registry in `backend/cloud_api_proxy/openalex_diagnostics.py`;
they name predicates and contain no input or exception text.

## 7. Structural-shape checksum

The descriptor identity is
`reagent.openalex-structural-shape/v0.1`. It may encode only:

- presence/absence and JSON kind of approved selected fields;
- null versus non-null structural state;
- bounded approved-field/object/array counts;
- approved path plus record/nested indices;
- the fixed failure stage, observed kind, and validator classification.

It excludes string contents, numeric Provider values, identifiers, titles,
authors, DOI, abstract tokens and positions, venue, language value, query, key,
URL, unknown Provider key names, raw JSON, and headers. The descriptor is
canonicalized with the existing Proxy canonical JSON rules and hashed with
SHA-256. Tests require determinism, same-shape/different-value equality, and
different-shape inequality.

## 8. Failure propagation

Known adapter predicates attach an immutable `OpenAlexStructuralFailure` before
generic service wrapping. Unexpected exceptions map to
`UNCLASSIFIED_INTERNAL / UNKNOWN / UNCLASSIFIED_INTERNAL` without their text.
The service adds only operation ID, request checksum, and adapter version, saves
the ordinary terminal operation, and conditionally emits the event.

The normal external categories remain unchanged, including
`PROVIDER_INVALID_RESPONSE`, `PROVIDER_CONTRACT_CHANGED`,
`PROVIDER_RESPONSE_TOO_LARGE`, and `PROVIDER_UNAVAILABLE`. The diagnostic is not
part of the delivery/status DTO.

## 9. Strict mixed-record behavior

Normalization proceeds in Provider order only to obtain a safe first-failure
index and count. If record `n` fails, the complete response fails, no normalized
paper list is retained, and later records are not normalized. The diagnostic
may report `record_index=n` and the count already constructed transiently. It
never contains those records or their values.

Exact replay reads the durable terminal operation and emits no second adapter
call, cost reservation, settlement, or diagnostic event.

## 10. Service-safety distinction

The unchanged sensitive-content scanner runs after canonical normalization and
before persistence. A match remains complete-response
`PROVIDER_INVALID_RESPONSE`; when diagnostics are enabled, it is identified
only as:

```text
failure_stage = SERVICE_SAFETY
approved_json_path = /service_safety
observed_kind = SENSITIVE_CONTENT
validator_code = SERVICE_SENSITIVE_CONTENT
```

The matched pattern, substring, field, surrounding text, and exception are not
logged. This is distinct from `WORK_NORMALIZATION` and related per-Work stages.

## 11. Logging and retention

Disabled mode emits nothing. Enabled mode uses one canonical structured warning
event with no `exc_info`, stack trace, request/response object, HTTPX request
representation, URL, header, query, key, token, or Provider value. A future
live diagnostic may route that logger only to an owner-controlled temporary
mode-`0600` file outside Git.

No migration, ORM field, SQL payload, Package file, artifact, Progress Report,
submit response, status response, or client option is introduced.

## 12. Qualification and gates

Synthetic tests cover all current response/per-Work predicates, service safety,
mixed-record complete failure, value-independent hashing, leakage canaries,
cost, replay, reconciliation, fake-adapter isolation, and no-network behavior.
Existing SQL suites verify durable compatibility without a diagnostic column.

No live diagnostic has occurred. `R3C_I2_IMPLEMENTATION_GATE` remains closed.
The at-most-one-call live diagnostic gate requires separate owner authorization
under `R3C_OPENALEX_STRUCTURAL_DIAGNOSTIC_LIVE_ACCEPTANCE.md`. R3D remains
closed.
