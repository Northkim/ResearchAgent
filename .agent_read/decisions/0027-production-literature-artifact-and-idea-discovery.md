# 0027: Production literature Artifact and Idea Discovery

- Status: Accepted
- Date: 2026-08-07

## Context

NIGHT-B6 proved typed Artifact metadata, exact dependency binding and explicit
local copy using test-only contracts. It intentionally did not guess a
production Artifact type or consumer. The owner subsequently ratified the
first producer/consumer contract so NIGHT-B7 could validate the architecture
with a real second Workflow while preserving all previously published
Literature Search bytes and pins.

## Decision

`selected-paper-library/v1` is the first production Artifact type and schema.
Literature Search 0.4.0 / Capsule 0.6.0 publishes one self-contained canonical
JSON file only after explicit successful finish and validation of
`candidate-papers/v0.2` plus `selected-papers/v0.2`. It joins exact records by
unique `candidate_id`, preserves selected order and exact source records, and
records source checksums. The final canonical UTF-8 bytes determine both the
SHA-256 checksum and
`outputs/artifacts/selected-paper-library/sha256-<digest>.json`. New bytes
create a new Artifact; an existing checksum-bound record is never updated.

Literature Search 0.3.0 / Capsule 0.5.0 remains immutable and supported. It is
not automatically upgraded or promoted. An existing Project must explicitly
retire the old instance and add Literature Search again to adopt the reviewed
producer pin; its history, Package and retained Capsule remain unchanged.

`idea-discovery-local-experimental` 0.1.0 / Capsule 0.1.0 is a reviewed,
available, multi-instance-capable `TRUSTED_BUILT_IN_UNSIGNED` production
Workflow. Its exact `paper_library` requirement accepts one
`selected-paper-library/v1`, uses explicit specific-Artifact selection, and
materializes by verified copy to `inputs/selected-paper-library.json`. There is
no first/latest selection, symlink, hardlink, cloud byte storage, automatic
materialization or browser-local execution.

Idea Discovery is a local interactive Codex/Claude-Code Harness contract. Its
AGENT and prompt require read-only materialized input, separate Capsule memory
and outputs, user review of key choices, stable `candidate_id` provenance,
Progress before session end, and explicit evidence/inference/candidate
direction language. `candidate-ideas/v0.1` and the human-readable report are
normal outputs only; they are not a production Writing Artifact.

The B4 generic sync/compiler path installs the separately pinned Idea Capsule.
The B6 exact binding, Artifact Index, materialization plan and receipt remain
the sole handoff mechanism. The generic Workspace `run` command now selects an
exact installed Workflow Instance and fail-closes Idea Discovery unless its
dependency and materialized checksum are current.

## Consequences

New Projects use Literature Search 0.4.0/0.6.0 and can complete the first real
multi-Workflow chain: producer finish, canonical Artifact, Idea addition,
Manifest revision, incremental sync, explicit binding and copy, local Idea
execution, Progress and Registry-driven Board projection. Existing Projects
and old Capsule checksums do not change.

Cloud can answer provenance and setup state but cannot recover lost local
bytes. Installed state, dependency binding, materialization and research
Progress remain distinct. Retiring a producer preserves references and local
outputs; materialization remains possible only while retained bytes verify.

Writing, Review, Experiment, novelty search, cross-Project sharing, cloud
Artifact bytes, automatic selection/materialization and background execution
remain deferred.

## Alternatives considered

- Mutating Literature Search 0.3.0/0.5.0 was rejected because immutable
  checksum-bound Packages and installed Capsules must remain reproducible.
- Promoting legacy selected files was rejected because the old Capsule never
  declared the production finalization/type contract.
- Bundling every Literature Search output was rejected because the ratified
  single-file joined schema is sufficient and avoids another unstable bundle
  checksum contract.
- Selecting the only or latest compatible Artifact was rejected because it
  becomes unsafe as soon as a Project has two Literature Search Instances.
- Cloud execution and direct sibling-output reads were rejected because they
  violate the hybrid Workspace/Capsule ownership boundary.
