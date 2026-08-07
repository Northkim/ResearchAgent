# 0028: Derived product guidance and immutable adapter recovery

- Status: Accepted
- Date: 2026-08-07

## Context

NIGHT-H1 exercised the accepted B1–B7 product as a first-time user rather than
as an architecture fixture. The underlying state boundaries were sound, but
the normal journey exposed three blocking integration gaps: the published
Literature Search 0.6.0 local-session adapter did not forward its redundant
canonical Artifact declaration list; the Idea Discovery output contract needed
the selected Artifact ID even though materialization correctly copied only the
Artifact bytes; and user guidance required raw Workflow Instance UUIDs and
internal state interpretation.

Published Capsule 0.6.0 and 0.1.0 bytes are immutable. Cloud cannot inspect
materialization receipts or other Local Workspace files, and the browser must
not perform local writes or execution. A repair therefore had to use existing
authoritative identities without weakening explicit selection, checksums, or
Cloud/local ownership.

## Decision

User-facing next actions are derived read guidance, never a persisted state
machine. Cloud UI guidance uses Desired state, installation acknowledgement,
dependency binding, and Progress. Because materialization is local-only, the
browser remains conservative after binding and tells the user to prepare the
input; `reagent_local.py workflow list` reads verified local Lock, receipts,
input bytes, and self-identifying Progress to give the exact local next action.

The CLI accepts a stable `--workflow` selector only when exactly one active
installed instance matches. Ambiguity fails closed and `workflow list` provides
the exact `--workflow-instance` alternative. Existing exact-ID commands and
all `--json` result schemas remain supported.

For an accepted `COMPLETED` Progress Report, Cloud may deterministically derive
canonical Artifact declarations only from the exact producer Workflow Instance,
its exact reviewed Capsule `artifact_outputs` contract, and matching immutable
Progress path, kind, media type, size, and checksum metadata. An exact retry may
repair a missing canonical Artifact row from those same facts without creating
a second Progress row. Any mismatch or undeclared output still fails closed.

After Idea Discovery run preflight has verified the exact Cloud binding,
materialization receipt, and current input checksum, the Workspace runner may
atomically create an empty `candidate-ideas/v0.1` output envelope containing
only the verified source Artifact identity. It never invents research content,
overwrites an existing output, or reads a sibling Capsule. The Agent/user still
owns all candidate ideas and report content.

## Consequences

The controlled user journey no longer requires manual internal JSON editing or
raw UUID copying when Workflow selection is unambiguous. Human CLI errors say
what happened, why it matters, and the next safe action while retaining stable
machine error codes. Web and local readiness can differ without becoming
contradictory because each explicitly states its authority.

Existing B7 Progress that hit the immutable adapter omission can recover by an
exact idempotent upload retry. Published Capsule hashes, Artifact identity,
specific binding, no-auto-latest behavior, explicit materialization, and local
byte ownership do not change. No database migration or new production Workflow
is introduced.

## Alternatives considered

- Editing Literature Search 0.6.0 or Idea Discovery 0.1.0 was rejected because
  their checksum-bound Capsule content is already published.
- Trusting arbitrary client declarations or inferring from display names was
  rejected because it would permit producer and same-type Instance spoofing.
- Uploading materialization receipts to Cloud was rejected because H1 did not
  authorize a new persistence contract and Cloud still could not verify local
  bytes.
- Automatically selecting the only/latest Artifact or materializing during
  sync/run was rejected because both actions must remain explicit.
- Persisting `next_action` was rejected because it would create a second state
  truth that can drift from Manifest, acknowledgement, dependency, receipt, and
  Progress evidence.
