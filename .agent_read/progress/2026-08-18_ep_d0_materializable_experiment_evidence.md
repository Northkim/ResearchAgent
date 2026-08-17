# EP-D0 materializable Experiment scientific evidence carrier

Date: 2026-08-18
Baseline: `610bf694bfad4ea9bf9615529b1ab623c4d39e79` on `main`
Packet status: IMPLEMENTED_AND_VERIFIED
Implementation authorization: explicit Owner EP-D0 instruction

## 1. Objective

Publish one forward Generic Experiment version whose single final Artifact carries
canonical bounded scientific findings that exact downstream consumers can
materialize without Cloud presentation metadata or sibling Workflow reads.

## 2. Owner intent

Preserve Generic Experiment 0.6/0.9/v4 and every accepted lifecycle/execution
boundary. Repair only the missing downstream evidence carrier through immutable
Experiment 0.7, Capsule 0.10, and `experiment-record/v5`.

## 3. User problem

V4 stores normalized outcome/validity/evidence status, limitations, claim
boundaries, and an opaque result-payload checksum, but not the bounded findings.
The separate Cloud presentation companion is UI metadata and cannot be research
evidence authority.

## 4. Current baseline

Main is clean at the accepted GEN-D commit, one worktree, and Alembic sole head
`20260817_0030`. Experiment 0.6/0.9/v4 is the recommended generic version.

## 5. Authoritative sources

The EP-D0 Owner instruction, project plan, source-of-truth policy, ADRs 0043 and
0044, immutable v4 dataclasses/publication, Generic Coordinator evaluation and
finalization, exact Artifact binding/materialization, and GEN-C qualification.

## 6. Conflicts

None. ODR-009 permits local authoritative Artifact bytes while Cloud stores exact
metadata. ODR-016 is superseded for its original W1/R1/W2 gate by later accepted
reviewed implementations but does not affect this upstream Experiment repair.

## 7. Scope

Add a domain-neutral bounded evidence contract, a v5 wrapper over exact v4
lifecycle bytes, a forward version-specific producer/compiler, production Artifact
registration, Workspace sync/run pin support, one additive publication migration,
focused tests, and isolated E1-E5 qualification.

## 8. Non-goals

No downstream Workflow, frontend, presentation persistence, Generic Coordinator,
Capability interface, runner, Resource/runtime/package, preset, Path B, D1, or
historical migration change.

## 9. Domain semantics

Evidence blocks are Capability-owned canonical research evidence. Core validates
kind, bounds, identity, checksums, safe typed payload, and evaluation/output
lineage without interpreting scientific meaning. Claim eligibility continues to
require evaluation validity, scientific evidence status, methodology claim
boundaries, and limitations.

## 10. State transitions

The 0.6 lifecycle is unchanged. After exact v4-ready finalization, an exact local
Capability evidence projection binds the evaluation receipt/result payload and
produces v5. Retry with identical inputs is deterministic; changed blocks or
lineage produce a different v5 checksum and cannot replace an immutable Artifact.

## 11. Artifact impact

Add incompatible forward `experiment-record/v5`; embed one exact v4 lifecycle
record plus `reagent.experiment-bounded-scientific-evidence/v0.1`. V2-v4 remain
unchanged. No second final Artifact is introduced.

## 12. API impact

None. Existing generic Artifact metadata, exact binding, materialization plan, and
verified-copy APIs apply by type/version.

## 13. Persistence impact

One additive publication migration only. No ORM/schema or presentation-row change.

## 14. Frontend impact

None. Experiment 0.6 remains the default/recommended product version during EP-D0.

## 15. Security impact

Evidence rejects code, HTML, logs, credentials, private paths, non-finite numbers,
unbounded shapes, and arbitrary nesting. Raw output/package/dataset/checkpoint bytes
remain Local and outside v5.

## 16. Cloud/local boundary impact

Local finalization owns concrete evidence bytes. Cloud stores ordinary exact
Artifact metadata. Presentation remains an optional immutable UI companion and is
neither read nor required by downstream materialization.

## 17. Compatibility and versioning

Add Experiment 0.7.0, Capsule 0.10.0, and v5. Version 0.7 has
`default_project_setup=false`, preserving the 0.6 recommendation. All previous
Definitions, Capsules, Artifacts, Skills, and instances remain available and exact.

## 18. Migration impact

Add the policy-next revision `20260818_0031` after 0030, with fail-closed unused
identity and exact 0.6 predecessor checks. Downgrade removes only 0.7 publication.

## 19. Files expected to change

- new v5 Artifact/evidence contract module;
- new forward Experiment publication/compiler module;
- Artifact registry, Workspace sync, and Workspace CLI additive routes;
- one migration;
- up to four focused tests;
- ADR, this progress record, and compressed context.

## 20. Rejected alternatives

Second scientific-result Artifact, presentation-as-evidence, v4 mutation, raw
result embedding, arbitrary JSON blocks, sibling reads, special payload fetch,
new runner, default/preset advancement, and Core parsing of scientific semantics.

## 21. Test design

E1 typed/raw v5 validation, status cases, unsafe/oversize negatives, wrong-version
rejection, v4 checksum regression. E2 synthetic and reference-shaped Capability
projections. E3 exact service binding/materialization. E4 disposable PostgreSQL
upgrade/downgrade/re-upgrade/conflict. E5 disposable public Workspace sync,
selected-Idea materialization, controlled v5 finalization, and test-consumer copy.

## 22. Acceptance criteria

One normal v5 Artifact carries all downstream-readable bounded evidence; no
presentation/sibling/raw-output read is needed; domain-neutral fixtures pass;
historical identities remain exact; migration and public Workspace qualify; tree
is committed and clean.

## 23. Rollback conditions

Before publication, revert only new EP-D0 files/edits if evidence safety, exact
lineage, compiler identity, materialization, or migration qualification fails.
After immutable publication, use forward repair rather than row/byte mutation.

## 24. Stop conditions

Stop for historical source drift, occupied identity, need for a second Artifact,
new persistence/generalized fetch, scientific-semantic parsing in Core, browser or
downstream expansion, unisolated PostgreSQL, or material budget expansion.

## 25. Owner decisions

All material decisions are explicit in EP-D0: one v5 Artifact, bounded typed
evidence, presentation separation, forward publication, one migration, unchanged
recommendation/preset, and no downstream implementation.

## 26. Implemented result

Experiment `0.7.0`, content-derived Capsule `0.10.0`, and
`experiment-record/v5` are published additively at Alembic revision
`20260818_0031`. V5 contains one exact v4 lifecycle record and one canonical
`reagent.experiment-bounded-scientific-evidence/v0.1` section. Every block has a
stable identity and checksum, and the evidence section binds the exact Capability,
evaluation receipt, and local result-payload checksums. Output references must
resolve to an exact execution-output checksum.

The generic contract accepts PROSE, SCALAR, TABLE, SERIES, FIGURE_REFERENCE, and
OUTPUT_REFERENCE without scientific-domain fields. The reviewed sklearn reference
projection is isolated in a Capability-owned forward module; generic validation
does not import or interpret sklearn semantics. The forward Capsule reuses the
frozen lifecycle/runtime sources by content and adds only v5 finalization authority.

## 27. Publication and product-width result

The migration reuses the exact reviewed reference Capability Skill, adds one exact
Idea input requirement, and records Artifact evidence—not presentation—as the
authority. `default_project_setup=false` deliberately keeps Experiment 0.6/v4 as
the catalog recommendation and leaves Full Research unchanged. No schema table,
frontend, downstream Workflow, existing instance, or historical publication was
changed.

## 28. Verification result

Verifier independence is `LIMITED`: implementation and verification occurred in
the same session, using production validators plus independent materialized JSON,
public command, and PostgreSQL boundaries.

- E1/E2: 21 focused contract/compiler/migration-authority tests passed, including
  non-ML and scalar/table/series/reference cases, wrong versions, safety, bounds,
  exact lineage, deterministic checksums, and frozen v4 checksum assertions.
- E3/E5: the copied public Workspace CLI used a real loopback FastAPI service to
  refresh and idempotently materialize one exact v5 Artifact into a test-only
  consumer. The consumer validated findings, status, claim boundaries, and
  limitations from the materialized v5 bytes with no presentation lookup.
- E4: a marked disposable PostgreSQL database upgraded base→0031, passed
  Alembic check, publication/readback assertions, downgrade→0030, re-upgrade,
  immutable-conflict rejection, and identity-verified deletion. Three tests passed.
- Historical/affected: 93 passed and one explicit E7-only test skipped. The
  macOS no-egress cases passed under their required OS execution context.
- Controlled-local PostgreSQL regression: 2 passed on a second marked disposable
  database, which was deleted.
- Compileall, sole-head, and `git diff --check` passed.

E7 was not required or re-claimed: the initial Experiment methodology/Codex
interaction is byte-equivalent to accepted 0.6 behavior; EP-D0 changes only local
final Artifact evidence projection. No real scientific Experiment ran.

## 29. Evidence limits

The E5 finalizer uses controlled Capability evaluation bytes, not real scientific
execution or real Codex completion. No browser or Owner D1 evidence is claimed.
The public v5 path is intentionally not the default Full Research path until the
separately authorized downstream product-width phase consumes v5.

## 30. Engineering verification packet

Verification identity: `EP-D0-V1`, baseline
`610bf694bfad4ea9bf9615529b1ab623c4d39e79`, verifier independence `LIMITED`.

| Requirement | Risk | Evidence | Level | Fixture | Result |
|---|---|---|---|---|---|
| One exact v5 carrier | release blocking | typed/raw validator and record checksum tests | E1 SCHEMA | synthetic independent JSON reread | PASS |
| Domain-neutral bounded blocks | release blocking | non-ML plus reference-shaped block matrix | E1/E2 CONTRACT | synthetic + Capability-owned reference | PASS |
| Status/claim semantics | release blocking | unavailable/failed/invalid/inconclusive/bounded-support cases | E1 CONTRACT | production v4 lineage | PASS |
| Safety and bounds | release blocking | code/HTML/log/key/URL/path/JSON/NaN/nesting/size negatives | E1 SCHEMA | adversarial synthetic | PASS |
| Exact materialization | release blocking | ordinary binding, verified copy, reread, repeat | E3/E5 PUBLIC_WORKSPACE_COMMAND | disposable Workspace | PASS |
| Presentation separation | release blocking | consumer validates v5 with no companion lookup | E3/E5 | controlled materialized Artifact | PASS |
| Additive publication | release blocking | base upgrade, check, downgrade/re-upgrade, conflict/readback | E4 MIGRATION | marked disposable PostgreSQL | PASS |
| Historical compatibility | release blocking | v2/v3/v4/compiler/runner/approval checksums and regressions | E1-E4 | historical goldens + disposable DB | PASS |

Risk review found no hidden sibling read, implicit/latest binding, second Artifact,
hosted execution, browser filesystem mutation, presentation evidence authority,
new network/dependency behavior, local-private path exposure, or historical-byte
edit. E6, E8, and E9 are outside EP-D0. E7 is `NOT_REQUIRED` for the permitted
claim because the accepted Harness start/checkpoint semantics are unchanged; it is
not reported as a pass.

Permitted claim: `PASS_EP_D0_READY_TO_RETRY_DOWNSTREAM`. This permits Owner review
and a separately authorized EP-D1 retry using exact v5. It does not qualify
downstream contracts, Full Research, real scientific execution, or D1 continuation.
