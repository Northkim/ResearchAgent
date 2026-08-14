# Owner Real Research Test

This guide opens only the single-owner, loopback, local real-research gate.
It does not authorize public deployment or production Provider use.

## 1. Choose the correct mode

| Purpose | Start command | Literature Provider | Evidence |
|---|---|---|---|
| Controlled product test | `make controlled-start` | deterministic fake | fictional and labelled demo evidence |
| Developer debugging | `make dev` with explicit developer configuration | profile-dependent | developer-selected |
| Owner local real research | `make owner-start` after one-time setup | real OpenAlex through the ReAgent Backend | publication metadata and available abstracts |
| Public production | not available | not authorized | `R3D_PRODUCTION_PROVIDER_GATE = CLOSED` |

Do not reuse a controlled/demo Project for real research. Create a new Full
Research Project so fictional and real evidence never share one research
lineage.

## 2. Provider disclosure and evidence boundary

Before every NORMAL Literature session, the Local Workspace command displays a
disclosure and requires the exact confirmation `continue-real-search`. Until
that confirmation is accepted by the Backend, no OpenAlex session or Provider
call can open. The confirmation is short-lived, exact-Project/Package/Workflow
scoped, consumed once, and is not a permanent preference.

The ReAgent Backend sends each confirmed search query to OpenAlex, a third-party
service. OpenAlex may receive the query and normal network request metadata.
ReAgent retrieves publication metadata and an abstract when OpenAlex supplies
one. It does not retrieve full text or PDFs. This is not a private or offline
search.

The owner-controlled ReAgent PostgreSQL database retains query checksum and
length evidence, call/cost/rate metadata, and normalized Provider records. It
does not retain the complete query text in the Proxy request row. The complete
query plan, normalized operation results, memory, outputs and Artifact bytes
remain in the Local Workspace. There is no automatic retention-expiry or
deletion promise in this owner-local version; retained database records remain
until a separately owner-approved cleanup is performed.

## 3. First-time owner setup

Owner secure local startup currently supports macOS. PostgreSQL and the Conda
environment `reagent-dev` must already exist. From the repository root, run:

```zsh
conda activate reagent-dev
make owner-setup
```

The setup asks for the loopback PostgreSQL database name, port and user, checks
connectivity and reports whether its migration is current. It does not create,
drop, reset or migrate the database. The current owner defaults are
`127.0.0.1:5432`, `reagent_local_v01`, and the current macOS account.

The non-secret, versioned configuration is written atomically to
`~/.config/reagent/config.toml` (or the equivalent absolute
`$XDG_CONFIG_HOME/reagent/config.toml`). Its directory is owner-only and its
file mode is `0600`. It contains only profile, loopback database identity,
loopback ports and whether OpenAlex is enabled. It never contains a database
password, Provider credential, Project/Workflow identity, or research state.

For OpenAlex, the macOS Keychain command prompts securely. The credential uses
the ReAgent-specific service `com.reagent.owner-local-real.openalex` and
account `openalex-api-key`; its value does not appear in shell history, Make
arguments, argv, stdout, the repository `.env`, or `config.toml`.

Rerun `make owner-setup` to keep or explicitly replace the credential. To
remove it without changing config or research state:

```zsh
make owner-secret-remove
```

Keep the credential out of `workspace-bootstrap.json`, `project.json`, a
Package, Capsule, memory, output, Artifact and Progress.

## 4. Daily startup and diagnostics

In a fresh terminal, no owner runtime variables need to be exported:

```zsh
cd /path/to/ResearchAgent
make owner-start
```

The trusted startup helper validates the user config, PostgreSQL identity,
migration, Keychain item and ports. It retrieves the Keychain credential only
inside the helper, gives it only to the FastAPI Backend, and launches Next.js
with a scrubbed environment. It never exports the credential to the parent
shell and never performs an automatic migration.

Expected bounded output is equivalent to:

```text
ReAgent Owner Runtime
Database: reagent_local_v01 - ready
Migration: 20260813_0021 - current
OpenAlex: configured
Backend: http://127.0.0.1:8000
Frontend: http://127.0.0.1:3000
Mode: owner-local real research
```

If startup is not ready, use:

```zsh
make owner-doctor
```

Doctor reports config validity, PostgreSQL reachability, migration equality,
Keychain presence and port availability without retrieving or printing the
credential. A missing setup points to `make owner-setup`; a migration mismatch
fails closed and requires separately reviewing the approved migration process.

Repository `.env` remains a developer/runtime input for `make dev`; it is not
owner runtime authority. `make controlled-start` reads neither owner config nor
the owner Keychain and remains deterministic DEMO-only.

## 5. Verify the local services

```bash
curl --fail --silent --show-error http://127.0.0.1:8000/health
curl --fail --silent --show-error http://127.0.0.1:8000/ready
```

Both commands must return HTTP 200. There is no standalone public Provider
readiness endpoint. OpenAlex-enabled startup fails closed when the Backend key
or adapter is missing; the exact Workspace run also verifies that NORMAL is
server-authorized before asking for consent.

## 6. Create an independent real Project

Open <http://127.0.0.1:3000/projects> and create:

- setup: **Full Research Project**;
- suggested name: `real-research-test-1`;
- suggested topic: `Multi-agent reinforcement learning for urban drainage systems`.

Download **Workspace setup** as `workspace-bootstrap.json`. Do not reuse the
controlled `project1` Workspace.

## 7. Bootstrap and sync

In a normal terminal, from the directory containing the downloaded client and
descriptor:

```bash
python reagent_local.py bootstrap ./reagent-workspace \
  --descriptor ./workspace-bootstrap.json
cd ./reagent-workspace
python reagent_local.py sync .
python reagent_local.py workflow list .
```

Do not edit internal JSON, locks, indexes, receipts or checksums.

## 8. Run real Literature Search

```bash
python reagent_local.py run . \
  --workflow literature-search-local-experimental
```

Expected before Codex starts:

- the server-authorized mode is `normal`;
- Provider is OpenAlex through the ReAgent Proxy;
- the third-party disclosure is printed;
- the command waits for `continue-real-search`;
- any other input cancels with zero Provider calls.

After confirming, review the search plan, screen candidates and type `finish`
only after the selected set is correct. NORMAL output must describe **real
Provider metadata** and the metadata/abstract-only limitation. It must not
contain `FICTIONAL DEMO EVIDENCE`.

```bash
rg -n "FICTIONAL DEMO EVIDENCE" capsules/literature-search-local-experimental
find capsules/literature-search-local-experimental \
  -path '*/outputs/artifacts/selected-paper-library/sha256-*.json' -print
python reagent_local.py artifact refresh .
```

The first command should print nothing. If no papers were included, Literature
may still finish honestly as insufficient evidence, but Idea Discovery will
remain blocked until a Literature result contains at least one selected paper.

If the Harness is interrupted, run `python reagent_local.py workflow list .`
and use the displayed Resume command. Completed query-result checksums are
reused and are not automatically sent to OpenAlex again. Explicit finish is
still required.

## 9. Bind and materialize the Literature Artifact

In the browser Workflow Board, select the exact Literature Search Artifact for
Idea Discovery. Then run:

```bash
python reagent_local.py sync .
python reagent_local.py artifact refresh .
python reagent_local.py artifact materialize . \
  --workflow idea-discovery-local-experimental
python reagent_local.py workflow list .
```

Materialization copies the exact checksum-bound Artifact. It never selects
`latest` automatically and never reads a sibling Capsule directly.

## 10. Run real Idea Discovery

```bash
python reagent_local.py run . \
  --workflow idea-discovery-local-experimental
```

Idea Discovery uses only the materialized `selected-paper-library/v1`. Review
the candidate ideas, evidence/inference distinctions, assumptions, risks and
validation needs. The Agent begins automatically at **INPUT_REVIEW**: it reads
the pinned local Workflow instructions and exact materialized Literature
Artifact, reports the selected-paper count and metadata/abstract-only boundary,
summarizes the bounded evidence, and asks for owner priorities and constraints.
There is no startup phrase such as `start`, `begin`, or `generate ideas`.
Global novelty is not proven, full text was not reviewed, and feasibility
requires further validation. Explicitly select exactly one idea before
completing the round.

Expected output:

- `candidate-ideas/v0.1` and an evidence-grounded report;
- one explicitly selected idea;
- content-addressed `selected-research-idea/v1`;
- bounded Progress and exact source-Literature provenance.

If local Idea finalization succeeded but Cloud Progress acknowledgement did
not, `workflow list` reports **Progress Upload Pending** instead of claiming
that Cloud completion is current. Run the same printed Idea command again. The
generic Workspace client validates the existing append-only report chain,
uploads only the missing execution rounds in order, and exits without starting
Codex or changing the selected Idea Artifact. Do not rerun Literature Search,
edit Progress JSON, or recreate the Project/Workspace.

### Existing Idea 0.2 Capsule after this repair

An existing Workflow Instance remains immutably pinned to Capsule 0.2.0 and is
not silently upgraded. In the same Project, use the Workflow Board to retire
that Idea Instance, add Idea Discovery again, and bind the **existing** real
Literature Artifact to the new Instance. Then run:

First stop an older running owner process and apply the approved seed-only
migration once from the repository root (it publishes Capsule metadata and
does not delete Project or Artifact data):

```bash
make stop
REAGENT_DATABASE_URL='<passwordless loopback owner database URL>' \
  conda run --no-capture-output -n reagent-dev alembic upgrade head
make owner-start
```

The generic client copied into an older Workspace is also versioned startup
code and does not rewrite itself during sync. Download the current
`reagent_local.py` again from the Project's Local Guide, replace only the
Workspace-root client with that reviewed download, and keep the old Workspace
state/Capsules unchanged. Then retire/add/bind in the browser and, from the
existing Workspace, run:

```bash
python reagent_local.py sync .
python reagent_local.py artifact refresh .
python reagent_local.py artifact materialize . \
  --workflow idea-discovery-local-experimental
python reagent_local.py run . \
  --workflow idea-discovery-local-experimental
```

The new Instance resolves Workflow Definition 0.2.0 / Capsule 0.4.0. The old
Capsule and its local history are retained. Do not rerun OpenAlex, recreate the
Project, copy an Artifact across Projects, edit the Installed Lock, or replace
Capsule bytes manually.

## 11. Continue with the Experiment scaffold

The current Experiment Workflow uses Definition 0.3.0 / Capsule 0.5.0. After
selecting the exact `selected-research-idea/v1` and any optional exact
Literature Artifact, refresh and materialize, then use the printed command:

```bash
python reagent_local.py artifact refresh .
python reagent_local.py artifact materialize . \
  --workflow reproduction-experiment-local-experimental
python reagent_local.py run . \
  --workflow reproduction-experiment-local-experimental
```

The Agent begins automatically at **INPUT_REVIEW**. It reports the exact input
and configured/unconfigured Resource categories, then states that this is an
`IDEA_EXPERIMENT` Scaffold Core: paper reproduction is not enabled, Resource
bytes are not executed, and no simulation, training, metric, or scientific
result is produced. A valid final record remains
`PLACEHOLDER_NOT_EXECUTED` with `actual_results = null`.

An existing Experiment Instance pinned to Capsule 0.3.0 is never upgraded in
place. To continue the same Project after this repair, stop the old services,
apply the approved seed-only migration, and restart:

```bash
make stop
REAGENT_DATABASE_URL='<passwordless loopback owner database URL>' \
  conda run --no-capture-output -n reagent-dev alembic upgrade head
make owner-start
```

Download the current `reagent_local.py` from that Project's Local Guide and
replace only the Workspace-root client. In the Workflow Board, retire the old
Experiment 0.3.0 Capsule Instance, add Reproduction & Experiment again, bind
the **existing same-Project** selected Idea (and optional Literature Artifact),
then run:

```bash
python reagent_local.py sync .
python reagent_local.py artifact refresh .
python reagent_local.py artifact materialize . \
  --workflow reproduction-experiment-local-experimental
python reagent_local.py run . \
  --workflow reproduction-experiment-local-experimental
```

The new Instance resolves Definition 0.3.0 / Capsule 0.5.0. Do not rerun
Literature or Idea, copy Artifacts across Projects, edit the Installed Lock, or
replace Capsule bytes manually.

## 12. Continue with Writing and Review scaffold UX

Migration `20260813_0021` publishes Writing and Review Capsule 0.4.0 without
changing either Definition 0.2.0. A new Instance resolves the repaired Capsule
and automatically begins `INPUT_REVIEW`; it never requires `start`, `write
paper`, or `review draft`.

First preserve and synchronize the two already-completed local executions. Do
not retire them, resume Codex, regenerate either Artifact, or edit Progress or
context JSON. Stop the older owner runtime, apply migration `0021`, restart,
then download the current Workspace-root `reagent_local.py` from the Local
Guide and replace only that root client. In the existing Workspace run:

```bash
python reagent_local.py sync .
python reagent_local.py workflow list .
python reagent_local.py run . \
  --workflow-instance wfi-38e75d740c6a4b2fbbbacd898e9adc96
python reagent_local.py run . \
  --workflow-instance wfi-2219af640f4a4cb58b22a4c7f91b4cc6
python reagent_local.py workflow list .
```

For each `Progress Upload Pending` entry, prefer the exact command printed by
`workflow list`; the explicit commands above identify the evidence-reported
Writing and Experiment Instances. The repaired root client proves the exact
historical terminal-context fingerprint. For Experiment Capsule 0.4.0 it also
proves that the current `outputs/experiment_plan.md` is byte-for-byte the
deterministic replacement written by that exact historical runner, while the
typed `experiment-record/v1` remains exact. It then uploads the existing
immutable report only, verifies the Cloud projection, and stores its
acknowledgement. It starts no Harness, creates no new round, and changes no
plan, context, Progress Report, or Artifact bytes. An arbitrary or one-byte
different Markdown file remains `Local Progress Invalid / Repair Required`.

If the existing Full Research Project already contains an unstarted Review
Capsule 0.3.0 Instance, retire only that Instance in the Workflow
Board and add Review again to receive Capsule 0.4.0. Keep the Project, Workspace,
Literature, selected Idea, Experiment output, Progress, and Artifact history.
Then update only the Workspace-root `reagent_local.py` from the Local Guide,
sync, explicitly bind Draft A and the desired Literature/Experiment Artifacts,
materialize, and run the printed Review command. Do not copy or replace any
installed Capsule bytes manually, and do not regenerate Draft A.

For the revision loop, keep Writing #1 and Review #1. Add Writing #2, explicitly
bind the same Idea and Literature plus Draft A as `prior_manuscript` and Review
A as `review_feedback`, then run the exact instance-specific command printed by
`workflow list`. Draft A and Review A remain immutable.

## 13. Inspect and stop

Use the Project Workflow Board, Artifacts and Progress views to inspect bounded
Cloud metadata. Inspect research bytes only in the Local Workspace.

```bash
make stop
```

This stops only the ReAgent Backend and Frontend. It does not stop PostgreSQL.
It does not remove the owner config, Keychain item, database, Projects, or
Workspace. A later `make owner-start` uses the persisted configuration and
credential again; no setup or export is needed.

## 14. Owner-local residual risk

Codex remains a general-purpose Agent Harness and may have network capability
according to the owner's local Codex configuration. This version does not add
an OS-level egress sandbox. ReAgent removes the OpenAlex credential and ReAgent
session/database secrets from Capsule and Codex environments, and the supported
Literature Provider path uses only the loopback Backend Proxy. Stronger Harness
isolation, public privacy UX, authentication, production secret management and
rotation remain future production gates.

```text
OWNER_LOCAL_REAL_RESEARCH_GATE = OPEN
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```
