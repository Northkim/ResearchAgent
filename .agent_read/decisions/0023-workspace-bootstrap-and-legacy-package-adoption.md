# ADR 0023: Workspace Bootstrap and Legacy Package Adoption

- **Status:** Accepted
- **Date:** 2026-08-07
- **Scope:** NIGHT-B3 promotion of the local Workspace identity/bootstrap contract
- **Governing decisions:** ADR 0009, ADR 0017, ADR 0019, ADR 0021, ADR 0022

## Context

ADR 0022 freezes one canonical Workspace identity per Project, a root
`project.json`, isolated versioned Capsule paths, and non-destructive V0.x
Literature Search compatibility. ARCH-D1 did not freeze the bootstrap HTTP
path, distribution command, or the integrity envelope needed to promote its
design-only Workspace schema into a runtime contract. B2 already persists the
canonical `workspace_id`, Desired Manifest, Workflow Instance, and exact
Workflow/Capsule pins, so B3 must not add another identity or an empty database
migration.

Existing Literature Search Packages may contain valid mutable outputs, memory,
Progress drafts/reports, and receipts. Adopting them by rewriting the Package
manifest would invalidate accepted checksums and its self-contained launcher;
moving them by default would also risk user state. A local copy operation must
therefore verify immutable Package content while preserving declared mutable
state and the original source.

## Decision

The sole bootstrap read route is:

`GET /projects/{project_id}/workspace-bootstrap`

It returns `reagent.workspace-bootstrap/v0.1`, reconstructed from persisted
Project, current Desired Manifest, entries, Workflow Instances, Capsule pins,
and current legacy Package metadata. Its canonical checksum excludes only its
own checksum field. A damaged or cross-Project relation returns
`WORKSPACE_BOOTSTRAP_NOT_AVAILABLE`; the router does not invent metadata.

The promoted Workspace identity file is root `project.json` using
`reagent.project-workspace/v0.1`. It binds the B2 Project/Workspace identity,
cloud-origin identifier, bootstrap Manifest revision/checksum, lifecycle,
secret policy, fixed control paths, creation time, and its own canonical
checksum. The file contains no local absolute path or credential. Bootstrap
caches the exact cloud descriptor and Desired Manifest and creates only the
minimal Capsule registry and `capsules/` container. The design-reserved
Installed Lock path is declared but the file is not created.

The canonical Workspace management entry is `python reagent_local.py` with:

- `bootstrap <target> --descriptor <file>`;
- `adopt <legacy-package> <workspace> [--descriptor <file>]`;
- `workspace status <workspace>`.

Bootstrap is non-interactive, staging-based, atomic, checksum-verified, and
idempotent for the same identity. Adoption accepts an extracted Package or ZIP,
derives the frozen legacy Workflow Instance from the Package Project identity,
checks it against the descriptor and exact Capsule pin, verifies every
immutable manifest entry, preserves declared mutable/dynamic state, copies into
the ARCH-D1 Capsule path through same-filesystem staging, then atomically writes
the minimal registry. The source is never moved, rewritten, or deleted.
Package code is not executed during adoption. Existing Package
`python reagent_local.py run .` remains unchanged inside the adopted Capsule.

The Capsule registry is local presence metadata only. It does not claim cloud
sync, successful generic installation, Installed Lock state, or
acknowledgement. A valid Capsule copied before a registry-write failure is an
explicit recoverable partial state; rerunning the same adoption verifies the
copy and repairs only the registry.

## Consequences

- B3 requires no database migration; B2 `workspace_id` and Manifest state are
  reused without reinterpretation.
- Workspace roots are movable because identity and Capsule locations are
  relative and contain no machine path.
- Source Packages and all accepted V0.x Package checksums remain unchanged.
- Absolute/traversal paths, portable-name collisions, symlinks, hardlinks,
  special files, archive bombs, identity mismatch, immutable drift, and target
  conflict fail closed.
- A refreshed descriptor may be supplied to adoption when Package metadata was
  generated after the initial Workspace bootstrap; this does not mutate the
  Workspace identity or claim sync.
- Pull-based sync, generic Capsule download/installation, Installed Lock,
  acknowledgement, Progress aggregation, and other Workflows remain deferred.

## Alternatives considered

- Add a B3 database table or new Workspace ID: rejected because B2 already owns
  the canonical identity and desired-state pins.
- Rewrite the legacy Package with `capsule.json`: rejected because it breaks the
  accepted manifest/launcher checksum contract.
- Move or delete the source by default: rejected as destructive and unnecessary.
- Adopt by symlink or external absolute-path reference: rejected because it is
  non-portable and conflicts with the no-symlink/no-machine-path boundary.
- Implement generic sync/install now: rejected as NIGHT-B4 scope.
