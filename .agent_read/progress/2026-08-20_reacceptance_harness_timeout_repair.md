# REACCEPTANCE-HARNESS-TIMEOUT-01 bounded repair

Date: 2026-08-20

Status: **IMPLEMENTED; CONTROLLED E5 PASS; REAL RECOVERY ENVIRONMENT-BLOCKED**

`VERIFIER_INDEPENDENCE = LIMITED`: the implementing Codex session also ran the
available qualification.

## Root repair

Forward Literature 0.5/0.7 and 0.6/0.8 now use the normal root Workspace
coordinator as a sequence of bounded active phases. Managed Codex planning and
synthesis retain the 20-minute active-work limit, but each subprocess exits
before a natural Owner checkpoint. OpenAlex/Provider access opens only for exact
query execution and closes in `finally` before screening review.

ReAgent-owned local checkpoint state records exact package/Workflow scope, query
plan checksum, normalized result checksums, staged file checksums, candidate-set
checksum, pending decision state, and accepted per-candidate dispositions.
Harness screening output remains a proposal. Owner approval writes the exact
decision snapshot before the later finalization wait.

Append-only coordinator Progress lives beside the atomic checkpoint root rather
than in the immutable Capsule report directory. Bounded nonterminal and terminal
reports upload automatically through the existing exact upload-only session and
acknowledgement lifecycle. Final publication produces the unchanged
`selected-paper-library/v1` contract exactly once.

## Verification packet

- Approved packet:
  `.agent_read/progress/2026-08-20_reacceptance_harness_timeout_change_packet.md`
- Baseline: `main` / `99302c14fd9be508a9a0081f65ceec115e8e5a66`.
- Migration impact: none; sole head `20260820_0039`.
- Historical publication impact: none; Literature 0.6/0.8 rebuild and preset
  checks pass.

| Requirement | Evidence | Level / fixture | Result |
|---|---|---|---|
| Dwell beyond former 15/20 minute limits | screening callback after synthetic 21-minute elapsed interval; no active subprocess/provider spans it | E2, controlled fake clock | PASS |
| Exact screening durability | approved candidate disposition reloads byte-for-byte; synthesis cannot repeat | E2, production Capsule + fake Harness | PASS |
| Pending decision truth | exact checkpoint reload has revision 0 and no decisions | E2 | PASS |
| Provider release | open/execute/close complete before Owner callback; second invocation cannot reopen or repeat query | E2 | PASS |
| Active-work timeout | `TimeoutExpired` maps to bounded lifecycle failure | E1 | PASS |
| Automatic bounded Progress | nonterminal and terminal reports upload in exact chain with receipts | E2/E3 | PASS |
| Public normal Workspace path | full temporary Full Research Workspace, root `run_workflow`, real in-memory API/Progress service, production Capsule, controlled Provider, fake Harness; five reports and one typed Artifact | E5 `PUBLIC_WORKSPACE_COMMAND + FAKE_HARNESS` | PASS |
| Terminal idempotency | replay requests no decision, repeats no upload, creates no second Artifact | E2 | PASS |
| D1 repair locks | Writing recovery, Review optional evidence, Revision subset support, Revision approval resume | E1-E3 | PASS |
| Historical forward pins/bytes | R4 Literature and Full Research preset tests | E1-E3 | PASS |

Executed results:

- focused/public lifecycle: `6 passed`;
- affected Workspace plus all four D1 locks: `161 passed`;
- historical Literature/preset: `15 passed`;
- Python compileall, `git diff --check`, Alembic sole-head: PASS.

## Qualification limit and real recovery

The repository-native real loopback test could not execute because the managed
execution environment rejected the required loopback elevation after its
approval quota was exhausted. This is `BLOCKED_ENVIRONMENT`, not a product-test
PASS or product failure. It was not bypassed with an alternate network path.
No PostgreSQL change exists in this repair, and no Owner database was accessed.

Read-only inspection of the current re-acceptance Workspace proves:

- Workflow Instance `wfi-80985df1a5665195ac3835e4ccb5bfc4`;
- state `INTERRUPTED`, last completed state `SEARCH_COMPLETED`;
- three exact normalized query results remain present with recorded checksums;
- no new checkpoint, terminal Progress, or selected-paper-library Artifact yet.

The current Workspace is outside the repository write boundary and requires the
same unavailable elevation plus real loopback access for normal sync/recovery.
Therefore no query was rerun and the Owner was not asked to reconfirm `2 / 0 /
11` in this turn. E7 Real Codex, E8 long-lived Workspace recovery, and E9 Owner
reconfirmation remain unqualified. The original real occurrence remains a
confirmed defect record.

## Safety audit

- Exact Artifact/input authority weakened: NO.
- Auto-latest/implicit selection introduced: NO.
- Complete scientific bytes uploaded to Cloud: NO.
- User Skill/Capability boundary changed: NO.
- Historical publication or migration changed: NO.
- Protected historical D1 Project or Owner database accessed: NO.
- Completed Provider work repeated during qualification/recovery: NO.

Permitted claim: bounded repair passes controlled E5 with fake Harness. Real
Owner re-acceptance recovery remains environment-blocked and cannot be claimed.
