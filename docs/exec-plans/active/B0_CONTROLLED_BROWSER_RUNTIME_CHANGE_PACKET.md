# B0 controlled browser runtime qualification change packet

> Completing this packet does not authorize implementation.

## 1. Identity and status

- Change ID / title: `B0_CONTROLLED_BROWSER_RUNTIME_QUALIFICATION`
- Author / date / baseline: Codex / 2026-08-14 / `main` at `3b792cbd1b5b28422a88b75f3b69c6e5f758c0d0`
- Git root/worktrees/status: repository root; one worktree; clean before packet creation.
- Migration/published baseline: static sole head `20260813_0021`; B0 affects no published Definition, Capsule, Skill, Artifact, Progress, or Registry identity.
- Packet status: `READY_FOR_IMPLEMENTATION_REVIEW`
- `IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED`

## 2. Intent and baseline

- Objective: qualify the smallest safe browser-accessible controlled runtime needed by later UX-A1, without implementing product capability or auditing current UX.
- Owner intent and user problem: establish reproducible browser evidence without owner data, a long-lived Workspace, live Providers, Real Core behavior, or confusion with an owner runtime.
- `PLAN_ALIGNMENT = PASS`: Cloud coordinates; Local Workspace executes; browser never writes Workspace; the controlled runtime is disposable and owner-data-free; Experiment 0.4 remains frozen and uninspected; B0 qualifies infrastructure only, implements no Real Core or frontend redesign, and precedes UX-A1.
- Approved sequence: H1B -> H2A -> B0 -> UX-A1. H2A stayed within two Skills/templates/routing/static validation; both Skills are committed and discovered in this fresh session.
- Current supported controlled path: `make controlled-start` -> `scripts/dev-start.sh` -> `isolated-controlled-test` FastAPI plus standalone Next.js on selected loopback ports; browser traffic uses the same-origin `/backend/*` rewrite.
- Current isolated qualification path: `scripts.run_isolated_qualification controlled-e2e` creates a guarded `reagent_qualification_<uuid>` PostgreSQL database, migrates it, copies frontend source with existing `node_modules`, selects loopback ports, starts controlled services, runs Playwright, validates fixture Projects, stops services, drops the database, and removes its temporary root.
- Existing E6 history: controlled Playwright has exercised real frontend/backend/PostgreSQL paths. It is baseline evidence only; it is not a B0 result because B0's seven-state report, fixture manifest, required viewports, and teardown proof do not yet exist.

### Confirmed capabilities

- Controlled backend profile positively enforces loopback PostgreSQL, fake provider/proxy, no live OpenAlex/key, empty CORS, absolute runtime roots, hidden API docs/Hosted routes, and `/ready` checks.
- Disposable DB creation, identity marker validation before mutation, exact-name drop, dynamic loopback port allocation, production frontend build/start, PID identity-aware local stop, and temporary roots already exist.
- `@playwright/test`, `playwright`, and `playwright-core` 1.61.1 resolve from existing `frontend/node_modules`; no installation is needed.
- Playwright declares one project named `chromium` but explicitly uses channel `chrome`. The configured expectation is installed Google Chrome, not the cached Playwright Chromium.
- The configured Google Chrome executable and a Playwright Chromium cache are present on this host. Neither was launched in this planning phase, so compatibility is not yet proved.
- This session advertises an approved in-app browser-control backend. It was not invoked because browser start is unauthorized in this phase.
- `frontend/test-results/`, `frontend/playwright-report/`, and repository `runtime_data/` are ignored; no ignore-rule change is needed.

### Unknown capabilities

- `BROWSER_BINARY_PRESENT`, launch compatibility, screenshot capture, console/network cleanliness, and all other runtime states remain `NOT_CHECKED` until B0 implementation.
- Current tests do not expose one B0 fixture manifest or one explicit disposable Workspace marker.
- Existing controlled startup identifies the backend profile, while the frontend proves its target by the build-time API URL and observed same-origin requests; B0 still needs one shared run/fixture identity asserted by the runner, real API, and rendered page.
- Existing H1/F1F browser journeys execute local Workflow/Capsule paths and therefore are evidence references, not reusable B0 fixtures.

## 3. Decisions and scope

- Authoritative sources: Owner request; `docs/PROJECT_DEVELOPMENT_PLAN.md`; ODR-009/010/011/013/014/015/016; ADR 0009, 0022, and 0029; `SOURCE_OF_TRUTH_POLICY.md`; `ENGINEERING_CHANGE_CONTRACT_SPEC.md`; `CONTROLLED_BROWSER_RUNTIME_SPEC.md`; and `ENGINEERING_HARNESS_IMPLEMENTATION_PLAN.md`.
- Implementation evidence: `Makefile`; `scripts/dev-start.sh`; `scripts/dev-stop.sh`; `scripts/run_isolated_qualification.py`; controlled deployment/readiness/disposable-DB code; frontend package/lock/Playwright config; current E2E and component fixtures; root/frontend ignore rules.
- Conflict `CONFLICT_VISIBLE_NON_BLOCKING`: the harness plan's embedded H2A record says Owner review/commit pending, while `main` contains `28fdfb2` and `3b792cb` and the worktree discovers both Skills. Git proves commit, not Owner acceptance. B0 planning may finish; implementation stops until the Owner confirms H2A acceptance.
- Precision finding, not a conflict: Playwright's project label is `chromium`, but channel `chrome` selects system Google Chrome. Do not claim a bundled/downloaded browser.
- Owner decisions: confirm H2A acceptance; approve the bounded fixture mapping; approve deletion-only screenshot handling or explicitly authorize ignored retention; separately authorize B0 implementation.
- In scope: extend only the existing isolated qualification harness; create a B0-specific deterministic fixture seeder and Playwright spec; add one stable Make target; produce temporary screenshots and a seven-state report.
- Non-goals: migration; product domain/API/persistence/frontend change; Core or Artifact contract change; Capsule/Registry publication; Real Experiment/Writing/Review; general fixtures; CI; visual regression; axe/WCAG framework; multi-browser; dependency/browser installation; UX redesign; owner/runtime acceptance.
- Deferred findings: `DEFERRED_NON_BLOCKING` — shared multi-user identity, live Provider testing, Claude qualification, full accessibility automation, visual baselines, and any UX defects discovered later by UX-A1.

## 4. Contract behavior

- Domain semantics: B0 data is synthetic qualification evidence, never owner or production state. Browser actions read/navigate only; fixture setup is a separate guarded application/persistence operation and never writes Workspace bytes.
- Operational transitions: `ABSENT -> DB_AND_PATHS_ALLOCATED -> MARKERS_VERIFIED -> MIGRATED -> FIXTURED -> BACKEND_READY -> FRONTEND_READY -> BROWSER_QUALIFIED -> TORN_DOWN`.
- Authority/idempotency: the runner owns transitions; one random run identity binds DB marker, temporary Workspace marker, fixture manifest, ports, screenshots, and report. Fixed fixture IDs/timestamps/checksums are deterministic inside the fresh database. A failed run is not resumed; retry starts with a new identity after verified teardown.
- Failure/retry: any pre-browser identity failure stops before browser launch. Browser/assertion failure proceeds directly to teardown. Teardown failure makes B0 fail and prohibits retry until the exact marked resources are reconciled.
- Product fixture states: one active synthetic Project with (1) completed Literature and output metadata, (2) blocked Idea with an unbound exact input, (3) Scaffold Writing awaiting owner action with an exact bound synthetic input, and (4) Review showing stale/incompatible local/Cloud installation evidence. No research execution occurs and scaffold maturity remains explicit.
- Additional presentation states: exact bound/unbound inputs, upload-pending/disagreement, loading, empty, API error, not-found, and narrow viewport. Use the real API for durable fixture states; transport interception may be used only for loading/API-error presentation and must not support backend-semantic claims.
- Artifact impact: only deterministic metadata/checksums in the disposable DB; no owner bytes, cloud Artifact bytes, implicit selection, sibling reads, or publication.
- API impact: unchanged. Seeder uses existing application/repository or public API boundaries; browser uses existing same-origin routes.
- Persistence impact: no migration/schema/seed publication. All rows exist only in the generated guarded database and are dropped.

## 5. Product and safety boundaries

- Topology: one qualification driver -> one marked disposable PostgreSQL DB + one temporary runtime root + one marked empty Workspace + one copied frontend tree -> loopback backend/frontend -> approved browser surface.
- Database isolation: require loopback admin URL selecting `postgres`/`template1`; create only `reagent_qualification_<32hex>`; write and verify exact marker/identity before migration, seed, browser, cleanup, and drop; protected names remain rejected.
- Workspace isolation: create under the runner's temporary root, outside Git and every configured owner path; write only a B0 marker/fixture manifest; run no root client, Capsule, Harness, sync, materialization, or research command; remove the root after process shutdown.
- Positive identity: scrub inherited owner/provider/ReAgent runtime variables without reading values, then set controlled values explicitly. Assert backend controlled-only invariants, exact DB identity, frontend same-origin target, fixture run ID visible through the real API/page, and a per-run port pair selected once and recorded.
- Owner/controlled separation: never read `.env`, owner config, Keychain, owner DB, or owner Workspace. Do not call the broad `make stop` path from B0; call the local PID-identity stop script against the exact temporary runtime directory.
- Browser surface: first try the available approved in-app browser controller; repository Playwright with its declared `chrome` channel is the repeatable fallback/qualification driver. Missing or incompatible browser blocks B0; no installation, update, alternate channel, or external service is allowed.
- Screenshots: capture `1440x900`, `1280x800`, and `390x844` with route/viewport/state/full-or-fold names under the temporary audit root. Delete on success by default. Retention, if Owner-approved, is limited to ignored `frontend/test-results/b0/<run-id>/` with a secret/payload scan and manifest.
- Teardown: `finally` stops the exact frontend/backend process trees, asserts both ports free, revalidates the DB marker, drops only that DB, removes Workspace/runtime/frontend-copy/audit paths, and reports every cleanup postcondition after success or failure.

## 6. Compatibility and delivery

- Compatibility/versioning: all product contracts are `UNCHANGED_COMPATIBLE`; the proposed work is test/orchestration-only. Historical immutable versions affected: none.
- Migration impact: none; migration head must remain `20260813_0021`.
- Rollback: before execution, revert only unpublished B0 harness/test files. After any run, rollback is cleanup of exact marked disposable resources, never deletion or rewrite of accepted user state. Cleanup ambiguity stops for bounded Owner review.

## 7. Implementation budget

- Expected files: `Makefile`; `scripts/run_isolated_qualification.py`; new `scripts/b0_controlled_fixtures.py`; new `frontend/tests/e2e/b0-controlled-runtime.spec.ts`.
- Limits: at most 4 changed files; 2 new, 2 modified, 0 deleted; at most 550 net new lines.
- No backend production, frontend route/component/type/config, dependency/lock, migration, Registry, Capsule, Artifact, Progress-contract, or documentation file is in the implementation budget.
- Scope expansion requires a packet amendment and explicit Owner approval; inability to represent the fixture states through current contracts is a stop, not frontend/backend implementation authority.

## 8. Alternatives and verification

- Rejected: persistent `make controlled-start` against an owner-selected DB; current H1/F1F Workflow-executing journeys; package declaration as binary proof; browser installation/update; external browser service; direct SQL from browser tests; mock-only frontend; Docker/CI/general fixture or visual framework.
- Reused commands/components: disposable DB guard and runner, `make controlled-start`, `scripts/dev-stop.sh`, existing Playwright executable/config, readiness and same-origin probes, existing E2E safety preflight, current ignored test-result paths.
- Stable future command: `make qualify-b0-browser` invoking the B0 subcommand only after implementation authorization.
- Seven required states: separately report `PLAYWRIGHT_PACKAGE_PRESENT`, `BROWSER_BINARY_PRESENT`, `CONTROLLED_BACKEND_REACHABLE`, `CONTROLLED_FRONTEND_REACHABLE`, `DATASET_VERIFIED_DISPOSABLE`, `SCREENSHOT_CAPTURE_PASS`, and `TEARDOWN_PASS` as PASS/FAIL/BLOCKED/NOT_CHECKED with evidence.
- Evidence claims: package/config/static baseline is E0; guard/helper tests may reach E1-E4; real controlled API plus browser plus verified disposable dataset reaches E6. Overall B0 PASS requires all seven states PASS at E6. No E7, E8, E9, real Core, long-lived compatibility, accessibility-conformance, or UX-quality claim is allowed.
- Verification: assert the shared run/fixture checksum, controlled profile invariants, exact API target/ports, real fixture states, required routes/viewports/screenshots, no page/console error except deliberate error-state case, no unexpected non-loopback request, basic landmark/heading/label/focus/overflow checks, and all teardown postconditions.
- Acceptance criteria: fixture manifest matches DB/API/page; browser never writes Workspace; completed/blocked/owner-action/stale-or-incompatible states render honestly; screenshots are named and policy-compliant; services and ports are gone; generated DB and temp roots are gone; Git shows only approved implementation files; all seven states PASS.
- Stop conditions: H2A acceptance unconfirmed; unsafe/missing admin DB; marker/path/port/API-target ambiguity; owner or credential environment cannot be proven excluded; browser binary launch fails; fixture needs owner data, Experiment 0.4, Real Core, implicit Artifact choice, sibling files, or product-source change; unexpected network; browser-to-Workspace write; teardown failure; dependency/install/update need; file/line budget expansion.

## 9. Authorization gate

- Packet approval: pending Owner review.
- `IMPLEMENTATION_AUTHORIZATION = NOT_GRANTED`
- Remaining blockers: Owner decisions above and a separate explicit B0 implementation authorization. `engineering-verification` is reserved for the later independently approved B0 acceptance phase.
