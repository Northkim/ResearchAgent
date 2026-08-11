# Owner Real Research Test

This guide opens only the single-owner, loopback, local real-research gate.
It does not authorize public deployment or production Provider use.

## 1. Choose the correct mode

| Purpose | Start command | Literature Provider | Evidence |
|---|---|---|---|
| Controlled product test | `make controlled-start` | deterministic fake | fictional and labelled demo evidence |
| Owner local real research | `make dev` with the two OpenAlex variables below | real OpenAlex through the ReAgent Backend | publication metadata and available abstracts |
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

## 3. Configure the Backend-only credential

Keep `REAGENT_OPENALEX_API_KEY` out of the repository `.env`, Workspace,
Capsules and shell command arguments. In a dedicated macOS `zsh` terminal:

```zsh
cd /path/to/ResearchAgent
conda activate reagent-dev
read -s "REAGENT_OPENALEX_API_KEY?OpenAlex API key: "
echo
export REAGENT_OPENALEX_API_KEY
export REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED=1
make dev
```

The startup wrapper passes the key only to FastAPI. It explicitly removes
Provider credentials from the Next.js build/server process. The Workspace
launcher also removes Provider credentials before starting every Capsule.
Never put the key in `workspace-bootstrap.json`, `project.json`, a Package,
memory, output, Artifact or Progress file.

`REAGENT_DATABASE_URL` remains the owner/manual runtime database setting. It
may be exported separately or loaded through the existing ignored database
dotenv support. That dotenv loader is not a Provider secret loader.

## 4. Verify the local services

```bash
curl --fail --silent --show-error http://127.0.0.1:8000/health
curl --fail --silent --show-error http://127.0.0.1:8000/ready
```

Both commands must return HTTP 200. There is no standalone public Provider
readiness endpoint. OpenAlex-enabled startup fails closed when the Backend key
or adapter is missing; the exact Workspace run also verifies that NORMAL is
server-authorized before asking for consent.

## 5. Create an independent real Project

Open <http://127.0.0.1:3000/projects> and create:

- setup: **Full Research Project**;
- suggested name: `real-research-test-1`;
- suggested topic: `Multi-agent reinforcement learning for urban drainage systems`.

Download **Workspace setup** as `workspace-bootstrap.json`. Do not reuse the
controlled `project1` Workspace.

## 6. Bootstrap and sync

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

## 7. Run real Literature Search

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

## 8. Bind and materialize the Literature Artifact

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

## 9. Run real Idea Discovery

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

## 10. Inspect and stop

Use the Project Workflow Board, Artifacts and Progress views to inspect bounded
Cloud metadata. Inspect research bytes only in the Local Workspace.

```bash
make stop
```

This stops only the ReAgent Backend and Frontend. It does not stop PostgreSQL.
Remove the key from the owner shell after shutdown:

```zsh
unset REAGENT_OPENALEX_API_KEY
unset REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED
```

## 11. Owner-local residual risk

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
