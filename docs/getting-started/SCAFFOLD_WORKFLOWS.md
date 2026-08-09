# Scaffold Workflows

Writing, Review, and Reproduction & Experiment are production product flows
with placeholder research cores. Their Registry cards and Progress state show
`SCAFFOLD_CORE`: product flow is functional, but research capability is not.

## What is real

Each Workflow has an immutable Definition and Capsule version 0.1.0, a Desired
Manifest entry, independent sync/install state, exact Artifact requirements,
verified local materialization, a generic local Harness run, memory, Progress,
and a content-addressed output Artifact. Cloud stores metadata and provenance;
the Workspace retains Artifact bytes.

Add each Workflow from the Registry, then run `python reagent_local.py sync
<workspace>`. Bind every required input to one specific same-Project Artifact
ID and checksum, materialize it, and run `python reagent_local.py run
<workspace> --workflow <stable-key>`. There is no automatic latest selection.

## Writing scaffold

Writing requires one selected research idea and one selected paper library.
Experiment, review and prior-manuscript inputs are optional. It publishes
`outputs/manuscript.md` and `manuscript-draft/v1`, both prominently marked
`SCAFFOLD PLACEHOLDER`. It does not invent citations, results, novelty or a
publication-quality manuscript.

For a review loop, create Writing Instance A and Review Instance A. Create a
new Writing Instance B and explicitly bind Draft A and Review A as
`prior_manuscript` and `review_feedback`. Draft A and Review A remain immutable.

## Review scaffold

Review requires one exact manuscript Artifact. It publishes
`review-report/v1` with `INSUFFICIENT_EVIDENCE`, no claimed major/minor issues,
and a visible `SCAFFOLD REVIEW PLACEHOLDER`. It does not score novelty, predict
acceptance or perform substantive peer review.

## Reproduction & Experiment scaffold

The current supported mode is only `IDEA_EXPERIMENT`, an experiment-plan
skeleton based on a selected research idea. Paper reproduction is not enabled.
The Artifact is forced to `PLACEHOLDER_NOT_EXECUTED` with `actual_results =
null`; no code, dataset, model, metric or benchmark is executed or fabricated.

## Replacement policy

Published 0.1.0 scaffold Capsules never become reviewed cores in place. A
future substantive implementation requires a new immutable Definition and
Capsule version, new checksums, and an explicit Project adoption decision.
