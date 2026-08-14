# Engineering change contract specification

Status: Owner-ratified specification; capability not implemented

Future capability name: `engineering-change-contract`

This combined capability covers spec-to-architecture, API contract design,
contract change control, implementation planning, and architecture review. It
does not authorize implementation by producing a packet.

## Trigger conditions

A change packet is mandatory for any proposed:

- user-visible product behavior or Workflow-state change;
- Workflow Definition, Capsule, Skill, Resource, Artifact, Progress, or prompt
  contract change;
- API operation, DTO, error, authorization, or idempotency change;
- persistence model, migration, seed, index, or lifecycle change;
- frontend route, task flow, mutation, status, or backend-type change;
- compatibility, historical-recovery, or long-lived Workspace repair;
- Provider, network, credential, storage, privacy, or trust-boundary change;
- architecture dependency or module-ownership change;
- material expansion beyond an already approved implementation plan.

Pure typo corrections may use a bounded documentation-only packet when they do
not alter contract meaning.

## Mandatory inputs

1. Owner Design Packet or explicit owner request.
2. Repository baseline: branch, HEAD, worktree, migration head, dirty-state
   classification, and relevant published versions.
3. Repository evidence for current implementation.
4. Affected authoritative contracts according to
   `SOURCE_OF_TRUTH_POLICY.md`.
5. Existing tests and their evidence levels.
6. Known owner-state evidence, including failures and unresolved observations.
7. Active Owner Decision Register entries.
8. Security and Cloud/local boundaries.

If an input is unavailable, record it as unknown. Do not replace it with an
assumption without an owner-approved assumption entry.

## Mandatory output packet

Every packet must contain these sections in this order:

1. Objective
2. Owner intent
3. User problem
4. Current baseline
5. Authoritative sources
6. Conflicts
7. Scope
8. Non-goals
9. Domain semantics
10. State transitions
11. Artifact impact
12. API impact
13. Persistence impact
14. Frontend impact
15. Security impact
16. Cloud/local boundary impact
17. Compatibility and versioning
18. Migration impact
19. Files expected to change
20. Rejected alternatives
21. Test design
22. Acceptance criteria
23. Rollback conditions
24. Stop conditions
25. Owner decisions

## Required packet semantics

### State transitions

List every legal before/event/after transition, transition authority,
idempotency identity, failure state, retry behavior, and durable evidence.
Absence of a transition is a contract decision, not an implementation detail.

### Versioning

Classify each affected contract as unchanged-compatible, new compatible
version, incompatible new version, companion contract, or prohibited in-place
change. Published bytes and historical identities are never update targets.

### File scope

Name expected files or bounded directories before implementation. During
implementation, expansion beyond this scope requires a packet amendment and,
when material, owner approval.

### Rollback

Rollback may revert unpublished source in an approved branch. It may not
delete accepted user state, rewrite uploaded Progress, or replace a published
Capsule. Forward repair/version publication is required once immutable state
exists.

## Fail-closed rules

The capability must stop with a named reason when:

- owner intent conflicts with an immutable contract;
- an architectural or owner decision is missing;
- implementation would silently read a sibling Workflow private file;
- historical Capsule bytes would need mutation;
- an Artifact would be selected implicitly;
- a browser operation would write Workspace state;
- migration or versioning impact is unresolved;
- expected files expand materially beyond the approved packet;
- implementation evidence contradicts the active contract;
- a real Provider, owner Workspace, owner database, credential, or destructive
  operation becomes necessary without explicit authority;
- the required verification level is unavailable and the change is release
  blocking.

Allowed outcomes are `READY_FOR_IMPLEMENTATION_REVIEW`,
`OWNER_DECISION_REQUIRED`, `QUALIFICATION_REQUIRED`, and `STOP_CONFLICT`.
Only a separate owner instruction may authorize implementation.

## Architecture review checklist

- Cloud coordinates; Local Workspace executes.
- Concrete continuation comes from durable local files, not chat memory.
- Browser-to-Workspace mutation is absent.
- Exact Artifact and Resource identities remain explicit.
- Core maturity is not inferred from publication review status.
- Capsule and Skill delivery preserves historical checksums.
- Progress finalization has one effective authority and safe recovery.
- Hosted Runtime remains compatibility-only unless explicitly reauthorized.
- Authentication assumptions match loopback single-user scope.
- Tests declare their qualification level and do not overclaim.
