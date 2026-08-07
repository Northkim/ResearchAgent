# 0026: Typed Artifact References and explicit local materialization

- Status: Accepted
- Date: 2026-08-07

## Context

NIGHT-B1 through NIGHT-B5 established independently identified Workflow
Instances and immutable Progress history, but Progress Artifact fields remained
display metadata. They could not safely establish that one exact producer
output was the reproducible input of another Workflow Instance. Cloud also
does not hold Workspace Artifact bytes, so a metadata reference cannot prove
that the local bytes still exist or still match their reported checksum.

ARCH-D1 requires typed, immutable, checksum-bound references, explicit verified
materialization, and no shared writable file or symlink. Its Artifact examples
are design examples rather than production type approval. The current
Literature Search Capsule compatibility contract contains no ratified
`artifact_outputs` declaration, and no second production Workflow exists.

## Decision

Local-product Artifact metadata uses the separate
`local_artifact_references` namespace and never reuses Hosted `artifacts`.
Each record binds an exact Project, producer Workflow Instance, producing
Progress receipt/report/round, exact Capsule pin, reviewed type/schema/media,
producer-relative output path, byte size and SHA-256 checksum. That immutable
identity cannot be updated to represent new bytes; a new output needs a new
Artifact ID.

Progress promotion is additive and atomic with ingestion. It is permitted only
when the exact Capsule compatibility contract declares the Artifact output and
the declaration exactly matches immutable Progress output metadata. Exact
retry returns the canonical rows; changed declarations fail closed. Existing
Progress metadata is preserved but is not guessed into canonical Artifacts.

Consumer requirements belong to an immutable Workflow Definition Version.
Project-scoped dependency bindings select a specific Artifact ID and expected
checksum for one exact consumer Workflow Instance and input slot. There is no
implicit latest selection or cross-Project binding. B6 bindings are a
reproducible input-selection record, separate from Desired Manifest Capsule
installation state; no parallel desired-Capsule truth or Manifest revision is
created.

`.reagent/artifact-index.json` is the canonical local index of independently
re-read and checksum-verified producer bytes. It is separate from
`.reagent/installed-lock.json`, which continues to describe Capsule
installation only. Explicit `artifact refresh` verifies producer outputs and
explicit `artifact materialize` copies one plan-bound Artifact through
same-filesystem staging into the consumer `inputs/` root. It never uses a
symlink or hardlink, never mutates the producer, never overwrites an existing
different target, and writes a checksummed receipt only after post-publish
verification. The B4 Workspace advisory lock serializes sync, Index mutation,
and materialization.

Cloud persists metadata and provenance only. It neither receives nor verifies
the Artifact bytes and cannot restore missing producer bytes. No production
Artifact type or consumer Workflow is seeded in B6. Reviewed test-only Capsule
contracts prove the generic infrastructure without introducing Idea Discovery.

## Consequences

A provenance chain can now be queried from consumer binding through exact
Artifact, producer Workflow Instance and producing Progress. Local
materialization revalidates the same checksum against the Cloud plan, local
Index, producer source and copied target. Source drift, Index drift, target
conflict, unsafe paths and incomplete crash states fail closed. A
publish-before-receipt crash can be recovered by exact checksum verification
without overwriting the target.

Users must explicitly refresh and materialize; sync does not transfer research
outputs. Producer retirement preserves history and retained local bytes remain
eligible when their identity and checksum still verify. Artifact Reference is
not cloud byte storage, backup, automatic latest resolution, or cross-Project
sharing.

## Alternatives considered

- Reusing Hosted Artifact provenance was rejected because it is a different
  execution architecture and ownership boundary.
- Treating Progress display metadata as canonical was rejected because it lacks
  a reviewed type contract and verified local-byte observation.
- Storing materialized inputs in Installed Lock was rejected because Capsule
  installation and produced research outputs are independent facts.
- Symlink, hardlink, shared writable directory and in-place overwrite handoff
  were rejected because a consumer could mutate producer evidence or destroy
  user state.
- Selecting the latest Artifact by type was rejected because it silently
  changes reproducible consumer input.
- Seeding `selected-paper-library` or Idea Discovery was rejected because no
  production type/consumer identity is owner-ratified yet.
