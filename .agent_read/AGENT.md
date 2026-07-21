# Persistent Agent Operating Instructions

This directory is ReAgent's durable handoff layer between development sessions. Keep it concise, current, and useful to the next agent.

## Required startup sequence

Before planning or changing the project:

1. Read `docs/PROJECT_DEVELOPMENT_PLAN.md` in full. It is the source of truth for product vision, development order, and engineering requirements.
2. Read `.agent_read/context.md` for the compressed current project state.
3. Read the most recent relevant report in `.agent_read/progress/`.
4. Read relevant records in `.agent_read/decisions/` before changing an established boundary or technology choice.
5. Inspect the repository itself and reconcile the written context with the current files and Git state.

## Rules while working

- Work within the current development stage unless the user explicitly changes the scope.
- Do not modify the project vision, core goals, or development order without explicit user confirmation.
- Keep Agent Runtime, Workflow Engine, Skill System, persistence, platform interfaces, and user interface separated by explicit contracts.
- Prefer framework-independent domain models and interfaces in core modules.
- Do not present a proposal as an accepted decision. Record accepted, consequential decisions in `.agent_read/decisions/`.
- Preserve user changes and existing project conventions.
- Never store secrets, credentials, private source material, or raw sensitive prompts in persistent context files.

## Required completion sequence

After a meaningful task:

1. Update `.agent_read/context.md` if the current stage, repository state, constraints, or next steps changed.
2. Add a concise progress report under `.agent_read/progress/`. Prefer `YYYY-MM-DD_<topic>.md`; add a numeric suffix if multiple reports share a date and topic.
3. Add or supersede an architecture decision record when a consequential decision was explicitly accepted.
4. Report verification performed, remaining risks, and the next recommended action.

Progress reports are handoff summaries, not raw logs. Keep `context.md` compressed enough to read at the start of every session.
