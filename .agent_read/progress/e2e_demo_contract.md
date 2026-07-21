# Phase 8B: End-to-End Demo Contract

- Date: 2026-07-21
- Status: Frozen for Phase 8B implementation
- Architecture contract: `.agent_read/progress/architecture_contract.md`

## 1. Demo workflow identity and version

- Workflow ID: `guided-literature-review`
- Workflow version: `1.0.0`
- Workflow schema: `reagent/v1alpha1`
- Display name: `Guided literature review`
- Canonical definition hash: `2e58bc1702f0393230c7f0e76d64f4b35684b709abf0597352498d508f45457f`
- Canonical fixture: `demo/workflows/guided_literature_review.v1.json`

The `(workflow ID, version)` pair is immutable. Seeding the same canonical document is a no-op; finding different content under the same identity is a hard failure.

## 2. Required user inputs

The workflow requires one string input:

- `query`: the literature topic to investigate.

The deterministic demonstration value is `persistent research agents`. The catalog exposes this as the default, and the browser flow lets the user confirm or replace it before launch.

The development-only frontend supplies `prototype-project`, `prototype-user`, and `deterministic-agent@1.0.0` for the currently unauthenticated project, actor, and agent-profile references.

## 3. Workflow steps

1. `search` — root Skill step that maps `${inputs.query}` to the paper-search query.
2. `approve_sources` — approval step depending on `search`; execution must durably pause here.
3. `summarize` — Skill step depending on `approve_sources`; it maps `${nodes.search.outputs.papers}` to the summary Skill.

The final workflow output is:

- `summary` from `${nodes.summarize.outputs.summary}`.

All steps use the existing `after_success` checkpoint policy and one attempt. Skill retry metadata uses the existing defaults: exponential backoff, one-second initial delay, and a 30-second cap.

## 4. Skill references

- `search`: `mock_paper_search@1.0.0`
- `summarize`: `mock_summary@1.0.0`

Both Skills are the existing allow-listed deterministic fake implementations registered by `register_fake_skills()`. Phase 8B adds no LLM or external research provider.

## 5. Approval point and reason

Approval occurs after deterministic papers are available and before summary generation.

- Step: `approve_sources`
- Policy/permitted role key: `project_reviewer`
- Durable Runtime prompt: `Approval required for workflow step approve_sources`
- Demonstration rationale: review the deterministic paper selection before synthesis.
- Recommended decision note: `Deterministic sources reviewed for the demo.`

The approval remains fingerprint-bound to the workflow version, run, StepRun attempt, policy, and inputs. Approval resumes the exact action; rejection or expiry cancels the run under existing v1 behavior.

## 6. Expected execution events

Checkpoint events may be interleaved at every durable Runtime boundary. The required semantic order is:

1. `WORKFLOW_STARTED`
2. `STEP_STARTED` for `search`
3. `SKILL_EXECUTED` for successful `mock_paper_search@1.0.0`
4. `APPROVAL_REQUESTED` for `approve_sources`
5. after approval, `STEP_STARTED` for `summarize`
6. `SKILL_EXECUTED` for successful `mock_summary@1.0.0`
7. `WORKFLOW_COMPLETED`

Every event sequence must be contiguous and strictly increasing. `CHECKPOINT_CREATED` records must appear between these semantic boundaries according to the existing Runtime lifecycle.

## 7. Expected final outputs

For the canonical query `persistent research agents`, `search` returns:

1. `Mock Foundations of persistent research agents`
2. `Mock Advances in persistent research agents`

The final run output is exactly:

```text
Mock summary: Mock Foundations of persistent research agents; Mock Advances in persistent research agents
```

The completed Run Detail page must expose this summary as visible text, not only as hidden transport data.

## 8. Expected frontend pages and transitions

1. `/workflows` loads the seeded definition from `GET /workflows`.
2. Selecting `Guided literature review` exposes the `query` input and `Create & execute run` action.
3. Submission creates and resumes the run, then navigates to `/runs/{run_id}`.
4. Run Detail shows `WAITING_FOR_APPROVAL`, successful `search`, waiting `approve_sources`, and the partial timeline.
5. `Review approval` navigates to `/approvals`.
6. `Approve & continue` resolves the pending request and executes `summarize` through the real backend.
7. The Run link returns to `/runs/{run_id}`, which shows `COMPLETED`, the ordered timeline, and final summary.
8. Reloading `/runs/{run_id}` shows the same persisted completed state.

The dashboard `/` must remain usable before and after the flow and reflect catalog, recent-run, and pending-approval state.

## 9. Success and failure criteria

### Success

- A clean PostgreSQL database migrates to Alembic head.
- The Seeder creates exactly one canonical workflow definition and repeated seeding reports it unchanged.
- The real browser, Next.js server, FastAPI application, Agent Runtime, SQL Unit of Work, and PostgreSQL participate in one observed flow.
- The run pauses before synthesis, exposes one pending ApprovalRequest, resumes only after approval, completes with the exact summary, and retains a strictly ordered event stream.
- A fresh HTTP application/session and a browser reload return the same completed run without new Skill execution or duplicate events.
- Startup, status, logs, tests, reset, seed, and stop are available through the root command interface and fail non-zero when their dependencies fail.

### Failure

The demo fails if migration or seed fails, the Catalog is empty or supplied only by a frontend fallback, the run skips approval, approval does not resume the same run, the output differs, events are missing/out of order, reload loses state, duplicate submission creates duplicate logical effects, or any service is silently substituted with an in-memory/fake HTTP layer.

## 10. Data reset and replay behavior

- The Docker demonstration stores PostgreSQL data in the named `reagent_postgres_data` volume.
- Normal stop preserves the volume and therefore run history.
- Reset explicitly removes the Compose stack and its named volume; the next start performs a clean migration and seed.
- Seeding never deletes runs and is safe to repeat. A conflicting immutable definition fails closed.
- Browser-created runs use a new client idempotency key. The submit button is disabled during creation to prevent concurrent duplicate submission from one page.
- Re-submitting an identical create command with the same idempotency key returns the existing run under the existing application contract.
- Resuming a completed run is a no-op: final state and event count remain unchanged.

No frozen Domain, Workflow Engine, Skill System, Runtime lifecycle, or persistence-port contract is changed by this demo contract.
