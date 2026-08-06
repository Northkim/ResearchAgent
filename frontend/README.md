# ReAgent V0.1 frontend

Next.js App Router product surface for the teacher-aligned local workflow:
create a project, download its Literature Search Package, work in the external
folder with interactive Codex through one bounded command, confirm the search
plan and screening, type `finish`, automatically upload its Progress Report,
and view cloud progress. Explicit `--auto` remains available for deterministic
unattended qualification.

## Local development

Use `make dev` from the repository root and open
`http://127.0.0.1:3000/projects`. See
`docs/getting-started/LOCAL_V0_1.md` for the supported full-stack sequence.

For frontend-only development, set `REAGENT_API_URL` if FastAPI is not at
`http://127.0.0.1:8000`, then run `npm run dev -- --hostname 127.0.0.1`.

Browser requests use `/backend/*`; the Next.js rewrite forwards them to `REAGENT_API_URL`, avoiding a separate browser CORS dependency.

## Checks

- `npm test`
- `npm run typecheck`
- `npm run lint`
- `npm run build`
- `npx playwright test tests/e2e/local-v0-1.spec.ts` against a running real
  backend/PostgreSQL stack

The V0.1 E2E test uses system Chrome, real loopback HTTP, and real PostgreSQL;
it does not mock API responses or invoke a Provider. Preserved Hosted E2E tests
are historical/internal coverage and are not V0.1 product acceptance evidence.
