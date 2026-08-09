# NIGHT-F1F Complete Product-Width End-to-End Qualification

Date: 2026-08-09

Status: PASS — READY FOR OWNER COMPLETE PRODUCT TEST

## Plan alignment

`ORIGINAL_PLAN_ALIGNMENT = PASS`

`EVOLVED_ARCHITECTURE_ALIGNMENT = PASS`

`ROUTE_DRIFT = false`

The qualified route remains Cloud Project/Workflow/Skill/Progress/configuration
metadata, Local Workspace research files/state, and Codex/Claude Code as the
Agent Harness. Artifact bytes, Resource bytes, memory and substantive work stay
local. F1F added no Workflow, Artifact type, Skill type, Resource provider,
Cloud execution, pipeline persistence, file hosting, multi-user system, or
real research core.

## Baseline

- branch/start: clean `main` at
  `ceeaa19eee4b0c2ac68dee367a113298537a1afa`
- F1E final commit: verified ancestor
- worktrees: one; extra worktrees: zero
- migration: sole head/current `20260806_0017`
- five production Workflows, Full Research preset, two production Skills and
  Resource schema/providers were independently verified from PostgreSQL seeds
- no `.env`, credential, owner database, owner Workspace, live OpenAlex,
  GitHub/Hugging Face request, branch, worktree or push was used

## Product capability inventory

- Cloud: Project creation; Literature-only, Literature+Idea, Full Research and
  Registry-driven Custom setup; Workflow Catalog/Board; derived readiness and
  next actions; friendly multi-Instance labels; Progress history/filtering;
  Help; controlled API/request IDs/readiness.
- Workspace: bootstrap, pull sync, Installed Lock, acknowledgement/retry,
  independent Capsules, local Workflow list/status/preflight/run, inputs,
  outputs and memory continuity.
- Workflows: reviewed Literature Search and Idea Discovery; safely marked
  scaffold Writing, Review, and Reproduction & Experiment.
- Artifact: immutable Reference/Index, exact same-Project dependency binding,
  verified materialization, content-addressed finalization and Progress
  promotion; no automatic latest.
- Skill: Registry/immutable Version/exact Workflow pin, Capsule delivery,
  local verification and read-only visibility.
- Resource: Project reference/exact revision/checksum, exact Experiment
  binding, independent Resource Index, controlled LOCAL_TEST resolver and
  metadata-only GitHub/Hugging Face boundary.
- Continuity/security: Progress upload/idempotency, local memory, restart
  reload, path/link/checksum/spoof protection, controlled deployment boundary.

## Complete product E2E

The new `qualify_complete_product_width` path uses only public API, Workspace
CLI services, real Capsule bytes and finalizers. It performs no direct database
insert and creates no synthetic Lock, Artifact receipt, Resource Index or
Progress response.

1. Full Research Project is created atomically with five Instances and
   Manifest revision 1.
2. Workspace bootstrap and sync install exact five Capsules; second sync is
   `NO_CHANGE`; scaffold Skills are present and checksum-bound.
3. Deterministic Literature fixture goes through production finalization and
   Progress upload to `selected-paper-library/v1` (`REVIEWED_CORE`).
4. Idea binds/materializes that exact Artifact, records one explicit selected
   candidate and promotes `selected-research-idea/v1` (`REVIEWED_CORE`).
5. LOCAL_TEST Resource metadata is created/bound/resolved through the Resource
   API/Index; GitHub and Hugging Face exact metadata records are also accepted
   without network resolution.
6. Experiment binds exact Idea/Literature and verified Resource state, then
   publishes `experiment-record/v1` with `PLACEHOLDER_NOT_EXECUTED` and null
   actual results.
7. Writing #1 binds exact Idea/Literature/Experiment and publishes Draft A with
   the visible scaffold marker and all three provenance edges.
8. Review #1 binds exact Draft A and publishes Review A with
   `INSUFFICIENT_EVIDENCE`.
9. Writing #2 is added as a new Instance, syncs without modifying prior
   Capsules, explicitly binds Idea/Literature/Experiment/Draft A/Review A, and
   publishes Draft B. Draft A and Review A remain byte-identical.
10. Progress reload contains six independent Instances and six reports;
    Writing #1/#2 remain distinct in Web/CLI labels.
11. fresh local invocations reconstruct Idea and Writing #2 continuity from
    Capsule memory/files, not chat history.
12. fresh FastAPI/SQLAlchemy sessions reload six Instances, six Artifacts,
    six Progress reports, three Resource records and Manifest revision 2 from
    isolated PostgreSQL.
13. the same complete state survives a physical PostgreSQL fast stop/start and
    a fresh application process; all counts and Manifest revision reload.

Canonical chain:

```text
selected-paper-library/v1
  -> selected-research-idea/v1
     -> experiment-record/v1
     -> manuscript-draft/v1 (Draft A, includes Experiment)
        -> review-report/v1 (Review A)
        -> manuscript-draft/v1 (Draft B, exact Draft A + Review A)
```

Every edge uses a specific Artifact ID and checksum. No latest, directory or
display-name selection participates.

## Skill and Resource qualification

- Writing 0.2.0, Review 0.2.0 and Experiment 0.3.0 contain exact Research
  Artifact Provenance 0.1.0 and Scaffold Core Safety 0.1.0 bytes below
  `workflow/skills/`; sync remains the only delivery unit.
- local Skill tampering makes Capsule verification fail closed with
  `LOCAL_CAPSULE_DRIFT`; restoring the verified bytes restores preflight.
- LOCAL_TEST Resource resolution writes only `resources/<resource-id>/` and
  `.reagent/resource-index.json`; tampering produces `RESOURCE_DRIFT` and
  blocks Experiment preflight until restored.
- Artifact input tampering makes scaffold preflight fail with materialized
  checksum drift; exact bytes restore it.
- existing F1E tests exercise GitHub/Hugging Face resolve as
  `RESOURCE_RESOLVER_NOT_IMPLEMENTED` with an instrumented network-call count
  of zero. Cloud never claims those metadata references are downloaded.

## P1 integration correction

The complete revision loop exposed one P1 recovery defect: after scaffold
finalization, adding Writing #2 and syncing caused the generic Capsule verifier
to reject legitimate content-addressed Artifact results, exact materialized
inputs and `memory/current-artifact.json` as undeclared files.

The verifier now follows the already-frozen Capsule contract: validated
content-addressed outputs are allowed only below `outputs/artifacts/`; dynamic
scaffold inputs are loaded from the immutable checksum-verified
`workflow/scaffold.json` requirement targets; current Artifact metadata is a
known mutable runtime file. Traversal, link, special-file, size, secret,
immutable-file and Skill checksum validation remain unchanged. The fix adds no
product capability or new authority and is directly covered by the complete
E2E's post-result sync.

## Web and CLI UX

- new real-browser F1F coverage confirms the four setup choices, pre-create
  scaffold disclosure, five current cards, three scaffold badges/warnings,
  exact Skill visibility, Experiment Resource boundary, Progress filter and
  Help limitations.
- Overview correctly recommends local setup/sync before Literature. It does
  not claim false research completion.
- current Workflow list/status, sync, Artifact refresh/materialize, Resource
  list/status/resolve and run/preflight paths are used by the qualifier.
- browser mutations remain Cloud metadata only; browser never writes local
  files. CLI never creates Project configuration independently of Cloud.

## User-friction diagnostics

- `CREATE_PROJECT_WEB_ACTIONS = 4` (open, enter metadata, choose/confirm preset)
- `WEB_MUTATIONS_REQUIRED = 18` in the maximal qualification including three
  Resource references, explicit bindings and Writing #2 creation
- `TERMINAL_COMMANDS_REQUIRED = 24` in the maximal drill including diagnostic
  status/recovery commands; reducing this was not allowed to blur Cloud/local
  authority
- `RAW_UUID_COPY_REQUIRED = 0` for normal flow; ambiguous same-type selection
  uses the friendly CLI-displayed exact command
- `MANUAL_INTERNAL_JSON_EDITS = 0`
- `DB_ACCESS_REQUIRED = 0` for the owner/user flow
- `PROVIDER_SECRET_ACCESS_REQUIRED = 0`
- `MANUAL_SKILL_INSTALL_REQUIRED = 0`
- `MANUAL_RESOURCE_INDEX_EDIT_REQUIRED = 0`
- `DEAD_ENDS_FOUND = 0` after the P1 sync correction

## Performance and security

- existing fixed-query scale covers 20 Workflow Instances and 1,000 Progress
  reports; PostgreSQL Artifact projection covers 20 producers and 1,000
  Artifacts with at most four SQL statements.
- Skill projection covers 100 Skill Definitions and repeated 20-Instance
  projections with one bulk versions/pins load; Resource projection covers 20
  Workflow Instances and 100 Resource references with stable pagination.
- path traversal, symlink, hardlink, special file, checksums, Skill/Artifact/
  Resource spoofing, cross-Project binding, request redaction and controlled
  readiness all passed full regression. No Redis/Celery or new infrastructure
  was introduced.

## Qualification results

- F1F complete-width focused and F1A–F1E relevant regression: `32 passed`
- isolated PostgreSQL full backend: `767 passed, 14 skipped`
- PostgreSQL F1F complete E2E/fresh-session reload: PASS (included above)
- physical PostgreSQL restart with complete state: PASS
- frontend Vitest: `17 files, 34 tests passed`
- Playwright existing product suite: `5 passed`; new F1F product-width spec:
  `1 passed`
- TypeScript: PASS; ESLint: PASS; production build: PASS
- Python compileall: PASS
- Alembic sole head/current `20260806_0017`; `check`: no drift
- git diff check: PASS

Skip audit: ten pre-existing dedicated historical-migration gates (B1, B2,
B4, B5, B6, B7, F1A, F1B, F1D, F1E), three pre-existing isolated destructive/
contract/research-v2 integration gates, and one owner-gated live OpenAlex test.
The ordinary PostgreSQL suite and new F1F PostgreSQL test ran. `F1F_NEW_SKIP = 0`.

The first production build attempt was rejected by the filesystem sandbox when
Turbopack tried to bind an internal local port; the same build passed outside
that restriction. The first two Playwright setup attempts diagnosed missing
test-only seeds/fake-proxy composition and two visibility assertions; the
canonical deterministic E2E profile and final assertions passed. These were
qualification-environment/test issues, not product defects.

## Product-width decisions

- `PROJECT_MANAGEMENT = PASS`
- `FIVE_WORKFLOW_SURFACE = PASS`
- `SKILL_MANAGEMENT_FOUNDATION = PASS`
- `SKILL_DELIVERY = PASS`
- `PROGRESS_CONTINUITY = PASS`
- `EXTERNAL_API_PROXY_INFRASTRUCTURE = PASS`
- `LOCAL_WORKSPACE = PASS`
- `AGENT_HARNESS_INTEGRATION = PASS`
- `WORKSPACE_CAPSULE_ARCHITECTURE = PASS`
- `DESIRED_MANIFEST = PASS`
- `PULL_SYNC = PASS`
- `INSTALLED_LOCK = PASS`
- `TYPED_ARTIFACT_HANDOFF = PASS`
- `SKILL_EXACT_PINS = PASS`
- `RESOURCE_REFERENCE_SHELL = PASS`
- `MULTI_WORKFLOW_PROGRESS = PASS`

Still intentionally deferred: full AG Admin, external/user Skill import,
substantive Writing/Review/Experiment cores, real GitHub/Hugging Face resolver,
multi-user auth, Workspace backup, live Provider qualification and public
deployment.

## Final assessment

`F1F_DATABASE_MIGRATION = NOT_REQUIRED`

`FULL_PRODUCT_SKELETON = PASS`

`PRODUCT_WIDTH_COMPLETE = YES`

`READY_FOR_OWNER_COMPLETE_PRODUCT_TEST = YES`

Owner handoff:

- `docs/getting-started/OWNER_COMPLETE_PRODUCT_TEST.md`
- `docs/getting-started/OWNER_TEST_OBSERVATIONS.md`

Next action is owner manual complete-product testing. No subsequent product
stage is selected or authorized by this report.
