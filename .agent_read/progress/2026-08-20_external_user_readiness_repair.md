# External-user readiness repair (2026-08-20)

Status: **IMPLEMENTED; controlled qualification PASS; real-owner acceptance pending**

## 1. Codex Managed Harness launch repairs

### Defect A - symlinked Codex executable rejected

`workspace_cli._managed_codex_executable` rejected any override path that was a
symlink. The fix resolves the symlink first and validates the resolved target
(regular file + executable). The override is additionally resolved ONCE at the
`run_workflow` root-CLI boundary, so published Capsule runtimes and subprocess
launchers always receive the resolved target - published Capsule bytes are
unchanged. The default PATH discovery was already portable (`shutil.which`).
The missing-Codex diagnostic is now actionable ("Codex is not ready on this
computer. ... Your Workspace was not changed.") and fails before Workflow
mutation (`CODEX_UNAVAILABLE`).

### Defect B - relative Capsule passed to Codex `-C`

`load_workspace` now normalizes the root with `Path(root).expanduser().resolve()`,
so `run .` produces absolute Capsule paths; Codex `-C` and the subprocess cwd
are absolute. Verified by the exact previously-failing shape: full CLI
`reagent_local.py run .` under a PTY with real Codex reaches the plan approval
checkpoint with no `os error 2`.

## 2. Cloud-to-Local command contract

- One authoritative command generator: `backend/progress_reports/aggregation.py`
  now attaches the exact local command to every LOCAL next-action projection
  (`WorkflowNextActionProjection.command`), using `--workflow` only when the
  definition has exactly one active instance, otherwise the exact
  `--workflow-instance` selector.
- Stale-state gating already existed server-side (`ACKNOWLEDGED_STALE` /
  `NOT_INSTALLED` -> SYNC as the single next action); the frontend now renders
  the server command verbatim instead of hand-writing commands.
- `CopyCommand` sanitizes copied text (non-breaking spaces, typographic quotes
  and dashes -> plain ASCII).
- `artifact materialize` already self-refreshes the exact Cloud binding and
  verifies the plan checksum, so no hidden refresh is required.

## 3. Available Workflows cards

Simplified to name + authoritative description + one action. Removed the
AVAILABLE/maturity badges, version caption, prototype note, and bundled-Skill
blocks from the cards; bundled Skill metadata moved to the existing
"Cloud configuration details" technical surface. Multi-instance support is the
documented contract (`allows_multiple_instances=True`); cards now show
"Add another" plus an "N already in project" caption when an instance exists.

## Verification

- Backend: `1129 passed` (full suite; 1 deselected pre-existing macOS
  spawn-child artifact test; 18 environment-only Postgres setup errors).
- New backend regression file `test_codex_launch_portability.py`: absolute
  override, symlink, Homebrew-like symlink, broken symlink, non-executable
  target, default discovery, missing-Codex diagnostic, relative-root
  normalization, fail-before-mutation, and authoritative command generation.
- Frontend: typecheck, lint, `84 passed` (Vitest), including card simplification
  and copy sanitization assertions.
- `compileall`, `git diff --check`, Alembic sole head `20260820_0039`: PASS.
- Controlled real-Codex PTY run of `reagent_local.py run .` (relative
  workspace): plan approval reached, no ENOENT.

## Real-owner acceptance (pending)

Primary command copied from Cloud, unchanged:
`python reagent_local.py run . --workflow literature-search-local-experimental`.
Optional override check: add `--codex-executable /opt/homebrew/bin/codex`.
Cloud copy-paste, materialization, and full-page screenshot acceptance remain
for the Owner.
