# V0.1 Owner Manual Acceptance Checklist

Target duration: approximately 10 minutes after PostgreSQL and repository
dependencies are installed.

Current state: **INTERACTIVE WORKFLOW QUALIFIED — OWNER ACCEPTANCE PENDING**.

Use only localhost and a fictional/public topic. Do not use the legacy Hosted
pages as substitutes. A real OpenAlex run requires separate explicit owner
authorization and server-side capability; the deterministic path below uses
explicit demo mode.

## Ten-minute checklist

1. **Start V0.1 locally.** After the one-time creation of a dedicated loopback
   database and ignored root `.env`, run `make dev` with no repeated export.
   Confirm that the printed FastAPI and Next.js readiness checks pass without
   displaying the database URL.
2. **Open the browser.** Visit `http://127.0.0.1:3000/projects`. Confirm that
   the primary navigation is Projects, New project, and Local guide, with no
   Hosted run/resume action.
3. **Create one project.** Enter a project name and fictional/public research
   topic. Confirm Literature Search is fixed and creation opens a project
   detail page without starting research.
4. **Generate and download the Package.** Open Package, generate it, note the
   displayed Package ID and checksum, and download the ZIP outside Git.
5. **Inspect the local instructions.** Extract the ZIP and read `AGENT.md`.
   Confirm it identifies the folder as authoritative, names the four outputs,
   limits evidence to metadata/abstracts, and includes no credential.
6. **Run one deterministic interactive round.** From the extracted folder run
   `python reagent_local.py run . --mode demo`. Confirm the launcher shows six
   stages and opens Codex in the current terminal. Review and confirm the
   search plan, inspect the candidate-screening summary, ask a bounded question
   or revision if desired, then type `finish`. Confirm fictional evidence is
   labelled, the search session closes, a fresh upload-only session is opened
   only after finalization, the projection verifies, and both phases are
   cleaned up.
7. **Inspect the local results.** Confirm the four declared output files, one
   append-only Progress Report, and one verified receipt exist. Run the same
   command again and confirm it reports the round already uploaded rather than
   rerunning it.
8. **View progress.** Refresh the project Progress page. Confirm project name,
   Workflow, completed state, concise summary, query/candidate/selected counts,
   evidence limitation, output names/checksums, warnings/errors, next action,
   and immutable report receipt/history.
9. **Restart application services.** Run `make stop`, confirm the application
   ports release, and run `make dev` again against the same PostgreSQL data.
10. **Confirm continuity.** Reopen the project. Confirm Package metadata,
    progress projection, and report history remain unchanged and no duplicate
    report appears. The downloaded external Package must also remain unchanged.

The owner does not need to inspect PostgreSQL manually.

## Optional owner-authorized normal mode

After separately authorizing real OpenAlex use, start the local product with the
experimental OpenAlex adapter and server-side key, then run
`python reagent_local.py run .`. Normal mode stops if the adapter is unavailable
and never uses fictional fallback. Do not put the key or token in the Package.
Use `--auto` only when explicitly choosing unattended execution.

## Known warnings

- Claude Code is Experimental / Untested; Codex CLI is the supported Harness.
- OpenAlex is experimental and disabled by default.
- Progress Report upload is automatic only after the local round and remains
  idempotent; it uses a fresh exact-report session and does not upload the
  complete research workspace. If the receipt is missing, rerun the same
  Package command—do not download a new Package for recovery.
- `Ctrl+C` preserves valid local files, revokes the session, and uploads no
  incomplete report. `--resume` continues partial work; a confirmed
  `--restart-round` removes only round-scoped mutable artifacts.
- Literature Search is the only Workflow.
- V0.1 is local, single-user software and is not accepted for public or
  production deployment.

## Out of scope

Production authentication, OAuth/SSO, multi-user authorization, HTTPS
termination, proof of possession, production secret management, workers,
queues, paid Provider activity, failover, more Providers or Workflows,
Hosted research execution, cloud LLM research, and production deployment are
not part of V0.1.
