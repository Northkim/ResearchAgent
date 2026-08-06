# 0021: Separate search and upload session lifecycles

- Status: Accepted
- Date: 2026-08-06

## Context

An owner-observed interactive demo completed every local research and
finalization gate, but the following automatic Progress Report request received
HTTP 401. Tracked evidence does not retain the exact failing upload/verification
substage or application code, so expiry is not assigned as the historical root
cause. The implementation nevertheless reused one 15-minute search bearer
across an interaction of unbounded human duration and the post-round upload.

Local artifacts are authoritative after finalization. Upload authorization must
therefore be obtained after local validation and must not depend on how long the
owner spent interacting with Codex.

## Decision

Search and upload use distinct local-session scopes. Normal and demo search
tokens authorize only bounded `paper.search/v0.1` operations for the exact
project, Package, Workflow, adapter, operation count, and cost policy. They
carry no Progress capability and are closed when the research phase ends.

After the four outputs, context, round control, native Progress Report, and
report chain validate, the launcher opens a new two-minute upload-only session.
Its neutral `local.progress-session/v0.1` scope is bound to the exact project,
Package checksum, Workflow version/checksum, execution round, report ID, and
report-content checksum. It has zero search operations, zero Provider calls,
zero Provider cost, and only upload plus report-history/projection verification
capabilities. The token remains in launcher memory and is never passed to Codex.

First upload and next-run upload-only recovery share one implementation. The
same upload envelope is reused for one safe refresh after an explicit expiry
classification or unknown response outcome. Revoked, unknown, malformed,
scope-mismatched, report-mismatched, checksum-mismatched, and unclassified
authentication failures remain terminal. Exact server replay returns the
existing receipt and projection without duplicating a report.

## Consequences

An arbitrarily long research conversation cannot age the later upload
authorization. Expired search cleanup is a warning rather than a local
finalization failure, while upload and cleanup failures retain separate safe
codes so cleanup never masks the primary result. A finalized report without a
verified receipt remains upload-pending and the same Package command reconciles
it without Codex or Provider search.

The existing JSONB capability column stores the optional report binding using a
backward-compatible object form; historical list-form rows continue to load.
No table, migration, Progress Report schema, Package state authority, Hosted
Runtime, Provider adapter, or cloud research responsibility changes.

## Alternatives considered

- Extending the search-token lifetime was rejected because owner interaction
  duration is not a safe authorization boundary.
- Reusing the search token after expiry was rejected because it weakens
  authentication and couples unrelated capabilities.
- Automatically refreshing every HTTP 401 was rejected because revoked,
  unknown, malformed, or wrong-scope credentials must fail closed.
- Regenerating a report after response loss was rejected because the accepted
  upload contract is already content-addressed and idempotent.
