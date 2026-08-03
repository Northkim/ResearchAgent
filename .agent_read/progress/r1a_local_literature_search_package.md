# R1A Experimental Local Literature Search Package

Date: 2026-08-03  
Status: **IMPLEMENTED / NETWORK-FREE; R1B PENDING**  
R1 state: **HARNESS_ACCEPTANCE_PENDING**

## Outcome

R1A adds a standard-library-only `backend.workflow_packages` compiler for one
experimental Literature Search folder. It renders Harness-neutral instructions,
Codex/Claude Code shims, pinned Workflow/Skill/prompt content, wholly fictional
offline inputs, declared outputs, human-readable context, an experimental
Progress Report schema, a disabled non-secret proxy placeholder and a
self-contained validator. It emits deterministic folder and ZIP bytes.

The compiler does not import or invoke AgentRuntime, ExecutionDispatcher,
database/persistence or providers. Generation read no environment file, opened
no network, called no provider and performed no research. Existing Hosted Mode
source and behavior were not modified.

## Acceptance package

Ignored root:
`runtime_data/workflow_packages/r1a-literature-search/`

- package ID: `literature-search-experimental-literature-search-v0.1`;
- package schema: `workflow-package/v0.1`;
- Workflow: `literature-search-local-experimental@0.1.0`;
- Workflow checksum:
  `sha256:8d25d7cd32a89e84ba8885454782cb923e93224df4637ddf6183af2a16f3980c`;
- Skill: `reagent.local-literature-search@0.1.0`;
- Skill checksum:
  `sha256:a9d451fa2c03d269321a5d0782da160c50a131cd1d57c9f8a2f4f1be7705ec74`;
- prompt: `literature-search-planning@0.1.0`;
- prompt checksum:
  `sha256:184b1f139cc67826e96551665e8240e02ffd645ee5fc62f54338f0e79b151616`;
- file-manifest checksum:
  `sha256:aa4a4e4b18acd7bce0835f3dc736e3ed753c485d703fee92ffadb19ecae5d0c3`;
- manifest checksum:
  `sha256:9ca23b4ed5330cebf12b0630f0b11d2af98d50074500d6df070e414d1e1f0633`;
- package checksum:
  `sha256:24790950e4ec3be8ee68dc5aa7103128c3ce15a494e6ee94d6f52d55380f0eaa`;
- ZIP checksum:
  `sha256:f5bcbc747b67b4d4ec2ac06607144d61ee20481f43294cb0548ca1545c7caffb`.

The package contains 21 files including its manifest, 34,329 unpacked file
bytes, and a 37,035-byte ZIP. Build/validation receipts and R1B handoff remain
ignored. Folder, archive, independently extracted, and copied-folder validation
passed. A second compiler invocation produced the identical manifest, package,
and ZIP checksums.

## Contracts and security

Contracts are frozen dataclasses with tuple-valued collections, canonical JSON
and stable SHA-256. Paths reject absolute/traversal/backslash/duplicate names,
environment files, local databases and sensitive suffixes. Content checks
reject high-confidence key/private-key/credentialed-database markers, raw
provider-response markers and machine-specific paths. ZIP members are sorted,
uncompressed and use a fixed timestamp/mode.

Inputs are immutable. Declared outputs, local context and appended Progress
Reports are Local Task State. The manifest normalizes the intentionally mutable
context entry out of package identity while retaining its initial checksum for
pristine validation. Immutable package files remain checksum-enforced after
Harness work.

## Validation

Focused command:

```text
conda run --no-capture-output -n reagent-dev python -m pytest -q backend/workflow_packages/tests
```

Result: `41 passed in 0.43s` (exit 0).

Full backend regression:

```text
conda run --no-capture-output -n reagent-dev python -m pytest -q backend
```

Result: `242 passed, 18 skipped in 5.25s` (exit 0). The 18 skips are the
existing opt-in external/PostgreSQL tests; no external service was used.

Compilation:

```text
conda run --no-capture-output -n reagent-dev python -m compileall -q backend
```

Result: exit 0 with no output. Runtime tests requiring PostgreSQL, frontend,
Docker, provider calls, and external Codex/Claude Code were not executed.

## R1B handoff

`docs/acceptance/R1B_AGENT_HARNESS_ACCEPTANCE.md` freezes the external test.
A fresh Codex session must receive only:

`Read the package instructions and continue the task.`

R1A did not open or simulate a fresh Harness session. Claude Code has not been
tested. Status remains `HARNESS_ACCEPTANCE_PENDING`.

## Unresolved questions

Final tree/prompt decomposition, Claude shim sufficiency, mutable-state
integrity, context representation, report identity/timestamp policy,
Skill embedding/reference strategy, package refresh/merge, R2 upload schema and
R3 proxy protocol remain experimental.

## Next milestone

Exactly one next milestone: **R1B — external Agent Harness execution and
continuation acceptance**. Do not begin R2 first.
