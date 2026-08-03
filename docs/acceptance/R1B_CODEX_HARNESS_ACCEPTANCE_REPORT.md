# R1B Codex Harness Acceptance Report

Date: 2026-08-03  
Phase: **R1B — External Codex Agent Harness Execution and Folder-only Continuation Acceptance**  
Overall result: **PASS_WITH_WARNINGS**

## Scope and evidence boundary

This report verifies the completed original package and its moved copy. The
package locations are intentionally recorded only as **Original executed
package** and **Moved executed package**; machine-specific absolute paths are
not part of committed evidence.

The owner attests that:

1. Session 1 was a fresh Codex session.
2. Session 2 was another fresh Codex session and did not use `codex resume`.
3. Session 3 was a fresh Codex session started in the moved package.
4. Every session received only `Read the package instructions and continue the task.`
5. No prior project explanation was provided.
6. No external provider, network search, AgentRuntime, or PostgreSQL execution
   was used.

Freshness, absence of `codex resume`, exact prompt delivery, lack of prior
explanation, and runtime non-use are **OWNER_ATTESTED**. File evidence does not
independently prove that the sessions were fresh, and this report does not make
that claim.

## Result summary

The package passed the Codex execution, continuation, checksum, moved-folder,
local-state-authority, and hosted-boundary gates. The result is
`PASS_WITH_WARNINGS`, not an unqualified pass, because the freshness facts are
owner-attested, no standalone Session 1 checksum snapshot was captured, the
per-session Harness transcript/version/session identity record is incomplete,
and Claude Code was not tested.

R1 therefore proves the teacher-defined **local-folder plus external Agent
Harness boundary for this bounded, offline Codex experiment**. It does not
prove Claude Code compatibility, cloud Progress Report round-trip, the Cloud
API Proxy, cross-machine transport, a final package tree, or compatibility for
the other four Workflow types.

## Verification matrix

| # | Verification | Classification | Result and evidence |
|---|---|---|---|
| 1 | Package integrity is valid | `VERIFIED_FROM_FILES` | The self-contained validator returned `valid: true` for both the original and moved folders, with 20 declared files, package checksum `sha256:24790950e4ec3be8ee68dc5aa7103128c3ce15a494e6ee94d6f52d55380f0eaa`, and manifest checksum `sha256:9ca23b4ed5330cebf12b0630f0b11d2af98d50074500d6df070e414d1e1f0633`. |
| 2 | All four declared outputs exist | `VERIFIED_FROM_FILES` | `search_plan.md`, `candidate_papers.json`, `selected_papers.json`, and `literature_search_report.md` exist in both folders. The JSON shape, four-candidate screening, three-record selection, and offline/fictional disclosures passed bounded manual checks. |
| 3 | Inputs and pinned package files were not modified | `VERIFIED_BY_CHECKSUM` | Both validators checked every immutable manifest entry, including both inputs, the Workflow, Skill, prompt, schemas, instructions, shims, and validator, against its pinned checksum and byte size. |
| 4 | Progress Report checksums match current outputs | `VERIFIED_BY_CHECKSUM` | All four current output digests match the four references in the sole Progress Report. Its canonical self-checksum also recomputed successfully, and its context reference matches the context object's canonical self-checksum. |
| 5 | Session 2 did not repeat completed package work | `VERIFIED_FROM_FILES` | The completed context says no further task action is required, only one round-001 report exists, and no duplicate output or later report was created. This proves the observable package result; no transcript exists to prove unrecorded internal reasoning. |
| 6 | Session 2 did not overwrite outputs | `VERIFIED_BY_CHECKSUM` | Post-Session-2 output digests equal the round-001 Progress Report digests for all four outputs. |
| 7 | The moved package independently validates | `VERIFIED_FROM_FILES` | Running the moved folder's own `validate_package.py` returned `valid: true` with the same package and manifest identities. |
| 8 | Moved outputs match pre-move outputs | `VERIFIED_BY_CHECKSUM` | Diffing the pre-move and moved checksum snapshots returned exit code 0. A full recursive original-versus-moved file comparison also returned exit code 0. |
| 9 | Context and Progress Reports provide sufficient continuation state | `VERIFIED_FROM_FILES` | Context records package/Workflow identity, `COMPLETED` state, all completed outputs, decisions, unresolved issues, latest report, and a concrete next action. The report records completed work, current state, checksummed outputs, warnings, unresolved questions, and continuation instructions. |
| 10 | No absolute source-repository dependency exists | `VERIFIED_FROM_FILES` | The package validator is standard-library-only and imports no ReAgent module. It rejects machine-specific paths. The unchanged moved copy validates independently outside the source repository. |
| 11 | No credential exists | `VERIFIED_FROM_FILES` | Both full-folder validations passed the package's credential/private-key/environment/database/high-confidence secret checks. The proxy placeholder is disabled, has no URL, and contains no credential. |
| 12 | No provider call occurred | `OWNER_ATTESTED` | The owner attests that no provider or network search was used. Package files corroborate the offline design and disclosures but do not independently prove execution history. |
| 13 | No AgentRuntime or PostgreSQL dependency occurred | `VERIFIED_FROM_FILES` | Instructions, Workflow, Skill, validator, outputs, context, and report require only folder-local operations; the moved package validates without either dependency. The owner separately attests that neither was executed. |
| 14 | Package state alone carries the concrete research-task state | `VERIFIED_FROM_FILES` | The byte-identical moved folder carries task identity, completed work, outputs, decisions, unresolved issues, and next action without source-repository or server state. The fact that Session 3 was fresh in the moved folder is `OWNER_ATTESTED`. |

No required gate is `FAILED`. No gate required for this bounded Codex result is
`NOT_VERIFIED`; the limitations below prevent a stronger or cross-Harness
claim.

## Session evidence

| Session | Evidence classification | Accepted result |
|---|---|---|
| Session 1 | `OWNER_ATTESTED` for freshness and prompt; `VERIFIED_FROM_FILES` and `VERIFIED_BY_CHECKSUM` for resulting state | A fresh Codex session produced the four declared offline outputs, updated context, and appended one checksum-bound Progress Report. |
| Session 2 | `OWNER_ATTESTED` for freshness, no resume, and prompt; `VERIFIED_FROM_FILES` and `VERIFIED_BY_CHECKSUM` for resulting state | The completed boundary was preserved: no duplicate report/output appeared and no output digest changed. |
| Session 3 | `OWNER_ATTESTED` for freshness and prompt; `VERIFIED_FROM_FILES` and `VERIFIED_BY_CHECKSUM` for moved state | The moved folder remained independently valid and byte-identical, with unchanged task identity, completion state, outputs, and next action. |

The Progress Report identifies the executing Harness as `OpenAI Codex Agent
Harness` and records Session 1 work from `2026-08-03T09:56:29Z` through
`2026-08-03T09:58:44Z`. Product version and independent session identifiers
were not recorded.

## Checksum evidence

| Artifact | SHA-256 |
|---|---|
| `outputs/search_plan.md` | `b7c9ebec979530837d15865d6f158c1140f9facdb4aba51f9f85a8d35f3df7b0` |
| `outputs/candidate_papers.json` | `314c90155200079add506faafa361cd88be1219a81b7ee5d49d979de68076424` |
| `outputs/selected_papers.json` | `1f61b00f0465795222a875fae2ff930dbaa1259f31459611dd59c30e2e6571d2` |
| `outputs/literature_search_report.md` | `356b17b33bcd4c84bd33526a7a48a66d1ab6e00a25a99384c4f08274528d8f2a` |
| Progress Report canonical self-checksum | `a235c6651f7e35e65b773843e3ac6f914fb3e1b190903b00893bcf53fb41869e` |
| Context canonical self-checksum | `e9763179e0ab001037df8fdadd74691d631c17929ff616c3e43bd615eb2750e6` |

The standalone Session 1 output snapshot is missing. Session 1 output digests
are instead bound by the Progress Report. Current post-Session-2 outputs match
those values. The post-Session-2 and pre-move snapshots match, and the pre-move
and moved snapshots match with diff exit code 0.

## State-authority and hosted-boundary findings

The local package, rather than hosted runtime state, contains the concrete
task's instructions, pinned identities, immutable inputs, outputs, current
context, and append-only progress. The moved-folder result demonstrates that
the source repository is not needed to validate or interpret that state.

No production backend action was part of the package execution. The folder
declares `hosted_agent_runtime_required: false`, the Skill prohibits hosted
runtime and provider behavior, and the validator is self-contained. Actual
non-use of AgentRuntime, PostgreSQL, providers, and the network is
owner-attested because files cannot independently establish a complete runtime
history.

## Warnings and deferred evidence

1. Fresh-session, no-resume, exact-prompt, no-prior-explanation, and runtime
   non-use facts are owner-attested rather than independently logged.
2. A standalone Session 1 checksum snapshot was not captured; the Progress
   Report plus the post-Session-2 snapshot closes the output-digest chain.
3. Codex product version, independent session identifiers, and complete
   per-session transcripts/start-end records were not captured.
4. `validate_package.py` validates package integrity but does not validate
   dynamic output schemas or the Progress Report's canonical self-checksum;
   this audit performed those checks separately.
5. The bundled v0.1 Progress Report schema permits the observed report ID and
   treats `context_checksum` as an unconstrained SHA-256 value. Repository-side
   helper code is stricter: it rejects the uppercase timestamp in the observed
   report ID and expects the raw context-file digest rather than the context
   object's canonical self-checksum. R2 must normalize these semantics before
   accepting uploads.
6. Claude Code is **UNTESTED**. Its shim exists and is immutable, but no Claude
   Code execution, continuation, or moved-folder compatibility claim is made.

## Exactly one recommended next milestone

**R2 — Progress Report upload and cloud progress aggregation**, including
normalization and validation of the v0.1 report-ID and context-checksum
semantics before upload acceptance.
