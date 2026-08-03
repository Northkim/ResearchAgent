# R2B External Progress Upload Acceptance

Status: **UPLOAD_ACCEPTANCE_PENDING**
R2A does not claim that this guide has been executed.

## Preconditions

- Use the committed R2A source and migration head `20260803_0003`.
- Create a new isolated PostgreSQL test database; do not use `ProjectDB` or a
  previous acceptance database.
- Use an isolated artifact root and fictional/approved package identity.
- Keep a pre-upload checksum snapshot of the complete local package.
- Start only the cloud management stack needed for upload/read storage.
- Instrument or inspect provider/runtime operations so non-use is observable.

## Procedure

1. Start the cloud management stack and record backend, database, and artifact
   configuration without recording credentials.
2. Select either the executed R1B v0.1 Progress Report or a freshly executed
   v0.2 package report. Do not commit the executed package or machine paths.
3. Run the local client `validate` command offline and retain its safe summary.
4. Explicitly upload the report to an isolated project/package identity.
5. Read the receipt, history item, exact original endpoint, and project
   projection.
6. Compare downloaded original bytes to the local report byte-for-byte and by
   SHA-256.
7. For v0.1, verify the original schema remains v0.1 and the normalized record
   explicitly records ambiguity/unavailable fields. For v0.2, recompute all
   three identity values and context field presence.
8. Re-upload the exact envelope/report and verify HTTP 200,
   `idempotent_replay: true`, the same receipt ID, and one history row.
9. Submit a fictional conflicting report with the same report ID and different
   checksum. Verify HTTP 409, retained rejected evidence, conflict state, and
   an unchanged accepted projection.
10. Submit a missing predecessor or context-continuity mismatch and verify it
    cannot replace accepted progress.
11. Restart the backend and database connection. Re-read history, original
    bytes, conflict result, and projection; verify projection reconstruction.
12. Confirm zero AgentRuntime/ExecutionDispatcher invocation, zero OpenAlex or
    structured-generation/LLM/provider call, and zero Workflow execution or
    run/resume side effect.
13. Recompute the complete local package snapshot and prove it is unchanged.

## Required evidence

- exact commands and exit codes;
- isolated database name and artifact-root label, with no credential;
- request/response status and safe receipt IDs/checksums;
- local versus downloaded byte checksum and byte comparison;
- normalized v0.1 limitations or native v0.2 identity recomputation;
- pre/post history counts and projection fields;
- conflict row plus unchanged accepted projection;
- restart/reload evidence;
- pre/post local package checksum diff;
- static/runtime proof of no research/runtime/provider call.

## Result rule

R2B passes only when upload, exact retention, normalization, immutable history,
idempotency, conflict exclusion, projection, restart reload, local-folder
non-mutation, and hosted-boundary gates all pass. R2A test results are not a
substitute for this external acceptance.

Authentication and multi-user permission policy remain `SOURCE_UNDECIDED`.
Conflicts remain manual/auditable; the cloud must not choose a branch.
