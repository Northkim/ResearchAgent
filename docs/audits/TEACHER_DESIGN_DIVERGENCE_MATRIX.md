# Teacher Design Divergence Severity Matrix

Audit date: 2026-08-03

Severity is based on teacher-source criticality and product-boundary impact,
not code volume, test coverage, or sunk cost. “Disable” and “stop” are audit
recommendations only; this audit changes no runtime behavior.

## Matrix

| ID | Divergence | Teacher IDs | Severity | Type | Consequence | Repository evidence | Minimal correction |
|---|---|---|---|---|---|---|---|
| DIV-001 | Cloud/backend executes concrete research steps | TMR-003, TMR-004 | CRITICAL | responsibility inversion | changes product identity | `backend/agent_runtime/runtime/agent_runtime.py:102-216,437-506`; backend Skills invoke providers | stop current route; disable endpoint from initial V1 after owner approval |
| DIV-002 | Project develops and uses its own AgentRuntime in place of Claude Code/Codex | TMR-003, TMR-010 | CRITICAL | responsibility inversion | changes product identity | `backend/agent_runtime/`; `SyncExecutionDispatcher` invokes it in caller process | stop current route; retain as internal/optional mode |
| DIV-003 | PostgreSQL is authoritative live task state instead of the local folder | TMR-009, TMR-016 | CRITICAL | responsibility inversion | changes product identity | ADR 0001 lines 15, 23, 33; ORM run/session/step/checkpoint/memory tables | reframe component around cloud metadata; require owner decision on hosted tables |
| DIV-004 | No generated/downloadable self-contained workflow folder | TMR-002, TMR-006, TMR-018 | CRITICAL | missing core feature | blocks teacher-design demo | no generator/archive/download-folder implementation found | add missing source feature |
| DIV-005 | No product contract proving existing Claude Code/Codex executes a folder | TMR-010, TMR-015, TMR-018 | CRITICAL | missing core feature | blocks teacher-design demo | no end-user `AGENT.md` generator, folder fixture, or cross-Harness acceptance | add missing source feature |
| DIV-006 | Derived development plan declares a hosted autonomous platform as product vision | TMR-003, TMR-004, TMR-009, TMR-010 | CRITICAL | responsibility inversion | changes product identity | `docs/PROJECT_DEVELOPMENT_PLAN.md:3-24,53-75` | require owner decision; later documentation correction only after review |
| DIV-007 | Browser “Create & execute” and Resume commands start backend work | TMR-004, TMR-010, TMR-018 | HIGH | responsibility inversion | changes product identity | `frontend/api/hooks.ts:63-69`; `workflow-catalog.tsx:121-189`; `/runs/{id}/resume` | disable endpoint from initial V1; replace journey with package/download |
| DIV-008 | Approval UI resumes/rejects hosted execution | TMR-004, TMR-010 | HIGH | premature implementation | creates avoidable work | approval endpoints dispatch `AgentRuntime`; frontend calls them | reframe component for package/proxy approvals or defer |
| DIV-009 | OpenAlex is called by a hosted research Skill rather than a local-Harness-facing cloud proxy | TMR-004, TMR-008 | HIGH | responsibility inversion | blocks teacher-design demo | `research.skills.search_papers` -> `OpenAlexPaperSearchProvider.search` | reframe component behind proxy; add missing source feature |
| DIV-010 | No Progress Report schema/upload/history/aggregation | TMR-007, TMR-016, TMR-018 | HIGH | missing core feature | blocks teacher-design demo | events/checkpoints exist; no Progress Report route or model | add missing source feature |
| DIV-011 | No AG Admin or external Skill conversion/import | TMR-005 | HIGH | missing core feature | blocks teacher-design demo | `SkillRegistry` has only in-process explicit registration | add missing source feature |
| DIV-012 | No prompt/Skill package builder and versioned folder delivery | TMR-006, TMR-015 | HIGH | missing core feature | blocks teacher-design demo | workflow definitions are seeded to DB; no package generation | add missing source feature |
| DIV-013 | No workflow-output-to-next-workflow-input handoff | TMR-012, TMR-017 | HIGH | missing core feature | blocks teacher-design demo | intra-DAG references exist; no workflow folder composition | add missing source feature |
| DIV-014 | Hosted Phase 9C real-LLM activation is planned | TMR-004, TMR-010 | HIGH | premature implementation | changes product identity | ADR 0008 and Phase 9C-2B execution plan | stop current route; defer |
| DIV-015 | Only Literature Search exists as a first-class workflow | TMR-011 | MEDIUM | missing core feature | creates avoidable work | only `guided-literature-review` v1-v3 are seeded | require owner decision on first workflow; later add source feature |
| DIV-016 | Live event timeline is treated as project continuity | TMR-007, TMR-016 | MEDIUM | naming/framing issue | creates avoidable work | frontend “Execution ledger” and event timeline | reframe component as uploaded Progress Report history |
| DIV-017 | Hosted artifact viewer is prioritized before folder package/download | TMR-006, TMR-018 | MEDIUM | premature implementation | creates avoidable work | artifact APIs/UI exist; folder download absent | reframe component for package and uploaded-output viewing |
| DIV-018 | Hosted Agent Session terminology suggests source-defined Harness sessions | TMR-010, TMR-016 | MEDIUM | naming/framing issue | documentation correction only | `AgentSessionORM`, domain `AgentSession` are server records | reframe terminology; no code rename in audit |
| DIV-019 | Checkpoints/memory revisions are presented as continuity but are not Progress Reports/local memory | TMR-007, TMR-009, TMR-016 | MEDIUM | naming/framing issue | creates avoidable work | DB checkpoint/memory repositories and hosted replay | reframe terminology; build separate source feature |
| DIV-020 | Automated Judge/evaluation route precedes source-defined cloud/folder core | TMR-005-TMR-008, TMR-018 | MEDIUM | premature implementation | creates avoidable work | ADR 0005/0006 and evaluation package | defer |
| DIV-021 | Queue/worker and hosted production execution planning | TMR-004, TMR-010 | MEDIUM | premature implementation | creates avoidable work | dispatcher replacement and architecture plans | defer |
| DIV-022 | Exact folder/prompt questions were bypassed rather than experimentally resolved | TMR-013-TMR-015 | MEDIUM | source-undecided implementation | blocks teacher-design demo | hosted architecture selected; no local folder experiment | add missing source feature; require owner decision |
| DIV-023 | Developer `.agent_read/` resembles teacher memory terminology | TMR-016 | LOW | naming/framing issue | documentation correction only | Git policy explicitly says it is not product runtime memory | no action beyond maintaining precise distinction |
| DIV-024 | Typed provider/Skill/artifact contracts exceed PDF detail | TMR-005, TMR-008 | LOW | harmless support detail | can remain hidden/internal | provider ports, Skill schemas, artifact checksums | no action; reframe their consumers |
| DIV-025 | Cloud lacks actual Project management and material-upload capability | TMR-006, TMR-018 | HIGH | missing core feature | blocks teacher-design demo | run creation accepts free-form `project_id`/actor ID; no Project API, aggregate, or upload route | add missing source feature |

## Critical path

The minimum sequence is not to remove current code. It is to stop extending
DIV-001/DIV-002/DIV-014, preserve existing work, obtain owner governance on
DIV-006, and build DIV-004/DIV-005/DIV-010 as the first source-faithful vertical
slice. Provider and Skill infrastructure can then be reused to correct
DIV-009/DIV-011/DIV-012.

## Severity notes

- The five-workflow gap is MEDIUM for the first milestone because the PDF does
  not specify initial implementation priority, even though all five belong to
  the product taxonomy.
- Folder generation, Harness execution, and Progress Report round-trip are
  higher severity because they are necessary to demonstrate the defining
  architecture with even one workflow.
- Hosted execution is CRITICAL because it changes which system part performs
  research; it is not merely an unfinished cloud feature.
