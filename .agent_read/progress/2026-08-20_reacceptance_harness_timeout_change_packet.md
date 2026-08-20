# Engineering change packet — REACCEPTANCE-HARNESS-TIMEOUT-01

> Completing this packet does not authorize implementation. The Owner's
> 2026-08-20 repair instruction separately authorizes this bounded repair.

## 1. Objective

Make human Literature checkpoints durable session boundaries so Owner dwell does
not consume active Codex or OpenAlex-session lifetime.

## 2. Owner intent

Provider work and bounded Harness phases end before a researcher is asked to
decide. Exact local checkpoint state is committed first, bounded Progress is
synchronized automatically, and a later invocation resumes without repeating
completed search or reconstructing an accepted screening disposition.

## 3. User problem

The real re-acceptance Literature round completed three searches and reached a
2-selected/0-uncertain/11-excluded finalization checkpoint. A 15-minute Provider
session and 20-minute Codex deadline continued during Owner review, terminated
the subprocess, and lost the conversational disposition.

## 4. Current baseline

- Repository: `main` at `99302c14fd9be508a9a0081f65ceec115e8e5a66`, clean, one worktree.
- Alembic sole head: `20260820_0039`.
- Current forward Literature: Definition 0.6.0 / Capsule 0.8.0.
- The protected historical D1 Project is not a repair or qualification target.
- The fresh re-acceptance Workspace is recovery evidence only after disposable
  qualification passes.

## 5. Authoritative sources

The explicit Owner repair contract; ADR 0053; the accepted R2/R7 records;
published Literature 0.6/0.8 bytes; `workspace_cli.py`; the installed Literature
launcher/validator/Progress contracts; and the real Owner failure evidence.

## 6. Conflicts

Capsule 0.8 declares durable `memory/owner-decisions.json`, but its interactive
prompt defers candidate outputs until `finish`, while that decision file is bound
to the candidate-output checksum. Its package validator also accepts only the
plan as partial Capsule output. The normal Workspace coordinator can preserve the
published bytes by staging exact pre-finalization checkpoint material under
ReAgent-owned Workspace state and publishing into the Capsule only after the
corresponding Owner decision. No immutable edit is permitted.

## 7. Scope

- Route forward Literature 0.5/0.7 and 0.6/0.8 through a phased Workspace
  coordinator on the normal root `run` path.
- Run bounded managed Harness phases only for active planning/synthesis.
- Open Provider authority only around exact query execution and revoke it before
  candidate/finalization review.
- Persist exact staged candidate/output bytes, provenance checksums, pending
  checkpoint identity, and accepted screening dispositions in ReAgent-owned
  Workspace state.
- Append and automatically upload bounded nonterminal/terminal Progress.
- Preserve a bounded active-work timeout for managed Harness subprocesses.

## 8. Non-goals

No frontend redesign, Provider/API expansion, Artifact/schema change, automatic
selection, historical Capsule mutation, Owner database operation, real search in
qualification, or repair of another re-acceptance/D1 finding.

## 9. Domain semantics

Harness output is a proposal, not an Owner decision. An approved screening
snapshot is exact only when bound to the staged candidate checksum. Pending
approval is represented explicitly and never fabricated. Session is disposable;
Workspace checkpoint state is durable.

## 10. State transitions

- No plan -> managed planning -> exact plan checkpoint -> Harness exited -> Owner
  approval -> plan confirmed.
- Confirmed plan -> short Provider session -> exact result checksums -> session
  revoked -> search completed.
- Search completed -> managed synthesis -> exact staged screening checkpoint ->
  Harness exited -> Owner screening decision.
- Screening approved -> exact disposition snapshot + finalization-pending
  checkpoint -> later Owner approval -> atomic publication/finalization.
- Terminal local report -> automatic idempotent Cloud upload/receipt.
- Active Harness hang -> bounded failure with checkpoint bytes preserved.

Retries validate all exact identities, reuse completed query results, and never
infer approval from a prior chat.

## 11. Artifact impact

`selected-paper-library/v1` is unchanged. It is created only after finalization
approval from the exact staged candidate/selection bytes.

## 12. API impact

No new API. Existing Provider session and Progress upload/history routes are
reused. Nonterminal Progress carries bounded state only.

## 13. Persistence impact

No database schema change. New state is local under a ReAgent-owned `.reagent`
checkpoint root and existing append-only Progress storage.

## 14. Frontend impact

None in this bounded repair. Cloud Progress receives the existing bounded
projection.

## 15. Security impact

Provider tokens remain outside Harness environments. Staged research bytes stay
Local. Checkpoint paths are exact, bounded, non-symlink ReAgent-owned paths.

## 16. Cloud/local boundary impact

Complete candidates/reasons remain Local. Cloud receives bounded Progress and,
after final approval, existing Artifact metadata only.

## 17. Compatibility and versioning

Unchanged-compatible Workspace orchestration for published Literature 0.5/0.7
and 0.6/0.8. No historical publication bytes or identities change. Direct
Capsule launch remains an operator path; the normal Owner path is root `run`.

## 18. Migration impact

`MIGRATION_REQUIRED = NO`.

## 19. Files expected to change

- `backend/project_workspaces/workspace_cli.py`
- one or two focused Workspace/Literature test files
- this packet, one progress report, context, and one accepted ADR

Budget: <= 4 production/test files and <= 1,600 net production lines. Material
expansion requires a packet amendment and stop.

Implementation note: qualification required one additional reusable PTY fixture
file so direct historical Capsule prompts and the new root-Workspace natural
checkpoint prompts remain independently testable. The resulting five
production/test files do not expand product scope; production remains one file
and below the 1,600-line bound. The current Owner authorization explicitly
requires both public-path checkpoint and resume coverage.

## 20. Rejected alternatives

Increasing timeouts; treating chat as authority; leaving Provider sessions open;
editing Capsule 0.8; rerunning search on resume; fabricating the lost 2/0/11
decision; or storing complete research checkpoint bytes in Cloud.

## 21. Test design

Controlled fake-clock dwell beyond 15/20 minutes; exact screening resume;
pending-decision resume; Provider close-before-decision; active Harness timeout;
no repeated queries; automatic Progress upload; idempotent terminal replay; and
the four accepted D1 regression locks.

## 22. Acceptance criteria

All requested A-G cases pass with disposable Project/Workspace/Provider state;
no real Provider call occurs; the real re-acceptance Workspace then reaches its
exact screening checkpoint without repeating completed queries.

## 23. Rollback conditions

Before real recovery, revert only this unpublished coordinator change. Never
delete accepted Owner state, Progress, query results, or Artifacts.

## 24. Stop conditions

Stop on historical byte mutation, implicit selection, Cloud scientific-byte
storage, Owner database access, inability to prove staged-state ownership, or a
new HIGH/CORE lifecycle defect.

## 25. Owner decisions

The Owner explicitly selected durable checkpoint/session boundaries, Provider
release before human dwell, exact decision durability, automatic Progress, and
one permitted reconfirmation of the previously lost 2/0/11 disposition.

## Authorization gate

- Packet status: `READY_FOR_IMPLEMENTATION_REVIEW`
- Explicit implementation authorization: `AUTHORIZED_BY_CURRENT_OWNER_REQUEST`
- Remaining blocker: implementation and disposable qualification evidence.

## 26. Amendment - REACCEPTANCE-SYNTHESIS-CONTRACT-01 (2026-08-20)

Severity: `CORE HARNESS CONTRACT DEFECT` (Owner-confirmed record).

Finding: the synthesis Harness phase is required to emit exact
machine-consumed structures, but its staged execution context omitted the
authoritative output contracts (`workflow/schemas/*.schema.json` and
`validate_package.py`) and the exact proposal field contract. The model had to
infer the schema; the downstream validator correctly failed closed.

Bounded, provider-independent fix (narrow surface:
`_prepare_literature_synthesis_checkpoint`,
`_literature_synthesis_instruction`, `_literature_staged_files`, and the
coordinator-owned proposal contract):

- The staged synthesis context now carries the capsule's authoritative
  `workflow/schemas/*.schema.json` and `validate_package.py` verbatim (bytes
  copied and bound by checkpoint checksum). No shadow schema is introduced for
  contracts that already exist.
- The screening proposal has no published package schema; one coordinator
  schema (`workflow/schemas/proposed-screening.schema.json`) is generated from
  the same exact field/disposition constants the coordinator validator
  enforces, so generation and validation cannot silently drift.
- The phase instruction identifies each output and the contract governing it,
  states the exact proposal fields, and the local-context checksum rule.
- Validation remains exact and fail-closed; no validation was weakened; no
  model/provider-specific special case was added.

Qualification evidence (disposable state):

- Focused lifecycle: `8 passed` (original 6 plus contract-staging and
  extra/missing-field regression tests).
- Affected Workspace plus all four D1 locks: `41 passed`.
- Historical Literature/preset pins: `18 passed`.
- Full `backend/project_workspaces/tests`: `232 passed` plus the pre-existing
  macOS spawn-child artifact test passing standalone (the artifact is
  unrelated to this repair and documented separately).
- REAL LOOPBACK + REAL PTY + fake Harness: PASS incl. idempotent resume
  (5 Progress uploads, 1 typed Artifact, byte-stable query operations).
- REAL CODEX HARNESS (codex-cli 0.146.0, provider `deepseek`, model
  `deepseek-v4-flash`): full public path PASS. Planning and synthesis both
  conformed to the authoritative exact contracts without manual repair; the
  proposal contained exactly `{schema_version, decisions}`; checkpoint
  `FINALIZED`; 5 Progress uploads; 1 typed `selected-paper-library/v1`.
  Claim: real Codex Harness execution PASS (actual CLI lifecycle exercised).
  OpenAI-hosted model: NOT claimed.
- `compileall`, `git diff --check`, Alembic sole head `20260820_0039`: PASS.

The original REACCEPTANCE-HARNESS-TIMEOUT-01 lifecycle qualification remains
intact and is re-verified above; the working set is committed as one bounded
repair.
