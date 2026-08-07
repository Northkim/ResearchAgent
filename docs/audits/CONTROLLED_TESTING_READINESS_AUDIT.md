# H2 Controlled Testing Readiness Audit

Date: 2026-08-07

## Conclusion

The repository's actual security model was `LOCAL_SINGLE_USER`: FastAPI had no
user/tenant identity, Projects had no owner, Next.js used a same-origin proxy,
and local execution remained outside the browser. H2 does not turn this into a
SaaS. It adds a fail-closed `isolated-controlled-test` profile and qualifies
one isolated instance per tester behind an operator-managed authenticated
private access layer.

Shared use by mutually untrusted testers is blocked by the identity/ownership
model. Public production is not ready. No new Workflow or database migration
was added.

Finding totals: **P0 0; P1 8; P2 6; P3 4**. Seven P1 findings were fixed. The
remaining P1 is the owner-level shared multi-user identity decision and does
not block isolated controlled testing.

## P0

None. The H1 product journey was complete on loopback, and no H2 audit finding
required changing Artifact, Workflow, trust, or Cloud/local semantics.

## P1

1. **Open — owner decision:** `backend/database/orm.py` and Project DTOs contain
   no user/owner/tenant identity. `backend/api/app.py` has no authentication.
   Any network caller reaching one instance may mutate its Projects. Shared
   mutually-untrusted testing is unsafe; use one isolated instance per tester.
2. **Fixed:** `scripts/dev-start.sh` previously had only development startup.
   The new controlled mode validates a dedicated loopback database, fake-only
   Provider flags, absolute runtime roots, empty CORS, and production frontend,
   and binds both processes to loopback.
3. **Fixed:** `GET /health` previously reported process life without database,
   migration, or production Registry state. `GET /ready` now checks all three
   and fails 503 without contacting a Provider.
4. **Fixed:** development API docs and legacy Hosted run/approval routes were
   mounted by default. `backend/api/app.py` omits them in controlled mode while
   preserving the local-development compatibility contract.
5. **Fixed:** API responses/logs had no reliable correlation. The operational
   ASGI boundary now supplies `X-Request-ID` and metadata-only structured events
   with route templates, duration, status, and stable error codes.
6. **Fixed:** unexpected exceptions could produce a generic Uvicorn traceback
   and existing access logs included raw query strings. Controlled mode catches
   pre-response failures, records only exception class, disables access logs,
   and returns a stable Request-ID-bearing body.
7. **Fixed:** JSON request bodies were not globally bounded. Controlled and
   development profiles now enforce a configurable 64 KiB–8 MiB limit, 1 MiB
   by default, before application parsing and while streaming.
8. **Fixed:** there was no repeatable production-build/backup/onboarding path,
   and a tester needed repository access to obtain `reagent_local.py`. The
   fixed `/local-client/reagent_local.py` download, Help/Overview links,
   controlled startup, runbook, threat model, and tester guide close that gap.

## P2

1. No distributed rate limiter exists. Process isolation, body/archive limits,
   Provider deadlines, and one trusted tester per instance are the accepted H2
   boundary.
2. Database dump scheduling, encryption, retention, and off-host copies remain
   operator responsibilities; H2 qualifies commands and recovery, not a
   backup service.
3. PostgreSQL backup does not include configured Cloud Package/Progress
   filesystem roots. The runbook explicitly requires a separate operator copy
   when those Cloud-managed bytes are needed.
4. The standard-library local client is checksum-labelled but unsigned, not on
   PyPI, and the current advisory lock is Unix-oriented. Controlled testers use
   the reviewed download and supported Python/macOS environment.
5. Live Provider controlled testing is unexecuted. Fixed URL, time/response
   limits, redaction, persistence, and offline contracts pass, but owner
   authorization is still required.
6. Supply-chain checks are bounded to lock-file build, `pip check`, offline npm
   audit, and tests. No Python vulnerability database client is installed, and
   no external advisory database was authorized.

## P3

1. Application user identity, Project ownership, tenants, invitations, and
   audit actors.
2. Public TLS/domain/WAF, managed secrets, billing, and quota product.
3. Centralized metrics/tracing/log aggregation and distributed rate limiting.
4. Signed local-client installers, automated encrypted backup scheduling, and
   managed deployment orchestration.

## Audited surfaces

- deployment/start/stop: `scripts/dev-start.sh`, `scripts/dev-stop.sh`,
  `Makefile`, `frontend/next.config.ts`;
- configuration: `backend/api/deployment.py`, `config/*.example`, composition;
- network/browser: app router mounting, same-origin frontend rewrite, CORS,
  API/frontend headers, API docs and Hosted routes;
- mutations: Project, Workflow create/retire, Progress, sync acknowledgement,
  Artifact binding/materialization-plan and downloads, with B2-B7 scope tests;
- Provider: local fake and OpenAlex composition, fixed transports, timeout,
  response/cost/privacy contracts, SSRF input surface, feature flags;
- operations: readiness, migration startup, PostgreSQL pool/reconnect,
  structured logs, Request ID, shutdown, pg_dump/pg_restore;
- local boundary: fixed client distribution, Workspace explicit sync/run,
  checksums, locks, receipts, no browser filesystem access;
- onboarding: README, Project Help/Overview, tester guide and operator runbook.

## Qualification evidence

- controlled frontend/backend listened only on `127.0.0.1`; API docs and
  `/runs` returned 404; cross-origin preflight received no allow-origin;
- `/health` remained 200 during database downtime while `/ready` returned 503;
  business requests returned sanitized 500 plus Request ID; PostgreSQL restart
  recovered without restarting the application;
- readiness rejected a synthetic database at migration `20260806_0012`;
- a representative B7 database was dumped, dropped, recreated, restored, and
  reconnected. Project, Workflow, Progress, Artifact, binding, checksums, and
  Manifest revision remained exact; a second full H1 journey created new
  Progress after restore;
- deterministic 25-step controlled deployment journey and all failure drills
  completed without direct DB insertion for product steps or internal JSON
  edits;
- full backend: 700 passed, one expected live-Provider skip; Vitest 31 passed;
  Playwright 5 passed; typecheck, ESLint, production build, compileall, and
  Alembic no-drift passed.

