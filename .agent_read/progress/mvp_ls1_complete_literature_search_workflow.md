# MVP-LS1 Complete Literature Search Workflow

Date: 2026-08-06

Status: **PASS_WITH_WARNINGS — READY FOR OWNER ACCEPTANCE**

## Baseline and authority

MVP-LS1 began from clean `main` at exact commit
`9d76c7b89ce124829fd76741a676d7bb50a4eb43`
(`MVP-I1: load local dotenv configuration on startup`). The teacher-aligned
cloud-management/local-folder/Codex-execution boundary remains authoritative.

```text
CURRENT_OWNER_TEST = ABORTED
CURRENT_ABORTED_REPORT_UPLOAD = NOT_AUTHORIZED
```

The previous external fictional Package/report was excluded from evidence and
was neither uploaded nor reused.
The phase began with `LITERATURE_SEARCH_AUTONOMOUS_WORKFLOW =
IMPLEMENTATION_IN_PROGRESS` and `V0_1_STATE = NOT_READY`; the terminal states
below follow only from the new implementation and qualification evidence.

## Implementation

Accepted ADR 0019 defines the complete single-round contract. Generated
Packages now carry `python reagent_local.py run .`, fixed Codex planning and
synthesis boundaries, a configurable bounded policy of two or three queries,
three maximum calls, five results per call, 15 retained candidates, and a
three-to-six-paper target. Normal mode is OpenAlex-only and stops if that
adapter is unavailable. Explicit `--mode demo` is fake-only and requires
fictional labels. Exact Provider identity/DOI deduplication, query provenance,
exclusion reasons, insufficient-evidence handling, and metadata/abstract-only
claims are validated.

The four local output contracts cover the search plan, candidate library,
selected library, and literature report. Package validation now recognizes
only bounded `.DS_Store` metadata, validates mutable context/search/report/
receipt state, enforces one report for round 1, and rejects undeclared or
malformed evidence.

The additive local-session API uses existing Proxy tokens. A session is
literal-loopback, 15-minute, active/unrevoked/unexpired, and exactly scoped to
project, Package identity/checksum, Workflow version/checksum, adapter and
capability. It grants bounded search plus progress upload/read; an upload-only
session has zero search operations. Token plaintext stays in launcher memory,
is stripped from the Codex environment, and is revoked. Migration
`20260806_0007` persists only the local capability tuple and zero-operation
allowance; no task state or Progress schema changed.

One untouched Package runs round 1. A valid report without a receipt performs
upload-only idempotent recovery. A verified receipt prevents repetition.
Partial outputs without a valid report fail closed without overwrite.
Automatic upload verifies receipt, report history, and Project Progress
Projection before storing one safe local receipt. Full query/candidate/report/
context state stays local; the existing v0.2 report exposes only a bounded
summary/count/limitation/artifact-checksum view.

The frontend now provides a task-oriented Start here overview, four-step Quick
Start, dedicated project Guide, action-first Package page, and six-state
Progress/result surface with counts, limitations, artifacts, warnings, next
action, immutable report history, and upload receipt. Technical identities are
preserved but visually secondary.

## Qualification

A fresh isolated PostgreSQL 18.1 cluster passed migration head/current/no-drift
at `20260806_0007` and downgrade/re-upgrade. Real Uvicorn, Next.js, PostgreSQL,
browser HTTP, and an external Package completed the deterministic path from
project creation through fake Codex-equivalent one-round outputs, two fake
Proxy operations, automatic upload, browser-visible COMPLETED summary, and
restart continuity. Repeating the command did not repeat the round.

The E2E was rerun after checking the launcher against the installed Codex CLI.
Final aggregate SQL retained two independent project/report/projection/revoked-
token sets, four fake operations, and zero Provider call/cost, WorkflowRun,
StepRun, ExecutionEvent, Hosted ProviderOperation, or AgentSession rows.
External network was denied and OpenAlex was disabled.

Verification: focused matrix 323 passed; full backend 575 passed with four
unrelated gated integration skips; compileall passed; frontend typecheck,
10-file/13-test Vitest, ESLint, production build, and real-stack Playwright E2E
passed. Relevant PostgreSQL/Proxy/OpenAlex tests had zero skip.

## Complete changed-file inventory

- governance/evidence: `.agent_read/context.md`,
  `.agent_read/decisions/0019-complete-autonomous-literature-search-round.md`,
  `.agent_read/progress/mvp_ls1_complete_literature_search_workflow.md`,
  `README.md`, `docs/PROJECT_DEVELOPMENT_PLAN.md`,
  `docs/acceptance/V0_1_LITERATURE_SEARCH_WORKFLOW_QUALIFICATION.md`,
  `docs/acceptance/V0_1_OWNER_MANUAL_ACCEPTANCE_CHECKLIST.md`,
  `docs/architecture/LOCAL_V0_1_PRODUCT_INTEGRATION.md`, and
  `docs/getting-started/LOCAL_V0_1.md`;
- local-session/API boundary: `backend/api/app.py`,
  `backend/api/routers/__init__.py`,
  `backend/api/routers/local_sessions.py`,
  `backend/api/schemas/__init__.py`,
  `backend/api/schemas/local_sessions.py`,
  `backend/application/errors.py`, `backend/local_sessions/__init__.py`,
  `backend/local_sessions/service.py`,
  `backend/local_sessions/tests/__init__.py`, and
  `backend/local_sessions/tests/test_service.py`;
- Proxy/persistence and migration: `backend/cloud_api_proxy/contracts.py`,
  `backend/cloud_api_proxy/service.py`, `backend/cloud_api_proxy/sql.py`,
  `backend/cloud_api_proxy/tests/test_contracts.py`,
  `backend/cloud_api_proxy/tests/test_service.py`,
  `backend/database/orm/models.py`,
  `backend/database/migrations/versions/20260806_0007_local_workflow_sessions.py`,
  `backend/database/tests/conftest.py`,
  `backend/database/tests/test_cloud_api_proxy_openalex_postgresql.py`,
  `backend/database/tests/test_cloud_api_proxy_postgresql.py`, and
  `backend/database/tests/test_postgresql_persistence.py`;
- project/Package/one-round controller:
  `backend/local_projects/service.py`,
  `backend/local_projects/tests/test_api.py`,
  `backend/local_projects/tests/test_service.py`,
  `backend/workflow_packages/compiler.py`,
  `backend/workflow_packages/contracts.py`,
  `backend/workflow_packages/local_runner.py`,
  `backend/workflow_packages/package_validator.py`,
  `backend/workflow_packages/template.py`,
  `backend/workflow_packages/tests/fake_codex_cli.py`,
  `backend/workflow_packages/tests/test_compiler.py`,
  `backend/workflow_packages/tests/test_literature_outputs.py`,
  `backend/workflow_packages/tests/test_local_runner.py`, and
  `backend/workflow_packages/tests/test_state_and_boundary.py`;
- frontend product and verification: `frontend/README.md`,
  `frontend/app/globals.css`, `frontend/app/local-guide/page.tsx`,
  `frontend/app/projects/[id]/guide/page.tsx`,
  `frontend/components/local-project-detail.tsx`,
  `frontend/components/local-project-list.tsx`,
  `frontend/components/package-product-panel.tsx`,
  `frontend/components/progress-product-panel.tsx`,
  `frontend/components/project-guide.tsx`,
  `frontend/tests/e2e/local-v0-1.spec.ts`, `frontend/tests/fixtures.ts`,
  `frontend/tests/local-project-detail.test.tsx`,
  `frontend/tests/local-project-list.test.tsx`,
  `frontend/tests/package-product-panel.test.tsx`,
  `frontend/tests/progress-product-panel.test.tsx`, and
  `frontend/tests/project-guide.test.tsx`;
- startup: `scripts/dev-start.sh`.

No other tracked or untracked file is part of the phase.

## State

```text
MVP_LS1_IMPLEMENTATION = PASS_WITH_WARNINGS
ABORTED_OWNER_TEST_EXCLUDED = PASS
LITERATURE_SEARCH_REAL_PROVIDER_PATH = PASS
LITERATURE_SEARCH_NO_FAKE_FALLBACK = PASS
LITERATURE_SEARCH_OUTPUTS = PASS
ONE_COMMAND_LOCAL_EXECUTION = PASS
LOCAL_SESSION_SECURITY = PASS
CODEX_ONE_ROUND_AUTOMATION = PASS
AUTOMATIC_PROGRESS_UPLOAD = PASS
UPLOAD_ONLY_RETRY = PASS
PROJECT_QUICK_START_UI = PASS
PROJECT_GUIDE_PAGE = PASS
PACKAGE_PAGE_UX = PASS
PROGRESS_RESULT_UX = PASS
MVP_RUNTIME_HOSTED_BOUNDARY = PASS
LITERATURE_SEARCH_AUTONOMOUS_WORKFLOW = READY_FOR_OWNER_ACCEPTANCE
V0_1_STATE = OWNER_ACCEPTANCE_PENDING
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```

Warnings: no owner-authorized real OpenAlex LS1 end-to-end run occurred in this
phase; OpenAlex stays experimental/default-off; evidence is metadata/abstract-
only; Claude Code is untested; only Literature Search round 1 exists; local
single-user V0.1 is not public/production deployment. Wait for owner review.
