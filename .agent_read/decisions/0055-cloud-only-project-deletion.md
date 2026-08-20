# 0055: Cloud-only Project deletion

- Status: Accepted
- Date: 2026-08-20

## Context

Owners need to remove mistaken, obsolete, duplicate, or completed Projects from
ReAgent Cloud. A Project spans canonical and local-facing Project rows, Workflow
Instances, exact bindings, Progress, manifests, Workspace acknowledgements,
Artifact metadata, resource bindings, and User-Skill associations. Existing
foreign keys do not provide one uniform cascade. Local Workspace files are owned
by the user and are outside Cloud authority.

## Decision

Expose one explicit, confirmed Cloud Project delete operation. Centralize the
Project-owned relational deletion graph at the Unit-of-Work persistence boundary
and execute it child-to-parent in one transaction. Delete Project-Skill
associations but never the global User Skill, immutable Workflow/Capsule
publication, reviewed Skill, ExperimentCapability, or unrelated Project.

Never enumerate, read, write, or delete a Local Workspace from Cloud. Before a
normal Local sync opens its write boundary, verify the Workspace's exact Cloud
Project identity. If the Project no longer exists, return `PROJECT_NOT_FOUND`,
leave every local byte unchanged, and never recreate or rebind the Project.

## Consequences

- Project deletion is deliberately destructive for Cloud relational state and
  therefore requires an Owner confirmation.
- Local research files survive unchanged and become an orphaned historical
  directory that the Owner may keep or delete manually.
- Shared User Skills survive Project deletion and retain associations to other
  Projects.
- Physical retention/erasure of immutable content-store objects or generated
  delivery archives is a separate storage-governance concern; R5 removes their
  Project-addressable relational records without introducing a broad filesystem
  deletion API.
- No schema migration is required for the current ownership graph.

## Alternatives considered

- Remote Local Workspace cleanup: rejected because Cloud does not own or access
  user research files.
- Database-wide cascade migration: rejected as unnecessarily broad for the
  current mixed historical ownership graph.
- Route-level scattered deletes: rejected because partial deletion would be
  difficult to reason about and qualify transactionally.
- Soft delete/archive: rejected because the authorized minimum lifecycle is
  explicit deletion, not a release-management system.
- Implicit recreation from an old Workspace: rejected because it substitutes
  identity and could upload stale state into a new Project.
