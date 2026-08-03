# Progress Report v0.2 Contract

Status: **implemented for R2A; upload acceptance pending R2B**
Schema: `progress-report/v0.2`
Normalizer: `reagent-progress-normalizer/0.2.0`

## Purpose and authority

A Progress Report is an immutable document produced by the existing local
Codex/Claude Code Harness. It reports local task state to the cloud without
giving the cloud authority to continue the task. The local Workflow Package
remains authoritative for concrete research inputs, outputs, context, and
continuation state. Cloud metadata is an audit and aggregation projection.

Progress Reports are not interchangeable with:

| Concept | Producer and purpose | Concrete task authority |
|---|---|---|
| Local Progress Report | Existing local Harness; append-only task progress for explicit upload | Yes, while in the local package |
| Server `ExecutionEvent` | Optional Hosted Mode runtime; lifecycle event stream | No for teacher-aligned local V1 |
| Server `Checkpoint` | Optional Hosted Mode runtime recovery | No for teacher-aligned local V1 |
| `MemoryRevision` | Optional Hosted Mode server memory | No for teacher-aligned local V1 |
| `.agent_read/progress` | Repository development handoff for maintainers | No; it describes ReAgent development, not a user research task |
| Research output | Concrete result authored locally | Yes; referenced by checksum, not replaced by the report |

The R1 v0.1 mismatch was exact: its arbitrary `report_id` was not a content
identity; one `context_checksum` could mean a context object checksum or raw
file digest; its Skill/template fields were version strings rather than full
pins; output references omitted type and size; and the package self-validator
did not validate dynamic report identity, outputs, or chain state. Server event
and checkpoint contracts describe hosted execution and therefore cannot repair
these local-document semantics.

## Native v0.2 fields

`ProgressReportV2` is frozen and includes:

- schema, package, project, Workflow, Harness, round, predecessor, and time
  identities;
- `report_content_checksum`, deterministic `report_id`, and
  `report_checksum`;
- `context_before_checksum` and `context_after_checksum`;
- status (`IN_PROGRESS`, `COMPLETED`, `BLOCKED`, `FAILED`, or `CANCELLED`);
- completed work, current state, next action, optional continuation reason,
  warnings, errors, unresolved questions, and continuation instructions;
- checksum-bound output artifact metadata;
- checksum-bound Skill and package-template pins;
- generation time and the explicit experimental declaration.

Collections are tuple-backed and the contract is frozen. Native v0.2 requires
both context checksums and at least one Skill and template pin.

## Canonical JSON and non-cyclic identity

Canonical JSON is UTF-8 JSON with object keys sorted, separators `,` and `:`,
Unicode retained, non-finite numbers rejected, and no insignificant whitespace.
SHA-256 values use `sha256:<64 lowercase hexadecimal characters>`.

Identity is computed in this order:

1. Remove `report_id`, `report_content_checksum`, and `report_checksum` from
   the report object. SHA-256 of its canonical JSON is
   `report_content_checksum`.
2. Canonically hash this object:

   ```json
   {
     "execution_round": 1,
     "package_id": "<package-id>",
     "previous_report_id": "<string-or-null>",
     "report_content_checksum": "sha256:<digest>",
     "workflow_id": "<workflow-id>",
     "workflow_version": "<semantic-version>"
   }
   ```

   The report ID is `prv2-` plus the 64-character digest portion.
3. Insert the content checksum and report ID, set only `report_checksum` to
   JSON `null`, and SHA-256 the complete canonical object. That digest is
   `report_checksum`.

No field depends on upload time or a database ID. There is no cyclic hash and
no random UUID. Identical semantic report content has identical identity;
changed content changes the content checksum, ID, and final checksum. The
separate `original_report_checksum` in the upload envelope hashes the exact
uploaded bytes, including formatting and a possible trailing newline.

## Context transition

`context_before_checksum` is SHA-256 of the exact authoritative
`memory/context.md` bytes consumed at the beginning of the round.
`context_after_checksum` is SHA-256 of that exact file after local outputs,
decisions, and continuation state have been written. The report append occurs
after that snapshot and must not silently rewrite context.

The values may be equal for a verified no-op round. The cloud can compare the
previous `context_after_checksum` with the next `context_before_checksum`; a
mismatch is `CONTINUITY_CONFLICT`. Without uploaded context bytes, the cloud
records only the claimed digests and does not claim byte verification. It does
not upload hidden conversation history, merge context, or choose a branch.

## Chain rules

Round 1 has no predecessor. Later rounds name the immediately previous report
ID and checksum, increment the round by one, remain in the same project,
package/checksum, and Workflow/version, and continue the context checksum.
Continuing a `COMPLETED` report additionally requires a non-empty new-request
or continuation reason.

Chain states are `VALID_CHAIN`, `LEGACY_CHAIN_WITH_WARNINGS`,
`INCOMPLETE_CHAIN`, `CONTINUITY_CONFLICT`, `IDENTITY_CONFLICT`, and
`BRANCHED_HISTORY`. No automatic merge or winning-branch selection exists.

## v0.1 compatibility

Historical `progress-report/v0.1` bytes and self-checksum remain valid. The
cloud retains those exact bytes, applies a deterministic compatibility
normalizer, and records source schema, normalizer version, assumptions,
unavailable fields, and evidence limitations. The legacy checksum is retained
as `legacy_context_checksum`; native before/after fields remain unavailable.
The normalizer does not fabricate report-content identity, Workflow checksum,
Harness session identity, full pins, or a context transition. Safe round-1
legacy reports may update projection with `LEGACY_CHAIN_WITH_WARNINGS`.

Future generated packages declare v0.2. Executed R1 package bytes, IDs, and
checksums are not rewritten.
