# Real Grounded Report Live Failure Matrix

Date: 2026-07-30  
Status: **Proposed fail-closed execution policy**

No failed run publishes a partial report as completed.

| Failure | Start/retry | Settlement and evidence | Publication / recovery / reapproval |
|---|---|---|---|
| missing key | do not start | no operation | blocked; configure approved secret |
| invalid key / unauthorized account | no retry | settle failed if request ID/usage known; safe category only | blocked; account/key owner reapproval |
| model unavailable or ID drift | do not start or abort; no fallback | settle known attempt; retain identity diagnostic | blocked; model re-review/approval |
| price unavailable | do not start | no reservation | blocked; new price manifest |
| ZDR/retention uncertain | do not start | no content sent | blocked; evidence or explicit policy exception |
| abstract permission missing | do not start | no content sent | blocked; owner approval |
| rate limit | one bounded retry honoring `retry-after`, global cap | settle each known attempt/usage | private failure if exhausted; new window, normally no reapproval if contract unchanged |
| timeout/network failure | at most one bounded retry; ambiguous send is not automatically retried | leave ambiguous call unsettled | blocked pending reconciliation; owner decides rerun |
| malformed structure | one mechanical repair if unused | settle original and repair separately | publish only if repaired output fully validates |
| repair failure | no second repair | settle failed repair, retain private diagnostics | blocked; code/prompt review and owner approval for new run |
| refusal | no automatic retry | settle as refused with usage/request ID | blocked; owner reviews scope |
| unknown citation | repair only if mechanical removal leaves valid supported structure | retain checksum/diagnostic, not raw text | blocked if substantive structure changes |
| invalid evidence span | no repair/retry | settle generation; retain safe mismatch diagnostic | blocked; regenerate responsible stage only after review |
| unsupported claim | no mechanical relabelling | retain claim/evidence IDs and checksums | blocked; regenerate or human reject |
| incomplete usage | no next call | operation remains unsettled | blocked until provider/account reconciliation |
| budget/attempt/runtime exhaustion | no further call | settle known attempts | blocked; higher budget requires owner reapproval |
| process crash | no blind retry | reconstruct operations/checkpoints/artifacts | settled verified stages reused; unsettled stage reconciled |
| artifact-write failure | one identical-byte write retry | provider result stays private | blocked until immutable write and checksum succeed |
| human rejection | no automatic regeneration | retain review and private accepted-gate artifacts for term | not published; changed prompt/sample/budget needs owner decision |

Retries never bypass the six-logical-call, eight-attempt, token, runtime, repair,
or USD caps. Diagnostics are bounded and secret/content safe. Cleanup never
occurs automatically after failure: retain the isolated evidence until owner
review or expiry, then run the exact scoped cleanup procedure.

