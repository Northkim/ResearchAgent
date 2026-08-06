# ADR 0022: Hybrid Project Workspace and Workflow Capsule Architecture

- **Status:** Accepted
- **Date:** 2026-08-06
- **Scope:** Design contract for post-V0.1 local research continuity
- **Governing decisions:** ADR 0009, ADR 0010, ADR 0017, ADR 0019,
  ADR 0020, and ADR 0021

## Context

The accepted V0.1 Literature Search product is intentionally Package-centric:
one `LocalProject` selects Literature Search, owns one current Package identity,
and projects one Package-scoped Progress chain. That model safely established
the teacher-aligned cloud/local/Harness boundary, but a complete Package is not
a durable coordination unit for adding Workflows, sharing immutable outputs, or
maintaining project-level continuity.

The owner ratified a hybrid rather than replacing either boundary. A cloud
Project needs one long-lived logical local Workspace, while each Workflow
Instance needs an isolated, versioned Capsule. Cloud desired configuration and
verified local installation state must remain different facts. Concrete
research state remains local, and the cloud never writes directly to it.

## Decision

One cloud Project has one stable logical `workspace_id`. The Workspace contains
project-level control metadata, bounded cognitive context, typed Artifact
references, Resource references, and isolated Workflow Capsules. Multiple
instances of one Workflow Definition are valid in the domain; the first UI
allows at most one active instance of each type.

A Workflow Capsule has an immutable definition and only explicitly declared
mutable execution-state roots. Capsule versions and built-in reviewed Skill
versions are checksum-bound and installed side by side. Pull-based sync stages,
validates, and atomically installs only missing content. It never overwrites a
Capsule or Artifact. Workflow removal retires desired state and never deletes
local history. Manifest mutation uses an explicit base revision and has no
automatic multi-device merge.

Artifacts cross Workflow boundaries only through typed, immutable,
checksum-bound references and explicit verified materialization. Symlinks and
shared writable files are prohibited. The cloud stores Artifact metadata by
default, not bytes. External Resources are revision-pinned metadata resolved by
local tools using local credentials; no cloud connector or automatic push is
authorized.

Cloud desired state is represented by the revisioned Desired Project Manifest.
Verified local state is represented by the Installed Workspace Lock and
Installation Acknowledgements. Neither the manifest nor a cloud Progress
projection claims that local bytes currently exist. Project progress is a
graph/list of per-Workflow-instance state, not a required linear pipeline.

The current Literature Search Package contract and checksum semantics remain
unchanged. Existing Packages remain runnable for the V0.x line and may be
adopted as legacy-compatible Capsules by reference or moved only by an explicit
owner operation. Historical Progress Report bytes are never rewritten; a
deterministic compatibility mapping supplies a legacy Workflow Instance
identity outside the original report.

## Consequences

- The stable product abstractions become Project, Project Workspace, Workflow
  Definition, Workflow Instance, and Workflow Capsule; “Package” refers only to
  the accepted legacy downloadable V0.1 bundle.
- New local-product tables are additive and use unambiguous physical names
  where current Hosted tables already occupy a generic name.
- The cloud/local/Harness boundary remains unchanged: cloud manages desired
  configuration and bounded metadata; local Capsules own concrete state; Codex
  performs research.
- Skills are executable only when built-in and reviewed. Private/imported
  executable Skills, device identity, automatic cross-device sync, Workspace
  backup, general Artifact upload, and deep GitHub/Hugging Face connectors are
  deferred.
- Idea Discovery is the first planned extensibility test, but this ADR does not
  implement it or authorize any implementation.

## Alternatives considered

- Preserve independent complete Packages and coordinate only in cloud: rejected
  as the long-term model because cross-Workflow handoff and local continuity
  remain manual and duplication-prone.
- Use one fully shared mutable Workspace: rejected because Workflow isolation,
  rollback, checksum safety, and reproducibility become ambiguous.
- Replace current Packages immediately: rejected because it would discard
  accepted Literature Search evidence and break downloaded folders.
- Store complete Workspace or Artifact bytes in cloud: rejected because it
  expands privacy, retention, storage, and credential boundaries without being
  necessary for the initial local product.
