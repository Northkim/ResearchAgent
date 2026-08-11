# 0036: Owner-local runtime configuration and Keychain startup

- Status: Accepted
- Date: 2026-08-11
- Supersedes: the owner-startup-command portion of ADR 0035; its Provider
  consent and secret-boundary decisions remain unchanged

## Context

ADR 0035 opened the single-owner local real-research safety gate, but its
canonical startup still required manually exporting the owner database URL,
OpenAlex credential, and experimental Proxy switch before every `make dev`.
That procedure preserved credential custody but exposed developer-level
configuration as normal owner UX. ReAgent had no user-level runtime config or
OS secret-store abstraction. Persistent Provider consent remains forbidden.

## Decision

Keep three separate authorities. `make controlled-start` remains the
deterministic DEMO test runtime. `make dev` remains explicit developer startup.
`make owner-start` becomes the canonical owner-local NORMAL-capable startup and
uses the same local-development application semantics without using repository
`.env` as owner authority.

`make owner-setup` writes one strict, versioned, bounded TOML document under
the user's ReAgent config directory. It contains only loopback database
identity, loopback Backend/Frontend ports, profile and Provider availability.
It is atomically replaced, owner-only, symlink-rejecting, schema-validated, and
cannot represent passwords, secrets, Projects, Workflows, or research state.

An `OwnerSecretStore` boundary keeps startup infrastructure independent from
research domains. The current implementation is macOS-only and uses the
Keychain service `com.reagent.owner-local-real.openalex`, account
`openalex-api-key`. Initial and replacement writes pass a final bare `-w` to
the macOS `security` tool so the OS prompts; secret values never enter argv or
shell history. Startup retrieves the value inside the trusted helper and
constructs separate child environments: only FastAPI receives it. Frontend and
all downstream Workspace/Harness scrubbing remain intact.

`make owner-doctor` performs bounded config, database, migration, Keychain
presence and port diagnostics. Owner startup checks but never upgrades the
database. `make stop` uses the existing PID/identity enforcement for both
developer/controlled and owner runtime records, and never stops PostgreSQL or
removes config, Keychain data, or database state.

## Consequences

After one setup, a fresh terminal can run `make owner-start` without any
ReAgent database, OpenAlex, or Proxy environment exports. Credential
persistence remains distinct from per-NORMAL-run `continue-real-search`
consent. Automated qualification replaces both config location and Keychain
command, uses a marker-guarded disposable PostgreSQL database, and never reads
the owner's config, Keychain, or persistent database.

Owner secure startup is currently macOS-only. Password-bearing PostgreSQL
connections, Linux Secret Service, Windows Credential Manager, hosted secret
management, multi-user auth and public production remain outside this
decision. `OWNER_LOCAL_REAL_RESEARCH_GATE` remains open and
`R3D_PRODUCTION_PROVIDER_GATE` remains closed.

## Alternatives considered

- Reusing repository `.env` was rejected because it couples owner, developer
  and automated runtime authority and risks secret persistence near Git.
- Exporting `security find-generic-password -w` into the parent shell was
  rejected because the interactive shell must not receive the credential.
- Storing the Provider key or database password in TOML was rejected.
- Changing `make dev` semantics was rejected because developer startup remains
  a separate intentional mode.
- Adding a browser settings/secret UI or durable consent model was rejected as
  production/multi-user scope expansion.
