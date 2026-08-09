# NIGHT-F1D Skill Registry, version pins, and Capsule delivery

Date: 2026-08-09

Status: PASS — OWNER REVIEW READY

## ORIGINAL_PLAN_ALIGNMENT

`ORIGINAL_PLAN_ALIGNMENT = PASS`

The original plan requires Cloud Skill Library management, normalized Skill
content, exact Workflow requirements, delivery beside the Workflow template,
local `skills/`, and consumption by the existing Codex/Claude Code Harness.
F1D maps those goals to canonical Skill Definition/Version/pin persistence,
the existing `local-skill/v0.1` declarative format, immutable Capsule delivery,
and verified local Harness instructions. ReAgent still does not implement an
Agent execution engine.

Deferred original-plan portions are full AG Admin mutation UI, external Skill
import and user-created uploads. They require an authenticated identity/tenant
boundary and a broader executable-content trust policy that the controlled
deployment does not yet possess. Resource Registry/Binding, GitHub/Hugging Face,
marketplace behavior and real research cores were not implemented.

`AG_ADMIN_FOUNDATION = READY`

`AG_ADMIN_MULTI_USER_UI = DEFERRED_BY_IDENTITY_BOUNDARY`

## Baseline and scope

- branch/start: `main` at `61e17b6e7ee2f5982f22e56db4682a675754cb35`
- F1C final commit: verified ancestor
- initial worktree: clean; extra worktrees: none
- starting migration: sole `20260806_0015`
- recovered model: `CURRENT_SKILL_MODEL = EMBEDDED_ONLY`
- recovered content format: `local-skill/v0.1`, `skill.json` + `SKILL.md`
- no live Provider, `.env`, credentials, owner DB/Workspace, branch, worktree or push

## Domain, versions and trust

- canonical authorities: Skill Definition, immutable Skill Version, exact
  Workflow Definition Version Skill Pin
- production trust: reviewed repository built-ins only
- production Skills: Research Artifact Provenance 0.1.0 and Scaffold Core
  Safety 0.1.0
- supported content: bounded Markdown, JSON and plain text with normalized
  relative paths; traversal, absolute/backslash paths, collisions, oversized
  manifests, links, special files and executable payloads fail closed
- pins are exact version/checksum/order; there is no floating `latest`
- Writing, Review and Experiment 0.1.0 remain immutable; new 0.2.0 versions pin
  both Skills and remain `SCAFFOLD_CORE`
- existing Instances retain 0.1.0; new Instances and Full preset use 0.2.0

## Delivery and visibility

- Capsule compilation places exact content under
  `workflow/skills/<stable-key>/` and binds every byte into the Capsule checksum
- B4 sync installs the complete Capsule; no Skill daemon, separate download or
  second Installed Lock authority exists
- AGENT reads Capsule identity, exact pin manifests and each `SKILL.md` before
  the Workflow prompt; no arbitrary Workspace scan is permitted
- generic preflight rejects missing or tampered Skills and directs the user to
  restore/sync the verified Capsule
- bounded read-only `/skills` list/detail metadata APIs and exact Workflow/Instance
  Skill projections are available without per-card Skill requests
- Workflow UI shows names, exact versions and reviewed trust while keeping
  Skill presence separate from Workflow maturity
- existing operator CLI provides read-only list/show/verify; no network
  mutation endpoint or top-level marketplace navigation was added

## Migration and immutability

- revision: `20260806_0016`, down revision `20260806_0015`
- schema: Skill Definitions, Skill Versions and Workflow Version Skill Pins
- seeds: 2 Definitions, 2 immutable Versions, 6 exact pins, and 3 new scaffold
  Definition/Capsule 0.2.0 versions
- empty/base through 0016: PASS
- populated 0015 to 0016: PASS
- 0016 to 0015 to 0016: PASS with deterministic identities/checksums
- Alembic current: `20260806_0016`; sole head/check: PASS/no drift
- Literature Search, Idea Discovery and all scaffold 0.1.0 checksums: unchanged

## Qualification

- focused final Skill/API/H2: `24 passed`
- full backend, isolated PostgreSQL: `758 passed, 12 skipped`
- dedicated F1D migration cycle: `1 passed`
- frontend Vitest: `16 files, 33 tests passed`
- Playwright, local-development fake Provider: `5 passed`
- TypeScript: PASS; ESLint: PASS; production build: PASS
- Python compileall: PASS; git diff check: PASS
- old/new exact pin fixture, tamper, missing file, unsafe path, trust,
  deterministic bundle, current-version adoption and bounded-query tests: PASS

## Skip audit

Eight historical dedicated migration database gates (B1, B2, B4, B5, B6,
B7, F1A, F1B), three pre-existing isolated integration gates (destructive
demo, 9B-1 contract, 9A-2), and one explicit live OpenAlex gate were skipped in
the full run. The dedicated F1D migration gate was supplied and passed.

`F1D_NEW_SKIP = 0`

## Manual qualification

- A: new Full Research Project resolves skill-backed scaffold 0.2.0 Capsules;
  sync delivers both Skills without manual copying — PASS
- B: local Writing Skill tamper causes generic preflight to fail closed with
  restore/sync guidance — PASS
- C: existing explicit Writing 0.1.0 remains pinned; retire/add resolves 0.2.0
  with Skills — PASS
- D: fixture Workflow versions pinned to Skill 0.1.0 and 0.2.0 build exact,
  independent content rather than floating to current — PASS

## Deferred

- F1E: Resource Definition/Binding and deterministic local resolver shell
- F1F: complete product-width E2E
- Skill: authenticated AG Admin writes, user upload, external/network import,
  arbitrary executable content and marketplace
