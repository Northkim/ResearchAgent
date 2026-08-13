# Full Research Flow contracts

Status: complete production skeleton implemented through NIGHT-F1E

ReAgent composes five independent Workflows. Literature Search and Idea
Discovery have reviewed production research cores. Writing, Review, and
Reproduction & Experiment are real production Workflows whose published
versions remain explicitly `SCAFFOLD_CORE`. The current Skill-backed Writing
and Review versions are 0.2.0; the current Skill- and Resource-aware Experiment
Definition is 0.3.0 with interactive Capsule 0.4.0. Its immutable 0.3.0 Capsule
and the earlier published versions remain history.

```text
Literature Search
  -> selected-paper-library/v1
  -> Idea Discovery
  -> selected-research-idea/v1
       |-> Writing -> manuscript-draft/v1
       |                -> Review -> review-report/v1
       |                     -> new Writing Instance revision
       `-> Reproduction & Experiment -> experiment-record/v1
                                             `-> optional Writing input
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

Production scaffold output in F1B. Media type: `application/json`.

Required sources are one `selected-research-idea/v1` and one
`selected-paper-library/v1`. Optional exact sources are
`experiment-record/v1`, `review-report/v1`, and a prior
`manuscript-draft/v1`. The payload also contains non-empty `title` and string
`content_markdown`. Source roles cannot repeat the same Artifact identity.

A revision after review explicitly binds both the review report and the prior
manuscript. It produces a new manuscript Artifact; it never edits the reviewed
Artifact in place.

## review-report/v1

Production scaffold output in F1B. Media type: `application/json`.

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

Production scaffold output in F1B. Media type: `application/json`.

Modes are `IDEA_EXPERIMENT` and `PAPER_REPRODUCTION`. The record binds exact
source Artifacts, an execution status, a structured plan, optional actual
results, and limitations.

The scaffold safety invariant is mandatory: when maturity is
`SCAFFOLD_CORE`, status must be `PLACEHOLDER_NOT_EXECUTED` and
`actual_results` must be null. A scaffold cannot publish fabricated metrics,
runtimes, p-values, or execution claims. Only a future `REVIEWED_CORE` version
may use real planned/running/completed/failed execution states.

## Production scaffold dependency map

Writing requires selected research idea and literature library;
experiment record, review feedback and prior manuscript are optional. Its
output is manuscript draft.

Review requires manuscript draft; literature library and experiment
record are optional. Its output is review report.

Reproduction & Experiment requires selected research idea; literature
library is optional. Its output is experiment record.

Migration `20260806_0015` seeds these three stable production Definitions,
immutable Definition/Capsule 0.1.0 versions and exact requirements. The generic
Workspace sync, Installed Lock, verified materialization, local run, Progress
and Artifact promotion paths are real. Their deterministic outputs are visibly
marked placeholders. Reproduction & Experiment supports only
`IDEA_EXPERIMENT`; paper reproduction and all real execution remain disabled.
Migration `20260806_0016` adds exact built-in Skill pins through new 0.2.0
scaffold versions. Migration `20260806_0017` adds the metadata-only Resource
shell and Experiment 0.3.0 without changing the frozen Artifact contracts or
performing external resolution/execution.
Migration `20260813_0019` publishes only immutable Experiment Capsule 0.4.0
metadata. It keeps Definition 0.3.0 and every Artifact, Progress, Resource,
Skill, maturity, and execution-safety contract unchanged while adding a bounded
automatic `INPUT_REVIEW` Harness turn. Existing 0.3.0 Capsule instances remain
pinned and are never silently upgraded.

F1C adds `full-research` as a server-resolved Project creation preset. It
atomically creates five ordinary Workflow Instances and one revision-1 Desired
Manifest. The preset is not stored as a pipeline and does not enforce order.
Readiness and next action are derived from Desired state, installation
acknowledgement, immutable requirement contracts, exact bindings, compatible
Artifact metadata and Progress. Local materialization remains local truth.

Revision guidance creates a new Writing Instance so Draft A and Review A remain
immutable and Draft B binds both explicitly. Same-definition Instances remain
visible separately with friendly ordinal labels.

## Cloud/local and version boundaries

Cloud keeps Artifact metadata, producer Instance/Progress/Capsule provenance,
exact bindings and maturity-bearing Workflow Version metadata. Local Workspace
keeps Artifact bytes, candidate sources, memory and outputs. Cloud metadata is
not a backup of local research bytes.

Any scaffold-to-reviewed core replacement requires a new immutable
Workflow Definition and Capsule Version. Published Capsule content and
checksum-bound contracts are never updated in place.

F1D publishes new scaffold Definition/Capsule 0.2.0 versions without changing
0.1.0. Each 0.2.0 version pins Research Artifact Provenance 0.1.0 and Scaffold
Core Safety 0.1.0 exactly. Their reviewed declarative bytes are delivered only
inside the Capsule and do not change Artifact contracts or core maturity. See
[`SKILL_SYSTEM.md`](SKILL_SYSTEM.md).
