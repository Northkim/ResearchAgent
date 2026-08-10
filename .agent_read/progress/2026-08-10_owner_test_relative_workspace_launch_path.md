# Owner Manual F1F Test Defect Repair — Relative Workspace Launcher Path

Date: 2026-08-10

Status: PASS — OWNER MANUAL TEST MAY RESUME

## Classification

- `OWNER_TEST_DEFECT_ID = LOCAL_RELATIVE_WORKSPACE_LAUNCH_PATH`
- `OWNER_TEST_SEVERITY = P0_BLOCKING_E2E`
- `OWNER_TEST_DEFECT_REPAIR = PASS`
- `MIGRATION_REQUIRED = NO`

This is a narrow F1F integration repair. It adds no phase, feature, Workflow
semantics, persistence, Artifact, Skill, Resource or Progress contract.

## Root cause and reproduction

On clean `main` at `3d47faf57269be84e3305a93029cbea40f910d40`,
`load_workspace(".")` correctly retained a relative Workspace path. The
generic runner then formed both a relative Capsule cwd and a relative
Capsule-prefixed launcher argv:

```text
cwd  = capsules/<workflow>/<instance>/0.6.0
argv = python capsules/<workflow>/<instance>/0.6.0/reagent_local.py run .
```

The child process interpreted argv relative to cwd, duplicating the Capsule
path and returning `WORKFLOW_RUN_FAILED` before the Capsule launcher or Codex
could start. Pre-fix isolated reproduction produced the exact duplicated path
reported by the owner. Existing F1F calls supplied absolute `tmp_path`
Workspace roots or invoked finalizers/preflight directly, so their launcher
argv was absolute and the product-shaped dot path was not covered.

## Repair

The existing verified Capsule remains subprocess cwd. After all existing Lock,
checksum, containment, symlink and immutable-Capsule checks, the child argv now
uses only the Capsule-local `reagent_local.py` basename. This creates one rule:
the launcher path is interpreted exactly once from its Capsule cwd. No broad
`resolve()` call or path-validation relaxation was added.

`WORKFLOW_RUN_FAILED` guidance now distinguishes a launcher/path failure from
a Harness that started and wrote local state. A path/file start failure tells
the user to stop repeated retries and report the stable code; local-memory
continuation advice is retained only for a Harness that actually started.

## Qualification

- exact pre-fix temporary reproduction: duplicated Capsule path and
  `WORKFLOW_RUN_FAILED`;
- exact post-fix temporary `workspace="."` subprocess: Capsule launcher reached
  `[2/6] Checking local ReAgent backend` against an intentionally unavailable
  loopback endpoint, proving it passed launcher path resolution without
  ENOENT;
- owner-shaped copied generic launcher test: bootstrap, five-Capsule sync,
  workflow list and `run . --workflow literature-search-local-experimental`;
- path/launcher regression: dot, absolute, named relative, spaces, Unicode,
  Literature, Idea, Writing, Review, Experiment, preflight-only and tamper
  fail-closed;
- `backend/project_workspaces/tests/test_sync.py`: 24 passed;
- all Workflow Package/fake Harness tests: 103 passed;
- all Project Workspace/Artifact/Skill/Resource/security path tests: 83 passed;
- isolated PostgreSQL F1F complete-width reload: 1 passed;
- full backend with isolated PostgreSQL: 777 passed, 14 existing skips;
- compileall and `git diff --check`: passed.

The explicitly named temporary PostgreSQL database was migrated to the existing
head `20260806_0017`, used only for qualification, and deleted afterward. No
live OpenAlex, GitHub, Hugging Face, credential, owner Workspace, owner Project
or owner database was used.

## Owner recovery

Deliver the repaired generic client, then rerun the unchanged product command
from the Workspace root:

```bash
python reagent_local.py run . \
  --workflow literature-search-local-experimental
```

No absolute path, Capsule `cd`, JSON edit, direct Capsule invocation or database
change is required.
