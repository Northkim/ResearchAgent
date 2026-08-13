# Owner Complete Product Test

This guide is the handoff test for the complete ReAgent product skeleton. It
uses the real Project, Workflow, Workspace, sync, Skill, Artifact, Resource,
Progress, and recovery paths. Literature Search and Idea Discovery have
reviewed cores. Writing, Review, and Reproduction & Experiment have real
product flows but intentionally produce unmistakable scaffold placeholders.

Do not use owner research data, a live Provider key, GitHub credentials, or a
Hugging Face token for this test. Use one isolated controlled PostgreSQL
database and a temporary or dedicated test Workspace.

This guide is a manual owner test. Its `REAGENT_DATABASE_URL` may intentionally
select the owner's persistent continuity database. Do not run H1/F1F
Playwright qualification against that manual server. Automated qualification
uses `make test-controlled-e2e`, which creates, marks, migrates, verifies, and
drops a separate generated database. Destructive PostgreSQL fixtures will fail
closed if given `reagent_local_v01`, `ProjectDB`, `reagent`, an unmarked
database, or a mismatched generated identity.

## 1. Start the controlled environment — Terminal

Follow the operator steps in
[`CONTROLLED_TESTING_RUNBOOK.md`](../operations/CONTROLLED_TESTING_RUNBOOK.md),
then open the loopback frontend. Expected: readiness is healthy and no secret
or database URL appears in the browser.

## 2. Create the Project — Web

Choose **Full Research Project**, enter a synthetic topic, and read the
confirmation before creating it. Expected: the confirmation lists all five
Workflows and explicitly identifies Writing, Review, and Experiment as
prototype/scaffold cores. The Project Overview recommends local setup and then
Literature Search; it does not claim the Project is a pipeline.

## 3. Bootstrap and sync — Web, then Terminal

Download **Workspace setup** as `workspace-bootstrap.json`. Run the exact
copyable command shown in Help:

```bash
python3 reagent_local.py bootstrap ./reagent-workspace \
  --descriptor ./workspace-bootstrap.json
cd ./reagent-workspace
python3 reagent_local.py sync .
python3 reagent_local.py workflow list .
```

Expected: five Capsules are installed. Writing, Review, and Experiment contain
their built-in reviewed Skills automatically. A second `sync` reports
`NO_CHANGE`. Do not edit `.reagent`, a manifest, lock, index, receipt, or UUID.

## 4. Run Literature Search — Terminal, inspect in Web

Use the Literature Search command printed by `workflow list`. Work only with
the controlled deterministic literature fixture. Review the search plan and
candidate list, explicitly select papers, and type `finish` only when ready.

Expected: `selected-paper-library/v1` is produced, Progress appears in the Web,
and Literature Search remains marked **Reviewed Core**. The fixture content is
test evidence, not a real literature conclusion.

Recovery check: if the interactive Harness is interrupted after a validated
search checkpoint but before Artifact publication, run
`python3 reagent_local.py workflow list .`. Expected: Literature Search says
**Interrupted** or **Finalization Pending**, with **Next: Resume**. Run the same
displayed Workspace command in a fresh terminal/Harness session. It must reuse
the checksum-bound query results without another Provider search and require
explicit finalization again when prior consent was not durably committed. Do
not re-bootstrap, edit round-control JSON, or recreate the Project.

## 5. Run Idea Discovery — Web, then Terminal

On the Idea Discovery card, select the exact Literature result. Then run:

```bash
python3 reagent_local.py artifact refresh .
python3 reagent_local.py artifact materialize . \
  --workflow idea-discovery-local-experimental
python3 reagent_local.py run . \
  --workflow idea-discovery-local-experimental
```

Review the candidate ideas, explicitly mark exactly one as selected, and
finish the round. The Agent must begin automatically at **INPUT_REVIEW**, state
the selected-paper count and metadata/abstract-only limits, summarize the
bounded evidence, and ask for owner priorities; no hidden startup phrase is
required. Expected: `selected-research-idea/v1` has exact Literature provenance;
no `latest` input is selected automatically.

## 6. Exercise the Experiment Resource shell — Web, then Terminal

Open Reproduction & Experiment. Add a credential-free Resource reference with
an exact immutable revision and expected SHA-256, then explicitly bind it to
the matching optional requirement. GitHub and Hugging Face references are
metadata-only in this version: resolving either must report
`RESOURCE_RESOLVER_NOT_IMPLEMENTED`, and **must not** claim bytes were
downloaded.

For the controlled `LOCAL_TEST` qualification only, the operator supplies a
deterministic fixture root and enables the qualification gate. Resolve it with:

```bash
REAGENT_CONTROLLED_RESOURCE_TEST=1 python3 reagent_local.py resource resolve . \
  --workflow reproduction-experiment-local-experimental \
  --local-test-fixture-root /path/supplied/by/operator
python3 reagent_local.py resource status .
```

Expected: the local Resource Index says `RESOLVED_VERIFIED`. Cloud stores only
reference metadata, never the fixture bytes or an absolute local path.

## 7. Run Experiment — Web, then Terminal

Select the exact Idea Artifact and any optional Literature input. Resolve every
Resource you chose, refresh/materialize Artifacts, and use the Experiment run
command printed by `workflow list`.

Expected: the Agent begins automatically at **INPUT_REVIEW**, identifies the
exact inputs and configured/unconfigured Resource categories, and explains
that this is an `IDEA_EXPERIMENT` Scaffold Core with paper reproduction and all
real execution disabled. No hidden startup phrase is required.
`experiment-record/v1` and `outputs/experiment_plan.md` are marked
`SCAFFOLD EXPERIMENT PLACEHOLDER`; `execution_status` is
`PLACEHOLDER_NOT_EXECUTED` and `actual_results` is null. No experiment,
repository code, dataset, model, or checkpoint is executed.

## 8. Run Writing #1 — Web, then Terminal

Explicitly select the Idea and Literature results. Optionally select the
Experiment record. Refresh, materialize, and use the Writing run command.

Expected: `manuscript-draft/v1` and `outputs/manuscript.md` visibly say
`SCAFFOLD PLACEHOLDER`. The provenance lists every selected input. Do not
expect substantive academic prose, citations, novelty claims, or results.

## 9. Run Review #1 — Web, then Terminal

Explicitly select Draft A, materialize it, and run Review.

Expected: `review-report/v1` is marked `SCAFFOLD REVIEW PLACEHOLDER` and uses
`INSUFFICIENT_EVIDENCE`. It is not a substantive peer review and does not
predict acceptance.

## 10. Create Writing #2 — Web, then Terminal

Use the Review card's suggested action to add a new Writing Workflow. Keep
Writing #1. Explicitly bind the same Idea and Literature, Draft A as the prior
manuscript, Review A as review feedback, and any desired Experiment record.
Run `sync`, then refresh/materialize and run the exact Writing #2 command shown
by `workflow list`.

Expected: Draft B is a new immutable Artifact; Draft A and Review A are
unchanged. When the stable key is ambiguous, the CLI prints and requires a
friendly Writing #2 command backed by its exact instance identity—no raw UUID
copy is needed from the browser.

## 11. Inspect the product width — Web and Terminal

Open Overview, Workflows, Progress, and Help. Also run:

```bash
python3 reagent_local.py workspace status .
python3 reagent_local.py workflow list .
python3 reagent_local.py artifact status .
python3 reagent_local.py resource status .
```

Expected: Progress shows Literature, Idea, Experiment #1, Writing #1, Review
#1, and Writing #2 independently. Reviewed and Scaffold maturity remain
separate from readiness. The Overview does not claim a false 100% research
completion.

## 12. Close and recover — Terminal and Web

Close the browser and terminal. Restart the controlled backend/frontend and,
if this is part of the operator exercise, PostgreSQL. Reopen the same Project
and Workspace, then run `workflow list` again.

Expected: Project configuration, Manifest, Workflow Instances, Progress,
Artifact and Resource metadata, Skill metadata, and installation
acknowledgement reload from Cloud persistence. Local inputs, outputs, memory,
Artifact bytes, Resource bytes, and continuity remain in the Workspace. No
chat history, Project recreation, database access, or internal JSON edit is
required.

Record observations in [`OWNER_TEST_OBSERVATIONS.md`](OWNER_TEST_OBSERVATIONS.md).
