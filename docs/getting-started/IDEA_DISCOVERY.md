# Idea Discovery and production Artifact handoff

NIGHT-B7 validates the first real multi-Workflow path. ReAgent Cloud manages
Workflow configuration, Progress and checksum-bound provenance. The local
Workspace remains authoritative for literature bytes, materialized inputs,
outputs and memory. Cloud does not store Artifact bytes and an Artifact
Reference is not a backup.

## Production contracts

New Projects use Literature Search definition `0.4.0` and Capsule `0.6.0`.
Only an explicit successful `finish`, after the existing
`candidate-papers/v0.2` and `selected-papers/v0.2` checks pass, publishes:

```text
selected-paper-library/v1
outputs/artifacts/selected-paper-library/sha256-<digest>.json
```

The JSON keeps each exact validated candidate record beside its exact selection
record, in selected-paper order. It stores both source checksums. The final
canonical UTF-8 bytes determine the SHA-256 path and immutable Artifact record.
Intermediate candidate lists do not create this Artifact. Changed final bytes
create another path and Artifact; an older reference never changes checksum.

Literature Search 0.3.0 / Capsule 0.5.0 remains supported and unchanged. Its
outputs are not silently promoted. To produce the typed Artifact in an older
Project, explicitly retire the old instance, add Literature Search again, sync,
and run the new immutable Capsule. Existing history and retained local files
remain intact.

Idea Discovery definition and Capsule `0.1.0` require exactly one specific
`selected-paper-library/v1` in input slot `paper_library`. Selection is explicit;
the service never picks the first or latest compatible Artifact. Its local
target is `inputs/selected-paper-library.json`, copied and checksum verified.

## End-to-end owner flow

1. Run Literature Search 0.4.0 and explicitly finish the reviewed round.
2. Upload its Progress declaration; Cloud creates the canonical Artifact
   metadata and producer/Progress provenance.
3. Refresh the local byte index:

   ```bash
   python reagent_local.py artifact refresh .
   ```

4. On **Workflows**, add Idea Discovery. This changes Cloud Desired Manifest;
   it does not install anything locally.
5. Install only the missing Capsule:

   ```bash
   python reagent_local.py sync .
   ```

6. On the Idea Discovery card, choose one compatible Artifact. Multiple
   Literature instances remain separate choices; the binding records exact
   `artifact_id` and checksum.
7. Preview and then perform explicit materialization:

   ```bash
   python reagent_local.py artifact materialize . \
     --workflow idea-discovery-local-experimental --dry-run
   python reagent_local.py artifact materialize . \
     --workflow idea-discovery-local-experimental
   ```

8. Preflight and run the exact local Capsule:

   ```bash
   python reagent_local.py run . \
     --workflow idea-discovery-local-experimental --preflight-only
   python reagent_local.py run . \
     --workflow idea-discovery-local-experimental
   ```

The stable key is a convenience, not a relaxed identity check: it resolves
only when exactly one active local Idea Discovery instance exists. With
multiple same-type instances, `python reagent_local.py workflow list .` prints
the exact `--workflow-instance` commands and ambiguous selection fails closed.

The browser never performs sync, materialization or Codex execution.

## Local safety and reproducibility

`.reagent/artifact-index.json` describes locally re-read producer bytes; it is
separate from `.reagent/installed-lock.json`. Materialization re-reads the
producer, compares the Cloud reference and Index checksums, copies through
same-filesystem staging, fsyncs, verifies, atomically publishes without
overwrite, and writes a checksummed receipt. It uses neither symlink nor
hardlink and never modifies the Literature Search output.

An exact repeat is idempotent. Different existing target bytes produce
`MATERIALIZATION_CONFLICT`; changed source bytes produce
`LOCAL_ARTIFACT_DRIFT`; changed materialized bytes produce
`MATERIALIZED_ARTIFACT_DRIFT`. There is no force mode. Retiring a producer
preserves history and local bytes; retained bytes remain usable only while all
identity and checksum checks pass.

## Idea Discovery local contract

The Capsule starts at `AGENT.md`, reads only the materialized input, and treats
`inputs/` as read-only. It must not read a sibling Literature Search output.
Evidence-supported observations, gaps/tensions and candidate directions are
discussed with the user rather than generated as an autonomous final truth.
The prompt distinguishes evidence, inference and candidate direction and never
claims global novelty.

Normal outputs are:

- `outputs/candidate_ideas.json` using `candidate-ideas/v0.1` and stable
  literature `candidate_id` references;
- `outputs/idea_discovery_report.md` for landscape, patterns, gaps, choices,
  uncertainty and next validation.

These outputs are not a production Writing handoff Artifact. Idea Discovery
Progress uses the existing Workflow-Instance Progress service and the stages
`INPUT_REVIEW`, `LANDSCAPE_ANALYSIS`, `GAP_EXPLORATION`, `CANDIDATE_IDEAS`,
`USER_REVIEW`, `REFINEMENT`, and `COMPLETED`.

Each session updates its own `memory/` and Progress before exit. A later Codex
session reads those files and existing outputs; continuity does not depend on
chat history or Cloud holding the complete Workspace.

## Current limits

Writing, Review, Experiment, automatic novelty web search, automatic Artifact
selection/materialization, cross-Project sharing, Cloud Artifact-byte storage,
Workspace backup, background sync and browser-local execution are not
implemented.
