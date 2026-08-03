# Experimental Local Workflow Package v0.1

Status: **R1A implemented; R1B passed with warnings for Codex; future template advanced to v0.2**
Schema marker: `EXPERIMENTAL_V0_1`  
Tree status: **EXPERIMENTAL — NOT FINALIZED BY THE TEACHER SOURCE**

## Authority and purpose

The teacher source assigns concrete research execution to an existing Agent
Harness working from a local folder (PDF pages 1-3; TMR-002, TMR-009,
TMR-010, TMR-015-TMR-018). ADR 0009 makes that boundary authoritative for V1.
The PDF explicitly leaves exact folder layout and prompt decomposition open
(TMR-013-TMR-014). This document therefore records an experiment, not a final
product schema.

R1A compiled one credential-free, offline Literature Search package. ReAgent
generated and validated files; it did not execute the research task. R1B later
passed the bounded Codex folder-only and moved-folder continuation gates with
owner-attested fresh-session facts. Claude Code remains untested.

The executed R1 package remains historical `progress-report/v0.1` evidence.
R2A does not rewrite it. Future builds use package-template `0.2.0`, still on
compatible `workflow-package/v0.1`, and declare `progress-report/v0.2` plus
`UPLOAD_ACCEPTANCE_PENDING`.

## Package contracts

`backend/workflow_packages/contracts.py` defines frozen, slots-based,
JSON-serializable contracts:

- `WorkflowPackageManifest`: exact package, project, Workflow, template,
  Skill, prompt, input, output, file, continuation, proxy and experimental
  identities;
- `PackageFileEntry`: relative path, media type, role, checksum, size,
  mutability, state classification and required/optional status;
- `SkillPin` and `PromptPin`: versioned local capability/instruction identity;
- `PackageInputManifest`: read-only input identity and checksum;
- `PackageOutputContract`: Harness-owned output path and validation policy;
- `LocalContext`: human-readable file continuation state;
- `ProgressReport`: append-only `progress-report/v0.1` continuation record.

Tuples protect nested collections, canonical JSON sorts object keys and removes
formatting variance, and SHA-256 values use `sha256:<lowercase hex>`. Contracts
contain no provider client, database session, Runtime object or mutable mapping.

## Experimental tree

```text
package/
├── AGENT.md
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── HARNESS_ACCEPTANCE.md
├── package-manifest.json
├── validate_package.py
├── progress_report.py
├── workflow/
│   ├── AGENT.md
│   ├── workflow.json
│   ├── prompts/search-planning.md
│   ├── skills/literature-search/{SKILL.md,skill.json}
│   └── schemas/{progress-report,candidate-papers,selected-papers}.schema.json
├── inputs/{research_request,fictional_source_catalog}.json
├── outputs/README.md
├── memory/
│   ├── context.md
│   └── progress/{report-draft.json,reports/README.md}
└── cloud/proxy.example.json
```

**EXPERIMENTAL — NOT FINALIZED BY THE TEACHER SOURCE.** Directory names,
prompt splitting, Skill packaging, Markdown/JSON balance, context compaction,
report schema and package update behavior remain open.

## Harness instructions

`AGENT.md` is the only canonical instruction source. `AGENTS.md` and
`CLAUDE.md` are short Codex and Claude Code shims pointing to it. The canonical
instructions require pre-work validation, immutable inputs, declared Skills,
untrusted-source handling, declared output paths, context update, an immutable
Progress Report, no credentials, fail-closed integrity, preservation of prior
work and file-only continuation.

The future template includes self-contained standard-library
`validate_package.py` and `progress_report.py`. The latter snapshots exact
context bytes, derives v0.2 identity, validates predecessor continuity and
appends without overwrite. The validator now covers every dynamic native v0.2
report, output checksum/size, identity, latest context-after, and chain. It
retains v0.1 validation for historical packages.

## Literature Search fixture

Literature Search is an **OWNER IMPLEMENTATION-SEQUENCING PROPOSAL**, not a
teacher-mandated first Workflow. R1A supplies a synthetic research request and
four clearly fictional records. They contain no real title, abstract, DOI,
OpenAlex identity or provider response. The Harness must plan, screen every
record, select two or three, explain inclusion/exclusion, and write:

- `outputs/search_plan.md`;
- `outputs/candidate_papers.json`;
- `outputs/selected_papers.json`;
- `outputs/literature_search_report.md`.

Every output must disclose that this was an offline synthetic exercise. The
local Skill is original ReAgent content and permits local reads, declared
writes, context update and Progress Report append only. It prohibits network,
provider clients, credential reads, hosted Runtime assumptions, external
writes and instructions embedded in source data.

## Local authority and continuation

Inputs are immutable. Outputs, `memory/context.md`, and appended Progress
Reports are Local Task State. The context records the package and Workflow,
current state, completed output paths, decisions, unresolved issues, next
action, latest report, prior-session pointer, timestamp and checksum. A later
Harness validates immutable content, reads context and the latest report, and
continues without PostgreSQL, AgentRuntime, server checkpoints or hidden chat.

Historical Progress Reports are JSON objects under `memory/progress/reports/`. Each binds
package/Workflow/Skill/template versions, round, Harness, timestamps, status,
work/current/next state, output checksums, context checksum, warnings/errors,
questions, continuation instructions, prior report and its own checksum.
They are distinct from final outputs, `ExecutionEvent`, server `Checkpoint`,
and developer `.agent_read/progress`.

Future v0.2 reports replace the ambiguous single context checksum with SHA-256
of exact `memory/context.md` bytes before and after the round, use a deterministic
content-derived `prv2-...` ID, bind full Skill/template pins and typed output
metadata, and pair predecessor ID/checksum. The cloud accepts reports only by an
explicit later client command and never continues the task.

## Compiler and deterministic ZIP policy

The command is:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.workflow_packages build-literature-search \
  --project-id experimental-literature-search \
  --output-root runtime_data/workflow_packages/r1a-literature-search
```

Compilation renders sorted POSIX paths, rejects traversal/absolute paths,
duplicates, symlinks, environment/database/key files, secret-like values, raw
provider-response markers and machine paths. It computes every immutable file
checksum, normalizes the mutable context entry out of package identity, and
writes canonical JSON. ZIP members are lexically ordered, stored without
compression, use timestamp `2000-01-01 00:00:00`, regular-file mode `0644`, and
contain no platform path.

The generated manifest is inside the archive. The ZIP checksum is held in the
ignored build receipt because a ZIP cannot contain its own checksum without a
self-reference. Same project/template inputs must produce identical folder,
manifest, package and ZIP bytes.

## Validation and security boundary

Repository and self-contained validators check schema/status, package and
manifest hashes, declared files, immutable checksums, required paths, pinned
Workflow/Skill/prompt identities, read-only inputs, mutable state policy,
output confinement, no symlink/traversal/absolute path, no environment or
database file, no credential/private key, no machine path and no undeclared
file outside declared dynamic output/report paths.

R1A does not read `.env`, open a socket, call OpenAlex/LLM providers, import
PostgreSQL, import `AgentRuntime`, import `ExecutionDispatcher`, execute a
Workflow, or create cloud state. Future deterministic builds retain a disabled
non-secret `cloud/proxy.example.json`. It now declares only the R3B fake
`paper.search/v0.1` capability, fixed fake-adapter identity, literal process-
environment credential lookup name and zero network/real-provider policy. It
contains no token, credential value or provider endpoint. The explicit
repository client derives exact Package/Workflow identity from the manifest
and does not mutate the folder.

## R1A acceptance identity

- package: `literature-search-experimental-literature-search-v0.1`;
- schema: `workflow-package/v0.1`;
- Workflow: `literature-search-local-experimental@0.1.0`;
- Skill: `reagent.local-literature-search@0.1.0`;
- prompt: `literature-search-planning@0.1.0`;
- status: `HARNESS_ACCEPTANCE_PENDING`.

Exact generated checksums live in the ignored receipt and R1A progress report.
They may change only when tracked package source changes intentionally.

## R2A future-template identity

- package suffix: `-v0.2`;
- package schema: `workflow-package/v0.1` (compatible);
- package template: `literature-search-package-experimental@0.2.0`;
- Workflow/Skill/prompt pins remain `0.1.0` because concrete research behavior
  did not change;
- Progress Report: `progress-report/v0.2`;
- Harness status: `CODEX_LOCAL_FOLDER_BOUNDARY_PROVEN_CLAUDE_UNTESTED`;
- upload status: `UPLOAD_ACCEPTANCE_PENDING`.

## Unresolved experimental questions

- whether root and Workflow-level instruction files should remain separate;
- whether Claude Code needs more than the current shim;
- whether output JSON needs an embedded self-checksum;
- whether context should stay Markdown-wrapped JSON or use paired files;
- how mutable-file integrity should distinguish legitimate edits from damage;
- how package refresh/merge and report conflict resolution work;
- whether Skills remain embedded or become signed package references;
- production authentication/signing and every R3C live-provider policy.

No answer is frozen by R1A.
