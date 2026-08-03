# Real Grounded Report Live Failure Matrix

Original proposal: 2026-07-30
Revalidated against source/provider contracts: 2026-08-03
Status: **Proposed fail-closed execution policy**

No failed run publishes a partial report as completed. All numeric retry and
retention values are **Proposed Class D ReAgent policy** and remain unapproved.
“Retain safe evidence” means identifiers, checksums, categories, request/usage
metadata when known, and bounded diagnostics—never keys, raw HTTP, or real
content in logs/Git.

| Failure | Start / retry / maximum | Operation settlement | Evidence retained | Publication and user status | Cleanup | Owner reapproval |
|---|---|---|---|---|---|---|
| missing key | do not start; 0 retries | no operation/reservation | preflight boolean only | blocked: `PREFLIGHT_BLOCKED/MISSING_KEY` | none | no policy reapproval; approved secret must be configured |
| invalid key | attempted call gets 0 retries | `FAILED/RELEASED` if rejected before billable start; otherwise settle known usage or leave unresolved | safe auth category and request ID if returned | blocked: `PROVIDER_FAILED/AUTHENTICATION` | retain isolated metadata to expiry | key/account owner must confirm replacement |
| unauthorized account/model access | 0 retries | same pre/post-call rule | safe permission category, returned identity/request ID | blocked: `PROVIDER_FAILED/UNAUTHORIZED` | retain to review/expiry | yes, account/workspace access decision |
| model unavailable | preflight blocks if known; otherwise at most 1 transient retry within global cap | settle each known attempt; ambiguity remains unsettled | exact requested/returned identity, category, usage | blocked if exhausted: `PROVIDER_FAILED/MODEL_UNAVAILABLE` | retain to review/expiry | normally yes if model/window changes; no if same approved model and owner opens a new window |
| model ID drift | abort immediately; 0 retries/fallback | settle known call with usage or unresolved state | requested and returned model IDs/checksums | blocked: `PROVIDER_FAILED/MODEL_ID_DRIFT` | retain | yes, model/pinning review |
| pricing unavailable/currency mismatch | do not start; 0 retries | no reservation | dated failed price-manifest check | blocked: `PREFLIGHT_BLOCKED/PRICE_UNKNOWN` | none | yes if price/currency policy changes |
| ZDR/retention uncertainty | do not start; 0 retries | no operation | account evidence gap only | blocked: `PREFLIGHT_BLOCKED/RETENTION_UNCONFIRMED` | none | yes: confirmed Policy A or explicit Policy B exception |
| abstract/title permission missing | do not start; 0 retries | no operation | missing approval reference only | blocked: `PREFLIGHT_BLOCKED/CONTENT_PERMISSION` | private sample stays local | yes, explicit transmission approval |
| rate limit | at most 1 retry for the affected operation, honoring `retry-after`, and no more than 2 transient retries globally | settle each attempt/usage if represented separately; no hidden SDK retry | status/category, request ID, retry-after, usage, timing | private failure if exhausted: `PROVIDER_FAILED/RATE_LIMIT` | retain to expiry | no if same approvals and execution window; yes for higher caps/window/policy |
| timeout | at most 1 only when transport proves request did not start; ambiguous send gets 0 blind retry | pre-call failure releases; known usage settles; ambiguous call stays `UNSETTLED` | timeout phase, cancellation metadata, request ID/usage if known | blocked: `PROVIDER_FAILED/TIMEOUT` or `PUBLICATION_BLOCKED/UNSETTLED` | retain for reconciliation | owner decision required before ambiguous rerun; higher timeout needs reapproval |
| network failure | same as timeout | same as timeout | safe transport phase/category; no URL query/body | blocked: `PROVIDER_FAILED/NETWORK` | retain for reconciliation | required when settlement is ambiguous; otherwise same-window retry policy applies |
| provider refusal | 0 automatic retries | `FAILED/SETTLED` with request ID and usage | refusal state/checksum and safe category | blocked: `PROVIDER_FAILED/REFUSAL` | retain to review/expiry | yes before prompt/sample/model change or rerun |
| max-token/incomplete output | may use the one repair only if structure is safely repairable; no transient retry | original settles; repair is a separate reserved/settled operation | finish state, checksums, usage, missing-field diagnostics | blocked unless repaired artifact fully validates | retain both operation records | yes if token cap/prompt changes; no for the already-approved single repair |
| malformed structured output | one mechanical repair if unused; no second repair | original and repair settle separately | output checksum, schema errors, request/usage metadata; no raw text | `RUNNING_PRIVATE` until repair; then pass or `PROVIDER_FAILED/MALFORMED` | retain to expiry | no for approved repair; yes for prompt/schema/rerun change |
| repair failure | 0 further repair/retry | repair `FAILED` and settled/released by call state | original/repair checksums and safe diagnostics | blocked: `PROVIDER_FAILED/REPAIR_FAILED` | retain | yes after code/prompt/schema review |
| unknown citation | no model retry; mechanical removal only if no substantive claim changes and repair remains unused | triggering call already settled; optional repair separate | label, report/claim checksum, path | blocked: `GROUNDING_FAILED/UNKNOWN_CITATION` unless complete revalidation passes | retain | yes for substantive regeneration; approved repair policy covers mechanical-only case |
| invalid evidence span | 0 repair/retry | generation operation remains settled with actual usage | paper/source/evidence IDs, offsets, checksums; not span text in diagnostics | blocked: `GROUNDING_FAILED/INVALID_SPAN` | retain private source/artifact to review/expiry | yes before responsible-stage regeneration |
| unsupported claim / invalid claim-evidence alignment | 0 mechanical relabel/retry | generation operations remain settled | claim/evidence/paper IDs, categories, checksums | blocked: `GROUNDING_FAILED/UNSUPPORTED_CLAIM` | retain | yes before regeneration or changed sample/prompt |
| incomplete or absent usage | 0 next call/retry | operation stays `UNSETTLED`; do not estimate success | request ID, provider/category, reservation, known counters | blocked: `PUBLICATION_BLOCKED/USAGE_MISSING` | retain until reconciled/expiry | owner decision required if reconciliation cannot prove usage |
| unsettled operation | 0 duplicate/blind retry | remains unsettled until authoritative reconciliation | durable operation/checkpoint state | blocked: `PUBLICATION_BLOCKED/UNSETTLED_OPERATION` | retain | yes before abandoning/restarting ambiguous call |
| budget/token/attempt/runtime exhaustion | no further calls | settle every known attempt; unstarted reservation released | totals, cap, projection, settled operations | blocked: `PROVIDER_FAILED/CAP_EXHAUSTED` | retain | yes for any increased cap or new run |
| process crash | no blind retry; restart reconstructs first | verified settled operations replay; RESERVED/RUNNING remains blocking | journal/DB state, private output checkpoint, artifact checksums | `RUNNING_PRIVATE` only for safely resumable state; otherwise blocked | retain until review/expiry | no for zero-call replay of settled stages; yes for ambiguous rerun |
| artifact-write failure | one identical-byte local write retry; no provider retry | provider operation remains settled; publication operation not complete | intended checksum/size/storage category and settled provider ID | blocked: `PUBLICATION_BLOCKED/ARTIFACT_WRITE` | retain verified bytes/orphans for scoped review; never broad-delete | yes only if storage policy/target changes |
| checksum/reload/replay failure | 0 provider calls | prior operations unchanged | expected/actual checksums and replay call count | blocked: `PUBLICATION_BLOCKED/REPLAY_INTEGRITY` | retain all isolated evidence | yes before any regeneration or artifact repair |
| human rejection | 0 automatic regeneration | operations remain settled | signed/pseudonymous review linked to report/provenance checksums | not published: `HUMAN_REJECTED` | retain for approved term, then scoped cleanup | yes for any new run, prompt, sample, model, budget, or substantive edit |

## Global abort rules

- Six logical generation operations, eight attempts, two transient retries,
  one repair, 60k/20k tokens, 15 minutes, and USD 1.00 are aggregate caps, not
  per-stage allowances.
- An ambiguous provider call is never converted into a successful or released
  operation by estimation.
- Cleanup is never automatic after failure. A named owner first preserves the
  safe evidence needed for settlement/security/human review, then runs only the
  exact acceptance-scoped cleanup after expiry or explicit cancellation.
- Any partial Markdown or structured output stays private and must not be
  exposed through completed-report API/UI status.
