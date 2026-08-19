# Post-D1 R1B2 forward Idea content precondition

Status: **PASS — R1B2 COMPLETE; R1C NEXT**

Date: 2026-08-20

Authority: R1 of
`.agent_read/progress/2026-08-20_post_d1_repair_program.md`, the narrowed R1
change packet, and ADR 0051.

## Scope and ledger disposition

R1B2 closes `D1-UPSTREAM-ZERO-PAPER-01` while preserving the real D1
occurrence. It does not repair R1C platform/package classification or begin R2.

The work was deliberately split at the phase budget boundary:

- R1B2a backend/publication/Local semantics: commit `4b19881`;
- R1B2b server-qualified frontend candidates: commit `5dec904`.

No historical migration, Definition, Capsule, Artifact schema, scientific
Artifact, protected D1 row, binding, Progress report, or Owner Workspace was
modified.

## Root correction

The producer and consumer semantics are now separate and explicit:

- a zero-paper `selected-paper-library/v1` remains a valid exact Literature
  Artifact;
- forward Idea requires an immutable bounded Local-derived qualification with
  `selected_count >= 1` for the same Artifact ID/checksum;
- candidate listing, exact bind, Progress readiness, and materialization all
  call the same compatibility evaluator;
- the browser requests compatible candidates from that exact consumer
  requirement rather than filtering by type alone.

The qualification reports no paper content. It is not presentation and cannot
satisfy a scientific binding. Missing or mismatched qualification fails closed.

## Forward publication and migration

Migration `20260820_0036` publishes:

- Idea Discovery Definition `0.3.0`, contract checksum
  `sha256:5385cfa76e7323664f1e321ad781f583edcd6f0fcbf32f36ffdbbefc4ef5e682`;
- Idea Discovery Capsule `0.4.0`, ID
  `capsule-717aa7729919ccef977520a3622fb44f`, checksum
  `sha256:717aa7729919ccef977520a3622fb44f883d827b2ba0127458fdf49417a48d0a`;
- one exact `paper_library` content precondition;
- bounded qualification persistence on Artifact references.

Historical Idea 0.2 / Capsule 0.3 is byte-identical and retains historical
compatibility. Fresh Full Research explicitly pins 0.3/0.4; no latest/highest
selection was added.

Marked disposable PostgreSQL passed empty database upgrade through 0036,
source/publication equivalence, Foundation idempotency, Alembic model drift
check, 0036→0035 downgrade, 0035→0036 re-upgrade, SQL qualification
round-trip/candidate enforcement, and identity-verified cleanup. The Owner
database remains at 0034.

## Qualification evidence

| Evidence | Result |
|---|---|
| R1B2 Artifact qualification, Local reporting, Idea package/preset/Progress focused suite | **72 passed** |
| Four accepted D1 repair locks | **87 passed** |
| Marked disposable PostgreSQL migration + SQL round-trip | **2 passed** |
| Frontend full suite | **20 files / 72 tests passed** |
| TypeScript | **PASS** |
| ESLint | **PASS** |
| Production Next.js build | **PASS** |
| Python compileall | **PASS** |
| `git diff --check` | **PASS** |
| Alembic sole head | **`20260820_0036`** |

R1B2 browser behavior is covered at component/client level; the consolidated
real-service R1/R7 browser matrix remains mandatory and is not claimed here.
No real provider or scientific research was run.

## Historical and safety result

- zero-paper Literature validity is preserved;
- historical Idea 0.2/Capsule 0.3 is unchanged;
- exact Artifact identity/checksum remains authoritative;
- presentation remains optional UI metadata;
- qualification cannot replace a binding or Artifact bytes;
- no auto-latest, implicit merge, or global comparator weakening was added;
- all four D1 repaired-contract locks pass;
- User Skills gained no Capability or evidence authority;
- protected D1 state and Owner database were untouched.

## New-defect prevention gate

All ten program questions are **NO**. The phase introduced no weakened exact
boundary, implicit latest/merge, Cloud authority over full Local bytes, Skill
authority, scientific rerun for sync, manual Owner orchestration step,
in-place publication edit, D1 lock change, fixture weakening, or additional
primary UI prose.

Safe next action: start R1C only, auditing `.DS_Store` and private-path/secret
classification without weakening arbitrary-file or real-secret rejection.
