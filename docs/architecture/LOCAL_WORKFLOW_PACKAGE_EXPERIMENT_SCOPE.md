# Local Workflow Package Experiment Scope

Status: **R1 scope proposed by owner-approved implementation sequence**

Date: 2026-08-03

Governing decision: ADR 0009

## R1 objective

Generate one versioned, downloadable local Workflow Package and prove that an
existing Codex or Claude Code session can understand, execute, and resume the
task from the folder without backend Hosted AgentRuntime performing the
research work.

R1 is an experiment in the exact folder/prompt area the teacher source leaves
open (TMR-013, TMR-014; PDF pages 1-2). It must establish the required semantics
without claiming the sample tree on PDF pages 2-3 is final.

## First-slice recommendation

**OWNER IMPLEMENTATION-SEQUENCING PROPOSAL — NOT A TEACHER REQUIREMENT:** use
Literature Search as the first experimental Workflow slice.

Reason: Literature Search is one of the five teacher-defined types and the
repository already has versioned Workflow definitions, fake/synthetic Skills,
grounded contracts, provider ports, artifacts, and provenance validators that
can be selectively repackaged. The PDF does not prioritize Literature Search,
and R1 does not implement all five Workflows.

## Source-required semantics

The experiment must preserve these teacher-supported properties:

- one local folder corresponds to one Workflow instance (TMR-002, page 1);
- cloud generates/packages/delivers the folder (TMR-006, page 1);
- the folder communicates task material and current state (TMR-009, pages 1-2);
- existing Codex/Claude Code performs the work (TMR-010, page 2);
- entry instructions make the folder understandable to a Harness (TMR-015,
  page 3);
- local memory/context and a Progress Report support continuation (TMR-016,
  page 3);
- inputs and outputs have explicit roles and outputs can support later handoff
  (TMR-017, page 3);
- the local execution and later continuation path is demonstrated (TMR-018,
  page 3).

R1 must not turn package generation into backend research execution.

## Experimental package roles

Every path, filename, or layout proposed during R1 must be labelled:

> **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE**

The package must contain or securely reference the following roles. The
placeholder names below are deliberately non-normative.

| Required role | Experimental placeholder | R1 purpose |
|---|---|---|
| Entry instruction | `<EXPERIMENTAL_ENTRY_INSTRUCTION>` — **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE** | Tell a fresh Harness what to read, where inputs/outputs/context live, and what to do before finishing |
| Package manifest | `<EXPERIMENTAL_PACKAGE_MANIFEST>` — **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE** | Bind project/package identity, schema version, content list, versions, and checksums |
| Workflow definition | `<EXPERIMENTAL_WORKFLOW_DEFINITION>` — **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE** | Describe the Literature Search method/steps without making backend Workflow Engine the executor |
| Pinned Skills | `<EXPERIMENTAL_SKILL_AREA>` — **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE** | Carry or reference versioned Harness-readable capabilities and methods |
| Prompts/instructions | `<EXPERIMENTAL_PROMPT_AREA>` — **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE** | Provide role/method/task guidance under an explicit precedence experiment |
| User inputs | `<EXPERIMENTAL_INPUT_AREA>` — **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE** | Preserve task materials and research request; no hidden backend-only input |
| Outputs | `<EXPERIMENTAL_OUTPUT_AREA>` — **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE** | Receive local Harness research results and later handoff candidates |
| Working/long context | `<EXPERIMENTAL_CONTEXT_AREA>` — **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE** | Record current task understanding and continuation information |
| Progress Reports | `<EXPERIMENTAL_PROGRESS_AREA>` — **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE** | Receive one Harness-produced per-round report |
| Continuation instruction | `<EXPERIMENTAL_CONTINUATION_INSTRUCTION>` — **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE** | Tell a new session how to reconstruct and continue state |
| Versions/checksums | Manifest entries and/or `<EXPERIMENTAL_CHECKSUM_RECORD>` — **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE** | Detect drift and identify exact package/Workflow/Skill/prompt/input contents |
| Cloud proxy configuration | `<EXPERIMENTAL_PROXY_CONFIGURATION>` — **EXPERIMENTAL — NOT FINALIZED BY TEACHER SOURCE** | Describe non-secret cloud capability endpoints/configuration; never store a provider key |

R1 must not present these placeholders as final names or freeze a tree in this
document.

## Package-generation boundary

Cloud-side R1 work may:

- resolve one project/package identity and one pinned Literature Search
  definition;
- select approved template/Skill/prompt inputs;
- render deterministic package files;
- produce a manifest and checksums;
- create a downloadable ZIP/archive;
- verify archive contents contain no credential or unexpected file;
- record package metadata and download evidence.

It may not:

- execute the Literature Search;
- invoke backend AgentRuntime to advance the task;
- call a hosted LLM to write outputs;
- hide concrete task state in PostgreSQL;
- include a provider key;
- silently resolve the teacher-undecided tree as permanent;
- implement all five Workflows.

## Harness experiment

The approved existing Harness opens an unpacked package and must be able to:

1. identify project/package/Workflow identity and the task from files;
2. find and respect the input, output, context, Skill, and prompt roles;
3. perform the bounded research task without backend AgentRuntime;
4. write outputs locally;
5. update local continuation state visibly;
6. write one local Progress Report;
7. stop with the folder in a state another fresh session can understand;
8. continue after the folder is copied to a different local path.

Codex is the recommended first compatibility target because R1 is being
prepared in Codex. Claude Code compatibility must be tested separately or
explicitly documented as deferred; successful Codex execution is not proof of
Claude Code compatibility.

## R1 acceptance gates

R1 must later prove all of the following; R0 does not implement or execute
them:

1. A cloud-side package definition exists.
2. Package generation is reproducible for the same canonical inputs.
3. A ZIP/archive is produced and available through a bounded download path.
4. The archive contains no provider credential, authorization header, secret,
   private runtime database, or unrelated project material.
5. Package, Workflow, Skill, template/prompt, and relevant input versions and
   checksums are pinned.
6. Codex can infer the task, rules, relevant inputs, output location, and
   current state from files without oral reconstruction.
7. Claude Code compatibility is tested separately or explicitly deferred with
   a recorded limitation.
8. The existing Agent Harness performs the concrete research task.
9. Backend Hosted AgentRuntime performs no research step for the acceptance.
10. Research outputs and tool artifacts are written locally.
11. The Harness creates a local Progress Report.
12. The Progress Report can be uploaded and associated with the exact
    project/package/Workflow identity.
13. The cloud displays validated uploaded progress rather than hosted
    `ExecutionEvent` state.
14. A fresh Harness session continues from the folder alone.
15. Copying/unpacking the folder at a second local path preserves continuation.
16. The experiment records unresolved folder, prompt, Skill, context, progress,
    and merge questions instead of silently freezing them.
17. No provider credential enters the folder, archive, outputs, report, logs,
    or screenshots.
18. If external API access is included, the local Harness uses a Cloud API
    Proxy; no direct key-bearing provider call originates from the folder.

Gates 12/13 require at least a bounded acceptance-grade upload and display path
within the completed R1 proof. R2 remains responsible for generalizing that
proof into the full Progress Report history, aggregation, conflict, and project
progress capability. R1 must not claim the generalized R2 product is complete.

## Evidence expected from R1

- package-definition identity and canonical checksum;
- two generated archive checksums proving reproducibility;
- manifest and archive inventory;
- secret/credential scan result;
- Harness identity and session record;
- proof that backend AgentRuntime/provider execution was not invoked;
- local output and Progress Report checksums;
- continuation result from a fresh session;
- second-location continuation result;
- recorded experimental questions and owner decisions;
- explicit Claude Code compatibility result or deferment.

Evidence must contain only synthetic or owner-approved bounded inputs. Runtime
packages and generated evidence belong under an approved ignored root, not in
canonical documentation unless separately reviewed and content-safe.

## Explicit R1 exclusions

- no final folder schema;
- no all-five-Workflow implementation;
- no hosted LLM activation;
- no backend research execution;
- no provider key in the package;
- no production Hosted Mode work;
- no automatic relevance Judge;
- no full-pool evaluation;
- no production deployment claim.

## Source-undecided questions R1 must record

- root and nested instruction-file layout;
- prompt split and precedence;
- embedded versus referenced Skill content;
- manifest format and archive format;
- context compression method;
- Progress Report provisional format;
- how local changes interact with package refresh;
- whether outputs are uploaded, referenced, or selectively returned;
- how cross-Harness instruction differences are handled;
- how Workflow output/input handoff will be represented later.

These questions are experiment outputs, not reasons to default to the preserved
hosted architecture.
