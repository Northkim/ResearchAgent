# Requirement-to-test ledger specification

Status: Owner-ratified specification; checker not implemented

The future ledger is a version-controlled, machine-checkable mapping between
authoritative requirements, implementation surfaces, tests, and evidence. YAML
is the proposed initial representation because entries remain reviewable while
retaining a strict schema. A later accepted decision may select JSON instead.

## Record schema

```yaml
requirement_id: REQ-AREA-NNN
contract_source: path-or-accepted-decision#anchor
requirement_text: concise normative statement
risk: LOW | MEDIUM | HIGH | CRITICAL
implementation_symbols:
  - package.module:symbol
test_ids:
  - stable-test-id
test_levels:
  - PUBLIC_WORKSPACE_COMMAND
negative_cases:
  - case-id-or-description
recovery_cases:
  - case-id-or-description
compatibility_cases:
  - version-or-case
browser_cases:
  - route-state-viewport
owner_evidence:
  - evidence-reference-or-NONE
highest_qualified_level: E0
known_gaps:
  - explicit-gap
release_blocking: true
fixture_class: STATIC | SYNTHETIC | CONTROLLED | LONG_LIVED | OWNER
evidence_refs:
  - report-or-test-path
skipped_levels:
  - REAL_CODEX
claim_scope: exact bounded behavior
status: PROPOSED | ACTIVE | PASS | FAIL | BLOCKED | CONFLICTING
last_verified_at: null
```

`requirement_text` is a summary, not a new authority. `contract_source` must
point to an immutable schema, accepted ADR/decision, or current approved spec.
Proposed contracts may be traced during planning but cannot yield a release
PASS until accepted.

## Stable test records

Each `test_id` resolves to a separate test record containing its file, exact
test name or selector, declared level, fixture class, public path, dependencies,
negative assertions, and last result. Renaming a test must update the ledger;
copying an implementation predicate into a test does not establish independent
contract evidence.

## Mechanical validation rules

The future checker must fail when:

1. a release-blocking accepted requirement has no test ID;
2. a test ID is missing, duplicated, skipped without disclosure, or maps to no
   contract purpose;
3. `highest_qualified_level` exceeds every attached result;
4. a fake Harness is reported as `REAL_CODEX`;
5. a component/mock test is reported as controlled browser or real API;
6. a skipped PostgreSQL, migration, browser, Harness, or compatibility suite is
   reported as PASS;
7. a historical compatibility requirement lacks the relevant version fixture
   or immutable checksum/golden reference;
8. a test asserts only that the implementation called itself or reconstructs
   the production predicate without independent expected values;
9. required negative, recovery, or compatibility cases are empty for HIGH or
   CRITICAL risks without an accepted waiver;
10. an E8/E9 failure is overwritten by a lower-level PASS instead of producing
    `CONFLICTING` or `FAIL`;
11. an owner evidence reference contains private payloads or secrets;
12. implementation symbols changed materially without a ledger review.

## Required reciprocal checks

- Requirement-to-test: every release requirement has purposeful evidence.
- Test-to-requirement: every contractual test explains which requirement it
  protects; exploratory tests may use an explicit non-contract classification.
- Contract-to-version: schemas, Capsules, Definitions, routes, and migrations
  state the exact applicable version.
- Failure-to-recovery: retryable/failure states name their safe recovery test.
- UI-to-API: real UI claims reference a controlled browser case against a real
  controlled API, not only a fixture component.
- Historical-to-current: incompatible changes preserve historical golden tests
  and add the new contract rather than rewriting old expected bytes.

## Example entry

```yaml
requirement_id: REQ-ARTIFACT-001
contract_source: docs/architecture/decisions/0030-artifact-driven-full-research-flow.md
requirement_text: Workflow inputs are explicitly bound to exact immutable Artifacts; no auto-latest selection is permitted.
risk: CRITICAL
implementation_symbols: []
test_ids: []
test_levels: []
negative_cases: [unbound-input, wrong-version, cross-project, implicit-latest]
recovery_cases: []
compatibility_cases: [artifact-v1]
browser_cases: [workflow-binding-explicit-selection]
owner_evidence: [NONE]
highest_qualified_level: E0
known_gaps: [Populate from the current suite during H2]
release_blocking: true
fixture_class: STATIC
evidence_refs: []
skipped_levels: [PUBLIC_API, PUBLIC_WORKSPACE_COMMAND, CONTROLLED_BROWSER]
claim_scope: Cross-Workflow Artifact input selection
status: PROPOSED
last_verified_at: null
```

H2A may add only one minimal ledger example or schema after separate Owner
authorization. A comprehensive checker or ledger platform is
`DEFERRED_UNTIL_CONCRETE_NEED`; this phase creates neither.
