# 0056: Human checkpoints bound active Harness phases

- Status: Accepted
- Date: 2026-08-20

## Context

The normal Literature path previously kept one Codex subprocess and one scoped
Provider session alive across search planning, retrieval, screening, and final
Owner review. The 15-minute Provider lifetime and 20-minute subprocess deadline
therefore counted time during which the researcher was only reading and
deciding. A real re-acceptance round was terminated after completed retrieval;
its exact result bytes survived, but the conversational screening disposition
did not.

Published Literature Capsules cannot be mutated. Their validator also permits
only one Capsule-owned terminal Progress report, so nonterminal coordinator
checkpoints cannot be inserted into the immutable Capsule report directory.

## Decision

The normal root Workspace client coordinates forward Literature as bounded
active phases. Planning and synthesis each run in a short noninteractive Harness
subprocess with an active-work timeout. Provider authority exists only around
the exact query operations and is released before screening or finalization
review.

Before each Owner wait, ReAgent commits exact local checkpoint state under a
ReAgent-owned Workspace namespace and automatically uploads bounded Progress.
Screening proposals are not Owner authority. An accepted disposition becomes
durable only when bound to the exact candidate-set checksum. A pending decision
is represented explicitly and is never inferred from chat.

Coordinator Progress is stored beside, not inside, immutable Capsule state. The
Capsule receives final scientific outputs only after exact Owner finalization.
Completed Provider queries are reused by checksum on resume.

## Consequences

- Human dwell no longer consumes active Harness or Provider lifetime.
- Active computation remains time-bounded and fails closed when hung.
- Provider sessions do not survive beyond actual Provider work.
- A terminal, disconnected, or restarted Harness session can resume the exact
  local candidate set and accepted scientific dispositions without new search.
- Cloud receives only bounded Progress and existing Artifact metadata; complete
  candidate/reason bytes remain Local.
- Published Definition/Capsule/Artifact identities and Alembic remain unchanged.
- Direct historical Capsule launch remains an operator surface; the root
  Workspace command is the normal Owner lifecycle authority.

## Alternatives considered

- Increase both timeouts: rejected because human dwell remains coupled to active
  execution and Provider authority.
- Treat the conversation as durable approval: rejected because chat is not exact
  Workflow authority.
- Write nonterminal reports into Capsule 0.8: rejected because it violates its
  immutable one-terminal-report contract.
- Keep Provider access alive and pause only Codex timeout: rejected because
  Provider resources are not needed during Owner review.
- Repeat search on resume: rejected because completed exact Provider work is
  already durable and repetition can change evidence.
