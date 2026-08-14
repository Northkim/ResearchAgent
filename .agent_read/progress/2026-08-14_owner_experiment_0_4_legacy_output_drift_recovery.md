# Owner Experiment 0.4 legacy human-output drift recovery

Date: 2026-08-14

The Workspace root client now recognizes only the exact combined historical
Experiment Definition 0.3.0 / Capsule 0.4.0 failure fingerprint. The immutable
Progress Report may bind owner-reviewed plan A while current disk contains
plan B only when every other invariant passes and plan B is byte-for-byte the
output of that verified historical Capsule's own deterministic renderer. The
typed `experiment-record/v1`, input/materialization provenance, report chain,
trusted Capsule/package/immutable-contract identity, and canonical
`completed_rounds=N+1` context remain exact. There is no generic output
mismatch flag or relaxation.

Valid state is projected by the shared list/run evaluator as Progress Upload
Pending. The printed command uploads the original report and persists Cloud
acknowledgement with zero Harness starts, new rounds, Artifact generation or
changes to plan, typed Artifact, context, or Progress bytes. Acknowledged state
remains stable across list, refresh, semantic-noop sync and process-restart
equivalents. Arbitrary Markdown, one-byte/whitespace changes and identity,
typed Artifact, Progress, context, provenance, symlink and cross-instance
tampering all fail closed. Writing 0.3 and Idea recovery remain unchanged;
Experiment 0.5 and Review 0.4 healthy adoption remain passing.

Focused recovery qualification passed 62 tests. Complete backend qualification
on a generated marker-protected PostgreSQL database passed `904 passed, 14
existing skips`; Alembic upgraded from empty to sole head `20260813_0021`,
autogenerate reported no new operations, and the database was dropped.
Controlled Playwright passed 4, owner-runtime tests passed 43, frontend Vitest
passed 34, TypeScript/ESLint/production build and compileall passed. No owner
Project, Workspace, database or Artifact bytes and no live Provider were
accessed. No migration, Registry, Capsule, Definition, Skill, Resource,
Artifact schema or Progress schema changed.
