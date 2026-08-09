# 0033: Skill Registry, exact pins, and Capsule delivery

- Status: Accepted
- Date: 2026-08-09

## Context

The original product plan requires Cloud-managed normalized Skills, exact
Workflow requirements, and local delivery with the Workflow template. Existing
Capsules already contain declarative `local-skill/v0.1` instructions, but no
persistent Definition/Version/pin authority exists. The controlled deployment
has no authenticated administrator identity, so a network mutation surface
would be unsafe.

## Decision

Add canonical Skill Definition, immutable Skill Version, and exact Workflow
Definition Version Skill Pin persistence. Support repository-maintained,
declarative, built-in reviewed Skills only. The Capsule compiler is the delivery
boundary: it resolves exact pins, includes Skill manifests/instructions under
`workflow/skills/`, and binds their bytes into the Package/Capsule checksum.
B4 sync continues to install one complete Capsule; no independent Skill sync or
Installed Lock truth is introduced.

Expose bounded metadata-only read APIs and read-only operator list/show/verify
commands. Defer browser mutation, uploads, imports, marketplace behavior, and
executable Skills until identity and trust boundaries exist. Keep Resources as
a separate future domain.

## Consequences

Skill changes require a new Skill Version, Workflow Definition Version, and
Capsule Version. Existing Instances remain pinned and reproducible. Local
preflight fails closed on missing or changed Skills. Skill metadata is visible
without confusing Skill presence with Workflow core maturity. Writing, Review,
and Experiment remain `SCAFFOLD_CORE`.

## Alternatives considered

- Updating embedded Skill bytes in existing Capsules was rejected because it
  breaks immutable version provenance.
- Independent local Skill download and lock state was rejected because Capsule
  is the approved atomic install unit.
- Browser admin mutation was rejected until authenticated operator identity and
  tenant boundaries exist.
- Encoding repositories or datasets as Skills was rejected because those are
  Resources owned by F1E.
