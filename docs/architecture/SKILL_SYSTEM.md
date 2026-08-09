# Skill Registry, exact pins, and Capsule delivery

## Product alignment

ReAgent Cloud manages normalized Skill metadata and immutable versions. A
Workflow Definition Version pins exact Skill Versions, and the Capsule compiler
bundles those reviewed bytes under `workflow/skills/`. The existing local Agent
Harness reads the bundled instructions; ReAgent does not introduce a Cloud
agent runtime or a new execution engine.

The canonical chain is:

`Skill Definition -> immutable Skill Version -> exact Workflow Version pin -> Capsule -> local workflow/skills/ -> Agent Harness`

## Domain authority

A Skill Definition owns the stable key, display metadata, lifecycle, source
class, and trust tier. A Skill Version owns an exact semantic version, canonical
content manifest, checksum, review state, and repository-controlled source
identity. `WorkflowDefinitionVersionSkillPin` binds one Workflow Definition
Version to one exact Skill Version and checksum in deterministic order.

There are no floating `latest`, range, or caret pins. Published bytes, manifests,
and checksums are immutable. Changing Skill content requires a new Skill Version;
adopting it requires a new Workflow Definition Version and Capsule Version.
Existing Workflow Instances and Installed Locks are never upgraded in place.

## Declarative content contract

F1D uses the existing `local-skill/v0.1` format:

```text
workflow/skills/<stable-skill-key>/
  skill.json
  SKILL.md
```

`skill.json` identifies the stable key, exact version, reviewed built-in trust,
required harness capabilities, and the checksum of `SKILL.md`. The Skill Version
checksum binds both canonical files using the same canonical JSON and SHA-256
helpers already used by Workflow Packages.

Reviewed built-in content is bounded to Markdown, JSON, and plain text. Validation
rejects absolute or parent paths, backslashes, normalized/case-fold collisions,
oversized manifests, missing files, symlinks, hard links, special files, and
checksum drift. Skill validation never executes Skill files.

## Delivery and local consumption

The Capsule compiler resolves every pin before building. Missing, unavailable,
unreviewed, untrusted, duplicate, or checksum-conflicting Skills fail the build;
they are never silently omitted. Package manifests project the same ordered exact
pins, and the Capsule checksum binds the Skill bytes.

B4 sync remains unchanged: the Capsule archive is the only install unit. There
is no independent Skill download protocol, daemon, or Skill Installed Lock.
The Capsule Installed Lock and immutable-file checksum remain local truth.

At startup, a skill-backed scaffold Capsule instructs Codex or Claude Code to
verify the manifest, read each pinned `skill.json`, then its `SKILL.md`, and only
then read the Workflow prompt. The Harness must not scan the Workspace for
arbitrary Skills. Skills cannot override safety boundaries, modify `inputs/`,
write to immutable `workflow/skills/`, or access sibling Capsules. Missing or
tampered Skill files fail preflight and require a verified sync restore.

## Trust and operator boundary

F1D supports only repository-maintained `BUILT_IN_REVIEWED` declarative Skills.
The public API is metadata-only and read-only: `GET /skills` and
`GET /skills/{skill_id}`. Workflow catalog and instance projections include
exact pins without exposing server paths or arbitrary file fetches.

The existing Workflow Package operator CLI adds read-only `skill-list`,
`skill-show`, and `skill-verify` commands. Browser mutation remains disabled
because the controlled deployment has no authenticated admin identity or tenant
boundary. Full AG Admin write UI, upload, remote import, marketplace, and
executable Skills are deferred.

## Skill, Prompt, Artifact, Resource, and memory

- A **Prompt** says what one Workflow should do.
- A **Skill** is reusable reviewed method and safety guidance bundled with it.
- An **Artifact** is immutable research output/input provenance produced by a Workflow.
- A **Resource** is an external repository, dataset, model, checkpoint, or file locator; F1E owns this model.
- **Memory** is mutable per-Instance/session continuity and never belongs in a Skill.

Skill presence does not change Workflow maturity. Writing and Review 0.2.0,
Reproduction & Experiment 0.2.0, and its Resource-aware 0.3.0 successor remain
`SCAFFOLD_CORE`; the frozen placeholder validators remain authoritative.
