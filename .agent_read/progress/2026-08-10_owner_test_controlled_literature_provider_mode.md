# Owner Manual F1F Test Defect Repair — Controlled Literature Provider Mode

Date: 2026-08-10

Status: PASS — OWNER MANUAL TEST MAY RESUME

## Classification

- `OWNER_TEST_DEFECT_ID = CONTROLLED_LITERATURE_PROVIDER_MODE_MISMATCH`
- `OWNER_TEST_SEVERITY = P0_BLOCKING_E2E`
- `OWNER_TEST_DEFECT_REPAIR = PASS`
- `MIGRATION_REQUIRED = NO`

This is a narrow F1F integration repair. It adds no product phase, research
capability, Workflow semantics, Capsule version, migration, or Artifact, Skill,
Resource or Progress contract.

## Root cause and test gap

`make controlled-start` correctly configured the backend as
`isolated-controlled-test` with the deterministic fake Provider/Proxy, live
OpenAlex disabled and its key prohibited. That server-only policy was not
projected to the downloaded generic Workspace launcher. The Literature branch
always invoked its Capsule as `reagent_local.py run .`; the Capsule's existing
default is NORMAL, so its stage-3 scoped-session request selected the OpenAlex
adapter and failed against the fake-only controlled backend.

H2 validated the deployment profile and deterministic proxy separately. Its
interactive Literature E2E directly passed `--mode demo` to the Capsule. F1F
complete-width wrote deterministic Literature fixture outputs and finalized
them without the generic launcher/session path. The first owner-path regression
mocked the child subprocess and proved only path construction. None exercised
the exact generic `run .` command through server-authorized mode selection.

## Repair and security

The local-session service now owns an optional enforced search mode. In the
controlled profile it projects DEMO only after validating the exact Project,
Package ID/checksum and Workflow ID/version/checksum. The response echoes that
bounded identity and is non-cacheable. The generic Workspace client validates
the echoed identity and passes the Capsule's already-supported `--mode demo`.

Session creation re-enforces the controlled mode; a NORMAL/live attempt fails
closed even if a client spoofs a mode query parameter. Local development keeps
the existing normal/live gate and explicit demo behavior. Credentials are not
projected, persisted or inherited. Fake-provider unavailability has bounded
operator recovery guidance. This implements existing ADR 0029 and requires no
new architecture decision.

## Qualification

- real `make controlled-start` against an isolated PostgreSQL 18 database;
- real fixed local-client download and Full Research bootstrap descriptor;
- real bootstrap, five-Capsule sync and `workflow list`;
- exact Workspace-root command:

  ```bash
  python reagent_local.py run . \
    --workflow literature-search-local-experimental
  ```

- stage 3 opened a DEMO session; the existing deterministic fake Harness
  performed two query slots, finalized labelled fictional outputs, preserved
  local round memory, uploaded/verified Progress and returned
  `ROUND_COMPLETED` / `Run Completed`;
- controlled projection, absent OpenAlex key, live attempt denial, mode-spoof
  resistance, checksum tamper denial and fake-provider-unavailable tests;
- previous dot/absolute/relative/space/Unicode launcher, tamper and preflight
  regressions;
- targeted combined suites: `151 passed, 0 skipped`;
- full backend with isolated PostgreSQL: `780 passed, 14 existing skips`;
- frontend Vitest: `17 files / 34 tests passed`;
- `F1F_NEW_SKIP = 0`; `OWNER_DEFECT_NEW_SKIP = 0`;
- compileall and `git diff --check`: passed.

No live OpenAlex, GitHub, Hugging Face, credential, owner Workspace, owner
Project or owner database was used. The temporary services were stopped and
the explicitly named temporary database/Workspace/runtime were removed.

## Owner recovery

Restart the controlled backend/frontend so the server repair is active, then
download the current Local Workspace tool and replace only the existing
Workspace-root `reagent_local.py`. Rerun the same printed Literature command.
The installed Literature Capsule already supports DEMO; no Capsule sync,
re-bootstrap, Project recreation, database change or Workspace JSON edit is
required.
