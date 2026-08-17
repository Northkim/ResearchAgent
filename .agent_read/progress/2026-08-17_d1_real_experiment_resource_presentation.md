# D1 Real Experiment Resource presentation and readiness correction

- Date: 2026-08-17
- Baseline: `main` at `1ee391b2a80fe591bacb6e2f9f3bdf710dbe349f`
- Status: `PASS_WITH_WARNINGS_READY_FOR_OWNER_RETEST`
- Migration sole head: `20260815_0026` (unchanged)
- Released identity preserved: Real Experiment Definition 0.4.0 / Capsule 0.7.0

## Corrected behavior

Workflow Detail no longer uses the catalog's historical recommended version as
the contract for a pinned Workflow Instance. It loads Definition detail and
selects the exact `instance.workflow_version`. Real Experiment 0.4.0 therefore
shows one required Artifact input, `selected-research-idea/v1`, and does not
show the historical optional literature input.

The Resource section now presents the exact backend requirement rather than
hardcoded optional/scaffold copy. For Real Experiment it shows required
`source_repository`, kind `SOURCE_REPOSITORY`, cardinality exactly one, allowed
provider GITHUB, and the immutable owner-staged package purpose. It explains
that Cloud stores exact credential-free metadata while the browser neither
clones nor stages bytes, and exposes the supported local `resource stage`
command template and Experiment Package contents.

The derived Cloud projection now loads exact Resource requirements and active
bindings. Missing required bindings project `WAITING_FOR_RESOURCE` /
`SELECT_RESOURCE`; an exact binding projects `NEEDS_RESOURCE_STAGING` /
`STAGE_RESOURCE`. RUN is not advertised for either state. Existing Workflows
without required Resources preserve their prior ready-state behavior.

## Preserved authority boundary

Cloud still cannot observe `.reagent/resource-index.json`. It therefore does
not claim that bound bytes are staged, verified, or drift-free. The existing
Local Runner remains authoritative and continues to fail closed for unresolved
or drifted Resources. No new readiness persistence, acknowledgement field,
browser-to-Workspace write, or parallel Resource state machine was added.

## Verification

- Backend focused preset/readiness tests: `10 passed`.
- Affected Progress/API suites: `68 passed`.
- Frontend focused component tests: `2 files / 9 tests` passed.
- Full frontend Vitest: `17 files / 45 tests` passed.
- TypeScript: passed.
- ESLint: passed.
- Next.js production build: passed. The first sandboxed attempt was blocked by
  Turbopack's internal loopback-port helper; the unchanged build passed with the
  normal build permission.
- Python compileall: passed.
- Alembic sole head: `20260815_0026`.
- `git diff --check`: passed.

Highest evidence is E3 controlled service/API collaboration plus E1 component
behavior. `VERIFIER_INDEPENDENCE = LIMITED` because the same session implemented
and verified the change. No E6 controlled browser or E9 Owner UX result is
claimed.

## Integrity and next action

No Workflow Definition, Capsule, Artifact schema, migration, ORM/repository,
ResourceReference model, Local Runner, package manifest, network policy,
Project state, Workflow Instance state, database row, Resource binding,
Resource staging, Experiment Package, or Experiment execution changed. No ADR
was added because the accepted Cloud/local Resource boundary is preserved.

Safe next action: restart the supported runtime from this working tree and let
the Owner retest the existing Real Experiment Workflow Detail. D1 continuation
must remain paused until the Owner confirms that the Web UI clearly shows the
exact required Idea, required GITHUB source repository, owner-staged package
handoff, and blocked RUN semantics.

## Owner-facing Experiment Package UX follow-up

The Owner semantic retest confirmed the contract correction but found the
ResourceReference-shaped registration controls unsuitable for a research
Owner. The bounded frontend follow-up now presents one coherent progression:

1. Prepare the Experiment Package in the Local Workspace.
2. Register or choose its exact GitHub source and use that source.
3. Stage and verify the local package with the existing public command before
   running the experiment.

The primary form uses Package name, GitHub repository, Commit SHA, and Package
SHA-256. GitHub is displayed as the fixed source type derived from the exact
required 1..1 GITHUB-only `SOURCE_REPOSITORY` requirement, not as an editable
provider. Existing sources use “Registered sources” and “Use this source.” The
page-level action uses “Choose package source.” The exact staging command is
unchanged, and the page explains that the Local Runner verifies the manifest
and checksum and blocks unresolved or drifted packages.

Raw requirement key/kind/required/cardinality/provider and Resource/binding
identities remain available in expandable Technical details. No Cloud staging
claim was added: source identity stays in Cloud; package bytes and staging truth
stay local. Generic Resource UI retains its prior metadata-only/no-network
boundary.

Additional verification:

- Focused Resource/Workflow Detail/board tests: `3 files / 17 tests` passed.
- Full frontend Vitest: `17 files / 46 tests` passed.
- TypeScript and ESLint: passed.
- Next.js production build: passed outside the sandbox after the sandbox denied
  Turbopack's internal local-port bind.
- `git diff --check`: passed.

No Workflow/Capsule/Artifact/Resource contract, migration, persistence,
ResourceReference operation, Local Runner, package manifest, execution runtime,
network policy, Project state, binding, staging, package, or Experiment run was
changed. This is ready for another Owner production retest; it does not itself
unblock D1.
