# Real Grounded Report Owner Decisions

Original form: 2026-07-30
Revalidated: 2026-08-03
Status: **Open owner-response form; blank blocking responses prohibit execution**

Evidence keys: `SRC` = current Phase 9C-1 source; `ANTH` = current official
Anthropic contract in `REAL_GROUNDED_REPORT_PROVIDER_PREFLIGHT.md`; `POL` =
hosted-data/retention policy; `COST` = live cost model; `GATE` = live gates;
`SAMPLE` = private sample protocol; `HUMAN` = human review protocol. All
numeric recommendations are **Proposed Class D ReAgent policy**.

| Decision | Recommendation | Alternatives | Evidence | Consequence | Blocking | Owner response |
|---|---|---|---|---|---|---|
| Perform the acceptance | Yes, only after ADR 0008 and all gates are approved | Defer | SRC, GATE | Deferral preserves zero exposure but produces no live product evidence | yes | ___ |
| Provider | Anthropic first-party Claude API | OpenAI, local, or defer through a revised package | SRC, ANTH | Any other provider requires a new adapter/contract/retention/cost decision | yes | ___ |
| Exact model | `claude-sonnet-5` | Another exact current ID after re-review | ANTH | Changes schema behavior, price, retention eligibility, and identity checks | yes | ___ |
| Pinning policy | Canonical fixed `claude-sonnet-5`; record returned identity | Choose a stronger dated model if the provider offers one later | ANTH | Model mismatch aborts and requires re-review | yes | ___ |
| Transport | Injected direct HTTP using existing HTTPX | Official `anthropic` SDK | SRC, ANTH | SDK adds dependency/default behavior; HTTP requires a small explicit mapper | yes | ___ |
| New dependency | No | Approve an exact reviewed `anthropic` release and transitives | SRC, ANTH | Dependency approval and supply-chain review become required if SDK chosen | yes if SDK | ___ |
| API-key availability | One expiring/scoped backend-only workspace key | Workload identity later, or defer | ANTH, POL | Missing key fails before reservation and no call starts | yes | ___ |
| Secret variable/source | `ANTHROPIC_API_KEY` at explicit live composition only | Repository-consistent secret manager | ANTH, POL | Any frontend/Skill/artifact access fails the security gate | yes | ___ |
| Account/workspace | Record exact commercial organization/workspace and access tier | Defer | ANTH | Unknown account invalidates rate, spend, retention, and ZDR claims | yes | ___ |
| Region | Record selected inference region and processing contract | Global/default only if explicitly accepted; defer | ANTH, POL | Unresolved processing location blocks abstract transmission | yes | ___ |
| Hosted retention | Policy A: confirmed ZDR for exact account/model/features | Policy B: explicitly accept then-current standard retention via policy/ADR exception | ANTH, POL | Standard API retention may be up to 30 days plus safety/legal exceptions | yes | ___ |
| Permission to send titles | Permit exactly three approved titles | Exclude titles or use local/synthetic only | POL, SAMPLE | Exclusion reduces report/reference usefulness; no permission means no hosted run | yes | ___ |
| Permission to send abstracts | Permit exactly three approved abstracts | Local/synthetic only or defer | POL, SAMPLE | No permission means no substantive hosted generation | yes | ___ |
| Abstract limit | 12,000 normalized Unicode characters per paper; fail if exceeded | 8,000; approved checksum-bound excerpt policy | POL, SAMPLE | Changed/truncated content creates new SourceContent and needs reapproval | yes | ___ |
| Exact three-paper sample | Approve one private checksum-bound manifest | Select a different three-paper set and obtain a new approval | SAMPLE, SRC | No actual paper identity belongs in Git; mismatch fails preflight | yes | ___ |
| Report language | English; preserve original titles and `[P1]`–`[P3]` | Chinese only after separate acceptance | SRC, HUMAN | Keeps first acceptance to one output-language variable | yes | ___ |
| Logical call plan | 3 summary/evidence + 1 synthesis + 1 report + ≤1 repair | Prohibit repair; changing stages requires contract review | SRC, COST | Defines usage, replay, and artifact boundaries | yes | ___ |
| Mechanical repair | Permit one structure-only repair | Zero repair | SRC, GATE | Repair is a warning and cannot fix evidence/semantic failures | yes | ___ |
| Attempt limit | Eight total attempts; at most two transient retries globally | Six attempts/no transient retry | COST, GATE | Cap exhaustion aborts; a higher cap requires reapproval | yes | ___ |
| Token limits | 60k input / 20k output aggregate including retries | Lower after exact preflight; defer | COST | Projected/actual overage blocks the next call and publication | yes | ___ |
| USD hard cap | USD 1.00; initial reservation USD 0.75; per-operation reservation ≤USD 0.30 | USD 0/defer; lower owner cap | COST | Current authority stays USD 0.00 until explicitly changed | yes | ___ |
| Runtime limit | 15 minutes wall-clock | 10 minutes or defer | COST, GATE | Exhaustion aborts with private evidence only | yes | ___ |
| Live network enablement | One-run explicit flag; egress only to `api.anthropic.com` | Network disabled | ANTH, GATE | Default composition remains synthetic; no flag means zero live calls | yes | ___ |
| Isolated storage | Acceptance ID `grounded-report-live-v1`; dedicated SQL DB if needed plus isolated ignored root/journal | Defer; a different exact isolated naming plan | SRC, GATE | Reusing ProjectDB/other acceptance/production roots is prohibited | yes | ___ |
| Local retention | Isolated root/DB 30 days; hosted payload/normalized response 7 days; no raw body | Shorter deletion; separately approved longer term | POL | Named cleanup owner must act because no retention worker exists | yes | ___ |
| Human reviewer | Name one human able to compare every statement with supplied abstracts | Defer | HUMAN | Codex/model cannot provide acceptance; no reviewer means no completion | yes | ___ |
| Edit/revalidation policy | Any substantive edit creates a new immutable report version and full revalidation | Reject all substantive edits; cosmetic display-only notes outside bytes | HUMAN, GATE | Prevents silent provenance breakage | yes | ___ |
| Full text/PDF | Remain prohibited | Separate future ADR | SRC, POL | Changing scope invalidates the abstract-only acceptance | yes | ___ |
| Full candidate-pool generation | Remain prohibited | Separate later approval and budget | SAMPLE, GATE | One three-paper run cannot authorize broader processing | yes | ___ |
| Provider fallback/comparison | Remain prohibited | Separate priced/retained experiment | ANTH, COST | No automatic or manual fallback during this run | yes | ___ |
| Downstream Idea/Writing | Remain prohibited | Separate future approval of verified corpus | SRC | Acceptance produces no downstream execution authority | no for this acceptance | ___ |

## Approval completeness

The owner must explicitly answer every `yes` row. “Use recommended defaults”
is sufficient only when the owner expressly adopts the whole table **and**
separately supplies the account/workspace/region/ZDR, key availability, private
sample, reviewer, storage owner, execution window, and network facts. Those
facts cannot be inferred from public documentation or a repository commit.

Current state: provider/model recommendation unapproved; implementation and
execution authority absent; key/account/region/ZDR unknown; title and abstract
transmission unapproved; sample and reviewer unset; live network disabled;
current authorized spend **USD 0.00**.
