# Owner Real Research Mode Safety Gate Repair

Date: 2026-08-11

Status: PASS — OWNER LOCAL REAL RESEARCH GATE OPEN

## Boundary

- `ORIGINAL_PLAN_ALIGNMENT = PASS`
- `OWNER_LOCAL_REAL_RESEARCH_GATE = OPEN`
- `R3D_PRODUCTION_PROVIDER_GATE = CLOSED`
- `MIGRATION_REQUIRED = NO`
- `LIVE_NETWORK_CALLS = 0`

This is a narrow owner-local security/integration repair. It changes no
Workflow research semantics, Artifact/Skill/Resource/Progress contract,
Capsule version, database schema, scaffold maturity, or public deployment
claim.

## Repair

`make dev` remains the canonical owner real-research startup. Its Backend child
receives the exported `REAGENT_OPENALEX_API_KEY`; its Next.js build/dev/server
children execute through a common provider-secret scrub wrapper. The generic
Workspace client now removes Provider, database, session, and Proxy credentials
before starting every Capsule. Literature and Idea Codex therefore inherit no
OpenAlex credential. OpenAlex credential-like assignments are rejected by both
Package compilation security and delivered-Capsule preflight, while variable
name mentions and `<your-key>` placeholders remain legal.

Every NORMAL Literature run prints a plain-language OpenAlex disclosure and
requires `continue-real-search`. A two-minute in-memory Backend grant is exact
Project/Package/Workflow checksum scoped and one-time. It is consumed before a
NORMAL session token is issued. Missing/cancelled/expired/replayed/tampered
consent, controlled-mode consent, and client attempts to select NORMAL fail
closed before a Provider call. DEMO remains deterministic and needs no
OpenAlex consent.

The empty selected-library validator is unchanged, but the generic error now
states that the materialized Literature result contains no included papers and
that Idea requires at least one selected paper.

## Offline NORMAL qualification

The product route used a real Full Research Project, downloaded bootstrap
client, five-Capsule sync, generic Workspace `run`, explicit terminal consent,
NORMAL server authorization, real `OpenAlexPaperSearchAdapter`, and a scripted
local transport returning OpenAlex-shaped responses. The interactive PTY
Harness performed two queries and produced three normalized selected records,
`REAL PROVIDER METADATA` output, a content-addressed
`selected-paper-library/v1`, bounded Progress, and Cloud acknowledgement.

The exact Literature Artifact was bound, indexed, checksum-materialized, and
consumed by the real generic Idea route. A deterministic no-network Harness
performed cross-paper synthesis, recorded an explicit selection, and produced
`selected-research-idea/v1` with exact source Artifact provenance. A NORMAL
resume regression proves that persisted completed queries are not repeated.
The synthetic secret sentinel was available to the real Backend adapter and
absent from frontend children/build output, generic Capsule children,
Literature/Idea Harnesses, Workspace files, Artifacts, Progress and logs.

## Privacy and residual risk

OpenAlex receives confirmed query text and standard request metadata through
the Backend. The owner PostgreSQL retains query checksums/lengths,
call/cost/rate evidence, and normalized Provider records; complete query plans,
memory, outputs, and Artifact bytes remain local. No automatic retention expiry
is promised. Literature is metadata plus optional abstract only; no full text
or PDF is retrieved.

Codex remains a general-purpose local Harness and may have network capability
according to local Codex settings. No OS-level egress sandbox or production
secret manager was added; the Provider key is unavailable to the Harness.

## Qualification

- focused session/Workspace/Literature/Idea/security: `102 passed`;
- offline full NORMAL Literature-to-Idea product route: `1 passed`;
- full Backend on generated PostgreSQL: `799 passed, 14 existing skips`;
- scripts/security/startup: `17 passed`;
- frontend Vitest: `17 files / 34 tests passed`;
- TypeScript and ESLint: passed;
- scrubbed production build and build-output sentinel scan: passed;
- isolated Playwright current/H1/F1F: `4 passed`;
- compileall, shell syntax, Alembic head/check and `git diff --check`: passed.

Two generated `reagent_qualification_<uuid>` databases were marker-verified
and dropped. Read-only owner DB snapshots were eight Projects before and after,
with the exact owner Project present both times. The owner-controlled runtime
on port 8000 remained healthy and was never stopped. No new skip was added.

The owner should create a separate Full Research Project such as
`real-research-test-1`; the existing controlled `project1` and Workspace remain
untouched.
