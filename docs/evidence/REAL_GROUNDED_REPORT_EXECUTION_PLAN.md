# Phase 9C-2B Real Grounded Report Execution Plan

Date: 2026-07-30  
Status: **Future plan only; no step is authorized by this document**

## Dependency-ordered sequence

1. Owner accepts or revises ADR 0008 and completes every blocking decision.
2. Grant separate implementation authority for the transport/preflight code.
3. Implement injected direct HTTP `AnthropicStructuredTransport` using the
   existing HTTPX dependency; keep it absent from default composition.
4. Add explicit live composition behind a one-run configuration gate; read
   `ANTHROPIC_API_KEY` only at that backend boundary.
5. Add network-free transport mapping/error/timeout/retry/secret-safety tests.
6. Add an opt-in preflight command that validates configuration and local
   policy without sending paper data; do not make a token-count API call unless
   live execution authority explicitly covers it.
7. Create acceptance ID `grounded-report-live-v1`, a new isolated SQL database
   if durable SQL is required, an ignored artifact root, and ignored operation
   journal. Do not reuse ProjectDB or any prior acceptance root/database.
8. Privately build the exact checksum-bound three-paper manifest; do not commit
   titles, abstracts, DOI, or OpenAlex IDs.
9. Obtain existing exact selected-set approval and verify all checksums,
   abstract scope, operation settlement, retention expiry, and leakage scan.
10. Record current price/model/account/ZDR/region manifest; reserve the approved
    budget.
11. Obtain a separate explicit execution authorization and one-run network
    enablement.
12. Execute V3 sequentially: three summary/evidence calls, claims, report, and
    at most one repair.
13. Run the fail-closed provenance/publication gate and verify all 13 immutable
    artifacts. A failure remains private.
14. Have the named human reviewer complete the acceptance form.
15. If accepted, start a fresh process, reload DB/artifacts, and prove completed
    replay makes zero generation calls and no new reservations.
16. Record content-minimized acceptance evidence: identities, counts, usage,
    cost, latency, gates, checksums, review outcome, and retained-resource
    names. Do not commit real abstracts or raw outputs.
17. Disable live composition/network after the acceptance unless the owner
    separately authorizes continued use.
18. Retain or clean the isolated resources according to the approved policy.

## Isolated storage contract

Recommended identifiers are repository-relative placeholders, resolved only
after approval:

- acceptance ID: `grounded-report-live-v1`;
- dedicated database: `reagent_grounded_report_live_v1`;
- ignored root: `runtime_data/acceptance/grounded-report-live-v1/`;
- run-specific immutable keys remain below an opaque run subdirectory;
- ignored journal inside that root;
- retention expiry: run completion plus 30 days.

No environment is created in Phase 9C-2A.

Future cleanup commands use only these exact scoped acceptance targets, after
owner review and a read-only target check:

```bash
dropdb reagent_grounded_report_live_v1
rm -rf -- runtime_data/acceptance/grounded-report-live-v1
```

Do not substitute `ProjectDB`, any prior acceptance database/root, a glob,
unresolved variable, or broader path. Inspect and owner-confirm both targets
first.

## Completion evidence

Phase 9C-2B is not complete merely because transport tests pass. It requires
provider, grounding, product, human, restart, zero-call replay, usage/cost, and
cleanup/retention evidence. Passing this one acceptance still does not
authorize full-pool generation, fallback/comparison, full text, production
deployment, or downstream workflows.
