# EP-D2-U1-F1 forward foundation ordering correction

## 1. Objective

Make the runtime projection of the three EP-D1 forward Workflow Capsules exactly
reproduce the immutable `20260818_0032` publication order for `mutable_roots`.

## 2. Owner intent

Correct only the source/publication mismatch isolated by EP-D2-U1-F0 so Project
creation can replay the published Workflow Foundation without weakening immutable
equivalence or changing product recommendations.

## 3. User problem

Every PostgreSQL-backed Project creation fails before setup resolution because the
runtime Initial Writing Capsule projection orders two mutable roots differently
from the published row.

## 4. Current baseline

`main` at `9c58c372e59960b5686802178cd8fbbf86119f8d`, one worktree, sole
Alembic head `20260818_0032`, plus the intentionally uncommitted 17-file EP-D2-U1
working set fingerprinted as
`48e618aa59ae6ac82620c60a781aae8902353c2c10b0c4f1245dc132d4e62507`.

## 5. Authoritative sources

- Explicit EP-D2-U1-F1 Owner authorization.
- Frozen migration `20260818_0032_forward_downstream_v5_chain.py`.
- SQL immutable comparator `_capsule_content`.
- Version-specific projection `backend/project_workspaces/forward_downstream.py`.

## 6. Conflicts

Resolved by Owner authority: migration 0032 stores `memory/owner-review.json`
before `memory/current-artifact.json`; source projects the reverse. Migration is
immutable authority. No unresolved source conflict remains.

## 7. Scope

- Reorder only those two entries in the shared forward Capsule projection.
- Add complete SQL source/publication equivalence, double replay, Project setup,
  role, recommendation, preset, and immutable-identity regression assertions.

## 8. Non-goals

No comparator normalization, migration, catalog/preset change, role change,
Experiment change, presentation change, scientific contract change, D1, or EP-D2.

## 9. Domain semantics

`mutable_roots` remains an ordered immutable Capsule field. Exact published order
is authoritative even when the set of paths is otherwise identical.

## 10. State transitions

Fresh database at 0032 plus exact source replay remains unchanged and succeeds.
Repeated exact replay is idempotent. Any other immutable difference still fails
closed. Project creation proceeds only after exact foundation replay.

## 11. Artifact impact

None. Artifact schemas, bytes, bindings, and presentation authority are unchanged.

## 12. API impact

No API contract change. Existing `POST /projects` stops encountering the internal
foundation mismatch.

## 13. Persistence impact

No schema or row mutation. Existing migration-published rows are reused exactly.

## 14. Frontend impact

None.

## 15. Security impact

None. Immutable comparison remains strict and order-sensitive.

## 16. Cloud/local boundary impact

None.

## 17. Compatibility and versioning

Unchanged-compatible source correction. All published Definition, Capsule, and
Artifact identities remain byte-identical.

## 18. Migration impact

Zero. Sole head remains `20260818_0032`; migration 0032 stays byte-identical.

## 19. Files expected to change

- `backend/project_workspaces/forward_downstream.py`
- `backend/database/tests/test_forward_downstream_v5_postgresql.py`
- this governance record

## 20. Rejected alternatives

Sorting, sets, order-insensitive comparison, migration rewrite, repair migration,
manual row edits, recommendation changes, and fixture bypass.

## 21. Test design

E1/static immutable identity checks; E4 complete Capsule comparison and repeated
SQL foundation replay; real-API PostgreSQL Project creation for Literature-only,
Custom four-Workflow, and unchanged Full Research; role/recommendation regression;
then the frozen U1 targeted tests and controlled browser E6.

## 22. Acceptance criteria

All three source Capsules equal their 0032 rows under the production comparator;
double replay creates no rows; all three Project modes succeed; role and Experiment
defaults/preset stay fixed; F1 is separately committed; U1 fingerprint is unchanged;
U1 E6 passes.

## 23. Rollback conditions

Before acceptance, revert only the unpublished F1 source/test commit if complete
equivalence or browser recovery fails. Never change the published migration row.

## 24. Stop conditions

Stop for any migration/comparator/preset/role/Experiment/U1 change, more than four
F1 files or 500 net lines, unexpected immutable delta, or new E6 product defect.

## 25. Owner decisions

Packet status: `READY_FOR_IMPLEMENTATION_REVIEW`.

Packet approval and explicit implementation authorization are supplied by the
EP-D2-U1-F1 Owner instruction. No remaining design decision is required.
