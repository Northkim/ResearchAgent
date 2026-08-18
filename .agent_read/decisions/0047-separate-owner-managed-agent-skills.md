# 0047: Keep Owner-managed Agent Skills separate from reviewed Skill publication

- Status: Accepted
- Date: 2026-08-18

## Context

Reviewed Skills are immutable, qualified publications pinned by Workflow Definitions
and delivered inside Capsules. An Owner also needs reusable GitHub Agent Skills that
can be attached to Projects and discovered by the local Agent Harness. Giving these
mutable records reviewed publication semantics would falsely confer trust and couple
ordinary Project customization to Capsule identity.

## Decision

Store Owner-managed Skills and Project associations in separate mutable records.
Resolve the supported GitHub source to an exact commit and bounded package checksum,
but do not store package bytes in Cloud. Normal Workspace sync installs attached
packages under `.agents/skills/<slug>/`, records exact ownership in the existing
Installed Lock, and removes only unchanged ReAgent-managed installations.

User-managed Skills never enter reviewed Skill publication, Workflow Skill pins, or
ExperimentCapability qualification. ReAgent coordinates records and local presence;
the Agent Harness alone discovers and uses the installed instructions.

## Consequences

One Skill can serve several Projects without becoming a Workflow or execution unit.
Attach/detach is explicit and sync is idempotent. Source or local drift fails closed,
and unrelated user-owned local Skills are preserved. M1 supports only public GitHub
sources containing `SKILL.md`; marketplace, OAuth, uploads, activation, ratings, and
Capability promotion remain deferred.

## Alternatives considered

- Reuse reviewed Skill tables: rejected because their immutability and trust meaning
  are incompatible with Owner-managed records.
- Add a separate Skill installer/lock: rejected because normal Workspace sync and the
  existing Installed Lock already provide the required ownership boundary.
- Persist source archives in Cloud: rejected because exact local resolution suffices.
