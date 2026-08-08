# NIGHT-F1A-RC interruption recovery and Git closure audit

Date: 2026-08-09

Status: **PASS — OWNER REVIEW READY**

## Recovery assessment

- Starting branch: `main`.
- Starting HEAD: `2fc5a018ce190d32978817da57a85ef8820f6922`.
- Starting state: 34 F1A files changed (24 tracked modifications and 10
  untracked files), with no staged changes and no unrelated user changes.
- The baseline commit had not moved, no recovery commit or merge existed, and
  the repository had one worktree.
- The interruption caused no repository damage and left no partial product
  implementation or orphan state.
- One closure-test gap was corrected: the dedicated migration qualification now
  retains real legacy Project pins, Progress, and Artifact rows across
  `0013 -> 0014 -> 0013 -> 0014`. The initial fixture also creates its bounded
  product-state directory. This is test-only closure coverage within the
  approved F1A contract and changes no runtime semantics.

## Diff inventory

The initial 34 files classified as follows:

- Artifact contracts: 2.
- Idea Discovery 0.2.0: 2.
- Core Capability Maturity: 3.
- Database migration 0014: 1.
- API/readiness/serialization: 2.
- Workspace sync/run compatibility: 4.
- Frontend type compatibility: 1.
- Tests: 13.
- Documentation/ADR/progress/context: 6.
- Other: 0.

This closure report is the only additional file created by the recovery audit.

## Warning resolution

- Dirty, uncommitted F1A diff: expected closure warning; resolved by the
  semantic closure commits.
- Owner review pending: acceptance state, not an implementation warning.
- Eleven full-suite skips: non-blocking explicit gates. Seven are dedicated
  migration databases, three are pre-existing isolated-environment gates, and
  one is the opt-in live OpenAlex gate. The F1A migration gate passed in its
  dedicated database. `F1A_NEW_SKIP = 0`.
- Initial browser run lacked the repository's local-mode variable and returned
  expected 404s on local-session routes; the authoritative rerun used the
  standard fake-Provider/local-mode configuration and passed 5/5.
- Writing, Review, and Experiment remain unavailable by design and are the F1B
  boundary, not implementation warnings.

`WARNINGS_BLOCKING = false`.

## Scope and authority audit

- Production Registry remains exactly Literature Search and Idea Discovery.
- Writing, Review, and Experiment production seed counts are each zero.
- Future manuscript, review, and experiment contracts exist only as validators,
  documentation, and tests; no producer Workflow exists.
- `WorkflowDefinitionVersion.core_capability_maturity` is canonical. API, UI,
  and compatibility metadata are projections; lifecycle is separate.
- Artifact validators derive maturity from the producer version and reject a
  client claim of `REVIEWED_CORE` for a scaffold producer.
- The experiment validator enforces `PLACEHOLDER_NOT_EXECUTED` and null actual
  results for scaffold maturity.

## Immutable versions

Baseline and current packages were regenerated with the repository compiler and
were byte-identical:

- Literature Definition 0.3.0:
  `sha256:efd338d84b33665da25118c7dce6927f62b231ff3bc73527f4132c7bcb410e7f`.
- Literature Capsule 0.5.0:
  `sha256:0f827b56ed6c5ecf6634f5eee0171ead2b050910ed1c9223ad64c9d135267611`.
- Literature Definition 0.4.0:
  `sha256:864102b119364626b82a1644b3cfd7699746633950097ad0d5cd7bb5facf5c2c`.
- Literature Capsule 0.6.0:
  `sha256:e9e6a2e0aa46146818fb6123e03877f32abaa8745f9c0b3139572530ccd1b80d`.
- Idea Definition 0.1.0:
  `sha256:b9468ed938f4dce3fb856a06fe7c1c054456f361a0c3fb3b393234f9ac448491`.
- Idea Capsule 0.1.0:
  `sha256:f07330db6f0d87f3fd482b698223ea75414ce087fac193de80f8e8522e9e6452`.

Idea Definition/Capsule 0.2.0 are additive new immutable versions with checksums
`sha256:6ddc73c6bbe61a425a338f0b6d1c7c1cf50608ce87b5333a83c101a93cb519d5`
and
`sha256:6b66289a38895ce0eba2f76cd77251766711a6ec8ebf416cdd368695b5c727f5`.

## Migration audit

- Sole head/current: `20260806_0014`.
- `down_revision`: `20260806_0013`.
- No duplicate, temporary, orphan, or second 0014 revision exists.
- No historical migration changed; the baseline and current 0013 SHA-256 is
  `bacab22328da06575b460e1420e1606b4f7eaa736a910a9bc60883698deef4a6`.
- Upgrade seeds are deterministic; old pins and versions remain; downgrade and
  re-upgrade pass with real Project, Progress, and Artifact state retained.

## Contract audit

`selected-research-idea/v1` requires explicit exactly-one selection, validated
`candidate-ideas/v0.1`, exact literature source bytes/checksum and valid
literature-basis identifiers. Canonical JSON is written content-addressed and
atomically, promoted through B6 provenance, idempotent on exact retry, and
conflicting on mutation. Idea completion cannot become `COMPLETED` before the
Artifact is successfully finalized. Old Artifact bytes remain immutable.

The manuscript, review, and experiment contracts are runtime validators without
producers. The experiment scaffold safety rule is enforced in code, not only
documented.

## Qualification

- Focused F1A/B6/B7/H2: 57 passed.
- Dedicated migration: 1 passed.
- Relevant PostgreSQL: 19 passed.
- Full backend: 725 passed, 11 skipped.
- Frontend Vitest: 16 files, 31 passed.
- Playwright: 5 passed.
- TypeScript: passed.
- ESLint: passed.
- Production build: passed.
- Python compileall: passed.
- Alembic heads/current/check: passed, sole 0014 head, no drift.
- `git diff --check`: passed.

All databases and filesystem roots were fresh and isolated. No `.env`, owner
database, owner Workspace, real credential, live Provider, or network research
call was used.

## Closure

`NIGHT_F1A_RC = PASS`

`NIGHT_F1A_IMPLEMENTATION = PASS`

`OWNER_REVIEW_READY = true`

The next separately authorized phase is NIGHT-F1B. It may introduce production
Writing, Review, and Reproduction/Experiment scaffold Workflows, immutable
scaffold Capsules, dependencies, outputs, Progress, and placeholder research
cores. None is implemented or production-seeded in F1A.
