# R3C-A Supervised OpenAlex Live Acceptance Plan

Status: **FUTURE LIVE ACCEPTANCE PLAN — GATE CLOSED / NOT STARTED**
Provider: OpenAlex only
Capability: `paper.search/v0.1` only

## 1. Authorization and baseline

R3C-A may start only after owner review of a clean committed R3C-I baseline
whose state is `LIVE_ACCEPTANCE_PENDING`. It requires explicit owner permission
for this live run and an owner-supplied OpenAlex key. R3C-D and R3C-I do not
authorize the live call.

Initial gate:

- exact required commit and `main` branch;
- clean tracked/untracked/staged state and `git diff --check`;
- no production-source modification during acceptance;
- current ADR 0012 and adapter/security contracts unchanged;
- re-retrieval of official Authentication & Pricing, Search, Errors, Terms and
  Privacy sources from approved documentation domains only;
- confirmation that Works search remains `$0.001`, the keyed allowance and
  relevant headers/`meta.cost_usd` remain compatible, and current Terms/Privacy
  do not contradict the slice;
- confirmation that the R3C-I integer-microusd mapping, fixed select list and
  current Provider header names still match official sources;
- owner confirmation that prepaid spending is unavailable/disabled.

If source, price, terms, privacy or implementation has materially changed, stop
before any Provider call and keep the live gate closed.

## 2. Isolated environment

Create outside Git:

- a fresh fictional Workflow Package;
- a dedicated loopback-only PostgreSQL cluster and unique non-default port;
- separate migration/live and test databases whose names clearly contain
  `reagent_r3ca` and are not ProjectDB;
- short-lived capability token files;
- server/client logs and response evidence;
- any owner-controlled key file.

Use the committed Uvicorn/FastAPI entrypoint on literal `127.0.0.1`, explicit
Proxy SQL persistence and the explicit OpenAlex feature flag. Do not use
TestClient or in-memory persistence for the core path.

The OpenAlex key is supplied only to the supervised server environment, never
as a command argument, Package field, `.env` entry, database value or evidence
file. Do not enable shell tracing.

## 3. External Package and non-mutation proof

Generate and validate a wholly fictional Package outside the repository. It
contains no key, token, private query, real R1B data or machine path. Its proxy
configuration remains provider-neutral and disabled by default.

Before token issuance or client call, generate a recursive relative-path/type/
size/SHA-256 manifest. After all success, replay, rejection and restart tests,
generate the same manifest and require exact equality. No Package input,
output, context, Progress Report, prompt, Skill or configuration may change.

## 4. Migration and live composition

Against the isolated database, require one expected Alembic head, upgrade to
head, current revision, no drift and actual Proxy SQL tables/constraints. Prove
there is no Hosted WorkflowRun/step/provider-operation foreign key and no key,
credential URL, raw body or query-text persistence column.

Verify:

- OpenAlex Proxy remains disabled by default;
- enabled without valid SQL fails closed;
- enabled without the Provider key fails closed before route operation;
- enabled with exact SQL/key/fixed adapter starts on `127.0.0.1`;
- fake and live adapters cannot be selected by request data;
- no in-memory or Hosted fallback occurs.

## 5. Live call ledger and privacy-safe queries

Maintain an independent acceptance ledger before the first call and after every
operation:

- admitted live operation count;
- actual Provider HTTP call count;
- exact reported USD cost;
- remaining owner call/cost budget;
- operation ID, request checksum and safe response/provider-data checksums;
- Provider status and safe numeric usage headers.

Use only fictional, public and non-sensitive scholarly queries. Include a small
UTF-8/ordinary-syntax matrix only when each new query is necessary and within
the cap. Never use a real project question or private title/abstract.

Hard ceilings across the whole acceptance are 20 admissions, 20 Provider calls
and `$0.05` reported spend. The plan should target substantially fewer calls
than the ceiling. Do not intentionally trigger quota/rate exhaustion or paid
use.

## 6. Successful operation evidence

Through the committed local client and real loopback HTTP, submit one valid
request with an explicit UUIDv4 key. Require:

- one OpenAlex request to the fixed HTTPS Works origin;
- no redirect, ambient proxy or other outbound destination;
- status `SUCCEEDED` and adapter `reagent.openalex-paper-search/v0.1`;
- at most 20 results and 512 KiB;
- only the approved normalized `PaperRecord` fields;
- untrusted-provider-data declaration and no cloud relevance/synthesis fields;
- independently valid request, operation, provider-data, response-content and
  response checksums;
- exact safe `meta.cost_usd`/header evidence and total within budget;
- successful status read by operation ID and scoped idempotency key;
- SQL row/result persistence with no raw body/key/URL/query;
- zero Hosted/Progress rows and zero local Package mutation.

Do not reproduce raw Provider records in tracked evidence. Record only bounded
field counts, safe Provider IDs/checksums, costs and validation results.

## 7. Idempotency, conflict and uncertain outcome

Replay the exact accepted request and prove no second OpenAlex call and no new
cost/admission. Changed content under the same scoped key must return
`IDEMPOTENCY_CONFLICT` before Provider use.

Run real concurrent exact replay only when R3C-I guarantees it cannot issue two
Provider calls; independently compare Provider call counters and SQL rows.

For uncertain outcome, use only an implementation-supported deterministic
acceptance fault path. Do not manufacture a Provider outage or abuse the live
service. Demonstrate `RECONCILIATION_REQUIRED`, status reads and no automatic
retry. If the safe live test cannot force uncertainty, rely on R3C-I scripted
evidence and retain an explicit warning rather than risking a duplicate live
call.

## 8. Security and error observation

Test local/cloud rejections that consume zero Provider calls: absent/revoked/
wrong-scope token, wrong Package/Workflow checksum, invalid capability, unknown
field, URL/header/provider selection, invalid limits/timestamp/checksum and
exhausted local budget.

Observe naturally occurring Provider errors only if they occur. Do not send
malformed abuse traffic, hammer rate limits, attempt authentication failure with
the real key, fetch content/PDF, or intentionally cause paid usage.

Use private leakage canaries to scan SQL, logs, client/operator output,
temporary responses, Package and tracked changes for the OpenAlex key and
credential-bearing URL. Require zero matches outside the owner-designated
secret location/environment. Do not retain the key or its fingerprint.

## 9. Outbound and Hosted boundary evidence

Combine:

- fixed-origin transport configuration and canary tests;
- Provider HTTP call ledger;
- process socket inspection during operation;
- server logs with key/query redaction;
- absence of other Provider credentials;
- SQL row counts before/after for Hosted ProviderOperation, WorkflowRun,
  StepRun, ExecutionEvent, Checkpoint, MemoryRevision and Progress Reports.

Only loopback Uvicorn/PostgreSQL and the fixed OpenAlex HTTPS origin are
allowed. Socket snapshots are supporting evidence, not packet-capture proof.
AgentRuntime, ExecutionDispatcher, research Skills, LLM, Judge and automatic
Progress Report counts remain zero.

## 10. Restart recovery

Record operation IDs, safe checksums, exact cost/call totals, token metadata,
Proxy row counts/statuses and Package manifest. Then:

1. stop Uvicorn cleanly;
2. stop the dedicated PostgreSQL cluster;
3. retain its data directory;
4. restart the same cluster;
5. verify migration head/no drift;
6. restart Uvicorn with the same database, key environment and feature flag.

After restart, require identical accepted operation/result/checksums/cost,
unchanged token state and no duplicate rows. Status reads must work. Exact POST
replay remains idempotent and causes zero additional OpenAlex call. A reconciled
operation remains uncertain and is not reissued.

## 11. Regression and qualification

Against the isolated test database run, without Proxy SQL skips:

- focused OpenAlex Proxy tests;
- Proxy PostgreSQL tests;
- existing fake Proxy tests;
- Workflow Package tests;
- Progress Report tests;
- full backend regression;
- compileall;
- Alembic heads/current/check.

No frontend run is required when no frontend file changes. Record every skip by
verified category; a skipped R3C Proxy PostgreSQL test is a hard blocker.

## 12. Cleanup and evidence commit

After restart and final replay:

- revoke acceptance capability tokens;
- stop Uvicorn and dedicated PostgreSQL and verify ports/processes stopped;
- remove the owner key from process environment and delete any secret file;
- delete external Package, token files, isolated database/data and temporary
  runtime/log/response material;
- retain no real Provider data beyond sanitized tracked acceptance evidence.

Do not stop/delete another PostgreSQL service/database, touch ProjectDB, run
`git clean`, or remove unrelated data.

Create only an R3C-A acceptance report, progress record, context update and
narrow acceptance-plan corrections. Make one documentation-only evidence
commit and end clean. No production source repair is permitted during R3C-A; a
defect produces a blocked evidence commit.

## 13. Gate result

R3C-A may pass only when every hard call, cost, key, SQL, idempotency, restart,
Package and boundary gate passes. It must never claim production/public
authorization.

```text
R3C_A_LIVE_ACCEPTANCE_GATE = CLOSED  # until owner starts the future phase
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```
