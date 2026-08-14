# 0037: Interactive scaffold Progress adoption and exact recovery

- Status: Accepted
- Date: 2026-08-14

## Context

Writing 0.3 and Experiment 0.4 proved that an interactive Agent may follow the
bundled contract and finalize a terminal Progress round before the Harness
exits. Their historical runners then published and rewrote context again and
attempted the same round, leaving a valid immutable report plus a deterministic
post-report context drift but no Cloud acknowledgement. The generic list path
used weaker validation than the run recovery path.

## Decision

New interactive scaffold Capsules snapshot the Progress tail before Harness
launch. After exit they either strictly adopt exactly one valid next terminal
report, output, context transition and provenance, or perform the existing
runner-owned deterministic finalization once when no report was created. The
Agent uses a public Capsule-local `finalize-scaffold` command; terminal replay
returns the existing report and cannot create another round.

The Workspace root client has one structured readiness evaluator shared by
`workflow list` and upload-only `run`. Exact current-context completion is
recoverable normally. Historical Writing 0.3, Review 0.3 and Experiment 0.4
may additionally recover only when every immutable invariant passes and the
current context exactly matches the historical runner's deterministic
`completed_rounds = N+1` terminal rewrite. Arbitrary mismatches remain invalid.
Recovery uploads the exact missing Cloud suffix and never runs a Harness,
rewrites context, regenerates an Artifact, or creates N+1.

Publish only new immutable Writing/Review Capsule 0.4 and Experiment Capsule
0.5 records in seed-only migration `20260813_0021`; Definitions, Skills,
Artifact/Progress schemas and historical Capsule bytes remain unchanged.

## Consequences

Agent-driven interactive completion has one Progress authority per round while
retaining the existing owner-approved scaffold method. Existing affected local
completions can be acknowledged in place by replacing only the Workspace-root
client. The deterministic historical context is preserved after acknowledgement
because it is semantically terminal and the shared evaluator continues to
recognize the exact fingerprint; immutable report and Artifact bytes are never
normalized or edited.

Future simplification to a runner-only finalization authority is deferred.
Any broader context relaxation or silent historical Capsule change remains
forbidden.

## Historical Experiment 0.4 output-drift clarification

The owner subsequently proved that one Experiment 0.4 completion also carried
a second deterministic defect dimension: its immutable Progress Report bound
the owner-reviewed human plan A, then the historical runner's post-report
`_publish()` replaced that file with deterministic plan B while reusing the
same typed Artifact. The original decision remains unchanged for exact and
context-only recovery. The generic evaluator recognizes this additional state
only for the exact trusted Experiment Definition 0.3.0 / Capsule 0.4.0
identity, only when the typed Artifact and all provenance remain exact, and
only when current Markdown bytes equal that immutable Capsule's own historical
renderer output and the existing N+1 context fingerprint also passes. It is
not enabled for Writing, Review, Idea, Experiment 0.3/0.5, or arbitrary output
drift. Recovery preserves plan B and every execution byte and uploads only the
existing report.

## Alternatives considered

- Runner-only finalization would require changing the current Agent contract
  and was rejected for this narrow repair.
- Asking the Agent to exit before finalization would redesign interactive UX.
- Ignoring context checks or trusting output existence was rejected because it
  permits stale, tampered or cross-execution Progress upload.
- Rewriting historical Capsule bytes or creating repair round N+1 was rejected
  by immutable execution continuity.
