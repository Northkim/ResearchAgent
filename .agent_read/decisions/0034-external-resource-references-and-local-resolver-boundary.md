# 0034: External Resource references and local resolver boundary

- Status: Accepted
- Date: 2026-08-09

## Context

The original three-page product plan did not define Resource as a first-class
module, but the accepted hybrid Workspace/Capsule architecture assigns code and
version history to GitHub, ML assets to Hugging Face, metadata coordination to
Cloud, and byte resolution to the Local Workspace. Experiment needs a
reproducible way to name these external assets without turning Cloud into file
storage or remote execution.

## Decision

Add Project-scoped immutable Resource References, exact Workflow Version
Resource Requirements, and exact Workflow Instance Resource Bindings. Cloud
stores credential-free provider metadata, exact revision, expected checksum,
and bindings only. Local resolution owns bytes and records verified state in a
separate Workspace Resource Index. Capsule Installed Lock, Artifact Index,
Skill Registry, and mutable memory remain separate authorities.

GitHub and Hugging Face are metadata-only providers in F1E and always fail
resolution as not implemented without network access. Provide a deterministic,
explicitly gated LOCAL_TEST resolver solely for isolated qualification. Publish
Experiment 0.3.0 with four optional Resource requirements while preserving its
Skill pins, `SCAFFOLD_CORE` maturity, and no-execution safety.

## Consequences

References never float to a branch or latest revision. Bound but unresolved or
drifted Resources fail local preflight, while optional unbound Resources do not
block the Scaffold. Existing Experiment 0.1/0.2 Instances do not upgrade. A real
provider resolver, credentials, cache and cleanup policy require future owner
approval. This is an architecture extension aligned with, rather than a change
to, the original Cloud/local execution boundary.

## Alternatives considered

- Encoding repositories or datasets as Skills was rejected because Skills are
  immutable method instructions, not external bytes.
- Encoding Resources as Artifacts was rejected because Artifacts are immutable
  Workflow-produced research outputs.
- Storing bytes or credentials in Cloud was rejected by the frozen hybrid
  boundary and controlled-deployment security policy.
- Live GitHub/Hugging Face resolution was rejected for F1E because provider
  authentication, network and large-data policies are not yet approved.
- Adding Resource state to Installed Lock was rejected because Capsule and
  Resource installation are independent local truths.
