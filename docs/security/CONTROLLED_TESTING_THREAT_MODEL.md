# Controlled Testing Threat Model

## Scope and security model

H2 supports `ISOLATED_CONTROLLED_TESTER_INSTANCE`: one tester, one loopback
frontend/backend pair, one database, one Cloud runtime directory, and one or
more tester-owned Local Workspaces. Access from another host must traverse an
operator-managed authenticated private tunnel or gateway with TLS. The
application has no user identity or Project ownership model.

This is not a public-production or shared multi-tenant threat model. CORS,
Request IDs, checksums, and UUIDs are not authorization.

## Protected assets

- operator-only database and optional Provider credentials;
- Project, Workflow, Manifest, Progress, acknowledgement, and provenance data;
- Cloud Package/Progress content stored under configured runtime roots;
- local Workspace identity, research outputs, memory, Artifact bytes, indexes,
  and materialization receipts;
- immutable reviewed Capsule packages and their checksums;
- availability and bounded cost of Provider operations.

## Trust boundaries and controls

### Browser and Cloud API

The production-built frontend calls the API through the same-origin `/backend`
rewrite. Controlled startup binds both processes to `127.0.0.1`, configures no
cross-origin access, hides API docs and legacy Hosted execution routes, bounds
request bodies to 1 MiB by default, and emits clickjacking, MIME-sniffing,
referrer, permissions, and frame CSP headers. No cookies or browser session
authentication exist, so CSRF is not the primary present risk; unauthorized
network access is.

An authenticated tunnel/gateway must expose only the frontend and isolate one
tester from every other database/process set. TLS termination belongs at that
gateway. Proxy headers are ignored by the loopback application.

### Project and Workflow metadata

B2-B7 database/service validation rejects cross-Project Workflow, Progress,
Artifact, and dependency spoofing. Idempotency, optimistic Manifest revisions,
immutable checksums, and PostgreSQL constraints remain active. These controls
protect consistency after an instance is reached; they do not establish who
may reach it.

### Provider boundary

The controlled profile fails startup unless the deterministic fake Provider
and bounded fake Proxy are selected. It rejects OpenAlex/live flags and even
the presence of an OpenAlex key. Provider adapters use fixed reviewed URLs,
bounded operations, 10-15 second deadlines, response-size limits, safe error
details, and no caller-supplied arbitrary URL. The reviewed path has no SSRF
surface. Live Provider abuse/cost qualification is not authorized by H2.

### Cloud and local files

Download routes resolve fixed reviewed content or scoped IDs, never a supplied
filesystem path. B3/B4/B6 archive, relative-path, symlink, hardlink, special
file, traversal, checksum, staging, and atomic publication protections remain
in force. The browser cannot write a Workspace, run Codex, sync, or materialize.
The local client performs those operations explicitly under the Workspace
advisory lock.

Cloud stores metadata/provenance and bounded application content, not a Local
Workspace backup or complete Artifact bytes. A lost Workspace cannot be rebuilt
from PostgreSQL.

### Configuration, logs, and diagnostics

Controlled startup validates the deployment profile, loopback PostgreSQL,
dedicated database name, fake Provider, disabled live flags, empty CORS list,
body-size range, and absolute runtime roots. Provider and database secrets are
never passed to the browser or Local Workspace.

Every response carries a Request ID. Controlled logs record route templates,
status, duration, bounded object IDs, error code, and exception class only.
Uvicorn access logging is disabled in this profile so query strings and
research values are not copied into logs. User responses omit tracebacks,
database URLs, filesystem paths, and exception text.

## Threat and failure analysis

| Threat/failure | H2 mitigation | Residual risk |
| --- | --- | --- |
| Unauthorized API caller | Loopback bind; authenticated private access layer; isolated instance | App has no identity; exposure or tunnel misconfiguration compromises that instance |
| Cross-Project spoofing | Existing service validation, FKs, checksums, Project-scoped lookups | Any caller inside the instance may use its Projects |
| Malicious archive or path | Size/file-count bounds, root checks, traversal/symlink/hardlink/special-file rejection, atomic install | Reviewed unsigned built-ins remain a trust decision |
| Provider proxy abuse | Fake-only controlled profile; fixed operations/URLs; timeout and response bounds | Live Provider is not qualified or enabled |
| Secret leakage | No frontend Provider credential; fail-closed config; sanitized responses/logs; no body logging | Operator environment and dump storage remain host responsibilities |
| Oversized request/resource exhaustion | 1 MiB default ASGI body limit; bounded archives and Provider responses | No distributed limiter; one tester can still consume their isolated resources |
| Database loss/corruption | Dedicated DB, migrations/readiness, qualified pg_dump/pg_restore, restart recovery | Scheduling, encryption, retention, and off-host copies are operator responsibilities |
| Local Workspace loss | Explicit documentation and tester retention | Cloud cannot restore research bytes or local memory |
| Artifact/file drift | Immutable references, checksum verification, Artifact Index, receipts, fail-closed materialization | User must retain or reproduce correct local bytes |
| Operator misconfiguration | Controlled validation and readiness; no traffic on mismatch | Firewall, tunnel auth, TLS, storage permissions, and PostgreSQL policy are external |
| Legacy Hosted execution exposure | Hosted run/approval/workflow/artifact routes and API docs not mounted in controlled profile | Legacy code remains available in local-development profile |

## Accepted H2 risks

- One tester is trusted within their own isolated API/database.
- No application-layer account, tenant, ownership, or audit actor identity
  exists.
- There is no distributed rate limiter, WAF, secret-manager vendor, automated
  database backup scheduler, or public TLS configuration.
- The local client is an unsigned reviewed Python file; distribution is
  checksum-labelled but not OS code-signed or published to PyPI.
- PostgreSQL backup alone does not include Local Workspaces or every configured
  Cloud filesystem byte.
- Live Provider behavior and cost are not executed in H2.

These risks block a shared instance for mutually untrusted users and block
public production. They are acceptable only for small, supervised, isolated
controlled tests behind an authenticated private access layer.
