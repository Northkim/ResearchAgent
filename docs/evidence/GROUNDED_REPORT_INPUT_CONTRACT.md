# Grounded Report Input Contract

Status: **Proposed `GroundedReportInput/v1`**
Date: 2026-07-30

## Immutable fields

`GroundedReportInput` is canonical-JSON serializable, deeply immutable, and
SHA-256 addressed. It contains:

- `project_id`, `workflow_run_id`, `workflow_id`, `workflow_version`;
- `approved_selected_paper_artifact_id` and checksum;
- `approval_request_id`, status, expiry, and `approval_fingerprint`;
- ordered `paper_record_ids` and record checksums;
- ordered `source_content_ids` and SourceContent checksums;
- deterministic citation-label-to-paper mapping;
- `query_hash` and search/normalization operation IDs;
- `content_scope: ABSTRACT_ONLY` and user-visible disclosure text;
- prompt IDs/versions/hashes and skill/workflow/schema versions;
- allowed provider, exact model ID/snapshot, adapter version, endpoint mode;
- token/call/cost/runtime budgets and currency;
- `created_at`, `input_checksum`, `schema_version`.

No mutable collection, credential, rank, citation count, raw provider response,
arbitrary executable rule, or unrelated project content is permitted.

## Approval binding

The application reconstructs the input from stored records; clients do not
supply trusted checksums. Before reserving an LLM operation it must:

1. load the selected artifact and recompute its checksum;
2. verify the approval request is approved, unexpired, unrejected, and for the
   current run/step/attempt;
3. recompute the existing approval fingerprint including pinned skill versions;
4. compare the ordered PaperRecord set and SourceContent set exactly;
5. verify every prior OpenAlex ProviderOperation is settled;
6. generate `[P1]…[Pn]` from the approved artifact order;
7. validate DOI uniqueness and all source hashes;
8. compute canonical input checksum.

## Fail-closed rejection

Reject before any LLM reservation or call for:

- missing, expired, pending, or rejected approval;
- unapproved/additional/missing paper or changed order/ID;
- changed selected-paper, PaperRecord, or SourceContent checksum;
- unknown/duplicate citation label or duplicate normalized DOI;
- unset or non-`ABSTRACT_ONLY` content scope;
- unsettled search operation;
- provider/model/prompt policy mismatch;
- token/cost/call reservation exceeding owner-approved budget.

There is no “best effort” substitution. A new paper set or source checksum
requires a new approval and new input checksum.

## Class D limits

Proposed: 3–5 approved papers and at most 12,000 normalized Unicode characters
of abstract text per paper. Longer input pauses for owner review; it is not
silently truncated. Alternatives are 3 papers/8,000 characters or a separately
approved deterministic excerpt artifact. The proposal balances useful coverage
against privacy, cost, and attention risk; it blocks implementation until owner
approval and is revisited after real token measurements.

## LLM-visible projection

Only topic, citation label, title, bounded abstract, year, venue, content-scope
notice, rubric, and output schema are projected. Local/project/database IDs are
replaced by run-scoped pseudonymous paper IDs. Authors, DOI, OpenAlex ID/URL,
rank, citation count, human notes, approval internals, other outputs, paths, and
keys remain outside the prompt unless separately approved.

