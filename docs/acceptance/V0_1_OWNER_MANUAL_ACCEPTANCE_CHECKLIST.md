# V0.1 Owner Manual Acceptance Checklist

Target duration after the blocking gaps are corrected: approximately 10
minutes.

Current status: **NOT EXECUTABLE END TO END — MVP-A0 IS BLOCKED**.

Do not use the existing Hosted demo actions as substitutes. Do not use a real
Provider credential for this checklist. The owner should not need to inspect
PostgreSQL manually.

## Ten-minute checklist

1. **Start V0.1 locally — BLOCKED.** Run the supported localhost startup
   command or short sequence. It must configure local PostgreSQL, apply
   migrations, and start FastAPI and Next.js with displayed local URLs. No such
   complete V0.1 procedure exists at this baseline.
2. **Open the browser — WORKING IN PART.** Confirm the frontend loads on
   localhost. The current page loads, but it is the Hosted research-operations
   prototype rather than the V0.1 local-product home.
3. **Create one Literature Search project — BLOCKED.** Enter a project name and
   a fictional public topic, then select Literature Search. The required
   project UI/API does not exist.
4. **Download its Workflow Package — BLOCKED.** Generate the Package and save
   the ZIP outside the repository. The compiler works from the CLI, but no
   frontend generation/download action exists.
5. **Inspect Package instructions — COMPONENT WORKING.** In a Package produced
   by the committed compiler, verify that `AGENT.md` directs Codex to validate
   the Package, write only declared local state, finalize one Progress Report,
   and upload explicitly. Claude Code is optional and remains untested.
6. **Validate the Package — COMPONENT WORKING.** Run its bundled validator in
   the extracted folder. Expect a passing checksum result. Do not place a
   credential, database URL, or private path in the folder.
7. **Upload one fictional Progress Report — COMPONENT WORKING.** Use the
   Package helper to finalize a native report, validate it offline, and use the
   committed explicit upload client. Expect one accepted receipt. This remains
   a manual local-client step, not automatic synchronization.
8. **View progress in the browser — BLOCKED.** Confirm project name, Workflow,
   round, status, completed work, current state, next action, outputs,
   warnings/errors, and report history. No corresponding frontend view exists.
9. **Restart local services — WORKING IN PART.** Stop frontend, backend, and the
   dedicated local PostgreSQL service using the documented shutdown procedure,
   then restart them. Backend continuity passed the audit; a complete supported
   V0.1 shutdown/cleanup sequence is not documented.
10. **Confirm project and progress remain — BLOCKED.** The project, Package
    metadata, history, and projection must remain visible with no duplicate or
    missing report. Backend report bytes and projection survive restart, but
    the required frontend surfaces are absent.

## Optional checks

- Issue a short-lived fake-Provider capability and submit one fictional local
  request through the provider-neutral client; exact replay should return the
  same Proxy operation with zero external Provider call.
- Inspect the downloaded ZIP checksum shown by the product once that UI exists.

## Known warnings

- The current primary frontend starts/resumes Hosted Workflow runs and must not
  be used as the V0.1 research path.
- Standalone frontend typechecking currently fails in test files even though
  unit tests, lint, and the production build pass.
- Claude Code is Experimental / Untested.
- R3C accepted only OpenAlex and retains its documented warnings.

## Out of scope

Public deployment, production authentication, multi-user authorization, OAuth
or SSO, HTTPS termination, proof of possession, production secret management,
paid Provider activity, failover, multiple Providers, additional Workflows,
automatic Progress Report synchronization, Hosted research execution, and
cloud LLM research work are not part of V0.1 acceptance.
