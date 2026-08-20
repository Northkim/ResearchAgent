# REACCEPTANCE-SYNTHESIS-CONTRACT-01 bounded repair (2026-08-20)

Status: **PASS; combined repair committed**

`VERIFIER_INDEPENDENCE = LIMITED`: the implementing session also ran the
qualification.

## Root cause

The Literature synthesis Harness phase produced exact machine-consumed
structures, but the staged execution context did not include the authoritative
output contracts. The capsule's `workflow/schemas/*.schema.json` and
`validate_package.py` were not staged, and the screening proposal contract
(exactly `{schema_version, decisions}`) was not stated anywhere in the
generation context. A real model had to infer the schemas and produced
additional/incompatible fields; the coordinator validator failed closed
correctly.

## Fix (provider-independent)

1. `_prepare_literature_synthesis_checkpoint` stages the capsule's
   authoritative schema files and `validate_package.py` verbatim, and writes
   one coordinator proposal schema derived from the same exact field and
   disposition constants the validator enforces.
2. `_literature_synthesis_instruction` names the governing contract for every
   output, states the exact proposal fields, and the local-context checksum
   rule; it forbids executing the validator (read-only authority).
3. `_literature_staged_files` binds all staged contracts by checksum so resume
   re-verifies the exact generation context.
4. No validation was weakened; no model/provider special case was added; no
   shadow schema was introduced for existing package contracts.

## Qualification evidence

- Focused lifecycle: `8 passed` (contract staging, drift guard, conforming
  accept, extra-field fail, missing-field fail, pending truth, query reuse,
  timeout fail-safe).
- Affected Workspace + all four D1 locks: `41 passed`.
- Historical Literature/preset pins: `18 passed`.
- Full `backend/project_workspaces/tests`: `232 passed` plus the pre-existing
  spawn-child artifact test passing standalone (macOS Python 3.11 `spawn`
  import-path artifact triggered by two unmodified test files; not a product
  regression and not related to this repair).
- REAL LOOPBACK + REAL PTY + fake Harness: PASS, including idempotent resume
  (5 Progress uploads, 1 typed Artifact, byte-stable query operations).
- REAL CODEX HARNESS: codex-cli 0.146.0, provider `deepseek`, model
  `deepseek-v4-flash`. Full public path PASS: planning and synthesis both
  conformed to the authoritative exact contracts without manual file repair,
  schema surgery, or operator editing; proposal keys exactly
  `{schema_version, decisions}`; checkpoint `FINALIZED`; 5 Progress uploads;
  1 typed `selected-paper-library/v1`.
- `compileall`, `git diff --check`, Alembic sole head `20260820_0039`: PASS.

## Claims

- Real Codex Harness execution: PASS (actual Codex CLI and tool/process
  lifecycle exercised end-to-end).
- OpenAI-hosted Codex model: NOT claimed (active provider is DeepSeek with
  model deepseek-v4-flash).
- Provider independence: the controlled fake-Harness path and the real-Codex
  path both pass; the fix is provider-independent contract staging, not a
  provider-specific workaround.

## Safety

No completed query was repeated; no Owner decision was fabricated; no
checkpoint/search state was lost; no protected historical D1 Project or Owner
database was accessed; no migration or historical byte changed; validation
remained exact and fail-closed throughout.
