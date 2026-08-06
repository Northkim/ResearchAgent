# V0.1 Owner Manual Acceptance Checklist

Target duration: approximately 10 minutes after PostgreSQL and repository
dependencies are installed.

Current state: **IMPLEMENTATION QUALIFIED — OWNER ACCEPTANCE PENDING**.

Use only localhost and a fictional/public topic. Do not use the legacy Hosted
pages as substitutes, and do not enable a live Provider for this checklist.

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
   Confirm it tells Codex to treat the folder as authoritative task state,
   write only declared paths, finalize one Progress Report, and upload only by
   an explicit later action. Confirm no credential is included.
6. **Validate the Package.** In the extracted folder run
   `python validate_package.py --root .`; expect a passing result.
7. **Create and upload one fictional Progress Report.** Follow the bundled
   `progress_report.py` instructions, validate again, then run the explicit
   upload command in `docs/getting-started/LOCAL_V0_1.md`. Do not rely on
   automatic synchronization.
8. **View progress.** Refresh the project Progress page. Confirm project name,
   Workflow, execution round, status, completed work, current state, next
   action, outputs, warnings/errors, and the new report-history receipt.
9. **Restart application services.** Run `make stop`, confirm the application
   ports release, and run `make dev` again against the same PostgreSQL data.
10. **Confirm continuity.** Reopen the project. Confirm Package metadata,
    progress projection, and report history remain unchanged and no duplicate
    report appears. The downloaded external Package must also remain unchanged.

The owner does not need to inspect PostgreSQL manually.

## Optional deterministic demonstration

An operator may issue a short-lived fake-adapter capability outside Git and the
Package, then use the provider-neutral client for one fictional
`paper.search/v0.1` request and exact replay. This is optional and must make no
external Provider call. Full Proxy operation detail is not required in the
frontend.

## Known warnings

- Claude Code is Experimental / Untested; Codex CLI is the supported Harness.
- OpenAlex is experimental and disabled by default.
- Progress Report upload is explicit and manual.
- Literature Search is the only Workflow.
- V0.1 is local, single-user software and is not accepted for public or
  production deployment.

## Out of scope

Production authentication, OAuth/SSO, multi-user authorization, HTTPS
termination, proof of possession, production secret management, workers,
queues, paid Provider activity, failover, more Providers or Workflows,
automatic Progress synchronization, Hosted research execution, cloud LLM
research, and production deployment are not part of V0.1.
