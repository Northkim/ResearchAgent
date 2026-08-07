# NIGHT-B7 Multi-Workflow Architecture Validation

Date: 2026-08-07

Status: **PASS — OWNER REVIEW REQUIRED**

## Baseline and recovered contracts

Implementation ran directly on clean `main` from accepted NIGHT-B6 final commit
`95acc28896b150b7559dd477c48dd650b9fa5e79`; it remained an ancestor and the
repository had one worktree. ARCH-D1 commit
`e880d40ec73f07198f7b064afd898982a3357e16`, product plan, ADRs 0022–0026,
Literature Search 0.3.0/0.5.0 sources and output validators, B4 sync, B5
Progress/Board and B6 Artifact/Index/materialization contracts were inspected.
No `.env`, credential, owner database, ProjectDB, live Provider or external
network was read or used. No branch/worktree was created and nothing was
pushed.

## Ratified production Artifact and immutable versioning

The owner-ratified `selected-paper-library/v1` contract is one canonical JSON
file. Literature Search 0.4.0 / Capsule 0.6.0 extends the accepted compiler
without changing 0.3.0/0.5.0 source or bytes. Explicit successful finish first
runs existing candidate/selection semantic validation, rejects missing or
duplicate joins, preserves exact records and selected order, includes source
checksums, computes SHA-256 over the actual canonical UTF-8 bytes, then
atomically publishes and re-verifies the content-addressed path. Intermediate
output produces no Artifact; another content creates another immutable record.

Existing Projects retain old pins. There is no automatic upgrade or legacy
promotion. New Projects use the reviewed 0.4.0/0.6.0 pin; standalone Package
generation is exact-instance-bound and the existing 0.5.0 compiler/path remains
the compatibility default for legacy service composition.

## Idea Discovery and dependency

`idea-discovery-local-experimental` 0.1.0 / Capsule 0.1.0 is Registry-backed,
reviewed, available, creatable, multi-instance-capable and
`TRUSTED_BUILT_IN_UNSIGNED`. Its exact `paper_library` requirement accepts one
specific `selected-paper-library/v1` and copies it to
`inputs/selected-paper-library.json`. The Cloud API/UI never selects first or
latest. Multiple producers remain explicit choices with producer instance,
time and checksum context.

The deterministic Capsule contains AGENT, reviewed method prompt, minimal
evidence-grounded built-in Skill, input/output contracts, local memory and the
existing Progress helper. It forbids sibling output access and input mutation,
distinguishes evidence/inference/candidate direction, and does not claim global
novelty. Normal outputs are `candidate-ideas/v0.1` and a human-readable report;
no Writing Artifact is registered.

## Sync, materialization and local execution

B4 dispatches the exact compiler for old Literature Search, production
Literature Search and Idea Discovery. Adding Idea Discovery increments Desired
Manifest; explicit sync installs only the new Capsule, atomically updates the
Installed Lock and acknowledges the current revision. Existing Literature
Capsule and mutable output hashes remain unchanged.

B6 remains the only handoff path. Artifact refresh independently re-reads
producer bytes. Explicit materialization validates the Cloud plan, Index,
source and target checksum, copies through same-filesystem staging without
symlink/hardlink/overwrite, and writes a checksummed receipt. Repeats are
idempotent. Source, Index, Cloud and target drift fail closed; publish-before-
receipt recovery is checksum exact.

The generic command `python reagent_local.py run <workspace>
--workflow-instance <id>` validates Workspace identity, Installed Lock, exact
Capsule and immutable pins. Idea preflight additionally requires the bound plan,
receipt and current materialized bytes. It never materializes or invokes cloud
research execution. Session continuity is carried by Capsule memory, Progress
and outputs rather than chat history.

## Persistence, frontend and qualification

Migration `20260806_0013` is data-only and follows `0012`. It seeds deterministic
reviewed versions/Capsules and the exact production requirement into existing
B6 tables, validates immutable conflicts after idempotent inserts, and removes
only B7 seed rows on safe downgrade. Empty and populated upgrade,
downgrade/re-upgrade, conflict rollback, sole-head/current/check and a dedicated
PostgreSQL restart qualified.

The Registry-driven Board naturally renders Literature Search and Idea
Discovery. The type-specific setup panel reads the generic Artifact/dependency
APIs, requires explicit radio selection and only shows local sync/materialize/
run commands. Overview and Progress consume the existing generic projections;
Help documents the new production boundary and legacy adoption rule. The
browser never writes local files.

Qualification results:

- focused B7 Package/Artifact/Workspace chain: `179 passed`; the final
  Artifact/Project/PostgreSQL E2E retest added `10 passed` after UTC response
  normalization;
- full backend with isolated PostgreSQL: `681 passed, 9 skipped`;
- database-only suite before final integration: `52 passed, 5 skipped`;
- B7 PostgreSQL end-to-end chain: `1 passed`;
- B7 migration qualification: `1 passed`;
- frontend Vitest: `13` files / `23` tests passed, including 10 Literature
  producers/Artifacts and 10 Idea cards with one shared Artifact request and
  no per-card dependency request;
- frontend typecheck, ESLint and production build: passed;
- backend compileall, Alembic heads/current/check and `git diff --check`: passed.

The nine skips are expected pre-existing gates: four integration suites need
separately authorized HTTP/live environments and five historical B1/B2/B4/B5/
B6 migration tests require their dedicated destructive database variables. No
B7 test skipped. The first production build attempt was sandbox-blocked by
Turbopack helper-port binding; the approved isolated rerun passed.

Temporary fictional Workspaces exercised a new Project, legacy preservation,
two Literature producers with explicit choice, Artifact drift repair, retired
producer retention and fresh-session Idea continuation. The PostgreSQL E2E
persists and reloads producer Artifact, Idea binding, both Progress histories
and Board projections across independent sessions. Original producer and
installed Literature Capsule hashes remain unchanged.

Project aggregation bulk-loads dependency bindings and Artifact provenance in
fixed repository queries rather than issuing per-Workflow lookups. The Board
uses the aggregated dependency edges and a shared paginated Artifact query, so
the 10-by-10 frontend fixture has no per-card request explosion.

## Boundary

No Writing, Review, Experiment, automatic novelty search, cloud LLM execution,
cross-Project Artifact sharing, cloud Artifact bytes, Skills marketplace,
GitHub/Hugging Face resolver, Workspace backup, watcher, background sync,
automatic latest/materialization or browser-local execution was added.

ADR 0027 records the accepted production type, immutable upgrade strategy and
Idea execution boundary. The architecture now has one proven production chain
from Literature Search through typed handoff to separate Idea Discovery.
