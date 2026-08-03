# Teacher Design Alignment Audit Handoff

Date: 2026-08-03
Status: **PASS — audit complete; repository verdict is FUNDAMENTALLY_DIFFERENT_PRODUCT**

## Scope

This was a read-only source-of-truth audit. It did not implement realignment,
change an ADR status, update `.agent_read/context.md`, edit the development
plan, modify source/dependencies, call a provider, stage, or commit.

The pre-existing Phase 9C-2A documentation changes were preserved unchanged by
this audit.

## Teacher source

- workspace-relative path: `../Background/Meta-Research-Agent-架构.pdf`;
- size: 188,843 bytes;
- SHA-256: `fa725dcd5a894f4025a94181e8595226c05d2895ae2f27c6a46c48a2fc5dd23c`;
- pages: 3;
- accessed: 2026-08-03;
- method: direct page text extraction plus page-by-page rendered visual review.

## Finding

The teacher source defines cloud management/supply, local-folder task-state
authority, and execution by existing Claude Code/Codex. The current repository
implements a hosted Web Agent platform: browser commands dispatch backend
`AgentRuntime`, server Skills call providers, PostgreSQL owns live execution
state, and server artifacts/events drive the UI.

The best core classification is **B**, not A or a balanced hybrid. The most
important conflicts are:

- cloud performs concrete research despite an explicit source prohibition;
- project-owned `AgentRuntime` replaces the existing external Agent Harness;
- PostgreSQL replaces the local folder as authoritative task state;
- no downloadable workflow-folder generator exists;
- no Progress Report upload/aggregation round-trip exists;
- no AG Admin/import/conversion path exists;
- OpenAlex is a hosted research operation, not a local-Harness-facing proxy.

## Phase 9C disposition recommendation

Stop further Phase 9C-2B hosted activation work before owner review. Preserve
V3 schemas, prompts, grounded contracts, provenance validators, provider ports,
ProviderOperation, synthetic fixtures/tests, and inactive Anthropic mapping.
Reframe them as potential local Skill/package contracts, folder-side/cloud-side
deterministic validation, and later proxy support. Do not change ADR 0007 or
ADR 0008 in the audit.

## Deliverables

- `docs/audits/TEACHER_DESIGN_REQUIREMENT_LEDGER.md`
- `docs/audits/TEACHER_DESIGN_ALIGNMENT_AUDIT.md`
- `docs/audits/TEACHER_DESIGN_DIVERGENCE_MATRIX.md`
- `docs/audits/TEACHER_DESIGN_REALIGNMENT_PLAN.md`
- `.agent_read/progress/teacher_design_alignment_audit.md`

## Recommended next milestone

Exactly one: **experimental local workflow-folder package and Agent Harness
compatibility slice**. The cloud should generate one synthetic downloadable
folder for one owner-selected workflow; Claude Code or Codex should complete
the task and write an output plus Progress Report without backend
`AgentRuntime` or PostgreSQL live execution.

Owner review is required before any roadmap, ADR, source, or context update.
