# R7 input-setup decision timezone repair

Date: 2026-08-20

Status: **PASS_AT_DECLARED_LEVEL**

Baseline: `main` at `a6d44432c78ba9e2950bc468f283f9f6704cdfe3`

Change packet:
`.agent_read/progress/2026-08-20_r7_input_setup_decision_datetime_change_packet.md`

Verifier independence: `LIMITED` — the same Codex session implemented and
qualified the bounded repair.

## Root cause and repair

`WorkflowInputSetupDecision.decided_at` is a PostgreSQL `timestamptz` instant,
but integrity validation previously reconstructed the canonical payload from
the database driver's textual offset representation. PostgreSQL could reload
the exact instant under a different session offset, making an accepted decision
appear invalid.

The decision service now uses its existing aware-datetime UTC serializer before
`decided_at` participates in identity/checksum creation, validation, or response
projection. The timestamp remains integrity-protected, precision is retained,
and binding/omission integrity is unchanged.

## Compatibility audit

The supported HTTP/service creation path does not accept an Owner-supplied
`decided_at` and already normalized the application clock through `_aware()`
before deriving stored identity/checksum bytes. Therefore all supported valid
persisted records were created with the UTC `Z` representation now produced by
canonical reload validation. Existing IDs/checksums remain valid without a
fallback, row rewrite, schema change, or migration. A representation-sensitive
non-UTC ID could only have bypassed the supported service contract.

## Requirement coverage

| Requirement | Evidence | Level | Result |
|---|---|---:|---|
| Same instant/different offsets canonicalize identically | `test_optional_evidence_requires_exact_durable_omission_decision` | E1 | PASS |
| UTC creation/reload identity remains stable | service idempotency regression and PostgreSQL product-width route | E1/E4 | PASS |
| Different instant and tampered microsecond fail | focused service regression | E1 | PASS |
| Binding-set and omission-set integrity remain exact | complete artifact-reference service suite | E1 | PASS |
| HTTP 201, PostgreSQL reload, current decision, materialization | `test_complete_product_width_survives_fresh_postgresql_sessions`, non-UTC clock | E4 | PASS |
| Migration remains reversible | isolated `test_input_setup_decision_migration_is_reversible_without_project_rows` | E4 | PASS |

Commands/results:

- `pytest -q backend/artifact_references/tests/test_service.py` — 15 passed.
- marker-verified disposable PostgreSQL product-width qualification — 1 passed;
  database created and dropped by the isolated harness.
- marker-verified disposable migration-cycle qualification — 1 passed;
  database created and dropped by the isolated harness.

The first combined database invocation was invalid as qualification evidence
because a downgrade test shared its database with later tests. Its failures
were isolated to cross-test schema contamination plus an obsolete manifest
revision assertion. The tests were rerun in isolated databases; no migration
product defect remained. The manifest assertion was aligned to the exact six
revision lifecycle already exercised by the production fixture.

## Boundaries

- Production files changed: 1.
- Schema/migrations/publications changed: 0.
- Owner database / protected D1 Project access: 0.
- Binding-set or omission-set integrity weakening: none.
- Generic datetime behavior changes: none.

Highest achieved evidence for the bounded defect: **E4**.

R7 may resume from its first unmet qualification gate.
