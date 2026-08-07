# 0029: Isolated controlled testing security boundary

- Status: Accepted
- Date: 2026-08-07

## Context

NIGHT-H2 audited deployment, security, recovery, and onboarding after B1-B7 and
H1. The product has no user identity, Project owner, tenant, or authenticated
browser/API session. Project-scoped database constraints prevent object
spoofing but do not decide which human caller may reach an instance. Browser
traffic is same-origin, local Workspace operations are explicit, and local
research bytes must remain outside Cloud.

Three to ten controlled users can be evaluated without inventing an unapproved
SaaS identity architecture only if their Cloud state and network access are
isolated. Development routes, live Provider configuration, raw exception logs,
and permissive network exposure are not acceptable in that mode.

## Decision

The first controlled-user topology is one isolated tester instance per tester:
one dedicated PostgreSQL database, runtime directory, backend/frontend port
pair, and tester-owned Local Workspace. Backend and frontend bind only to
loopback. Remote access must go through an operator-managed authenticated
private tunnel or gateway with TLS, and only the frontend may be exposed.

The `isolated-controlled-test` application profile is fail closed. It requires
a named loopback PostgreSQL database, explicit absolute Cloud runtime roots,
the deterministic fake Provider and Proxy, same-origin browser access with no
CORS origins, and no OpenAlex/live flag or key. It hides API documentation and
legacy Hosted execution routes, bounds request bodies, returns Request IDs and
security headers, and emits metadata-only structured logs without Uvicorn
access-query logging.

Liveness means process life. Readiness additionally requires PostgreSQL,
exact Alembic head `20260806_0013`, and the reviewed production Literature
Search/Idea Discovery/dependency Registry records. Startup retains the existing
single-operator `alembic upgrade head` contract before serving traffic; schema
mismatch or dependency loss fails readiness.

PostgreSQL dumps cover Cloud database metadata and provenance, not Local
Workspaces or research Artifact bytes. Configured Cloud filesystem content also
requires a separate operator backup when byte recovery is desired. Browser,
sync, materialization, local Harness, and Workspace ownership boundaries do not
change.

Shared use by mutually untrusted testers is not authorized. Adding application
identity, Project ownership, tenancy, sessions, or an auth vendor requires a
new owner decision and migration. Live Provider execution also remains a
separate authorization gate.

## Consequences

Small supervised tests can run reproducibly without giving testers Provider or
database credentials or repository access. Operators have actionable
readiness, correlation IDs, sanitized errors, backup/restore instructions, and
a graceful restart path. Existing local-development and legacy compatibility
tests remain available but are not exposed in controlled mode.

The topology costs one process/database allocation per tester and relies on an
external authenticated private access layer. It is not horizontally shared,
public-production ready, or a substitute for auth. CORS and UUIDs must never be
treated as authorization. No database migration or new production Workflow is
introduced by H2.

## Alternatives considered

- A shared no-auth instance was rejected because Project scoping does not
  establish caller ownership.
- Adding Auth0, Clerk, OAuth/JWT, sessions, user tables, or tenants was rejected
  because the owner did not authorize an identity product or ownership
  migration.
- Direct public binding was rejected because the app has no identity and H2
  does not provide TLS/firewall/WAF policy.
- Docker/Kubernetes, Redis rate limiting, Celery, and a monitoring stack were
  rejected as unnecessary infrastructure for the isolated 3-10 tester scope.
- Enabling live OpenAlex was rejected because H2 explicitly prohibits live
  Provider calls and credentials.
