# R3C OpenAlex Structural Diagnostic Live Acceptance

Status: **READY FOR SEPARATE OWNER AUTHORIZATION; NOT EXECUTED**

Date: 2026-08-04

Governing ADRs: 0012 and 0013

This is a future acceptance plan, not authorization, a live result, or an
R3C-A retry. It permits no action until the owner opens its separate gate.

## 1. Objective

Use at most one fictional public OpenAlex Works search to capture exactly one
privacy-safe `reagent.openalex-structural-diagnostic/v0.1` event from the
committed R3C-N2-I implementation. The run diagnoses structure only. It must
not remediate normalization, retry, retain a Provider value, or claim live
compatibility acceptance.

## 2. Immutable baseline gate

The owner authorization must name the exact committed R3C-N2-I Git hash. Before
reading owner inputs, verify that exact hash and its required ancestors,
`main`, clean status/porcelain, no staged or untracked files, `git diff --check`,
and commit history. Any mismatch blocks the run. Do not reset, restore, clean,
rebase, amend, squash, or alter attempt-0, retry-1, R3C-N1, or N2-I evidence.

## 3. New owner inputs

Require a new owner attestation and new owner-controlled OpenAlex key file.
Both path variables identify regular non-symlink files outside Git, every
Workflow Package, `.env`, and `runtime_data/`; files must be mode `0600` and
their parent directory inaccessible to group/world users.

The attestation must explicitly authorize only this diagnostic, one maximum
Provider call, one fictional public non-sensitive query, no paid/prepaid
overage, the exact maximum cost, temporary structural logging, and cleanup.
Read and validate the attestation first. Inspect key-file metadata next. Do not
read the key until the source recheck passes. Never print, hash, describe, log,
persist, or commit key contents.

## 4. Current official-source recheck

Before key read, repeat the committed official-source gate from only approved
OpenAlex documentation domains. Do not contact the Provider API. Reconfirm the
key mechanism, Works path, search parameter, selected fields, maximum results,
exact price/cost evidence, approved rate evidence, Terms, and Privacy. Record
UTC retrieval time, title/domain, revision date where present, byte fingerprint,
and affected decision. A material change blocks before key read.

This source review is engineering evidence, not legal advice.

## 5. Isolated execution environment

Create all of the following fresh and outside ProjectDB/private Packages:

- loopback-only dedicated PostgreSQL cluster and database at migration
  `20260805_0005`, with one head and no Alembic drift;
- fictional external Workflow Package with recursive pre-run manifest;
- short-lived OpenAlex-bound capability token in one mode-`0600` file;
- real Uvicorn/FastAPI process bound to literal `127.0.0.1`;
- owner-controlled temporary mode-`0600` diagnostic log outside Git.

The Package contains no query, key, token, private data, diagnostic event, or
Provider metadata. The local client receives only `REAGENT_PROXY_TOKEN`.
Server-side key injection uses no command argument, `.env`, Package, database,
tracked script, or tracked evidence.

## 6. Required process configuration

Enable both experimental server flags explicitly:

```text
REAGENT_EXPERIMENTAL_OPENALEX_PROXY_ENABLED=1
REAGENT_EXPERIMENTAL_OPENALEX_STRUCTURAL_DIAGNOSTICS_ENABLED=1
```

The diagnostic logger must be routed only to the temporary mode-`0600` file.
The normal application response/status logs must remain value-free. Confirm
that default-disabled and diagnostic-flag-alone composition still perform no
credential load or Provider call before enabling the complete supervised
process.

## 7. Single-call hard limit

The absolute diagnostic cap is exactly one actual OpenAlex call. Use one
fictional, public, non-sensitive query and `max_results <= 5`. Only the
committed Proxy adapter may originate Provider traffic.

Do not call the Provider directly, call `/rate-limit`, retry, compare, induce an
error, issue a second search, follow a URL, restart to obtain another response,
or use another Provider. Exact replay and status reads must cause zero calls.
An ambiguous outcome stops without retry.

## 8. Required safe extraction

If the operation fails in an instrumented terminal path, require exactly one
event and extract only:

- contract, adapter, stage, path, observed-kind, and validator identities;
- operation ID and request-content checksum;
- record/nested indices when present;
- normalized-record count before failure;
- structural-shape checksum.

Validate every enum and path against the committed closed registries. Confirm
that the event contains no extra fields, exception data, or Provider values.
If no diagnostic is emitted, multiple events appear, or
`UNCLASSIFIED_INTERNAL` is reported, preserve only safe evidence and stop for
owner review. Do not instrument or repair during the run.

## 9. Privacy, cost, and boundary audit

Scan the isolated database, logs, responses, Package, runtime files, and Git
state using transient comparison canaries. Prove absence of query text/marker,
key, token plaintext outside its file/header, paper/author/title/abstract/DOI
values in the diagnostic, raw body, full Provider URL, Authorization header,
and diagnostic fields in normal SQL/API payloads.

Confirm exactly one Provider call and exact current reported cost under the
fresh source/attestation gate. Provider credits remain distinct from USD.
Confirm zero Hosted ProviderOperation, WorkflowRun/StepRun, ExecutionEvent,
Checkpoint, MemoryRevision, Progress Report, AgentRuntime, Workflow, Skill, LLM,
Judge, or structured-generation activity.

## 10. Idempotency and non-remediation

Read status and submit one exact replay only after the terminal operation is
durable. Both must expose only the existing generic public category and no
diagnostic details. Replay must return the same operation with zero second
Provider call, reservation, cost settlement, or diagnostic event.

Do not change source, tests, migrations, fixtures, contracts, ADRs, Package
templates, frontend, or Progress Report code. Do not decide or implement a
normalization correction during this acceptance.

## 11. Package immutability and cleanup

Require byte-identical pre/post Package manifests. Then revoke all acceptance
tokens; stop Uvicorn and dedicated PostgreSQL and verify ports released; delete
token, key, attestation, Package, temporary log, source downloads, request files,
wrappers, and only the dedicated PostgreSQL directory. Remove runtime-only
variables from child processes. Never alter unrelated PostgreSQL or ProjectDB,
and never rotate/delete the owner account key.

## 12. Append-only evidence and closure

Create a new diagnostic-result report and progress record; do not overwrite any
earlier report. Tracked evidence may contain only sanitized fields from Section
8, safe counts/checksums, gate outcomes, test results, and cleanup evidence. It
must exclude query/key/token/provider values, raw body, full URL, temporary
absolute paths, database password, and private data.

Only approved documentation may change. Create exactly one result-evidence
commit, do not push, and finish with a clean tree. A diagnostic result may inform
a later owner decision, but it does not itself open R3C-I2, accept live OpenAlex,
start R3C-A retry 2, or open R3D.

```text
R3C_DIAGNOSTIC_LIVE_CALL_GATE = READY_FOR_OWNER_AUTHORIZATION
R3C_I2_IMPLEMENTATION_GATE = CLOSED
R3C_STATE = LIVE_ACCEPTANCE_PENDING
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```
