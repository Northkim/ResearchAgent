# Agent Context and Git Tracking Policy

## Purpose

ReAgent uses `.agent_read/` as a durable development-governance and handoff
layer. It is not product runtime memory and must never be loaded into research
workflow context. Canonical records in this directory are versioned so another
developer or agent can recover architecture, owner decisions, implementation
boundaries, and phase continuity from a clone.

`docs/` contains the repository's formal product, engineering, evidence,
contract, security, retention, and acceptance documentation. Formal documents
are source material, not disposable generated output.

## Path classification

| Path | Classification | Git policy |
|---|---|---|
| `.agent_read/AGENT.md` | Agent operating instructions | Track |
| `.agent_read/context.md` | Stable, compressed project state | Track |
| `.agent_read/decisions/` | Proposed, accepted, superseded, or rejected ADRs and the ADR convention | Track |
| `.agent_read/progress/` | Curated milestone and phase handoffs | Track |
| `.agent_read/tmp/` | Temporary working files | Ignore |
| `.agent_read/cache/` | Rebuildable caches and generated indexes | Ignore |
| `.agent_read/scratch/` | Local scratch notes and prompts | Ignore |
| `.agent_read/logs/` | Transient agent or tool logs | Ignore |
| `.agent_read/local/` | Machine- or user-local working state | Ignore |
| `.agent_read/runtime/` | Process state, locks, journals, and generated runtime data | Ignore |
| `.agent_read/**/*.tmp`, `.agent_read/**/*.bak` | Temporary and backup files | Ignore |
| A new `.agent_read/` subtree | Unknown until classified | Review before adding; do not rely on the absence of an ignore match as approval to commit |
| `docs/PROJECT_DEVELOPMENT_PLAN.md` | Product source of truth | Track |
| `docs/evidence/` | Formal evidence, contracts, policies, registers, and acceptance protocols | Track |
| `docs/engineering/` | Repository engineering policy | Track |
| A new formal `docs/` subtree | Canonical documentation when owner/repository purpose is clear | Track after review |
| Generated, private, or runtime material proposed under `docs/` | Not canonical documentation | Do not commit; store in an approved ignored/private location |

The repository currently has no other `.agent_read/` or `docs/` subdirectory.
Tracked historical progress reports remain governance records even when they
describe a specific development machine. New reports should prefer
repository-relative paths unless an absolute path is necessary audit evidence.

## Canonical governance versus local state

Canonical governance is curated Markdown that records stable project context,
architecture decisions, owner approvals, implementation boundaries,
phase-completion evidence, reproducibility instructions, or formal policy. It
must be useful to a reviewer working from a fresh clone.

Local state includes scratch notes, temporary prompts, raw logs, caches,
generated indexes, local plans, process locks, debug output, credentials, API
responses, candidate pools, real abstracts, database files, and generated
acceptance artifacts. Local state must not be placed in canonical paths merely
because Git currently reports the path as trackable.

The `.gitignore` intentionally does not ignore `.agent_read/` or `docs/` as a
whole. It excludes named local-state subtrees under `.agent_read/`; existing
repository-wide rules continue to exclude secrets, logs, databases, editor
backups, and generated runtime data.

## Secrets, private evidence, and runtime data

- `.env` and `.env.*` remain ignored; only `.env.example` may be tracked.
- Credentials, key fragments, private keys, tokens, and secret-bearing test
  fixtures must never be committed to `.agent_read/` or `docs/`.
- `runtime_data/` is the ignored root for local workflow artifacts and
  acceptance evidence. It is not documentation and must not be unignored.
- Real abstracts, real candidate pools, private paper manifests, raw OpenAlex
  or model responses, provider request bodies/responses, operation journals,
  and live acceptance databases belong in an approved ignored private store,
  normally a bounded subtree of `runtime_data/`.
- A formal document may describe a private artifact's schema, checksum
  protocol, retention rule, or repository-relative placeholder. It must not
  embed the private artifact or its sensitive contents.
- If a possible credential or private dataset appears in a trackable path,
  stop before staging and request owner/security review.

## Working with a dirty worktree

Existing changes belong to their author until proven otherwise. Inspect and
preserve them, separate the current task's diff from pre-existing work, and do
not clean, reset, restore, overwrite, move, stage, or commit unrelated changes.
A dirty tree is not itself a reason to discard work. Before proposing a staging
boundary, classify every modified or untracked path and run secret/private-data
checks appropriate to the material.

## Adding governance records

### Architecture decision

Follow `.agent_read/decisions/README.md`. Use the next numbered Markdown file,
record its actual status, and never present a proposal as accepted. Accepted
ADRs are superseded by a later ADR rather than silently rewritten.

### Phase progress report

Add a concise Markdown handoff under `.agent_read/progress/`. Record scope,
verified outcomes, remaining risks, and the next permitted action; do not paste
raw logs, secrets, provider responses, or private research content. Update
`.agent_read/context.md` only when the compressed current state has changed.

### Private acceptance evidence

Commit only the protocol, schema, policy, redacted evidence register, and
checksum/retention design. Store the live manifest, source content, reports,
provider payloads, journals, and databases beneath the approved ignored
acceptance root. A human-readable report is not automatically safe to commit
when it was produced from private or bounded live inputs.

## Verification

Run these checks from the repository root before staging governance or
documentation changes:

```bash
git check-ignore -v --no-index .agent_read/context.md || true
git check-ignore -v --no-index .agent_read/decisions/NNNN-example.md || true
git check-ignore -v --no-index .agent_read/tmp/probe.tmp || true
git check-ignore -v --no-index docs/evidence/example.md || true
git check-ignore -v .env
git check-ignore -v runtime_data
git ls-files .agent_read
git ls-files docs
git status --ignored --short
git diff --check
```

Expected behavior:

- canonical `.agent_read` and formal `docs` paths have no positive ignore
  match;
- named local `.agent_read` subtrees and temporary/backup files are ignored;
- `.env`, databases, generated artifacts, and `runtime_data/` remain ignored;
- no staged path exists until an owner or maintainer deliberately stages the
  reviewed boundary.
