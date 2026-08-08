# Full Research Flow contracts

Status: owner-ratified contract foundation (NIGHT-F1A)

ReAgent composes five independent Workflows. Literature Search and Idea
Discovery have reviewed production research cores. Writing, Review, and
Reproduction & Experiment are not production Workflows yet; F1A defines only
their future handoff schemas and dependency map.

```text
Literature Search
  -> selected-paper-library/v1
  -> Idea Discovery
  -> selected-research-idea/v1
       |-> future Writing -> manuscript-draft/v1
       |                       -> future Review -> review-report/v1
       |                              -> future Writing revision
       `-> future Reproduction & Experiment -> experiment-record/v1
                                                   `-> optional future Writing input
```

This is a non-linear composition model, not a persisted pipeline entity.
Every edge binds one specific same-Project `artifact_id` and checksum. There is
no automatic latest/first selection, display-name resolution, shared writable
directory, symlink, or hardlink handoff. The consumer explicitly binds and
materializes bytes through the existing B6 verified-copy mechanism.

## Core Capability Maturity

`core_capability_maturity` is canonical on an immutable Workflow Definition
Version and is independent of lifecycle or review status:

- `REVIEWED_CORE`: the version contains an implemented, reviewed research core;
- `SCAFFOLD_CORE`: the version may exercise real flow, state, persistence and
  Artifact contracts, but its research core is explicitly a placeholder.

Existing executable Literature Search versions and Idea Discovery 0.1.0 are
backfilled as `REVIEWED_CORE`; Idea Discovery 0.2.0 is also reviewed. A JSON
Artifact maturity value must match its producer Workflow Version. A client
cannot upgrade a scaffold claim to reviewed maturity.

## selected-research-idea/v1

Producer: Idea Discovery Definition 0.2.0 / Capsule 0.2.0 (`REVIEWED_CORE`).

Media type: `application/json`.

Path:
`outputs/artifacts/selected-research-idea/sha256-<content-sha256>.json`.

```json
{
  "schema": "selected-research-idea/v1",
  "core_capability_maturity": "REVIEWED_CORE",
  "source_candidate_ideas": {
    "schema": "candidate-ideas/v0.1",
    "relative_path": "outputs/candidate_ideas.json",
    "sha256": "sha256:..."
  },
  "source_literature_artifact": {
    "artifact_id": "artifact-...",
    "artifact_type": "selected-paper-library/v1",
    "sha256": "sha256:..."
  },
  "selected_idea": {}
}
```

`selected_idea` is the exact validated `candidate-ideas/v0.1` record; its
bibliographic basis is not copied into a new idea schema. Publication requires
an explicit user decision, exactly one `selected` status, unique idea IDs,
valid candidate IDs in the materialized literature, and exact source
Artifact/checksum provenance. Candidate generation alone cannot publish it or
enter completed Progress.

The existing canonical JSON serializer produces final UTF-8 bytes. SHA-256 is
calculated over those bytes, staged, flushed, fsynced, atomically published,
reread and verified. Equal bytes are idempotent; different bytes create a new
path and canonical Artifact record. Earlier Artifacts are never rewritten.

Idea Discovery 0.1.0 remains immutable and does not gain this output. Existing
instances do not upgrade automatically. A Project that needs the new boundary
retires its old instance explicitly, adds the current reviewed version, and
syncs a separate Capsule while retaining old Progress, memory and outputs.

## manuscript-draft/v1

Contract-only in F1A. Media type: `application/json`.

Required sources are one `selected-research-idea/v1` and one
`selected-paper-library/v1`. Optional exact sources are
`experiment-record/v1`, `review-report/v1`, and a prior
`manuscript-draft/v1`. The payload also contains non-empty `title` and string
`content_markdown`. Source roles cannot repeat the same Artifact identity.

A revision after review explicitly binds both the review report and the prior
manuscript. It produces a new manuscript Artifact; it never edits the reviewed
Artifact in place.

## review-report/v1

Contract-only in F1A. Media type: `application/json`.

Every report binds one specific `manuscript-draft/v1`, optional supporting
Artifacts, summary, unique major/minor issue IDs, unique requested-revision
IDs with `MAJOR`/`MINOR` priority, and one of:

- `REVISION`
- `ACCEPT_CURRENT_DRAFT`
- `INSUFFICIENT_EVIDENCE`

Scores or probabilities for novelty, impact, publication, or acceptance are
not part of the contract.

The Writing/Review loop is immutable:
`Draft A -> Review A (references Draft A) -> Draft B (references Review A and Draft A)`.

## experiment-record/v1

Contract-only in F1A. Media type: `application/json`.

Modes are `IDEA_EXPERIMENT` and `PAPER_REPRODUCTION`. The record binds exact
source Artifacts, an execution status, a structured plan, optional actual
results, and limitations.

The scaffold safety invariant is mandatory: when maturity is
`SCAFFOLD_CORE`, status must be `PLACEHOLDER_NOT_EXECUTED` and
`actual_results` must be null. A scaffold cannot publish fabricated metrics,
runtimes, p-values, or execution claims. Only a future `REVIEWED_CORE` version
may use real planned/running/completed/failed execution states.

## Future dependency map (not Registry seeds)

Future Writing requires selected research idea and literature library;
experiment record, review feedback and prior manuscript are optional. Its
output is manuscript draft.

Future Review requires manuscript draft; literature library and experiment
record are optional. Its output is review report.

Future Reproduction & Experiment requires selected research idea; literature
library is optional. Its output is experiment record.

These definitions are code-level validation contracts only. NIGHT-F1A does not
create Workflow Definitions, Capsules, Prompts, UI cards, execution cores or a
Full Research Flow preset for Writing, Review, or Experiment.

## Cloud/local and version boundaries

Cloud keeps Artifact metadata, producer Instance/Progress/Capsule provenance,
exact bindings and maturity-bearing Workflow Version metadata. Local Workspace
keeps Artifact bytes, candidate sources, memory and outputs. Cloud metadata is
not a backup of local research bytes.

Any future scaffold-to-reviewed core replacement requires a new immutable
Workflow Definition and Capsule Version. Published Capsule content and
checksum-bound contracts are never updated in place.
