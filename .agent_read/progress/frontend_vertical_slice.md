# Phase 8A: Frontend Vertical Slice

Date: 2026-07-21

## Scope and outcome

Phase 8A adds a functional web prototype in `frontend/` for the complete ReAgent control flow:

1. discover a workflow;
2. create and execute a run;
3. monitor run and step status;
4. inspect the ordered execution-event timeline;
5. approve or reject a pending human decision.

The backend was not modified. The frontend consumes the stable Phase 7B HTTP contract and keeps backend lifecycle rules out of UI components.

## Frontend architecture

- **Framework:** Next.js 16 App Router, React 19, and TypeScript.
- **Styling:** Tailwind CSS 4 plus responsive application styles in `app/globals.css`.
- **Data layer:** TanStack React Query owns queries, polling, mutations, cache updates, and cross-page invalidation.
- **Transport:** `api/client.ts` is the only frontend module that calls `fetch`. It exposes typed methods and normalizes backend error envelopes as `ApiError`.
- **Contract types:** `types/api.ts` models workflow definitions, runs, step attempts, execution events, approvals, pagination, and mutation DTOs.
- **Backend routing:** browser calls target same-origin `/backend/*`; `next.config.ts` rewrites those paths to `REAGENT_API_URL` (default `http://127.0.0.1:8000`). This keeps local setup simple without requiring backend CORS changes.
- **Rendering boundary:** route files provide App Router page shells; interactive/data-driven components are client components beneath the root Query provider.
- **Refresh behavior:** active run details and timelines poll every 3 seconds; pending approvals poll every 5 seconds. Mutations invalidate all affected run, approval, workflow, and event queries.

The dependency flow is:

`Next.js pages -> React Query hooks -> typed API client -> FastAPI HTTP contract`

No frontend code imports backend Python modules or accesses persistence directly.

## Pages implemented

### Dashboard — `/`

- available workflow summary;
- recent paginated runs;
- status badges;
- pending-approval count and navigation to approval work.

### Workflow catalog — `/workflows`

- consumes the backend catalog;
- lets the user select a workflow and edit its top-level initial inputs;
- creates the run and immediately submits execution;
- navigates to the new run detail page;
- includes a deterministic guided approval/search/summary definition when the persisted catalog is empty, allowing a fresh development database to bootstrap its first workflow.

### Run detail — `/runs/[id]`

- displays workflow/run identity, lifecycle status, version, creation/update times, and final outputs;
- displays ordered workflow steps and the latest attempt state;
- displays the execution timeline returned by the backend;
- polls while work can still change;
- provides an explicit resume action for yielded runs.

### Approvals — `/approvals`

- pending and all-status filters;
- request context, policy/role, expiry, and current status;
- optional reviewer reason;
- approve and reject actions with idempotency keys;
- success feedback and synchronized query invalidation.

## API integration

The typed client consumes:

- `GET /workflows`
- `GET /runs?status=&offset=&limit=`
- `POST /runs`
- `GET /runs/{id}`
- `POST /runs/{id}/resume`
- `GET /runs/{id}/events`
- `GET /approvals?status=&offset=&limit=`
- `POST /approvals/{id}/approve`
- `POST /approvals/{id}/reject`

Creating from the catalog is intentionally a two-request application flow: create the durable run, then submit its execution. Approval decisions use the request fingerprint required by the backend for approve and refresh all related read models after either decision.

## Tests and verification

Executed from `frontend/`:

- `npm test` — 4 test files passed, 4 tests passed.
- `npm run lint` — passed with no lint errors.
- `npm run build` — passed under Next.js 16.2.10; static pages generated and `/runs/[id]` compiled as a dynamic route.
- `npm run dev` plus an HTTP request to `http://localhost:3000/` — returned HTTP 200.

The tests cover:

- workflow list rendering and selection callback;
- run status and step progress rendering;
- ordered event timeline rendering;
- approve/reject interaction payloads and disabled mutation state.

A graphical browser was not available in the execution session, so the local entry point was verified over HTTP rather than with screenshots or interactive visual QA.

## Files introduced

- App routes and application chrome under `frontend/app/`.
- Reusable UI/state components under `frontend/components/`.
- Typed transport and React Query hooks under `frontend/api/`.
- providers, formatters, and the bootstrap definition under `frontend/lib/`.
- API contract types under `frontend/types/`.
- Vitest/Testing Library setup, fixtures, and four component tests under `frontend/tests/`.
- Next.js, Tailwind, TypeScript, ESLint, Vitest, environment, and package configuration at the `frontend/` root.

## Remaining limitations

- This is a local/development prototype, not a deployed frontend.
- Backend, migrated PostgreSQL, and frontend must currently be started separately.
- There is no authentication, authorization, project chooser, or user-derived approval identity; the prototype uses fixed development identities.
- Execution and approval updates use polling rather than push delivery.
- The current Skill registry is deterministic/fake; no real research provider or LLM is integrated.
- Artifacts are metadata-only at the backend and have no frontend content or download experience.
- There is no workflow publication/admin interface; the bootstrap workflow only solves first-run discoverability for the prototype.
- Component tests use typed fixtures; a full create-to-approval-to-completion browser test against FastAPI/PostgreSQL is still needed.
- Accessibility, cross-browser, responsive-device, error-observability, and load testing have not yet been completed.

## Recommended next step

Create a reproducible full-stack demo environment and one browser end-to-end test for the entire vertical slice. Seed/publish the guided workflow, run PostgreSQL/FastAPI/Next.js together, and verify create -> wait for approval -> approve -> complete -> inspect events. This will turn the working frontend/backend pieces into a reliable stakeholder demo before expanding visual polish or product surface area.
