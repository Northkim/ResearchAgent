# 0046: Canonical bounded scientific findings belong in the Experiment Artifact

- Status: Accepted
- Date: 2026-08-18

## Context

The frozen generic `experiment-record/v4` records exact lifecycle provenance,
process outcome, evaluation validity, scientific evidence status, claim boundaries,
limitations, and an opaque Capability payload checksum. Its bounded findings exist
only in an Artifact-bound Cloud presentation companion. That companion is UI
metadata, while downstream research Workflows may use only exact immutable
materialized Artifact inputs. Treating presentation as evidence would create a
second research authority and make local downstream work depend on Cloud UI state.

## Decision

Publish immutable `experiment-record/v5` as the single final Artifact of forward
Experiment `0.7.0` / Capsule `0.10.0`. It embeds the exact v4 lifecycle record and a
canonical checksummed `reagent.experiment-bounded-scientific-evidence/v0.1`
section. Capability-owned projection produces bounded PROSE, SCALAR, TABLE, SERIES,
FIGURE_REFERENCE, and OUTPUT_REFERENCE blocks from the exact local evaluation
payload. Generic Core validates only typed shape, size, safety, identity, checksum,
and evaluation/output lineage. Claim eligibility remains the conjunction of the
blocks, evaluation validity, scientific evidence status, claim boundaries, and
limitations.

Cloud presentation remains an optional UI projection and is never downstream
research-evidence authority. The ordinary exact Artifact binding and VERIFIED_COPY
materialization path carries all v5 evidence; no second result Artifact or special
payload fetch exists. Experiment 0.6/v4 remains the current default until downstream
product-width compatibility is separately qualified.

## Consequences

Writing, Review, and Revision can later bind one exact Experiment Artifact and read
bounded findings without sibling Workspace access, presentation lookup, or raw
experiment output. V5 remains domain-neutral and supports empty, textual,
categorical, tabular, series, and exact output-reference evidence while preserving
invalid, unavailable, insufficient, and bounded-support states. Large/raw data,
packages, logs, credentials, source, and private paths stay outside the Artifact.

The reference scientific Capability owns its result-to-block mapping; adding a new
scientific family requires its own reviewed projection rather than Generic Core
parsing its fields. Historical v2/v3/v4 contracts and Capsules remain immutable.

## Alternatives considered

- Use the Cloud presentation companion as downstream evidence: rejected because it
  is optional UI metadata and not materialized research authority.
- Publish a second scientific-result Artifact: rejected because it adds pairing and
  Owner-selection ambiguity to one Experiment result.
- Mutate v4: rejected because its Definition, Capsule, validator, and checksums are
  immutable.
- Embed arbitrary/raw Capability output: rejected because it violates boundedness,
  portability, privacy, and domain-isolation requirements.
