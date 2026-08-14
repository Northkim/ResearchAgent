---
name: engineering-change-contract
description: Plan repository changes that may affect ReAgent product behavior, Workflow semantics or state, Artifact contracts, APIs, persistence, frontend behavior, Cloud/local or security boundaries, compatibility, versioning, or production implementation scope. Use before contract-affecting implementation or architecture review; normally skip wording-only or formatting-only work unless it changes an authoritative contract.
---

# Engineering change contract

Produce a bounded change packet. Do not implement merely because the packet is
complete.

## Authoritative inputs

Read, in order:

1. `docs/engineering/SOURCE_OF_TRUTH_POLICY.md`
2. `docs/engineering/OWNER_DECISION_REGISTER.md`
3. `docs/engineering/ENGINEERING_CHANGE_CONTRACT_SPEC.md`
4. `docs/engineering/templates/CHANGE_PACKET_TEMPLATE.md`

Then locate the relevant immutable contracts, current implementation, tests,
and known owner-state evidence. Do not duplicate the governance documents in
the packet.

## Procedure

1. Record Git root, branch, HEAD, status, worktrees, migration head, and affected
   published identities before proposing changes.
2. Apply the source precedence. List conflicts and unknowns without silently
   reconciling them.
3. Check accepted Owner decisions and identify any decision still required.
4. Trace current behavior through its supported public path, contracts,
   implementation, persistence, frontend consumer, and tests as applicable.
5. Fill the change-packet template compactly. State exact scope, non-goals,
   state transitions, compatibility, security, and Cloud/local effects.
6. Set an explicit file/count/line budget and name expected paths.
7. Separate non-blocking findings into deferred scope; do not turn discovery
   into cleanup authorization.
8. End with packet status and the explicit implementation authorization state.
   Packet approval and implementation authorization are separate events.

## Fail closed

Stop and report the gate when there is:

- a source conflict affecting the change;
- a missing Owner decision;
- implicit Artifact selection;
- browser-to-Workspace writing;
- sibling Workflow private-file access;
- historical Capsule mutation;
- unresolved migration or version strategy;
- material expansion beyond the approved file scope;
- unapproved Provider, credential, owner-data, or destructive access.

Never infer a migration, mutate an old Capsule, select an Artifact implicitly,
weaken an immutable contract, or absorb an unrelated observation into scope.

