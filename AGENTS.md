# ReAgent Repository Instructions

Before changing this repository, read these files in order:

1. `docs/PROJECT_DEVELOPMENT_PLAN.md`
2. `.agent_read/AGENT.md`
3. `.agent_read/context.md`
4. The most recent relevant file in `.agent_read/progress/`
5. Relevant records in `.agent_read/decisions/`

Treat `docs/PROJECT_DEVELOPMENT_PLAN.md` as the product source of truth. Do not change the project vision or goals without explicit user confirmation.

## Engineering change routing

Before changing production behavior, read `docs/engineering/SOURCE_OF_TRUTH_POLICY.md`.
Use `engineering-change-contract` for contract-affecting planning and its packet
template; a completed packet does not authorize implementation. Use
`engineering-verification` for acceptance and evidence review. Do not silently
resolve source conflicts. Keep non-blocking findings deferred instead of
expanding the active scope. Detailed rules live under `docs/engineering/` and
`docs/testing/`.

After completing a development task, update `.agent_read/context.md`, add or update a progress report, and record any consequential architecture decision according to `.agent_read/decisions/README.md`.
