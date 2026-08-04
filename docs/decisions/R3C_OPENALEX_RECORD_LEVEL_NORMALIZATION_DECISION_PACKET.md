# R3C OpenAlex Record-Level Normalization Decision Packet

Date: 2026-08-04

Status: **OWNER DECISION REQUIRED**

This packet does not change ADR 0012, the adapter contract, production code,
or the retry-1 result. It frames one policy ambiguity discovered during R3C-N1.

## Decision question

When one OpenAlex Work is structurally malformed among otherwise valid Works,
must the Provider response fail as a whole, or may valid Works be accepted?

The frozen implementation fails the complete response on the first malformed
Work. ADR 0012 and the adapter contract define strict selected-field
normalization and reject unapproved content, but do not explicitly decide
mixed valid/malformed record behavior. The normalized response has no rejected-
record count or record-level warning field.

This ambiguity does not prove that retry 1 contained a malformed Work. The live
field, path, type, record index, and validator were not preserved.

## Option A — strict complete-response failure

- Preserve the current fail-closed behavior.
- Any structurally malformed Work rejects the complete response.
- No raw record, partial result, warning, or rejected-record count is retained.
- No API schema, SQL schema, migration, identity, checksum, or partial-success
  change is needed.
- One malformed Work can prevent delivery of otherwise valid metadata.

## Option B — record-level quarantine

- Exclude a malformed Work and retain valid normalized Works.
- Add a deterministic warning and rejected-record count without retaining raw
  malformed content.
- Define behavior for all-invalid responses, stable record ordering, operation
  status, replay, checksums, and reconciliation.
- Review and likely revise the public normalized-response contract and tests.
- Keep query/key privacy and the raw-response prohibition unchanged.

This is a new partial-success policy, not a narrow compatibility repair.

## Option C — accept documented optional/null fields, keep structural failure

- Correct only a proven over-strict predicate for an officially and
  contractually allowed missing/null shape.
- Continue failing the complete response for structural malformation.
- Avoid general partial-success semantics.

R3C-N1 did not reproduce any approved nullable or sparse shape that the current
adapter rejects. Option C therefore has no evidence-backed predicate to change
at this gate.

## Recommendation

Recommend **Option A — strict complete-response failure** until a privacy-safe
diagnostic identifies the live rejecting predicate. It preserves the accepted
fail-closed boundary and does not invent a partial-success contract in response
to missing evidence.

The recommendation is not automatically approved. Owner acceptance should be
recorded before any later implementation work relies on this policy.

## Consequences of the owner decision

- Accept Option A: record-level policy becomes explicit, but R3C-I2 remains
  closed until an approved failing shape and exact predicate are identified.
- Select Option B: conduct a separate contract/ADR decision phase before any
  implementation; do not treat it as a normalization bug fix.
- Select Option C: first obtain evidence of the exact approved missing/null
  shape and rejecting predicate; no such evidence exists in R3C-N1.

In every option, another live diagnostic remains separately owner-gated. R3D
remains closed.
