+# Owner Writing and Review interactive bootstrap repair

Date: 2026-08-13

The owner audit confirmed that current Writing and Review Capsule 0.2.0 each
copied the historical scaffold runner and invoked bare `codex`. Root and
Workflow AGENT contracts plus pinned prompts supplied standing instructions but
could not create the initial user turn. The repair remains aligned with the
five-Workflow Meta Research Agent plan: Codex is the local Harness, while Skills
remain exact versioned Capsule-delivered rules rather than owner-run sessions.

Writing and Review Definition 0.2.0, prompts, validators, Artifact requirements
and outputs, Progress, maturity, and exact Skill pins remain unchanged.
Historical Capsule 0.2.0 checksums remain
`sha256:84896829db7ee1cb6b24a5e10bf6705beac93fa42857d0dc08d4916e0243ee0c`
(Writing) and
`sha256:9c3e4e8f065914393f5dc786b36d07bbbdc962f381ea70f125353429c48089f1`
(Review); their shared runner remains 20,876 bytes with SHA-256
`280a3cfaa2e8c4a1599a10e9e2052e270d992d8e1943d28e6b33270c707d8332`.
Existing Instances remain pinned.

Seed-only migration `20260813_0020` publishes Writing Capsule 0.3.0 checksum
`sha256:38e6a3d9bb0938fd9f0723767bc7d471973f2ca4d515f9c4097c2ddf3743f377`
and Review Capsule 0.3.0 checksum
`sha256:c497f21cc4876ae1aea19f56cb4491a4f2baf74657e0590bab41fe3056616c25`.
Only the version-specific `reagent_local.py` differs from the 0.2 rendered file
set. The new runner preflights Codex, uses explicit workspace-write/on-request/
no-alt-screen/cwd flags, scrubs credentials, forwards termination safely, and
passes an independent bounded positional instruction.

Writing automatically begins `REAGENT WRITING — INPUT_REVIEW`, identifies exact
Idea/Literature and optional Experiment/Review/prior-draft provenance, detects a
revision round when explicitly bound, and discloses `SCAFFOLD_CORE`. Review
automatically begins `REAGENT REVIEW — INPUT_REVIEW`, identifies the exact
Draft and optional evidence, and discloses the no-peer-review/no-acceptance
boundary. Frozen scaffold finalizers still reject fabricated citations,
experiments/results, metrics, novelty, substantive manuscript/review claims, or
missing placeholder markers; Review remains `INSUFFICIENT_EVIDENCE` with empty
major/minor issue lists.

Qualification used synthetic Artifacts only. Prompt-enforcing fakes reject bare
launches. Direct transport, Workspace-root generic commands, PTY startup,
progress upload/recovery, and the full Writing #1 -> Review #1 -> Writing #2
chain passed with immutable Draft A/Review A and exact Draft B provenance. Real
Codex 0.146.0 PTYs visibly received both positional INPUT_REVIEW turns before
safe interruption; no startup phrase, owner data, or OpenAlex call was used.

Final qualification: focused regression `47 passed` plus added pin tests; full
backend on generated disposable PostgreSQL passed `831 passed, 14 existing
skips`; scripts/owner runtime tests `43 passed`; frontend Vitest `17 files /
34 tests`, TypeScript, ESLint and production build passed; controlled
PostgreSQL Playwright `2 passed`; owner-runtime restart/secret isolation passed;
compileall, Alembic sole head/check at `20260813_0020`, and diff check passed.
Every generated database and temporary Capsule was removed. Nothing was pushed.

Owner continuation remains Scaffold UX testing. Apply migration 0020 and restart,
replace only the downloaded Workspace-root client if it predates this repair,
retire/add only any existing unstarted Writing/Review Capsule 0.2 Instances,
then explicitly bind and run Writing #1 -> Review #1 -> Writing #2. Do not begin
Real Writing, Real Review, or Skill work.
