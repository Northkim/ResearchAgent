# R1B External Agent Harness Acceptance

Status: **NOT EXECUTED — `HARNESS_ACCEPTANCE_PENDING`**

R1B tests whether a real fresh Agent Harness can understand, execute and
continue the package from files alone. R1A compiler/unit tests are not a
substitute. Do not give the Harness prior ReAgent context.

## Preconditions

- use the ignored ZIP produced by the R1A command;
- choose a clean directory outside this source repository;
- do not copy credentials or an environment file;
- keep network unavailable: the package fixture is wholly offline;
- record the package, manifest and ZIP checksums from the build receipt.

## First fresh Codex session

1. Extract the ZIP into the clean directory.
2. Run `python validate_package.py --root . --pristine`; require success.
3. Start a new Codex session with that directory as its workspace.
4. Give exactly this instruction and no project explanation:

   `Read the package instructions and continue the task.`

5. Verify Codex discovers the shim and follows canonical `AGENT.md`.
6. Verify it reads the manifest, Workflow instructions, pinned Skill/prompt,
   immutable request and fictional catalog.
7. Verify it performs the task locally without asking ReAgent backend to run it.
8. Verify these files are created:

   - `outputs/search_plan.md`;
   - `outputs/candidate_papers.json`;
   - `outputs/selected_papers.json`;
   - `outputs/literature_search_report.md`.

9. Verify outputs disclose offline fictional scope and make no real-search
   claim.
10. Verify `memory/context.md` records completed work and a concrete next action.
11. Verify one new checksum-bound report exists under
    `memory/progress/reports/`, without changing the supplied README.
12. Run `python validate_package.py --root .`; immutable validation must still
    pass while allowing declared Harness state.
13. Close the session completely.

## Second fresh Codex session

1. Start another new Codex session in the same folder with no chat history.
2. Give exactly:

   `Read the package instructions and continue the task.`

3. Verify it reads context and the latest Progress Report.
4. Verify it identifies completed outputs and does not repeat screening.
5. Verify it follows the recorded next action or reports that the completion
   boundary is already satisfied.
6. Any substantive correction must create a new output version/report rather
   than silently rewriting append-only history.

## Moved-folder test

1. Copy the completed folder to a different clean local path.
2. Run its self-contained validator there.
3. Start a third fresh Codex session with the same one-line instruction.
4. Verify no source-repository, database, server checkpoint, absolute original
   path or hidden conversation is needed.
5. Verify task identity, completed state and next action are unchanged.

## Claude Code follow-up

If Claude Code is available, repeat the first/second-session and moved-folder
checks. Confirm that `CLAUDE.md` leads to canonical `AGENT.md`. Unavailability
is recorded as pending compatibility evidence, not a package failure and not a
claim of acceptance.

## Acceptance record

Record for every session:

- Harness product/version and session identity;
- start/end time and workspace location classification (not private absolute path);
- validator result before and after work;
- files read/written and output/report checksums;
- whether any repeated work, undeclared write, network attempt or hidden
  dependency occurred;
- instruction ambiguity, failure, workaround and unresolved tree question.

R1B passes only after fresh-session execution, folder-only continuation and
moved-folder continuation are observed. Until then the status remains
`HARNESS_ACCEPTANCE_PENDING`. Do not infer Claude Code compatibility from Codex
evidence.
