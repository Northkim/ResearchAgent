# Phase 9C-2B Real Grounded Report Execution Plan

Original plan: 2026-07-30
Source/contract revalidation: 2026-08-03
Status: **Future plan only; no step is authorized by this document**

## Dependency-ordered sequence

1. Owner accepts or revises ADR 0008 and completes every blocking decision.
2. Grant separate implementation authority for the transport/preflight code.
3. Implement injected direct HTTP `AnthropicStructuredTransport` using the
   existing HTTPX dependency; keep it absent from default composition.
4. Add explicit live composition behind a one-run configuration gate; read
   `ANTHROPIC_API_KEY` only at that backend boundary.
5. Add the smallest live execution-policy path required by current source:
   replace the Phase 9C-1 live-provider prohibition only under the injected
   approved policy, mark operations live, use a live-scoped idempotency key,
   and freeze operation-specific provider schemas. Preserve the existing V3
   workflow and validators.
6. Add network-free transport mapping/error/timeout/retry/cancellation/
   schema/secret-safety tests.
7. Add an opt-in preflight command that validates configuration and local
   policy without sending paper data; do not make a token-count API call unless
   live execution authority explicitly covers it.
8. Create acceptance ID `grounded-report-live-v1`, a new isolated SQL database
   if durable SQL is required, an ignored artifact root, and ignored operation
   journal. Do not reuse ProjectDB or any prior acceptance root/database.
9. Privately build the exact checksum-bound three-paper manifest; do not commit
   titles, abstracts, DOI, or OpenAlex IDs.
10. Obtain existing exact selected-set approval and verify all checksums,
   abstract scope, operation settlement, retention expiry, and leakage scan.
11. Record current price/model/account/ZDR/region manifest; reserve the approved
    budget.
12. Obtain a separate explicit execution authorization and one-run network
    enablement.
13. Execute V3 sequentially: three summary/evidence calls, claims, report, and
    at most one repair.
14. Run the fail-closed provenance/publication gate and verify all 13 immutable
    artifacts. A failure remains private.
15. Have the named human reviewer complete the acceptance form.
16. If accepted, start a fresh process, reload DB/artifacts, and prove completed
    replay makes zero generation calls and no new reservations.
17. Record content-minimized acceptance evidence: identities, counts, usage,
    cost, latency, gates, checksums, review outcome, and retained-resource
    names. Do not commit real abstracts or raw outputs.
18. Disable live composition/network after the acceptance unless the owner
    separately authorizes continued use.
19. Retain or clean the isolated resources according to the approved policy.

Implementation approval covers steps 3–7 only. Execution approval covers the
specific resources and steps 8–19. Accepting ADR 0008 does not silently grant
either authority.

## Proposed future command surface

These commands do **not** exist in Phase 9C-2A. They freeze the minimum future
owner-visible interface; Phase 9C-2B may implement the names only after
implementation approval:

```bash
conda run --no-capture-output -n reagent-dev \
  python -m backend.research.grounded_live_acceptance \
  preflight grounded-report-live-v1 \
  --manifest runtime_data/acceptance/grounded-report-live-v1/private-manifest.json

conda run --no-capture-output -n reagent-dev \
  python -m backend.research.grounded_live_acceptance \
  execute grounded-report-live-v1 \
  --manifest runtime_data/acceptance/grounded-report-live-v1/private-manifest.json \
  --live --confirm grounded-report-live-v1

conda run --no-capture-output -n reagent-dev \
  python -m backend.research.grounded_live_acceptance \
  replay grounded-report-live-v1 --require-zero-calls

conda run --no-capture-output -n reagent-dev \
  python -m backend.research.grounded_live_acceptance \
  status grounded-report-live-v1
```

`preflight` must not send paper content or count tokens remotely. `execute`
must require both the explicit `--live` switch and exact confirmation string.
`replay` must refuse any network composition and verify DB, operation,
artifact, report, provenance, and corpus checksums through a fresh process.

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

Restart/reload procedure: stop the executing process after terminal settlement,
construct a fresh application container against only the isolated database and
artifact root with live composition disabled, reload the workflow run and all
13 artifact metadata/bytes, verify checksums, then invoke completed replay and
assert zero new reservations, attempts, requests, or artifact versions.

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
