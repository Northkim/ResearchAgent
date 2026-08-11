# 0035: Owner-local real Provider consent and secret boundary

- Status: Accepted
- Date: 2026-08-11

## Context

The reviewed Literature and Idea cores already support a server-authorized
NORMAL OpenAlex route, but an owner-local real run was not safe to recommend.
The `make dev` parent environment could pass the OpenAlex credential to the
Next.js process, the generic Workspace launcher did not remove it from every
Capsule, and no enforced acknowledgement preceded the first third-party query.
Public production remains outside the approved product boundary.

## Decision

Keep `make dev` as the canonical single-owner, loopback NORMAL entry. Pass
`REAGENT_OPENALEX_API_KEY` only to the Backend child and remove Provider
credentials from every frontend, generic Capsule, Literature, Idea, scaffold,
and Codex child environment. Reject credential-like OpenAlex assignments in
compiled or Workspace-delivered Package content while allowing variable-name
documentation and explicit placeholders.

Require every NORMAL Literature run to display the bounded OpenAlex disclosure
and receive the exact phrase `continue-real-search`. The loopback Backend
records a two-minute, exact Project/Package/Workflow-checksum grant in process
memory and consumes it once when the matching NORMAL scoped session opens.
Server configuration remains the NORMAL/DEMO authority; controlled deployment
cannot record or consume a real-Provider grant. Consent is per run, not a
durable preference, and adds no persistence model or migration.

## Consequences

An owner can use real metadata and available abstracts through the Backend
Proxy without putting the credential in the Workspace, Capsule, Codex,
frontend, browser, Artifact, Progress, or local research files. Cancellation,
expiry, identity drift, replay, controlled-mode requests, or a missing adapter
fail before a Provider session/call. Complete query text still goes to OpenAlex
and remains in the local query plan; Cloud persists only bounded query evidence
and normalized Provider records under the existing retention behavior.

This opens only `OWNER_LOCAL_REAL_RESEARCH_GATE`. Codex may retain arbitrary
network capability under the owner's local Codex configuration, although it
does not receive the Provider credential. Authentication, production secret
management/rotation, formal retention policy, public privacy UX, stronger
Harness isolation, and production Provider acceptance remain required, so
`R3D_PRODUCTION_PROVIDER_GATE` stays closed.

## Alternatives considered

- Putting the key in repository `.env`, Workspace metadata, Capsule files, or
  Harness input was rejected because it violates Backend credential custody.
- Treating `make dev` as implicit consent was rejected because the owner must
  see the third-party disclosure before the first query.
- A permanent consent row was rejected because per-run in-memory authorization
  satisfies the owner-local gate without adding a database domain or migration.
- A client-supplied boolean/hidden flag was rejected because it could bypass
  server-authorized mode and would not establish an explicit human action.
- A new deployment architecture was rejected; the existing local-development
  Backend, frontend, scoped session, Proxy, and generic launcher remain in use.
