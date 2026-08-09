# Full Research Project

Full Research Project is a setup preset, not an execution pipeline. Project
creation resolves the current production Registry versions on the server and
atomically creates Literature Search, Idea Discovery, Writing, Review, and
Reproduction & Experiment as independent desired Workflow Instances.

Literature Search and Idea Discovery use reviewed cores. Writing, Review, and
Reproduction & Experiment use scaffold cores: their Registry, Capsule, sync,
exact inputs, local run, immutable outputs, Progress, and continuity are real,
but their research content is an unmistakable placeholder. No substantive
manuscript, peer review, reproduction, or experiment is produced.

## Readiness and next actions

The Workflow Board derives guidance from the current Desired Manifest,
installation acknowledgement, frozen Artifact requirements, exact bindings,
compatible Artifact metadata, and Progress. Research status remains separate
from readiness. A scaffold Workflow can be ready to run while its research
maturity is still Scaffold Core.

The normal guidance is sync, wait for an upstream result, select one exact
Artifact, materialize it locally, run or continue, and review the immutable
result. The web service cannot inspect local bytes, so it conservatively asks
for materialization after binding; the Workspace CLI is local truth.

## Recommended, never enforced

The recommended path is Literature Search, Idea Discovery, Writing and/or the
optional Idea Experiment skeleton, then Review. A Review result suggests a new
Writing round. The user creates Writing #2 and explicitly selects the prior
manuscript and review report; Draft A and Review A are never overwritten.

Multiple compatible Artifacts are always shown as choices with their source
Workflow Instance and time. ReAgent does not select `latest`, automatically
bind optional Experiment output, write local files from the browser, or start a
Workflow automatically.

Bootstrap and sync remain explicit:

```bash
python reagent_local.py bootstrap ./reagent-workspace --descriptor ./workspace-bootstrap.json
cd ./reagent-workspace
python reagent_local.py sync .
python reagent_local.py workflow list .
```

The CLI prints friendly ordinal labels for multiple same-type Instances and
falls back to exact instance selectors when the stable selector is ambiguous.
No Manifest, UUID, checksum, or receipt JSON editing is required for normal use.
