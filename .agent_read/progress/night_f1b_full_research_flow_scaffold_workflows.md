# NIGHT-F1B Full Research Flow scaffold Workflows

Date: 2026-08-09

Status: PASS — OWNER REVIEW READY

## Baseline and boundary

- branch: `main`
- starting HEAD: `349538631bed4767880b8024afcc32e3aae7fa06`
- F1A final commit: verified ancestor
- initial worktree: clean
- extra worktrees: none
- migration baseline: sole `20260806_0014`
- live Provider, `.env`, credentials, owner database and owner Workspace: not used
- no branch, worktree, push, Full Flow preset, Skill/Resource platform or real experiment execution

## Production Registry

Reviewed cores remain Literature Search Definition 0.4.0/Capsule 0.6.0 and
Idea Discovery Definition/Capsule 0.2.0. F1B adds exactly:

- `writing-local-experimental`: Writing 0.1.0/Capsule 0.1.0
- `review-local-experimental`: Review 0.1.0/Capsule 0.1.0
- `reproduction-experiment-local-experimental`: Reproduction & Experiment 0.1.0/Capsule 0.1.0

All three are `AVAILABLE`, creatable, multiple-instance capable,
`TRUSTED_BUILT_IN_UNSIGNED`, and `SCAFFOLD_CORE`.

## Implementation

- deterministic data migration `20260806_0015`, down-revision 0014
- immutable Registry Definition/Capsule seeds and exact requirements
- canonical Capsule compiler, AGENT/prompt, memory, inputs, outputs and Progress helper
- generic Workspace CLI preflight/run through the existing local Harness
- exact Artifact ID/checksum binding and B6 verified-copy materialization
- shared safe finalization: validator, canonical JSON, checksum, atomic content-addressed write, Progress declaration and Artifact promotion
- producer-Workflow-Version maturity projection for Artifact, Progress API and frontend
- fixed visible scaffold manuscript/review/experiment output markers
- Review `INSUFFICIENT_EVIDENCE`; Experiment `IDEA_EXPERIMENT`, `PLACEHOLDER_NOT_EXECUTED`, null results
- new Writing Instance B for revision provenance; no mutable rebinding schema
- Registry-driven frontend badges and scaffold warning; no preset
- ADR 0031, architecture contract and scaffold getting-started documentation

## Qualification

- focused F1A/F1B/B6/H2: `36 passed`
- F1B migration and SQL-backed full chain: `1 passed`
- full backend with isolated PostgreSQL 18: `734 passed, 11 skipped`
- migration: empty -> 0014 -> 0015 -> 0014 -> 0015 deterministic PASS
- PostgreSQL stop/start, 0015 current and Alembic check: PASS
- Alembic sole head: `20260806_0015`
- frontend Vitest: `16 files, 32 tests passed`
- TypeScript: PASS
- ESLint: PASS
- production build: PASS
- Playwright with deterministic fake Provider: `5 passed`
- Python compileall: PASS
- git diff check: PASS
- scale: 20 Workflow Instances / 1,000 reports aggregation PASS

The SQL-backed synthetic qualification covers Idea -> Writing -> Draft A,
Idea -> Experiment placeholder, Draft A -> Review A, Draft A + Review A ->
new Writing Instance B -> Draft B, two explicit manuscript candidates,
producer retirement with retained Artifact, file-only fresh-session recovery,
and mixed reviewed/scaffold Progress projection.

## Skip audit

Dedicated historical migration gates (7): NIGHT-B1, B2, B4, B5, B6, B7 and
F1A databases were intentionally not supplied. Pre-existing isolated
integration gates (3): destructive HTTP/PostgreSQL demo, 9B-1 contract, and
9A-2 research-v2. Expected live-provider gate (1): 9B-1 live OpenAlex.
The dedicated F1B migration gate was supplied and passed.

`F1B_NEW_SKIP = 0`.

## Recovery corrections

The interruption caused no repository damage or partial product state. The
recovery closure retained the prior correction for maturity projection N+1 by
bulk-loading producer Workflow Instance/Definition Version maturity. It also
made the full-chain qualification reusable for both in-memory and SQL UoWs,
with explicit synthetic upstream Progress parents required by PostgreSQL
foreign keys. These are within F1B maturity/API and qualification scope and do
not change F1A Artifact schemas.

## Immutable evidence

- Literature Definition 0.3.0 / Capsule 0.5.0:
  `sha256:0f827b56ed6c5ecf6634f5eee0171ead2b050910ed1c9223ad64c9d135267611`
- Literature Definition 0.4.0 / Capsule 0.6.0:
  `sha256:e9e6a2e0aa46146818fb6123e03877f32abaa8745f9c0b3139572530ccd1b80d`
- Idea Definition/Capsule 0.1.0:
  `sha256:f07330db6f0d87f3fd482b698223ea75414ce087fac193de80f8e8522e9e6452`
- Idea Definition/Capsule 0.2.0:
  `sha256:6b66289a38895ce0eba2f76cd77251766711a6ec8ebf416cdd368695b5c727f5`

Only migration 0015 is new; no historical migration changed. Deterministic
re-upgrade retained all F1A identities and checksums.

## Deferred

- F1C: Full Research Flow preset, complete setup/readiness and cross-Workflow next-action UX
- F1D: Skill shell
- F1E: Resource shell
- F1F: complete five-Workflow product E2E
