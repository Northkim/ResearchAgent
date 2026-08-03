# Teacher-Aligned V1 Boundary Freeze Handoff

Date: 2026-08-03

Phase: R0

Status: **PASS — owner-authorized product boundary frozen; no implementation performed**

## Authority and source

- teacher source: `Meta-Research-Agent-架构.pdf`;
- stable workspace-relative location used for review:
  `../Background/Meta-Research-Agent-架构.pdf`;
- size: 188,843 bytes;
- SHA-256:
  `fa725dcd5a894f4025a94181e8595226c05d2895ae2f27c6a46c48a2fc5dd23c`;
- pages: 3;
- accessed: 2026-08-03;
- method: direct PDFKit text extraction plus visual inspection of every rendered
  page.

The owner accepted the committed Teacher Design Alignment Audit verdict
`FUNDAMENTALLY_DIFFERENT_PRODUCT` and explicitly authorized the route correction
recorded in ADR 0009.

## Accepted V1 boundary

Initial V1 is cloud management/supply plus a portable local Workflow Package
executed by an existing Claude Code or Codex Agent Harness:

- cloud owns projects, Skills, packages/downloads, Progress Report history and
  projections, credentials, API proxy, stored uploads/returned artifacts, and
  continuity metadata;
- the local folder owns authoritative concrete research-task state;
- the existing Harness performs research, invokes tools/proxy calls, writes
  outputs, updates context, and writes Progress Reports;
- PostgreSQL is authoritative for Cloud Project State only, not hidden Local
  Task State;
- Hosted AgentRuntime remains preserved as internal test infrastructure or an
  optional future Hosted Mode.

Teacher traceability: TMR-002-TMR-010 and TMR-015-TMR-018 on PDF pages 1-3.
The five-Workflow taxonomy remains TMR-011/TMR-012 on page 2; exact folder and
prompt decomposition remain source-undecided under TMR-013/TMR-014 on pages
1-2.

## Governance outcomes

- ADR 0009: **Accepted**;
- ADR 0007: **Deferred by ADR 0009 — Optional Hosted Mode**;
- ADR 0008: **Deferred by ADR 0009 — Optional Hosted Mode**;
- ADR 0006 / Optional Evaluation Module: remains **Deferred**;
- ADR 0005: retains only its accepted multilingual SearchPlan/safe-diagnostic
  scope; real Judge work remains deferred;
- Phase 9C hosted activation and hosted LLM generation: deferred.

The old ADR text, current hosted source, migrations, immutable Workflows, tests,
and evidence remain preserved. Grounded contracts/prompts/provenance validators
may be repackaged for local Harness use in a later authorized phase.

## Hosted-work freeze

Further V1 product development is paused for backend research execution,
browser run/resume, Hosted AgentRuntime productionization, real hosted LLM,
new hosted research adapters, hosted queue/worker/lease, automatic relevance
evaluation, full-pool benchmarks, and server research-execution/report UX.

Preservation, safety fixes, deterministic regression tests, schema/validator
extraction, and a separately authorized future Hosted Mode remain possible.

## Documents produced

- `.agent_read/decisions/0009-teacher-aligned-initial-product-boundary.md`;
- `docs/architecture/TEACHER_ALIGNED_V1_PRODUCT_BOUNDARY.md`;
- `docs/architecture/EXISTING_COMPONENT_RECLASSIFICATION.md`;
- `docs/architecture/CLOUD_PROGRESS_AND_API_PROXY_BOUNDARY.md`;
- `docs/architecture/LOCAL_WORKFLOW_PACKAGE_EXPERIMENT_SCOPE.md`;
- this handoff.

Updated governance/framing:

- `.agent_read/context.md`;
- `docs/PROJECT_DEVELOPMENT_PLAN.md`;
- ADR 0007 and ADR 0008 statuses and deferment records;
- `DEMO.md` labelled as the Preserved Hosted Prototype Demo.

`README.md` contains only the repository title and was not materially
misleading, so it was not changed.

## R1 boundary

The single next milestone is the **experimental local Literature Search
Workflow Package and Agent Harness compatibility slice**. Literature Search is
an owner implementation-sequencing proposal, not a teacher requirement. R1
must keep every proposed path/tree explicitly experimental, generate a
reproducible credential-free archive, prove existing-Harness execution and
file-based continuation without Hosted AgentRuntime, produce local output and a
Progress Report, and exercise the bounded upload/progress acceptance path.

R0 did not implement R1, add a feature flag, change production source, modify a
Workflow JSON/migration/dependency, create runtime data, read a secret, call an
API, stage, or commit.

## Next permitted action

Owner review of the R0 documentation, followed by one separately scoped R1
implementation task. Future tasks must read the teacher PDF, ADR 0009, and the
Teacher Design Audit before planning.
