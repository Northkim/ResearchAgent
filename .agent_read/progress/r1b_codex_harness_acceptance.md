# R1B Codex Harness Acceptance

Date: 2026-08-03  
Status: **PASS_WITH_WARNINGS**  
R1 state: **CODEX_LOCAL_FOLDER_BOUNDARY_PROVEN; CLAUDE_CODE_UNTESTED**

## Outcome

Three externally run Codex sessions exercised the R1A package. The owner
attests that all three were fresh, Session 2 did not use `codex resume`, Session
3 started in the moved folder, every session received only `Read the package
instructions and continue the task.`, no prior project explanation was given,
and no provider, network search, AgentRuntime, or PostgreSQL execution occurred.
These execution-history facts are `OWNER_ATTESTED`, not independently proven by
files.

Both the original and moved folders independently returned `valid: true` from
their self-contained validators with package checksum
`sha256:24790950e4ec3be8ee68dc5aa7103128c3ce15a494e6ee94d6f52d55380f0eaa`
and manifest checksum
`sha256:9ca23b4ed5330cebf12b0630f0b11d2af98d50074500d6df070e414d1e1f0633`.
All immutable inputs and pinned files remained checksum-valid.

All four declared outputs exist. Their current checksums match the sole
round-001 Progress Report and the post-Session-2, pre-move, and moved checksum
snapshots. Pre-move versus moved diff returned exit 0; the complete original
and moved folder trees also compared equal with exit 0. Session 2 created no
duplicate output/report and did not change an output digest.

Context and the Progress Report carry the completed Workflow state, output
paths/checksums, decisions, unresolved issues, latest report, and concrete next
action. The moved folder therefore carries the concrete research-task state
without the source repository, AgentRuntime, PostgreSQL, or hidden server
checkpoint state.

## Output checksums

- `outputs/search_plan.md`:
  `sha256:b7c9ebec979530837d15865d6f158c1140f9facdb4aba51f9f85a8d35f3df7b0`
- `outputs/candidate_papers.json`:
  `sha256:314c90155200079add506faafa361cd88be1219a81b7ee5d49d979de68076424`
- `outputs/selected_papers.json`:
  `sha256:1f61b00f0465795222a875fae2ff930dbaa1259f31459611dd59c30e2e6571d2`
- `outputs/literature_search_report.md`:
  `sha256:356b17b33bcd4c84bd33526a7a48a66d1ab6e00a25a99384c4f08274528d8f2a`
- Progress Report canonical self-checksum:
  `sha256:a235c6651f7e35e65b773843e3ac6f914fb3e1b190903b00893bcf53fb41869e`

## Warnings

- no standalone Session 1 checksum snapshot; the Progress Report records the
  Session 1 output digests and post-Session-2 files match them;
- no independent freshness transcript, Codex version, or session identifiers;
- the self-validator does not validate dynamic output/report content, so this
  acceptance audit checked output contracts and report checksums separately;
- repository-side report-ID and context-file-checksum semantics are stricter
  than the bundled v0.1 schema and must be normalized before R2 upload;
- Claude Code remains untested.

## Boundary conclusion

R1 proves the teacher-defined local-folder and external-Harness boundary for
the bounded offline Codex experiment. It does not prove Claude Code
compatibility, a final folder schema, cloud upload/projection, API-proxy use,
or other Workflow types. Hosted AgentRuntime remains preserved optional/internal
work and was not used as the concrete research executor.

Full evidence classification and limitations are recorded in
`docs/acceptance/R1B_CODEX_HARNESS_ACCEPTANCE_REPORT.md`.

## Exactly one recommended next milestone

**R2 — Progress Report upload and cloud progress aggregation**, beginning with
normalization of report-ID and context-checksum semantics.
