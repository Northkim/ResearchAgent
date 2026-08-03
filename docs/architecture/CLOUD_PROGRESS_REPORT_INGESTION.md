# Cloud Progress Report Ingestion

Status: **R2A implemented; R2B live acceptance pending**

## Source-aligned path

```text
existing local Harness
  -> append-only local Progress Report
  -> explicit client upload
  -> untrusted-byte/schema/identity validation
  -> immutable original artifact
  -> normalized cloud record
  -> chain/conflict result
  -> deterministic project progress projection
  -> read-only API
```

The path stops at storage and projection. It does not import or invoke
`AgentRuntime`, `ExecutionDispatcher`, OpenAlex, a structured-generation
provider, or an LLM. It has no run/resume endpoint, cannot generate a research
output, and cannot mutate local context.

## Upload envelope and validation

`progress-report-upload/v0.1` carries project/package/checksum, report schema/
ID/checksum, exact report bytes as base64 JSON content, media type, byte digest
and size, upload time, uploader/client identity, relative source hint, optional
context snapshot metadata, and an envelope checksum. Receipt IDs are cloud
receipt identities and are separate from local report IDs. Safe receipt fields
also carry a deterministic checksum that excludes the replay-display flag, so
an exact replay returns the same receipt identity and receipt checksum.

Only UTF-8 `application/json` reports up to 256 KiB are accepted. Source hints
must be clean relative paths. Validation rejects unsupported schemas, malformed
or mismatched identity/checksums, project/package mismatch, absolute paths,
control characters, hostile script forms, secret-like values, credential/
provider-response keys, invalid Unicode, and oversized structures. Unsafe
secret/path/script evidence is rejected before storage. Uploaded text is never
executed. Projection display strings are HTML-escaped.

## Immutable history and conflicts

`ArtifactContentStorage.write_immutable` retains the exact original at a
content-addressed relative key. PostgreSQL metadata links that key and byte
checksum to the receipt, validation result, normalized record, chain state,
and projection eligibility.

- Same project/package/checksum/report ID/report checksum re-upload returns the
  existing receipt with `idempotent_replay: true` and writes no history row.
- Same report ID with different bytes/checksum is retained as a rejected
  `IDENTITY_CONFLICT`.
- Same original bytes rebound to incompatible project/package identity are
  retained as a rejected identity conflict.
- A duplicate round with a different valid identity is `BRANCHED_HISTORY`.
- Missing predecessor is `INCOMPLETE_CHAIN`; context mismatch is
  `CONTINUITY_CONFLICT`.
- Invalid or conflicting rows remain auditable but never replace accepted
  progress.

Original bytes are append-only. The normalized record always records the
original byte checksum. The materialized projection is derived data and may be
reconstructed from accepted immutable history; a checksum mismatch between
stored and reconstructed projection fails closed.

## Projection

Projection exposes project, package/schema/checksum, Workflow/version, latest
accepted report and round/status, cumulative completed work, current state,
next action, output metadata/checksums, warning/error/unresolved counts,
Harness type, latest local execution/upload times, chain state, and legacy
warning state. It uses only deterministic field selection, de-duplication, and
escaping. There is no summary model or research inference.

## API

- `POST /projects/{project_id}/progress-reports`
- `GET /projects/{project_id}/progress-reports`
- `GET /projects/{project_id}/progress-reports/{report_id}`
- `GET /projects/{project_id}/progress-reports/{report_id}/original`
- `GET /projects/{project_id}/progress`

Accepted new upload is HTTP 201; exact replay is 200; identity/branch/
continuity conflict is 409; invalid envelope/report is 422. No endpoint
continues research. The two report-specific reads accept an optional
`receipt_id` query so a retained rejected/conflicting original remains directly
auditable when multiple receipts share a report ID.

## Persistence

Migration `20260803_0003_progress_reports` adds:

- `uploaded_progress_reports`: append-only receipt, identity, original artifact
  link, validation/chain state, and normalized JSON;
- `project_progress_projections`: deterministic latest projection keyed by
  project/package/Workflow/version.

The tables do not subtype or repurpose `execution_events` or checkpoints.
`SQLAlchemyUnitOfWork` and the in-memory adapter expose a distinct
`ProgressReportRepository`. PostgreSQL remains Cloud Project State only; it
does not replace local task authority.

## Explicit local client

Offline validation:

```bash
python -m backend.progress_reports.client validate \
  --package-root <package-folder> \
  --report memory/progress/reports/<report-id>.json
```

Explicit upload:

```bash
python -m backend.progress_reports.client upload \
  --base-url http://127.0.0.1:8000 \
  --package-root <package-folder> \
  --report memory/progress/reports/<report-id>.json
```

The client validates package/report identity locally, reads only a report
inside the selected package, uses a bounded timeout, makes one request with no
ambiguous automatic retry, embeds no credential, prints only receipt metadata,
and never changes output/context/report files. Authentication remains
`SOURCE_UNDECIDED` for supervised V1.

## Known R2A UI gap

The current Next.js surface is organized around preserved optional Hosted Mode
run/approval pages. R2A intentionally did not add a mixed-authority page there.
The API is complete for an additive future view labelled **Uploaded Local
Progress Reports**. This optional display gap does not authorize reuse of the
hosted event timeline as report history.
