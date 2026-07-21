# ReAgent frontend

Next.js App Router prototype for launching and monitoring ReAgent research workflows.

## Local development

1. Copy `.env.example` to `.env.local` if the FastAPI backend is not available at `http://127.0.0.1:8000`.
2. Start the backend with its configured PostgreSQL database.
3. Run `npm run dev` in this directory and open `http://localhost:3000`.

Browser requests use `/backend/*`; the Next.js rewrite forwards them to `REAGENT_API_URL`, avoiding a separate browser CORS dependency.

## Checks

- `npm test`
- `npm run lint`
- `npm run build`
- `npm run test:e2e` against a running real backend/PostgreSQL stack

The E2E project uses system Chrome by default and never mocks API responses.
See the repository-root `DEMO.md` for full-stack startup, database reset, and
Playwright browser setup.
