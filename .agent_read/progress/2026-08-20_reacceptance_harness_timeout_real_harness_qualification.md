# REACCEPTANCE-HARNESS-TIMEOUT-01 real-Harness qualification (2026-08-20)

Status: **FINDING RESOLVED** - the gap was fixed and re-qualified by
`REACCEPTANCE-SYNTHESIS-CONTRACT-01` (see
`2026-08-20_reacceptance_synthesis_contract_repair.md`); the combined repair
is committed.

`VERIFIER_INDEPENDENCE = LIMITED`: the implementing session ran the
qualification.

## What changed since the prior BLOCKED record

The environment no longer rejects loopback elevation, so the previously
blocked real-loopback gate ran and passed. A real Codex Harness run was then
attempted and produced a new, precise finding that blocks the real Owner
recovery path.

## Executed evidence (all disposable state)

- Focused Literature checkpoint lifecycle: `6 passed` (E1-E5).
- Affected Workspace plus all four D1 regression locks: `33 passed`.
- Full `backend/project_workspaces/tests`: `231 passed` when the
  multiprocessing lock test runs first. Normal collection order fails only that
  one pre-existing lock test in the spawned child (`ModuleNotFoundError:
  backend.api`); it passes standalone and in every repair-relevant combination.
  The trigger is the pre-existing combination of
  `test_forward_downstream_public_workspace.py` +
  `test_forward_review_optional_evidence_recovery.py` + `test_sync.py` under
  macOS Python 3.11 `spawn`; none of those files are modified by this repair.
- Historical Literature/preset pins: `18 passed` (literature outputs,
  consolidation, production workflows, R4 semantics, paper-library content).
- `compileall`, `git diff --check`, Alembic sole head `20260820_0039`: PASS.
- REAL LOOPBACK + REAL PTY + fake Harness: the full public root Workspace
  command ran against a real uvicorn loopback API under a real controlling PTY
  (plan approve, bounded DEMO search, screening approve, finalization approve,
  terminal sync; then an idempotent resume run). Verified: 5 Progress uploads,
  1 typed `selected-paper-library/v1` Artifact, checkpoint phase `FINALIZED`,
  query operations byte-stable across resume, no repeated uploads/Artifact.
  This is the gate that previously required unavailable loopback elevation.
- REAL CODEX CLI (installed `codex-cli 0.146.0`, provider `deepseek`,
  model `deepseek-v4-flash`):
  - Planning phase through the real CLI: PASS. The model read the pinned
    AGENT.md/Skill/schemas inside the capsule and wrote a valid
    `outputs/search_plan.md` and `memory/search/query_plan.json`.
  - Synthesis phase through the real CLI: executed bounded, then FAILED CLOSED
    at `_validate_literature_outputs` (`LOCAL_PROGRESS_INVALID`); staged temp
    was cleaned, capsule remained `SEARCH_COMPLETED`, all query results
    preserved. No fabricated decision, no checkpoint loss.

## New finding: staged synthesis context under-specifies the exact contracts

The root coordinator's synthesis phase stages only inputs/search files, the
search plan, context/draft, and a short AGENTS.md. The authoritative
`workflow/schemas/*.schema.json` and `validate_package.py` are not staged, and
the instruction names schema versions without their exact field layout.

- Without schemas, the real model wrote a richer, non-conforming
  `candidate_papers.json` (extra top-level fields, object-valued authors,
  non-hex candidate IDs) and was rejected.
- Diagnostic (disposable, no repository change) staging the schema files:
  the same model then wrote conforming `candidate_papers.json`,
  `selected_papers.json`, and report; `_validate_literature_outputs` PASS.
- In that diagnostic the model's `memory/proposed-screening.json` still
  carried extra fields (`mode`, `generated_at`, `candidate_set_checksum`);
  `_literature_proposed_decisions` requires exactly
  `{schema_version, decisions}` and rejected it (`Literature screening
  proposal fields are invalid`). There is no staged schema file for the
  proposal contract and the instruction does not state the exact two-field
  layout.

The fail-closed lifecycle behaved correctly on every attempt. The blocker is
that the real Owner recovery cannot produce a conforming synthesis checkpoint
through the repaired path with the available model until the synthesis phase
provides the exact schema contracts (and the exact proposal field contract) to
the Harness. This is a bounded implementation-completion item inside the
authorized phase, but it is a material change to the qualified implementation,
so it needs a packet amendment and re-qualification rather than a silent fix.

## Safety audit

No completed query was repeated; no Owner approval was fabricated; no
checkpoint or search state was lost; no protected historical D1 Project or
Owner database was accessed; no migration or historical byte changed; the real
re-acceptance Workspace was not touched.

## Resolution

Implemented as the bounded `REACCEPTANCE-SYNTHESIS-CONTRACT-01` repair: the
staged synthesis context now carries the authoritative package schema files and
validator verbatim plus a coordinator proposal schema derived from the same
exact field constants the validator enforces; the instruction names the
governing contract for every output. Real-Codex synthesis then conformed
without manual repair. Full re-qualification passed (controlled suite, D1
locks, historical pins, full project_workspaces suite, real loopback + PTY +
fake Harness, and real Codex Harness end-to-end). See the synthesis contract
repair progress record.
