# R3C OpenAlex Credential, Privacy, and Cost Policy

Status: **R3C-I2 ABSTRACT COMPATIBILITY OFFLINE QUALIFIED; LIVE ACCEPTANCE PENDING**
Date: 2026-08-05
Governing ADRs: 0012, 0013, and 0014

This is an engineering security policy, not legal advice and not production
authorization.

## 1. Assets and trust boundaries

Protected assets are the owner OpenAlex API key, short-lived ReAgent capability
token, Package/Workflow identity, query, normalized Provider metadata,
operation/idempotency records, exact cost evidence, logs and local Package
state.

The trust boundaries are:

```text
external local Package/Harness (untrusted request)
  -> loopback ReAgent Proxy (token trust boundary)
  -> fixed OpenAlex adapter (credential boundary)
  -> official OpenAlex HTTPS origin (external untrusted Provider)
  -> normalized untrusted data returned to the Harness
```

The Provider is trusted only as a configured transport peer. Its data, error
text, links, titles, names and abstracts are untrusted and are never executable
instructions.

## 2. Credential policy

The sole OpenAlex credential source is the server process variable
`REAGENT_OPENALEX_API_KEY`. R3C-I never sets or reads it. R3C-A receives it only
from the owner in the supervised environment.

Plaintext key is allowed only in:

- the supervised server process environment; or
- one owner-controlled secret file outside Git, Package and runtime evidence,
  used to populate that environment without exposing the key in command
  arguments.

It is prohibited from PostgreSQL, artifact storage, Package files, committed
`.env`, shell command arguments, API requests/responses, Progress Reports,
logs, exception text and tracked evidence. The fixed adapter adds the key only
inside the outbound transport. Configuration repr, application diagnostics and
HTTP client exception chains must redact it.

Because the documented Provider mechanism puts `api_key` in the query string,
the system must never log a complete outbound URL. A private R3C-A leakage scan
uses a locally computed key fingerprint only as a comparison canary and does
not retain that fingerprint in tracked evidence.

R3C-I implements a lazy credential-source interface. Default startup does not
call it; OpenAlex-enabled composition fails closed when it cannot supply a
credential. Tests inject runtime-generated synthetic values directly into the
interface and suppress HTTPX request-line logging on the Provider-call thread.
No real environment key is read during R3C-I.

## 3. Outbound-network controls

- Allow only `https://api.openalex.org/works`.
- Require certificate verification and SNI/Host for that exact origin.
- Disable redirects. No redirect target receives the key.
- Disable ambient proxy inheritance and ignore uncontrolled proxy variables.
- Reject every user-controlled URL, hostname, endpoint, method and header.
- Do not connect to loopback, private, link-local, alternate OpenAlex, content,
  PDF or third-party origins.
- Apply bounded DNS/connect/read/write/pool and 10-second complete-operation
  timeouts.
- Enforce at most one Provider HTTP request for each new admitted operation and
  at most 20 across R3C-A.

R3C-I uses a scripted transport and a socket/HTTP canary that fails on any
Internet attempt. R3C-A combines fixed-origin transport evidence, process socket
inspection, logs, call counters and Provider-operation records. A point-in-time
socket listing is supporting evidence, not a packet capture.

## 4. Query privacy

OpenAlex’s current Privacy Promise states that it collects basic request and
technical metadata linked to an API key. The full Privacy Policy identifies API
keys, IP addresses, URLs, browser/platform/equipment information and request
times and describes possible retention for up to six months after use ends
unless deletion is requested sooner.

Therefore R3C-A sends only fictional, public and non-sensitive queries. It must
not send unpublished ideas, private documents, confidential titles/abstracts,
personal information, real dissertation questions or real R1B material.

Before any future real-user use, the product must clearly disclose that query
text and technical metadata are sent to a third-party Provider under its
current privacy policy. Consent/notice UX, deletion requests and production
privacy governance are outside R3C and remain unapproved.

The Proxy does not persist query text for the R3C acceptance profile. It keeps
the canonical request checksum, query SHA-256, byte/character lengths and
`max_results` necessary for identity/privacy audit. Logs use operation IDs and
checksums and never query text.

## 5. Data minimization and retention

R3C-A retention is limited to the isolated acceptance environment lifetime.

Allowed durable data:

- canonical request and response identities/checksums;
- adapter ID/version and fixed Provider capability;
- operation status, timestamps and measured latency;
- local call count and exact decimal USD/credit evidence;
- safe Provider request identifiers when strictly validated;
- safe normalized `PaperRecord` metadata from the fixed field allowlist;
- response content/result checksums and bounded sizes.

Forbidden durable data:

- raw Provider body or raw error body;
- OpenAlex API key, credential-bearing URL or request credential material;
- short-lived ReAgent bearer plaintext/digest in response evidence;
- query text under the R3C retention profile;
- PDF, full text, Provider-supplied downloaded content;
- unallowlisted response fields, HTML/script execution or unsafe payload;
- local Package path, context, outputs or Progress Report content.

After R3C-A, stop the isolated Uvicorn/PostgreSQL environment, revoke/delete
acceptance credentials as applicable, remove the isolated database/runtime/key
material and retain only sanitized checksums, IDs, counts and conclusions in
Git. Production retention, backups, deletion/export SLAs and multi-user access
remain unapproved.

## 6. Budget and billing controls

Current official source evidence reports Works search at `$0.001` per call and
`$1/day` free usage with a free key. These are mutable facts, not permanent
constants.

R3C-A owner limits are:

| Dimension | Ceiling |
|---|---:|
| admitted live Proxy operations | 20 |
| actual Provider HTTP calls | 20 |
| total reported acceptance spend | USD 0.05 |
| results per request | 20 |
| response bytes | 512 KiB |
| complete operation timeout | 10 seconds |
| automatic Provider retries | 0 |
| prepaid spending authorization | none |

R3C-I represents cost as integer microusd (`USD 1 = 1,000,000`), never binary
float: the qualified search reservation is 1,000 microusd and the owner cap is
50,000 microusd. Provider credits remain separately typed evidence.

Before the first live call, recheck the current official price and obtain owner
confirmation that prepaid spending is unavailable/disabled. Reserve `$0.001`
locally for each admitted call under the qualified price snapshot. Settle with
exact `meta.cost_usd` and safe current usage-header values. Do not round sub-cent
cost down to zero.

Reject before Provider use when local call/cost reservation is exhausted,
Provider/capability is wrong or the key is missing. Stop further admissions and
classify contract change when price/cost fields are absent, malformed,
contradictory or differ from the qualified price. No `/rate-limit` call is
approved because that would add a Provider request. R3C-A must not intentionally
exhaust service limits or trigger prepaid use.

## 7. Threat and control matrix

| Threat | Required control | Residual risk |
|---|---|---|
| key leaks in URL/log/exception | never log URLs; fixed field logging; redact exception chains; private leakage canary | external observability can misconfigure capture; R3C-A must inspect it |
| arbitrary URL/SSRF | fixed origin/path, structured params, redirects/proxies disabled | DNS compromise remains a system trust dependency |
| query/private-data disclosure | fictional public queries only; no query-at-rest/logging; future disclosure gate | Provider still receives query and technical metadata |
| cost/quota abuse | token scope, 20-call ledger, exact `$0.05` cap, zero retry, no prepaid approval | first response can reveal an unexpected price; source recheck and stop are mandatory |
| idempotent replay charges twice | durable Proxy operation before call; exact replay returns existing state | uncertain network completion cannot be proved from Provider; reconcile, never retry |
| malicious Provider text/prompt injection | strict fields/Unicode/length; abstract-only TAB/LF/CR-to-space compatibility; all other controls rejected; untrusted-data flag; no cloud LLM/execution; no link following | general-purpose local Harness must continue to separate data from instructions |
| oversized/compressed response | actual decoded bytes bounded to 512 KiB before persistence | streaming implementation must prevent buffering beyond cap |
| raw/unsafe retention | normalize allowlist only; reject before durable body storage; isolated cleanup | normalization defects require tests and review |
| Hosted execution scope expansion | dedicated Proxy composition/import canaries; no Hosted rows/Skills/Runtime | optional Hosted code still exists elsewhere in repository |
| terms/privacy/pricing drift | exact source ledger and blocking R3C-A recheck | official pages can change without advance notice |

## 8. Safe error and logging policy

Only stable error categories, operation ID, adapter ID, status code class,
bounded numeric usage, retryability `false`, latency and checksums may be logged
or returned. Never include Provider error body, HTML, key, credential URL,
query, Authorization header, stack trace or local path.

The required categories are:

```text
PROVIDER_AUTHENTICATION_FAILED
PROVIDER_AUTHORIZATION_FAILED
PROVIDER_RATE_LIMITED
PROVIDER_BUDGET_EXHAUSTED
PROVIDER_TIMEOUT
PROVIDER_UNAVAILABLE
PROVIDER_INVALID_RESPONSE
PROVIDER_RESPONSE_TOO_LARGE
PROVIDER_CONTRACT_CHANGED
PROVIDER_RECONCILIATION_REQUIRED
```

Every failure stays within the Proxy ledger. It creates no WorkflowRun,
ProviderOperation, ExecutionEvent, checkpoint, memory revision, LLM call,
Progress Report or local file mutation.

## 9. Privacy-safe structural diagnostics

The internal structural diagnostic is disabled by default and uses only the
server-side process flag
`REAGENT_EXPERIMENTAL_OPENALEX_STRUCTURAL_DIAGNOSTICS_ENABLED`. The flag alone
does not enable the Proxy, read a credential/query, or cause a Provider call.

When enabled, one terminal OpenAlex normalization or service-safety failure may
emit exactly one canonical structured event. Its closed allowlist is limited to
contract/adapter identity, public operation ID, request checksum, processing
stage, approved-field path, record/nested indices, observed structural kind,
fixed validator code, normalized-record count before failure, and a canonical
value-independent structural-shape checksum.

It is prohibited from containing a Provider value, unknown Provider key,
title, author data, DOI value, abstract token/position value, venue, language
value, query, marker, key, token, full URL, raw JSON, exception, stack trace,
request/response object, or headers. The structural checksum encodes only
approved-field presence/type/null state, bounded counts, indices and fixed
classifications. Synthetic tests prove equal shapes with different values have
equal checksums.

The diagnostic never enters the public response/status DTO, `ProxyOperation`
request/result data, SQL, Package, Progress Report, or ordinary client output.
The only approved future live sink is an owner-controlled temporary mode-`0600`
log outside Git, deleted after append-only sanitized evidence is recorded. No
migration, ORM field, raw-error column, or raw response artifact is authorized.

Strict complete-response failure remains mandatory. The sensitive-content
scanner is unchanged and emits only its fixed `SERVICE_SAFETY` classification,
never the matched substring or surrounding text. Exact replay emits no second
event, adapter call, reservation, or settlement.

ADR 0014 permits only U+0009, U+000A, and U+000D within abstract inverted-index
tokens. They become U+0020, and a contiguous adjacent ASCII SPACE/TAB/LF/CR run
containing a permitted control becomes one SPACE before the unchanged control-
character validator runs. The original and normalized token are never emitted
to the diagnostic or logged independently. All other controls and every non-
abstract field retain the existing rejection policy. This introduces no new
retention sink, schema field, URL, request mapping, retry, or execution path.

## 10. Deferred production decisions

Public exposure, production user authentication, multi-user authorization,
proof of possession, HTTPS termination, production secret manager, paid/prepaid
plans, production query/result retention, backup/deletion/export policy,
external observability and multiple Providers remain unapproved.

```text
R3D_PRODUCTION_PROVIDER_GATE = CLOSED
```
