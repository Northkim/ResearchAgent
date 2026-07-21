# Architecture Decision Records

Use this directory for consequential decisions that future agents must preserve or deliberately supersede.

Do not create a decision record for an unapproved proposal. When a decision is accepted, create a file named `NNNN-short-title.md`, starting at `0001`.

Each record should contain:

```markdown
# NNNN: Decision title

- Status: Proposed | Accepted | Superseded | Rejected
- Date: YYYY-MM-DD
- Supersedes: NNNN (if applicable)

## Context

What forces and constraints require a decision?

## Decision

What was decided?

## Consequences

What becomes easier, harder, required, or intentionally deferred?

## Alternatives considered

What credible alternatives were evaluated and why were they not selected?
```

Accepted records are append-only. To reverse one, create a new record and mark the old record as superseded.
