# Post-D1 R7 full-system qualification — blocked

Date: 2026-08-20

Status: `RESOLVED_BY_BOUNDED_REPAIR`

## Entry state

- Branch: `main`
- R6 product commit: `39f4d72a67ca52d962bd0dcf552b930ae9e3b0cb`
- R6 governance commit / R7 entry HEAD: `a6d44432c78ba9e2950bc468f283f9f6704cdfe3`
- Alembic sole head: `20260820_0039`
- Owner database and protected D1 Project: not accessed

## Passing evidence before the stop

- Full frontend suite: 21 files / 82 tests passed.
- TypeScript, ESLint, Python compileall, and `git diff --check`: passed.
- Non-migration backend suite: 1,089 passed / 5 skipped in the broad run;
  its only failure was a multiprocessing child import-path issue, and that exact
  lock test passed separately with an absolute repository `PYTHONPATH`. Combined
  qualified total: 1,090 passed / 5 skipped.
- Focused current/historical product-route fixtures passed after aligning them
  to exact immutable publications and the explicit optional-evidence decision
  contract.
- All completed disposable databases were marker-verified and dropped.

## New CORE defect

ID: `R7-INPUT-SETUP-DECISION-TIMEZONE-01`

Reproduction on a fresh marker-verified PostgreSQL database:

1. Create an exact input setup with required inputs bound and optional evidence
   intentionally omitted.
2. POST the supported input-setup decision. Cloud returns HTTP 201.
3. Read the same setup through a fresh Unit of Work.
4. The binding-set checksum and omitted keys remain identical, but
   `current_decision` is `null`.
5. Materialization fails with `INPUT_SETUP_DECISION_REQUIRED`.

Observed exact state after the accepted POST:

- binding-set checksum:
  `sha256:e7b1b14385b2acd678f880bf23e0786837e5b9884103ad13b66773f11dc96e0b`
- omitted optional requirements: `prior_manuscript`, `review_feedback`
- `decision_required`: `true`
- `current_decision`: `null`

Root cause in current source:

- `confirm_input_setup` includes `decided_at` in the decision ID/checksum payload
  using `datetime.isoformat().replace("+00:00", "Z")`.
- PostgreSQL `timestamptz` preserves the instant but may reload it with the
  session timezone offset (the failing run returned persisted timestamps with a
  `+01:00` offset).
- `valid_input_setup_decision` hashes that reloaded textual offset form instead
  of first normalizing the instant to UTC.
- The same decision therefore passes at creation but fails integrity validation
  after PostgreSQL reload.

This is a product contract defect, not a stale fixture: an accepted durable
Owner decision cannot authorize the next exact materialization after persistence
reload. It blocks the required R7 optional-evidence scenario and violates the R2
durable decision contract.

## Stop and safety state

- No product repair was attempted.
- R7 E5/E6 was not started after the CORE defect was proven.
- No Owner database, protected Project, research Artifact, or binding was read or
  changed.
- No migration or immutable publication changed.
- Final disposable-database inventory: zero `reagent_qualification_%` databases.
- Repository remains intentionally dirty with R7 test/fixture alignment and the
  failing regression assertion; it is not committed as a passing phase.

Safe next action: authorize a bounded repair that canonicalizes integrity-bound
decision timestamps to UTC consistently at creation and validation, adds a
PostgreSQL reload regression, and then resumes R7 from the blocked gate.

## Resolution

The Owner authorized the bounded repair. Commit
`86abbc196fe388d1c7f6cd1030d8afbc7bba89dc` canonicalizes the integrity-bound
aware timestamp to deterministic UTC without removing it from protection,
weakening binding/omission integrity, rewriting persisted records, or adding a
migration. Focused E1/E4 and real PostgreSQL round-trip evidence passed. R7 then
resumed from this exact unmet gate and completed; see
`2026-08-20_post_d1_r7_complete.md`. The original stop evidence above is
retained as historical defect evidence.
