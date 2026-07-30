# Real Report Failure and Recovery Matrix

Status: **Proposed fail-closed policy**
Date: 2026-07-30

No partial or ungrounded report may be published as completed. Provider retries
are controlled by ReAgent, not compounded with SDK defaults.

| Failure | Retry / backoff | Checkpoint and settlement | User result / recovery |
|---|---|---|---|
| invalid approved set, missing/expired approval, changed checksum, duplicate DOI | no | no LLM reservation | blocked; reselect/reapprove |
| authentication/permission | no | settle failed, zero usage if confirmed | configure approved server key |
| 429/overload/5xx | once per operation; `Retry-After`, otherwise 1s, cap 15s | retain attempt metadata; settle final actual usage | retry later after budget check |
| timeout/network | once; 1s bounded backoff | uncertain calls become unsettled until reconciled; never blindly duplicate | reconcile provider request ID or manual retry |
| provider refusal | no automatic retry | settle with reported usage/refusal | disclose and owner reviews input/policy |
| malformed JSON/schema failure | one same-purpose repair/attempt if budgeted | retain invalid-output hash privately; settle each attempt | fail if still invalid |
| missing/unknown citation label | no semantic retry | operation settled; output rejected | rerun same stage only after cause reviewed |
| evidence span/offset mismatch | no semantic repair | output rejected | regenerate extraction or human inspect |
| unsupported claim/inference not marked | no mechanical repair | private checkpoint only | regenerate synthesis after review |
| budget/token/content limit exceeded | no | release reservation; no call | reduce approved input or approve new policy |
| provider contract/model ID drift | no | no call or unsettled operation blocks | update evidence/ADR/adapter |
| artifact immutable-key conflict | retry only if bytes/checksum identical | no overwrite | reconcile artifact metadata/key |
| artifact transient write failure | one identical-byte write | operation output stays private | resume same immutable write |
| process crash | no automatic provider duplication | reconstruct from DB, journal, operations, and checksums | replay completed operations; reconcile unsettled |
| unsettled ProviderOperation | no aggregation/publication | explicitly unsettled | provider reconciliation/manual owner action |
| partial per-paper completion | resume missing settled stages only | completed immutable outputs retained privately | continue or cancel; never publish partial |
| final report failure | one budgeted mechanical repair only | summaries/evidence/claims remain private | retry final stage or stop |
| provenance failure | no provider retry by default | all outputs private; validation artifact retained | repair deterministic linkage or regenerate responsible stage |

## Normalized diagnostics

Diagnostics contain provider/model/adapter/prompt/schema identity, operation and
attempt IDs, normalized category, retryability, status code, provider request
ID, latency/usage when supplied, input/output hashes, and a bounded sanitized
message. They exclude keys, database URLs, paths, full prompts, full abstracts,
raw HTTP bodies, and other users' content.

Global proposed Class D limits are three retry attempts beyond the eight logical
calls and one repair call. Alternatives are zero retry or two per operation.
The proposal balances transient recovery against duplicate-call/cost risk;
owner approval is required and it is revisited after acceptance telemetry.

## Replay

An idempotency key includes run, stage, paper (where applicable), input checksum,
provider/model/adapter, prompt/schema versions, and logical attempt. A settled
matching operation and verified artifact replay with zero provider calls.
An unsettled operation never authorizes a duplicate call simply because the
process restarted.

