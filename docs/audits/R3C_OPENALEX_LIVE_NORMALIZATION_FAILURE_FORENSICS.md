# R3C-N1 OpenAlex Live Normalization Failure Forensics

Date: 2026-08-04

Status: **INCONCLUSIVE - EXACT LIVE PREDICATE WAS NOT PRESERVED**

This is a documentation and offline-forensics result. It does not change the
adapter, authorize another live call, reinterpret retry 1, or open R3D.

## 1. Exact baseline and safety boundary

The phase began from a clean `main` branch at exact commit
`f78f145b2506400931247d8a669de0ff33367aec`
(`R3C-A-R1: record blocked supervised OpenAlex retry`). Required ancestors
`e381e74dac017f2466ac80b77a582ccc10cf6e78` and
`6ba48416b4936060298b9e5fd9ce197b782b2bb1` were present. Both status commands
were empty and `git diff --check` passed.

The owner key-path variable was present but ignored. No value from that path
was opened. `REAGENT_OPENALEX_API_KEY` was absent from the process environment.
No `.env`, credential file, Provider API, Provider endpoint, database, Uvicorn,
AgentRuntime, Workflow, Hosted Skill, LLM, Judge, or Progress Report path was
used.

The complete repository authority set and all three teacher-PDF pages were
read. The accepted responsibility boundary remains cloud credentialed metadata
transport with local-Harness research interpretation and local task-state
authority.

## 2. Immutable attempt history

- Attempt 0 remains blocked only because its owner-attestation prerequisite was
  absent. It made zero Provider calls and is not an implementation failure.
- Retry 1 remains blocked after exactly one live call and exactly 1,000
  microusd. It received HTTP 200 and cost/rate evidence, then durably settled
  `FAILED / PROVIDER_INVALID_RESPONSE` without normalized Provider data.
- Neither acceptance report nor ADR 0012 was modified in R3C-N1.

## 3. Available and missing live evidence

Preserved safe evidence identifies:

- one actual Provider HTTP call;
- HTTP status 200;
- a bounded response checksum;
- exact cost parsing and settlement at 1,000 microusd;
- successful parsing of the required rate-limit evidence before the failure;
- terminal `PROVIDER_INVALID_RESPONSE`;
- no persisted normalized Provider result;
- no raw response, query, marker, key, title, author, abstract, DOI value, or
  full Provider URL.

The following were not preserved:

- validator/function name;
- record index;
- selected-field presence/null/type bitmap;
- failing JSON pointer;
- field name;
- observed type;
- missing-versus-null distinction;
- per-Work completion count;
- exception message;
- post-normalization sensitive-canary result;
- structural-shape checksum.

The durable operation model stores the stable error code but not the safe
message carried by `ProxyAdapterError`. Consequently:

```text
EXACT_LIVE_FAILURE_PATH = NOT_PRESERVED
```

## 4. Safe ordering deduction

The live tuple narrows the stage without identifying a field:

1. HTTP status validation passed because status was 200.
2. Strict UTF-8/JSON and root-object decoding passed; otherwise no cost could
   have been parsed.
3. `meta.cost_usd`, all required rate headers, their bounds, and the exact
   1,000-microusd price check passed.
4. The failure therefore occurred after line 219 in
   `backend/cloud_api_proxy/openalex_adapter.py`.
5. A non-array or over-count `results` failure is not consistent with the
   durable 1,000-microusd settlement: those two direct errors do not attach the
   already parsed cost to `ProxyAdapterError`.
6. Normalized-size overflow has a different error code.
7. The preserved tuple is consistent with either a per-Work
   `PROVIDER_INVALID_RESPONSE` wrapped at lines 235-245 or the service-level
   sensitive-content rejection at
   `backend/cloud_api_proxy/service.py:293-310`.

This is a source-backed exclusion, not proof of which remaining branch ran.
Multiple Works may have been transiently constructed before a later Work
failed, but the list comprehension discards the entire list and retains no
count. That count cannot be reconstructed.

## 5. Normalization pipeline and failure predicates

| Stage | Source and predicate | Safe outcome/error | Scope | Committed coverage |
|---|---|---|---|---|
| 1. Response bytes | `openalex_adapter.py:120-137,209-216`; decoded bytes exceed 512 KiB | `PROVIDER_RESPONSE_TOO_LARGE` | Complete operation | Direct |
| 2. JSON decoding | `_decode_json`, lines 301-313; invalid UTF-8/JSON, duplicate key, recursion | `PROVIDER_INVALID_RESPONSE` | Complete operation | Direct for malformed JSON |
| 3. Root validation | `_decode_json`; root is not an object | `PROVIDER_INVALID_RESPONSE` | Complete operation | Direct |
| 4. Cost parsing | `_usage_evidence`, lines 316-325; missing/invalid `meta.cost_usd` | `PROVIDER_CONTRACT_CHANGED` | Complete operation | Direct |
| 5. Rate evidence | `_usage_evidence`, lines 326-349; missing, malformed, out-of-range, or contradictory headers | `PROVIDER_CONTRACT_CHANGED` | Complete operation | Direct |
| 6. Price equality | `search`, lines 220-228; parsed cost differs from 1,000 microusd | `PROVIDER_CONTRACT_CHANGED` | Complete operation | Direct through cost cases |
| 7. Results array | `search`, lines 229-231; `results` is not an array | `PROVIDER_INVALID_RESPONSE` | Complete operation | Direct |
| 8. Result count | `search`, lines 232-233; count exceeds requested maximum | `PROVIDER_INVALID_RESPONSE` | Complete operation | Direct |
| 9. Per-Work entry | `_paper`, lines 352-359; item is not an object | `PROVIDER_INVALID_RESPONSE` | Complete operation | Only top-level malformed families; no mixed list |
| 10. Work ID | `_work_id`, lines 482-488; not the required full Work-ID string | `Provider field id was invalid` | Complete operation | Direct |
| 11. DOI | `_paper`, lines 371-380 plus `PaperRecord.internal_id`; non-string or non-canonical nonempty DOI | `doi` or collapsed `paper metadata` invalid | Complete operation | Gap for R3C adapter |
| 12. Title | `_safe_text`, lines 491-497; missing/null/empty, over 2,000 characters, or Unicode category C | `display_name` invalid | Complete operation | Direct for control text; gaps for null/empty/length |
| 13. Authorship list | `_authors`, lines 500-506; non-array, over 100, non-object item, or missing/non-object `author` | `authorships` invalid | Complete operation | Direct only for non-array |
| 14. Author ID/name/ORCID | `_authors`, lines 507-518; name required and bounded, ID optional but when present must be a full Author ID, ORCID optional safe text | field-specific invalid response | Complete operation | No one-property R3C fixtures |
| 15. Abstract | `_abstract`, lines 522-546; non-object, too many tokens/positions, unsafe token, invalid/duplicate/noncontiguous/out-of-range positions, or oversized reconstruction | abstract field/position invalid | Complete operation | Direct for duplicate/gap/size; nullable and empty gaps |
| 16. Publication year | `_paper`, lines 364-366; non-null value is not a non-boolean integer from 1000 through 3000 | `publication_year` invalid | Complete operation | Direct for boolean only |
| 17. Primary location/source | `_venue`, lines 549-560; non-null location/source has wrong type or non-null venue name is unsafe | location/source/venue invalid | Complete operation | Direct for location wrong type only |
| 18. Language | `_paper`, lines 368-370; non-null language is empty, non-string, over 32, or contains category-C text | `language` invalid | Complete operation | Gap |
| 19. Contract construction | `PaperAuthor` and `PaperRecord` in `backend/research/contracts/models.py:255-317`; nonempty identity/name, aware time, checksum, HTTPS, DOI, and limitation invariants | collapsed `paper metadata` invalid for `PaperRecord` | Complete operation | No direct predicate-preserving R3C test |
| 20. Canonical normalized serialization | selected-field checksum and `paper.to_dict()` at `openalex_adapter.py:359,375-396,246-252` | uncaught serialization faults become `PROVIDER_UNAVAILABLE` in service | Complete operation | Baseline only |
| 21. Normalized result size | `openalex_adapter.py:252-261` and `service.py:293-301`; more than 512 KiB | `PROVIDER_RESPONSE_TOO_LARGE` | Complete operation | Direct |
| 22. Sensitive-content canary | `service.py:302-310` calling `workflow_packages.security.reject_sensitive_content` | `PROVIDER_INVALID_RESPONSE` for OpenAlex, no Provider data retained | Complete operation | Indirect fake-adapter canary only |
| 23. Canonical outcome | `contracts.py:592-643`; operation semantic checksum and delivery checksum | constructor/serialization exception, not the observed stable error | Complete operation | Service/identity suites |
| 24. Persistence | `service.py:473-537`, `sql.py:126-147`; failure stores code/call/cost/status/checksum, success stores normalized data | durable terminal ProxyOperation | Complete operation | Proxy and SQL suites historically; no R3C-N1 database |

No predicate implements record-level quarantine. The list comprehension at
`openalex_adapter.py:236` aborts the entire response on the first rejected Work.

## 6. Approved response-shape matrix

The classification combines ADR 0012, the committed adapter contract, current
provider-neutral `PaperRecord`/`PaperAuthor` semantics, and the one narrowly
retrieved official schema page.

| Field | Classification | Expected JSON type | Approved missing/null behavior | Current implementation | Synthetic fixture |
|---|---|---|---|---|---|
| top-level `meta` | `REQUIRED_NON_NULL` | object | Missing/null fails | Matches | Existing malformed test |
| `meta.cost_usd` | `REQUIRED_NON_NULL` | exact number/string | Missing/null fails contract | Matches | Existing cost tests |
| top-level `results` | `REQUIRED_NON_NULL` | array | Missing/null fails | Matches | Existing malformed test |
| Work `id` | `REQUIRED_NON_NULL` | string | Missing/null fails | Matches | Existing invalid-ID test |
| Work `doi` | `REQUIRED_BUT_NULLABLE` | string or null | Missing/null normalizes to null | Matches | R3C-N1 only |
| Work `display_name` | `REQUIRED_NON_NULL` | string | Missing/null/empty fails | Matches | R3C-N1 missing/null/empty |
| Work `authorships` | `REQUIRED_NON_NULL` | object array | Empty array accepted; missing/null fails | Matches | Empty case only in R3C-N1 |
| `authorships[].author` | `REQUIRED_NON_NULL` | object | Missing/null is structurally malformed | Matches strict shape | R3C-N1 only |
| `author.id` | `CONTRACT_UNCLEAR` | string or null | Provider-neutral model allows missing/null | Current adapter accepts | R3C-N1 only |
| `author.display_name` | `REQUIRED_NON_NULL` | string | Missing/null/empty fails `PaperAuthor.name` | Matches | R3C-N1 only |
| `abstract_inverted_index` | `REQUIRED_BUT_NULLABLE` | object or null | Missing/null/empty object -> no abstract | Matches | Null/empty only in R3C-N1 |
| `publication_year` | `REQUIRED_BUT_NULLABLE` | integer or null | Missing/null -> null | Matches | R3C-N1 only |
| `primary_location` | `CONTRACT_UNCLEAR` | official page says object; accepted normalized venue is optional | Contract/implementation allow missing/null | Permissive, not rejecting | R3C-N1 only |
| `primary_location.source` | `OPTIONAL_NULLABLE` | object or null | Missing/null -> no venue | Matches | R3C-N1 only |
| `source.display_name` | `OPTIONAL_NULLABLE` | string or null | Missing/null -> no venue | Matches | R3C-N1 only |
| `language` | `REQUIRED_BUT_NULLABLE` | ISO-style string or null | Missing/null -> null | Matches | R3C-N1 only |

The current official page types DOI, year, language, and abstract as nullable;
it types `display_name` as string, `authorships` as an object array, and
`primary_location` as an object. ADR 0012 and the adapter contract nevertheless
make venue optional. This primary-location wording difference is an owner
review note, but it cannot explain the failure because the implementation
already accepts missing or null primary location.

The official schema does not expressly authorize an empty string for any
selected string field. Empty-string probes were therefore classified
`CONTRACT_UNCLEAR` or rejected, not treated as approved compatibility cases.

## 7. Separate official documentation retrieval

The committed 2026-08-04 source ledger remained primary. One additional
official documentation page was retrieved only because nested/nullability
statements were materially missing:

- title: `Get a single work - OpenAlex Developers`;
- domain: `developers.openalex.org`;
- page: `https://developers.openalex.org/api-reference/works/get-a-single-work`;
- retrieval window: 2026-08-04, completed before the recorded UTC checkpoint
  `2026-08-04T09:06:18Z`;
- purpose: selected Work field types and nullability only;
- no API origin, key, query, or Provider operation was used.

## 8. Offline synthetic reproduction matrix

All cases used wholly fictional values, a synthetic credential-source object,
the committed adapter, a scripted one-response transport, and hard socket/DNS/
HTTP canaries. Each case made exactly one scripted transport invocation and
reported 1,000 microusd when it reached per-Work processing.

| Case | Approved expectation | Actual | Exact safe predicate | Existing committed test |
|---|---|---|---|---|
| Baseline valid | Accept | Accept | - | Direct |
| Optional DOI omitted | Accept | Accept | - | Gap |
| Optional venue name omitted | Accept | Accept | - | Gap |
| DOI null | Accept | Accept | - | Gap |
| Primary location null | Accept | Accept | - | Gap |
| Primary location source null | Accept | Accept | - | Gap |
| Language null | Accept | Accept | - | Gap |
| Abstract null | Accept | Accept | - | Gap |
| Abstract empty object | Accept | Accept | - | Gap |
| Empty authorships | Accept | Accept | - | Gap |
| Authorship missing `author` | Owner decision required | Reject | `Provider field authorships was invalid` | Gap |
| Author ID null | Accept | Accept | - | Gap |
| Author display name null | Reject | Reject | `Provider field author.display_name was invalid` | Gap |
| Publication year null | Accept | Accept | - | Gap |
| Valid sparse Work | Accept | Accept | - | Gap |
| One malformed Work among valid Works | Owner decision required | Reject entire response | malformed Work field predicate | Gap |
| Valid Unicode and punctuation | Accept | Accept | - | Gap |
| Nested unknown fields | Accept and discard | Accept and discard | - | Direct baseline |
| DOI empty string | Contract unclear | Accept as no DOI | - | Gap |
| Venue empty string | Contract unclear | Reject | `Provider field venue was invalid` | Gap |
| Author ORCID null | Accept | Accept | - | Baseline-compatible |
| Author ORCID empty string | Contract unclear | Reject | `Provider field author.orcid was invalid` | Gap |
| Display name empty string | Reject | Reject | `Provider field display_name was invalid` | Gap |
| Authorships omitted | Reject | Reject | `Provider field authorships was invalid` | Gap |
| Display name omitted | Reject | Reject | `Provider field display_name was invalid` | Gap |
| Abstract position gap | Reject | Reject | `Provider field abstract positions was invalid` | Direct |
| Post-normalization sensitive canary | Reject | Reject | `reject_sensitive_content` | Indirect fake-only |

The two owner-decision cases reproduce the durable error/cost signature, but
neither is an approved-shape incompatibility. The sensitive canary also
reproduces that signature intentionally and must not be weakened.

```text
OFFLINE_FAILURE_REPRODUCTION = NOT_REPRODUCED
```

Here `NOT_REPRODUCED` means no contract-approved Provider shape was
deterministically rejected. It does not mean that generic malformed-response
paths could not be exercised.

## 9. Root-cause classification

No safe live field/path/type evidence survives, and every unambiguously
approved sparse/null shape passed offline. The evidence therefore does not
prove an over-strict predicate, normalization transform bug, Provider contract
change, or malformed live record.

```text
ROOT_CAUSE_CLASSIFICATION = INSUFFICIENT_EVIDENCE
ROOT_CAUSE_CONFIDENCE = HIGH
```

Confidence is high in the insufficiency classification, not in any candidate
underlying mechanism.

## 10. Record-level versus response-level policy

Current code is strict complete-response failure. Neither ADR 0012 nor the
adapter contract explicitly decides what to do when one Work is structurally
malformed among otherwise valid Works. The response schema also has no rejected
record count or deterministic record-warning field.

Therefore:

```text
R3C_RECORD_LEVEL_POLICY = OWNER_DECISION_REQUIRED
```

The separate decision packet compares strict complete-response failure,
record-level quarantine, and narrow optional/null compatibility. Option A,
strict complete-response failure, is recommended until evidence identifies a
contract-approved shape. It preserves fail-closed behavior and makes no
unsupported partial-success contract.

## 11. R3C-I2 remediation status

No R3C-I2 compatibility patch is authorized. The exact source predicate/model
to correct is unknown, so the prompt's required precise before/after patch plan
cannot be truthfully completed.

If a later safe diagnostic proves an approved shape is rejected, the smallest
future correction should be confined to:

- `backend/cloud_api_proxy/openalex_adapter.py`, at the exact identified helper
  or `PaperRecord` construction input;
- `backend/cloud_api_proxy/tests/test_openalex_adapter.py`, with one exact
  fictional regression plus adjacent sparse and still-malformed cases;
- existing service and PostgreSQL regression tests, without changing their
  source unless the proven predicate crosses those boundaries.

The preferred compatibility correction would have no API response change, SQL
schema change, migration, operation/checksum identity change, error-category
change, query retention, raw-body retention, additional Provider call, or
partial-success semantics. Historical fake and OpenAlex operations would remain
compatible. This is a conditional boundary, not an implementation plan or
approval.

Any later implementation qualification must cover the exact reproduced case,
adjacent approved sparse shapes, malformed shapes that remain failures,
query/key leakage, cost parsing, exact replay, reconciliation, fake-adapter
regression, and PostgreSQL regression.

## 12. Future one-call diagnostic fallback

Because both prerequisite conditions hold, a future diagnostic requires a
separate owner gate and at most one live call. A diagnostic-only source change
would be reviewed before that call and would retain only:

- approved-field presence bitmap;
- missing/null/JSON-type classification;
- record index;
- safe validator code;
- failing JSON pointer composed only of approved field names and array index;
- structural-shape checksum over those classifications.

It must not retain any field value, query, marker, key, title, author name,
abstract, DOI value, raw JSON, full URL, or unapproved nested data. The
diagnostic should not change public API/response content, SQL schema,
idempotency/checksum identity, normalization outcome, record-level policy,
budget, or retry behavior. A dedicated `0600` diagnostic sink outside Git and
the Package may be used and deleted after a sanitized owner report. No
diagnostic call is executed or authorized here.

## 13. Validation

Using Conda environment `reagent-dev`:

| Command | Result |
|---|---|
| focused OpenAlex adapter tests | 54 passed |
| complete Cloud API Proxy tests | 110 passed |
| `python -m compileall -q backend` | exit 0 |
| offline synthetic probe | completed with zero network attempts |
| `git diff --check` before documentation | exit 0 |

These existing green tests prove deterministic mocked behavior, not current
live compatibility.

## 14. Remaining uncertainty and next gate

Unresolved facts are the exact live record index, field, path, missing/null/type
state, validator, whether prior Works had transiently normalized, and whether
the final rejection was per-Work or the sensitive-content canary.

```text
R3C_NORMALIZATION_FORENSICS = INCONCLUSIVE
R3C_I2_IMPLEMENTATION_GATE = CLOSED
R3C_DIAGNOSTIC_LIVE_CALL_GATE = OWNER_AUTHORIZATION_REQUIRED
R3C_LIVE_PROVIDER_CALL_COUNT_THIS_PHASE = 0
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

Do not implement R3C-I2 or start another live acceptance from this report.
