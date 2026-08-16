# FE-M task-first production frontend integration

- Date: 2026-08-15
- Baseline: `main` at `6d21d785a8976f15d7f73613a63d4c5ccc7b0c50`
- Status: `PASS_FE_M_DESKTOP_READY_FOR_OWNER_REVIEW`
- Migration sole head: `20260815_0026` (unchanged)

## Product implementation

The production frontend now uses the accepted task-first IA: Projects, Project
Overview, exact Workflow Detail, Outputs, and Activity. Projects is a searchable,
compact attention list. Overview leads with one Current Research State, and
Workflow Detail exposes exact inputs, current stage/actor/blocker, one valid next
action, expected/latest Output, recent Activity, contextual Resources, and
collapsed Technical Details.

The backend owns additive, derived Project attention and Workflow action
projections. They reuse authoritative Workflow Instance, Progress, continuation,
readiness, installation, Resource, and Artifact state without persistence. The
generic projection represents Experiment, Writing, Review, and Revision stages;
the frontend does not implement per-Core lifecycle machines.

## In-phase corrections

- Updated readiness publication checks from stale migration 0021 to the current
  immutable 0026 Real Core publications.
- Reconciled exact historical Skill-pin purpose text used by fresh Project
  foundation replay with the immutable W1/R1/W2 publication facts.
- Recognized the frozen “Awaiting owner action” Progress wording as an Owner
  checkpoint in the derived presentation projection.
- Corrected responsive long-name wrapping, 1280-width list reflow, mobile
  first-viewport density, and versioned Artifact-to-human Output labels.
- Corrected only FE-M fixture/assertion composition for stale-to-current public
  sync acknowledgement and the existing isolation runner markers.

## Verification

- Backend focused projection/API/foundation tests: 36 passed.
- Frontend: 17 files / 36 tests passed; TypeScript and ESLint passed.
- Next.js 16.2.10 production build passed with exact Outputs and Workflow Detail
  routes present.
- FE-M controlled Playwright journey: 1 passed against a generated disposable
  PostgreSQL database, then database dropped.
- Viewports: 1440x900, 1280x800, 390x844; nine ignored review screenshots saved.
- Assertions covered COMPLETED, BLOCKED, AWAITING_OWNER_ACTION,
  ACKNOWLEDGED_STALE, exact Output, actor, blocker, primary action, no fatal page
  error, no external request, no horizontal overflow, and no browser Workspace
  mutation.

## Boundaries and next action

No migration, Core capability, Artifact schema, Workflow/Capsule version,
scientific/evidence contract, hosted executor, or browser Workspace write was
added. Owner data and owner Workspaces were not used. The standalone in-app
browser was unavailable, so visual evidence comes from the repository-native
controlled Chromium runtime and locally inspected screenshots.

Owner visual review is still required. After acceptance, the safe next phase is
Q1 Focused Release Qualification; do not begin it automatically.

## Owner-reference desktop correction

The Owner rejected the prior FE-M visual/content layer and supplied three
1440x900 references plus a supporting standalone HTML reference. Mandatory
preflight visually inspected all three PNGs before production frontend source.
The accepted engineering foundation and its existing dirty working set were
preserved; the correction changed no backend production file or migration.

Projects now exposes only Project/topic, current step, concise status/reason,
updated time, and one specific action. Overview uses one compact next-step panel
and keeps Workflow progress, latest Output, and recent Activity in the first
viewport. Workflow Detail uses a specific attention/task/reason/action strip,
compact relevant Inputs, expected/latest Output and Activity, with Run locally,
input management, Resources, and Technical Details collapsed by default. The
sidebar, cream/forest identity, serif hierarchy, density, spacing, and action
placement now follow the approved references.

The controlled fixture accepts optional human-readable presentation names while
retaining B0 defaults. FE-M screenshots use `Urban drainage control study`,
`ResearchAgent architecture study`, and `Maritime video monitoring`; isolation
runner markers are created only after screenshot capture and are not review UI.
Synthetic fixture state is not described as real research evidence.

Final verification:

- `VERIFIER_INDEPENDENCE = LIMITED` because the same Codex session implemented
  and verified the correction.
- TypeScript, ESLint, and all 17 Vitest files / 36 tests passed.
- Next.js production build passed with the canonical Overview, Workflow Detail,
  Outputs, and Activity routes.
- Controlled browser E6 passed at 1440x900 and 1280x800 using real Next.js,
  FastAPI, PostgreSQL, and Chrome against a marked disposable database.
- Browser assertions covered realistic names, no raw Project ID heading, one
  specific primary action, rejected-copy absence, collapsed Technical Details,
  canonical routes, no fatal error, no external request, no overflow, and no
  browser-to-Workspace write.
- The disposable database was dropped and controlled services stopped.
- Exactly three ignored final screenshots exist under
  `.agent_read/tmp/fe-m-desktop-final-review/`.
- Highest evidence is E6 `CONTROLLED_BROWSER`; no E9 Owner visual acceptance is
  claimed, and no E7/E8 evidence was required for this presentation-only phase.

The desktop correction used the ten-file hard limit: five production frontend
files, three focused frontend test files, one controlled fixture script, and one
controlled browser spec. Context/progress updates reuse the pre-existing FE-M
handoff files. No ADR was added because no architecture decision changed.

## Controlled Owner-review state coherence correction

- Status: `PASS_FE_M_DESKTOP_COHERENT_READY_FOR_OWNER_REVIEW`
- Accepted desktop layout/style: unchanged
- Newly corrected implementation files: four
- Backend production / migrations / Core contracts: unchanged

The FE-M-only fixture scenario now uses existing exact Artifact and dependency
semantics to represent one coherent Project. Literature Search completes with a
selected-paper-library Artifact; that exact Artifact is bound to Idea Discovery,
which completes with a selected-research-idea Artifact; both exact Artifacts are
bound to Writing. Writing remains BLOCKED at the recognized OWNER review
checkpoint, so all three production screens recommend `Review outline` while
required inputs are Ready and Experiment is optional and not provided. The
default B0 fixture behavior remains unchanged.

Copy-only production changes preserve layout: primary dates are concise without
prominent UTC timestamps, the Writing description is natural product language,
the task panel names the six-section outline, and the optional Experiment input
states `Optional · Not provided`.

Verification evidence:

- `VERIFIER_INDEPENDENCE = LIMITED` (same session implemented and verified).
- Python syntax and `git diff --check`: passed.
- TypeScript and ESLint: passed.
- Vitest: 17 files / 36 tests passed.
- E6 controlled browser: 1 passed at 1440x900 and 1280x800 against real
  Next.js/FastAPI/Chromium and disposable PostgreSQL; database dropped.
- Assertions covered the exact three bindings, upstream COMPLETED states,
  Writing OWNER action, consistent `Review outline` actions, latest exact selected
  idea Output, Ready required inputs, optional Experiment, no Idea blocker, no raw
  ID heading, collapsed Technical Details, canonical routes, no fatal page error,
  no unexpected external request, and no browser-to-Workspace write.
- Exactly three ignored 1440x900 screenshots were regenerated and visually
  inspected in `.agent_read/tmp/fe-m-desktop-final-review/`.

No ADR was added because no architecture decision changed. E9 Owner visual review
remains pending. Q1 was not started.

## Owner acceptance and release closure (2026-08-16)

The Owner subsequently accepted Projects, Project Overview, and Workflow Detail
without further visual or structural changes. FE-M is frozen as
`OWNER_ACCEPTED`; its coherent controlled state is Literature Search completed,
Idea Discovery completed, Writing awaiting Owner outline approval with required
inputs Ready, and optional Experiment not provided.

Final Q1 qualified clean committed candidate
`35a961d7251ebbb3faedfbed446f12b6a0fea44c`, and the Owner approved that exact
candidate for `CONTROLLED_LOCAL_SINGLE_OWNER`. The earlier pending-review and
“Q1 not started” statements above remain historical phase records and are
superseded by `.agent_read/progress/2026-08-16_final_owner_release_handoff.md`.
