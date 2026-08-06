# Local Artifact Reference Design V0.1

> **Design only.** This registry is separate from current Hosted Artifact
> provenance and does not authorize a general Artifact upload service.

## 1. Contract

An Artifact Reference identifies immutable output bytes or metadata expected
from one Workflow Instance and round. Changing bytes, schema, or producer
creates a new `artifact_id`; availability changes may update the observed state
without rebinding identity.

Required fields are schema version, Artifact identity/type/schema version,
Project, producing Workflow Instance and round, media type, state, production
time, and cloud-metadata flag. Local path is Workspace-relative and optional.
Content checksum and byte size are required for `LOCAL_AVAILABLE` and
`EXTERNAL_AVAILABLE`; an External Resource binding is required when external
bytes are the authoritative materialization source. Consumer bindings name the
consumer Workflow Instance and exact schema predicate.

## 2. Lifecycle states

| State | Meaning | Allowed transition |
|---|---|---|
| `DECLARED` | Producer or manifest declares expected output; no byte claim. | Available, missing, retired |
| `LOCAL_AVAILABLE` | Exact bytes verified at the declared Workspace-relative path. | Missing, stale, retired; new bytes require new ID |
| `EXTERNAL_AVAILABLE` | Exact bytes verified/resolvable through a pinned Resource. | Missing, stale, retired |
| `METADATA_ONLY` | Cloud/local index has metadata but no current byte availability assertion. | Available, missing, stale, retired |
| `MISSING` | Expected bytes were not found at last local check. | Available or retired after explicit check |
| `STALE` | Bytes/reference are valid but no longer meet a consumer or revision requirement. | Available only after re-verification; otherwise retired |
| `INCOMPATIBLE` | Type/schema/media cannot satisfy the selected consumer. | New consumer/explicit converter output; never silent conversion |
| `RETIRED` | Preserved history, excluded from default selection. | Terminal in initial implementation |

State timestamps are observations. Cloud display always qualifies locally
reported availability by observation time.

## 3. Compatibility

Requirements specify Artifact type plus one of:

- `EXACT`: schema identifier must match exactly;
- `COMPATIBLE_RANGE`: producer schema must match a reviewed explicit range with
  semantic compatibility documented; or
- `CONVERTER_REQUIRED`: no direct consumption is permitted; a reviewed
  converter must produce a new Artifact identity/schema.

Unknown versions, absent schema metadata, or incompatible ranges fail with
`ARTIFACT_SCHEMA_INCOMPATIBLE`. Filename or media type similarity is never a
compatibility decision.

## 4. Verified materialization

Artifact sharing is reference plus explicit copy, never symlink or shared
writable state:

1. resolve the exact reference and authorization scope;
2. choose a new consumer-owned destination under
   `artifacts/materialized/<artifact_id>/`;
3. retrieve/copy to protected staging without executing content;
4. enforce size, path, media, schema, and checksum expectations;
5. reject links, devices, path traversal, destination collisions, and
   undeclared content;
6. atomically rename to the absent final destination;
7. write a local index observation binding path and checksum; and
8. pass a read-only reference to the consumer Capsule.

If equivalent bytes need modification, the consumer writes its own declared
mutable output and registers a new Artifact. No Workflow writes another
Capsule's Artifact.

## 5. Cloud boundary and privacy

Initial cloud storage includes only bounded Artifact metadata, checksums,
sizes, schema/type, producer/consumer identities, availability qualifier, and
optional Resource binding. Local paths sent to cloud must be logical
Workspace-relative paths, never private absolute paths. Complete candidate
libraries, reports, code, data, and Resource credentials remain local unless a
future separately authorized byte-transfer product is designed.
