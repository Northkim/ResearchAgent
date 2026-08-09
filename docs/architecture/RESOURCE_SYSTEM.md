# External Resource references and local resolution

## Plan alignment

The original Meta Research Agent plan did not name Resource as a separate
product module. F1E is an approved extension of the later frozen
HYBRID_WORKSPACE_AND_CAPSULES architecture. It preserves the original boundary:
ReAgent Cloud coordinates metadata, while the Local Workspace and the existing
Codex/Claude Code harness own real files and execution.

`ORIGINAL_PLAN_ALIGNMENT = PASS_WITH_ARCHITECTURE_EXTENSION`

`EVOLVED_ARCHITECTURE_ALIGNMENT = PASS`

`ROUTE_DRIFT = false`

## Domain model

A Resource is an external code, dataset, model, checkpoint, or generic-file
reference. It is not a Skill, Artifact, Capsule, or mutable Workflow memory.

The canonical chain is:

`Project Resource Reference -> exact Workflow Instance binding -> local resolver -> .reagent/resource-index.json`

`ProjectResourceReference` is Project-scoped and stores a stable Resource ID,
kind, provider, credential-free locator, exact immutable revision, expected
SHA-256 content checksum, bounded display metadata, and lifecycle. A new remote
revision creates a new reference; no `latest`, branch, or automatic advancement
exists.

`WorkflowResourceRequirement` belongs to an exact Workflow Definition Version
and declares kind, cardinality, optionality, permitted providers, and usage.
`WorkflowResourceBinding` selects one exact Project Resource for one exact
Workflow Instance requirement. Composite database constraints and service checks
reject cross-Project binding.

## Cloud and local boundary

Cloud stores reference and binding metadata only. It never stores repository,
dataset, model, weight, checkpoint, or generic-file bytes; provider tokens;
local absolute paths; clone directories; or request headers. Resource state is
not added to the Capsule Installed Lock or Artifact Index.

The Workspace keeps resolved bytes under `resources/<resource-id>/` and the
independent canonical index at `.reagent/resource-index.json`. The index stores
only Workspace-relative paths, exact reference identity, expected and locally
verified checksums, status, and verification time. Cloud cannot claim local
resolution.

## Resolver shell and security

The generic `reagent_local.py resource` commands list references, inspect local
status, and resolve exact bindings. Resolution is always explicit. A bound
Resource that is not locally verified fails Workflow preflight closed; optional
unbound requirements do not block a run.

F1E includes one deterministic `LOCAL_TEST` resolver gated by
`REAGENT_CONTROLLED_RESOURCE_TEST=1` and an explicit fixture root. It validates
the exact revision marker, rejects traversal, symlinks, hard links, special
files and case-fold collisions, builds a canonical ordered file manifest,
compares the expected checksum, stages on the same filesystem, atomically
publishes, rereads, then atomically updates the Resource Index. Drift fails
closed. Interrupted publish before index is recoverable by repeating resolve.

GitHub and Hugging Face are metadata-only providers in F1E. Their resolver
always returns `RESOURCE_RESOLVER_NOT_IMPLEMENTED`; it makes no network request
and never falls back to a live clone/download. OAuth, Apps, tokens, caches,
cleanup, cross-Project sharing, and large-resource strategies are deferred.

## Experiment integration

Reproduction & Experiment Definition/Capsule 0.3.0 adds four optional Resource
requirements: source repository, dataset, model, and checkpoint. The immutable
0.1.0 and Skill-backed 0.2.0 versions remain unchanged. Version 0.3.0 remains
`SCAFFOLD_CORE`, supports only the Idea Experiment skeleton, does not enable
paper reproduction, never executes Resource bytes, and continues to require
`PLACEHOLDER_NOT_EXECUTED` with `actual_results = null`.
