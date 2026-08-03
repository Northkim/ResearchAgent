# Teacher Design Requirement Ledger

Audit date: 2026-08-03

## Source identity

- Resolved source: `../Background/Meta-Research-Agent-架构.pdf` (workspace-relative;
  the machine-specific prefix is intentionally omitted)
- Size: 188,843 bytes
- SHA-256: `fa725dcd5a894f4025a94181e8595226c05d2895ae2f27c6a46c48a2fc5dd23c`
- Page count: 3
- Access date: 2026-08-03
- Review method: every page was text-extracted with macOS PDFKit and rendered to
  a page image for direct visual inspection. Page references below are PDF page
  numbers, not inferred section numbers.

## Authority and interpretation rules

The PDF is the primary product authority for this audit. The owner's explicit
instruction to follow the original design is next. Repository ADRs are
evidence of historical decisions, but an ADR does not override a conflicting
PDF statement. Requirements below do not fill silence with the current hosted
architecture.

`Mandatory` means the source states the responsibility or boundary as part of
the product. It does not mean every named workflow must be production-complete
in the first milestone. `Illustrative/optional` marks the source's own initial
folder sketch. `Explicitly undecided` preserves areas the source says require
development and experimentation.

## Page-referenced ledger

| ID | Exact source concept | PDF page | Faithful paraphrase | Source force | Evidence strength | Source does not specify | Current repository evidence | Primary alignment | Notes |
|---|---|---:|---|---|---|---|---|---|---|
| TMR-001 | Research process standardized as Workflows | 1 | Meta Research Agent turns research activities into standardized workflows. | Mandatory | Explicit definition | Workflow schema, graph semantics, implementation language | Three immutable `guided-literature-review` definitions exist under `demo/workflows/`; workflow contracts and validators are implemented. | ALIGNED_REQUIRED | The workflow concept aligns; the execution location does not. |
| TMR-002 | One local folder per Workflow instance | 1 | Every running workflow instance corresponds to a dedicated local folder containing everything needed for that task. | Mandatory | Explicit definition | Exact archive format and final directory names | No folder/archive generator or download endpoint was found. `/artifacts/{id}/content` returns individual server artifacts, not a workflow folder. | MISSING_REQUIRED | The developer repository and `runtime_data/` are not generated end-user workflow folders. |
| TMR-003 | Three-part system: cloud, local folder, existing Agent Harness | 1-2 | Product responsibilities are divided among a management cloud, a task-state folder, and Claude Code/Codex-like execution harness. | Mandatory | Explicit architecture boundary | Deployment topology and protocols between parts | Current path is Next.js -> FastAPI -> Application Services -> `SyncExecutionDispatcher` -> project-owned `AgentRuntime` -> Skills/providers. | MATERIAL_CONTRADICTION | The current product collapses task execution into the cloud/backend and omits the local-folder/harness runtime path. |
| TMR-004 | Cloud manages and supplies; cloud does not execute concrete research | 1-2 | Cloud owns resources and progress management but must not perform the research task. | Mandatory | Repeated explicit prohibition | Internal cloud module boundaries | `POST /runs/{id}/resume` and approval endpoints invoke backend `AgentRuntime`; server Skills invoke providers and create research outputs. | MATERIAL_CONTRADICTION | This is the central responsibility inversion. |
| TMR-005 | AG Admin and normalized Skill ingestion | 1 | Operators maintain a Skill library and convert self-written or external Skills into one system format. | Mandatory | Explicit cloud responsibility | Normalized format, review workflow, trust/sandbox policy | `SkillRegistry` is an in-process allow-list populated by Python composition; there is no operator admin UI, persistence/import, conversion, or external Skill ingestion. | MISSING_REQUIRED | The typed Skill model is reusable support, not AG Admin. |
| TMR-006 | Cloud project management and template/Skill folder delivery | 1 | After project/workflow selection, cloud generates the folder structure, packages prompts and Skills, and lets the user download it. | Mandatory | Explicit cloud responsibility | Archive format, template language, version manifest details | Workflow catalog/run creation exists, but no package builder, prompt/Skill copier, archive, or folder download route exists. | MISSING_REQUIRED | Current artifact downloads are outputs of hosted execution. |
| TMR-007 | Progress Report collection and unified progress continuity | 1 | Each local round produces a Progress Report uploaded to cloud; cloud aggregates project/workflow progress and outputs across machines/tools. | Mandatory | Explicit cloud responsibility | Report schema, upload protocol, merge/conflict rules | Backend has checkpoints, memory revisions, and execution events, but no Progress Report file schema, upload/import endpoint, history, or aggregation contract. | MISSING_REQUIRED | Hosted execution events are not equivalent to harness-authored Progress Reports. |
| TMR-008 | Cloud-managed external API credentials and proxy | 1 | Cloud holds external API keys; local execution calls providers through cloud without receiving keys. | Mandatory | Explicit cloud responsibility | Proxy authentication, provider response envelope, quotas | OpenAlex configuration reads a server environment key and the backend provider calls OpenAlex inside a research Skill. No local-harness proxy endpoint exists. | MISSING_REQUIRED | Central key placement is supporting evidence; call ownership is wrong for V1. |
| TMR-009 | Local folder files are the complete task state | 1-2 | The workflow folder is where research happens and its files represent the complete task state. | Mandatory | Explicit and repeated | Exact state serialization and cloud backup semantics | ADR 0001 explicitly makes PostgreSQL authoritative and rejects file-only execution state; runtime restoration requires DB records/checkpoints/memory. | MATERIAL_CONTRADICTION | Local artifact bytes cannot independently reconstruct a run. |
| TMR-010 | Existing Claude Code/Codex executes; project does not build a Harness | 2 | Existing harness reads/writes files, invokes tools, talks to the user, and performs the work; ReAgent only makes the folder understandable. | Mandatory | Explicit and repeated | Which harness first and compatibility test suite | Repository implements its own `AgentRuntime`, scheduler/Skill loop, approvals, checkpoints, and provider execution. Claude Code/Codex is not required for product workflow execution. | MATERIAL_CONTRADICTION | Current `AgentRuntime` functionally replaces the source-defined Harness. |
| TMR-011 | Five workflows | 2 | Product workflows are Literature Search, Idea Finding, Writing, Review, and Reproduction/Experiment. | Mandatory product taxonomy | Explicit list | Initial delivery priority and required maturity per workflow | Only literature-review workflow definitions are executable; the other four are absent as folder templates/packages. | MISSING_REQUIRED | Source does not say all five must be production-complete in initial V1. |
| TMR-012 | Workflows independent and composable | 2 | A user may run one workflow or chain them; previous outputs become next inputs. | Mandatory | Explicit behavior | Handoff manifest/schema and whether transfer is automatic copy or reference | Current static DAG composes steps within one hosted literature run. There is no five-workflow folder handoff or output-to-next-input mechanism. | MISSING_REQUIRED | Step dependencies are not the same as workflow-to-workflow composition. |
| TMR-013 | Exact local-folder and prompt decomposition remain open | 1-2 | Folder contents/organization and prompt splitting are core experimentation work and are not finalized. | Explicitly undecided | Explicit caveat | Final tree, prompt file count, naming, migration policy | Current planning selected a hosted runtime and DB authority rather than running the specified local-folder experiment. | SOURCE_UNDECIDED | A source-faithful milestone must experiment without presenting the sketch as frozen truth. |
| TMR-014 | Illustrative folder elements | 2-3 | Initial sketch includes project/workflow `AGENT.md`, prompt file(s), `skills/`, `memory/`, `inputs/`, and `outputs/`. | Illustrative/optional | Clearly labelled initial idea | Exact names, nesting, required files, serialization | The repository contains developer `AGENTS.md` and `.agent_read/`, but no generated user folder with these elements. | SOURCE_UNDECIDED | The sketch guides an experiment; it is not a final schema. |
| TMR-015 | Harness-readable `AGENT.md` behavior contract | 3 | Entry instructions tell any supported harness what to read, where to put work, and what to do before finishing. | Mandatory capability; illustrative file name | Role explicitly described | Exact instruction syntax and one-file versus multiple-file design | Repository instruction files govern repository development only. No end-user workflow `AGENT.md` generator or compatibility verification exists. | MISSING_REQUIRED | Developer governance must not be mistaken for the product feature. |
| TMR-016 | File memory supports session and harness continuity | 3 | Progress reports and compressed `context.md` let a new session or different harness continue without re-explaining background. | Mandatory behavior | Explicit rationale and example | Compaction algorithm, limits, merge rules | `.agent_read/context.md` provides developer continuity, while product runtime memory is stored in PostgreSQL; no exported local task memory contract exists. | MISSING_REQUIRED | The repository demonstrates the pattern internally but does not productize it. |
| TMR-017 | Inputs read-only; outputs become downstream inputs | 3 | User materials are preserved under inputs; workflow results live under outputs and can feed the next workflow. | Mandatory behavior within the sketch | Explicit element roles | Filesystem enforcement, copy/link policy, provenance manifest | Hosted run inputs/outputs live in database JSON and artifact storage; no local read-only input or workflow handoff folder contract exists. | MISSING_REQUIRED | Grounded corpus contracts may be reusable as handoff payload definitions. |
| TMR-018 | End-to-end local execution and progress round-trip | 3 | User creates project/uploads material/selects workflow in cloud, downloads folder, opens it in a Harness, writes outputs/report locally, uploads progress, then resumes later or with another Harness. | Mandatory product journey | Full worked example | Automation mechanism for upload and exact UX | Current browser creates and executes a hosted run, displays server events/artifacts, and resumes via backend. No download-local-execute-upload-resume journey exists. | MATERIAL_CONTRADICTION | The current demo proves a different product journey. |

## Ledger conclusion

The repository aligns on the idea of versioned workflows, typed Skills,
project-scoped metadata, artifacts, and provider abstraction. It does not align
on the product's defining execution and state boundaries. TMR-003, TMR-004,
TMR-009, TMR-010, and TMR-018 are explicit source statements and are directly
contradicted by the current hosted execution model.
