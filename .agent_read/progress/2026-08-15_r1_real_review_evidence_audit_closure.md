# R1 Real Review evidence-audit closure

- Date: 2026-08-15
- Baseline: `main` at `82dc6914135bdef662ceba3a1d972228b183cdc8`
- Status: `PASS_R1_COMPLETE`
- Migration sole head: `20260815_0025`
- Product identity: Review Definition 0.3.0 / Capsule 0.5.0

## Product closure

R1 publishes immutable `review-report/v2` and preserves v1 plus historical
Review 0.2/0.4. One exact `manuscript-draft/v2` is required. Exact Idea,
Literature, and Experiment v2 support may be bound only explicitly and must
match Draft lineage. Codex establishes a bounded Scope, crosses exact Owner
approval, audits the typed Draft and available evidence, emits structured issues,
crosses exact Owner review, then publishes v2, terminal Progress, and the Cloud
Artifact projection.

The v2 output contains exact manuscript/support identities, checksummed Scope
and approval, derived evidence availability, bounded assessment, typed issues,
limitations, exact Owner review, and producer lineage. Issue targets use section
and optional existing claim ID. No accept/reject, publication probability,
scientific score, or W2 resolution state is allowed.

## Development defects corrected

- The shared installed-Capsule validator and runtime dynamic-path authority now
  recognize the formal `workflow/real-review.json` descriptor.
- Reviewed Review Progress is routed through exact reviewed-Core provenance and
  never through Scaffold heuristics.
- Embedded issue validation now enforces the shared AVAILABLE/LIMITED/UNAVAILABLE
  evidence-reference values while the separate availability audit retains
  SCOPE_LIMITED.
- The first bounded Real Codex Scope pass added role fields and object/null values
  outside the exact contract. Harness instructions now explicitly require exact
  three-field ArtifactRefs and string arrays; the next public run passed.
- Registry regression expectations were updated for the immutable W1/R1
  publications without changing production semantics.

## Verification

- Focused Artifact, Writing/Review runtime, Workspace, and Skill Registry suites:
  60 passed.
- Disposable PostgreSQL migration/Registry qualification: 2 passed; migration
  upgraded from empty to `20260815_0025`, autogenerate found no operations, and
  the generated database was dropped.
- Controlled public Workspace fake-Harness qualification: seeded
  REVISION_REQUIRED and bounded NO_BLOCKING_ISSUES scenarios both passed exact
  v2, Owner checkpoints, Progress, Cloud projection, exactly-once, and cleanup.
- Bounded Real Codex public qualification: the seeded claim-scope violation was
  identified and anchored to Introduction/claim-1; no publication decision or
  numeric score was emitted; exact v2, Progress, Cloud projection, and cleanup
  passed.

## Boundaries and next action

This proves the narrow controlled R1 software and Agent path. It does not prove
arbitrary manuscript scientific correctness, publication fitness, global
novelty, external citation completeness, or issue resolution. No frontend,
hosted Review, Provider, retrieval, Writing revision, or sibling private-file
access was added.

`R1_STATUS = COMPLETE`. Next phase is W2 Revision Integration; do not begin it
automatically.
