# Real Grounded Report Owner Decisions

Date: 2026-07-30  
Status: **Open owner-response form; every blocking row must be answered**

Recommendations below are ReAgent engineering proposals. Selecting a value is
an owner action; blank responses mean Phase 9C-2B execution remains blocked.

| Decision | Recommended default | Alternatives / evidence / consequence | Blocking | Owner response |
|---|---|---|---|---|
| Perform live acceptance | Yes, only after ADR 0008 acceptance | Defer; no real product evidence is produced | yes | ___ |
| Provider | Anthropic first-party Claude API | OpenAI or local require revised adapter/contract | yes | ___ |
| Model | `claude-sonnet-5` | Re-review another exact ID | yes | ___ |
| Pinning | Canonical `claude-sonnet-5`; record returned model identity | Anthropic states 4.6+ dateless IDs are fixed snapshots; serving infrastructure may still change | yes | ___ |
| Transport | Injected direct HTTP using existing HTTPX dependency | Official `anthropic` SDK adds dependency and default-retry surface | yes | ___ |
| New dependency | No | Approve exact pinned `anthropic` SDK after supply-chain review | yes if SDK chosen | ___ |
| API key | Scoped backend-only key available for the acceptance workspace | Workload identity or defer | yes | ___ |
| Key variable | `ANTHROPIC_API_KEY`, read only in explicit live composition | Secret manager later; never frontend/artifact | yes | ___ |
| Account/workspace | Record exact commercial organization/workspace and rate/spend tier | Unknown account is not acceptable | yes | ___ |
| Region | Record selected inference region and applicable processing contract | Defer if region cannot be confirmed | yes | ___ |
| Hosted retention | Confirmed ZDR for exact organization/workspace/model/features | Explicit owner exception accepting current standard retention requires ADR revision | yes | ___ |
| Real titles | Permit exactly three approved titles | Exclude titles, with reduced report usefulness | yes | ___ |
| Real abstracts | Permit exactly three approved abstracts | Synthetic/local-only; without permission no hosted run | yes | ___ |
| Abstract limit | 12,000 normalized Unicode characters per paper; fail if exceeded | 8,000 or owner-approved bounded excerpt; never silent truncation | yes | ___ |
| Exact sample | Approve one private checksum-bound three-paper manifest | No actual identifiers belong in Git | yes | ___ |
| Report language | English, original titles preserved | Chinese after separate acceptance | yes | ___ |
| Call plan | 3 summary/evidence + 1 synthesis + 1 report + ≤1 repair | No repair; fewer stages would require contract change | yes | ___ |
| Repair | Permit one mechanical repair only | Zero repair is stricter but less recoverable | yes | ___ |
| Attempt cap | Eight total attempts, at most two transient retries globally | Six attempts/no retry | yes | ___ |
| Token caps | 60k input / 20k output aggregate, including retries | Lower caps after exact token preflight | yes | ___ |
| Monetary cap | USD 1.00 hard cap; reserve USD 0.75 | USD 0/defer or lower cap | yes | ___ |
| Runtime | 15 minutes wall-clock | 10 minutes or defer | yes | ___ |
| Network | Explicit one-run live flag and egress to `api.anthropic.com` only | Network disabled | yes | ___ |
| Storage | New isolated DB only if SQL path is required; separate ignored root/journal | In-memory cannot prove durable restart | yes | ___ |
| Retention | Acceptance DB/root 30 days; hosted payload/normalized response 7 days; no raw HTTP | Shorter deletion or owner-managed term | yes | ___ |
| Human reviewer | Name one reviewer who can inspect supplied abstracts | Codex/model cannot be reviewer | yes | ___ |
| Edit policy | Substantive edit creates a new report version and revalidation | Reject edits; cosmetic display-only correction | yes | ___ |
| Full text/PDF | Remain prohibited | Separate future ADR | yes | ___ |
| Full-pool generation | Remain prohibited after acceptance | Separate later owner decision | yes | ___ |
| Provider comparison/fallback | Remain prohibited | Separate priced and retained experiment | yes | ___ |
| Downstream Idea/Writing | Remain prohibited | Separate future approval of `literature_corpus.json` | no for acceptance | ___ |

## Approval completeness rule

The owner must give an explicit response for every row marked `yes`, including
the exact private sample approval outside Git. “Use defaults” is acceptable
only if the owner explicitly adopts this entire table and separately supplies
account-, key-, retention-, sample-, and reviewer-specific facts through the
private supervised channel.

Current state: provider/model recommendation unapproved; key unavailable to
this phase; abstract transmission unapproved; retention mode unconfirmed;
sample unset; reviewer unset; current authorized spend **USD 0.00**.

