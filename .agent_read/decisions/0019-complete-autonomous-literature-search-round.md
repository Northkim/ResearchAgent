# 0019: Complete autonomous Literature Search round and local-session boundary

- Status: Accepted
- Date: 2026-08-06

## Context

MVP-I exposed teacher-aligned project, Package, and Progress surfaces, but an
owner still had to direct Codex through multiple steps and upload a report
manually. That infrastructure was not a complete Literature Search Agent. The
aborted owner test and its report are not authorized acceptance evidence.

The local folder must remain authoritative for concrete research state and
Codex must perform research. At the same time, a normal round needs bounded
OpenAlex metadata and must return a useful summary to the product without
putting a key or durable capability in the Package or moving the complete
workspace into cloud state.

## Decision

One extracted Literature Search Package provides the supported command
`python reagent_local.py run .`. It validates immutable identities, opens a
15-minute loopback-only local session scoped to the exact project, Package
checksum, Workflow version/checksum, adapter, and capabilities, invokes Codex
at fixed planning and synthesis boundaries, performs one bounded round,
finalizes one native Progress Report, uploads it idempotently, verifies the
receipt/history/projection, revokes the session, and stops.

Normal mode is bound only to the accepted OpenAlex adapter and never falls back
to fake results. Explicit `--mode demo` is bound only to the deterministic fake
adapter and labels every research value fictional. At most three query variants
are issued, each returns at most five Works, no more than 15 candidates are
retained, and the target selection is three to six papers when evidence is
sufficient. Deduplication uses exact provider identity and DOI. V0.1 uses
metadata and available abstracts only.

The required local artifacts are `outputs/search_plan.md`,
`outputs/candidate_papers.json`, `outputs/selected_papers.json`, and
`outputs/literature_search_report.md`. Queries, candidate/selected libraries,
full report, and concrete context remain local. The unchanged Progress Report
v0.2 contract carries a bounded status/count/summary/limitation/artifact-
checksum view to Cloud Project State.

The local session adds `progress.upload/v0.2` and `progress.read/v0.1`
capabilities to the existing Proxy token scope. An upload-only token has zero
Proxy-operation allowance. Bearer plaintext is returned once, kept in launcher
memory, removed from the Codex subprocess environment, never written into the
Package, and revoked after use. Endpoints mount only in explicit V0.1 local mode
and require literal loopback.

Recovery is state-based: an untouched Package runs round 1; a valid report
without a receipt takes upload-only recovery; a verified receipt prevents a
repeat; partial outputs without a valid report fail closed without overwrite.
Exactly one report is permitted for round 1.

## Consequences

The owner can launch one complete local Literature Search round with one
Package command and view its verified summary in the frontend. Search,
screening, synthesis, complete outputs, and context stay local. The backend
issues capabilities, transports normalized metadata, persists the existing
bounded Progress Report, and renders Cloud Project State; it does not invoke
Codex, rank papers, synthesize findings, create Hosted runs, or resume work.

Migration `20260806_0007` stores only the local-session capability tuple and
permits a zero-operation token; it adds no concrete task state and changes no
Progress Report or Provider result schema. OpenAlex remains experimental and
disabled by default. A real end-to-end LS1 run requires separate owner
authorization and was not performed by this decision.

Only Literature Search is implemented. Claude Code, other Workflows, public
deployment, production security, and R3D remain deferred.

## Alternatives considered

- Manual multi-message Codex instructions and manual upload were rejected as
  incomplete product integration.
- Backend or Hosted Runtime execution was rejected because it violates the
  teacher-aligned local-Harness boundary.
- Bundling tokens or a key in the Package was rejected because Packages are
  portable research state, not credential containers.
- Silent fake fallback was rejected because fictional metadata cannot support
  normal-mode research conclusions.
- Uploading the complete workspace was rejected because Cloud Project State
  needs a bounded progress summary, not concrete Local Task State.
