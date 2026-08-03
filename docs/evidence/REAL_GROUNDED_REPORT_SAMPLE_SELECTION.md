# Real Grounded Report Three-paper Sample Selection

Date: 2026-07-30  
Status: **Proposed private-manifest protocol; no paper selected**

## Selection rule

The live acceptance uses exactly three real papers from one owner-approved
OpenAlex search result set:

1. one paper central to the approved topic;
2. one complementary paper supporting a common theme;
3. one paper providing a useful methodological or empirical contrast.

All three must have usable abstracts. At least two should support one theme and
one agreement; at least two should permit a qualified comparison or
disagreement. This is purposeful acceptance coverage, not a representative
sample or retrieval-quality evaluation.

Exclude duplicate DOI/OpenAlex identity, a record marked retracted when that
field is available, missing/empty abstract, content requiring private access,
PDF/full text, and any paper whose title or abstract the owner does not approve
for hosted processing. Rank and citation count are hidden from the generation
provider and do not justify selection.

## Private manifest

The ignored manifest should be canonical JSON and contain only:

- `acceptance_id`;
- private `project_id` and `workflow_run_id`;
- topic;
- paper and SourceContent IDs;
- selected-paper artifact ID and checksum;
- approval request ID and fingerprint;
- PaperRecord and SourceContent checksums;
- deterministic citation label;
- selection-rationale category;
- `content_scope: abstract_only`;
- retention expiry;
- schema version and manifest checksum.

Titles, abstracts, DOI, OpenAlex IDs, and provider URLs remain in the private
approved artifacts, not the committed manifest template or documentation.

## Approval and validation

The existing exact approval boundary must bind the ordered paper set and
produce `[P1]`, `[P2]`, `[P3]`. Before any LLM reservation, ReAgent must verify
approval status/expiry/fingerprint, selected artifact bytes/checksum, paper and
SourceContent checksums, order, DOI/OpenAlex uniqueness, abstract-only scope,
settled search operations, and private manifest checksum.

If an abstract exceeds the proposed 12,000 normalized Unicode-character cap,
preflight fails. No silent truncation is allowed. A separately approved,
checksum-bound excerpt policy would create a new SourceContent version and
requires owner reapproval.

## Retention

The private manifest and isolated acceptance storage have a proposed 30-day
expiry. No manifest or real content is committed to Git. Cleanup is performed
only after owner review and an evidence-retention decision.

