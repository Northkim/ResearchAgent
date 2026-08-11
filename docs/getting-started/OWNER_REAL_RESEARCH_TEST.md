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
Migration: 20260806_0017 - current
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
validation needs. Global novelty is not proven, full text was not reviewed,
and feasibility requires further validation. Explicitly select exactly one
idea before completing the round.

Expected output:

- `candidate-ideas/v0.1` and an evidence-grounded report;
- one explicitly selected idea;
- content-addressed `selected-research-idea/v1`;
- bounded Progress and exact source-Literature provenance.

## 11. Inspect and stop

Use the Project Workflow Board, Artifacts and Progress views to inspect bounded
Cloud metadata. Inspect research bytes only in the Local Workspace.

```bash
make stop
```

This stops only the ReAgent Backend and Frontend. It does not stop PostgreSQL.
It does not remove the owner config, Keychain item, database, Projects, or
Workspace. A later `make owner-start` uses the persisted configuration and
credential again; no setup or export is needed.

## 12. Owner-local residual risk

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
