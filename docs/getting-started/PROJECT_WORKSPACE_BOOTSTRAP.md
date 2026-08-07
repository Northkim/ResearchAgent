# Project Workspace Bootstrap and Legacy Package Adoption

NIGHT-B3 added an optional long-lived Project Workspace around the existing
Literature Search Package. NIGHT-B4 adds explicit pull sync, safe Capsule
installation, an Installed Workspace Lock, and installation acknowledgement.
Standalone Package operation remains supported.

## Boundary

The cloud owns the canonical Project and Workspace identities, current Desired
Manifest, Workflow Instance, and exact Workflow/Capsule pins. The local
Workspace owns concrete research files. Codex still runs inside the Literature
Search Capsule; the backend does not execute or synthesize research.

The Workspace contains no token, database URL, Provider key, or machine-local
absolute path. The cloud continues to retain only bounded metadata and accepted
Progress Report bytes, not the complete Workspace.

## Prerequisites

- start the local ReAgent product with `make dev`;
- create a Project and generate its Literature Search Package;
- keep the downloaded ZIP or extracted Package in a long-term, owner-controlled
  location outside Git;
- choose an empty or nonexistent Workspace target directory.

## Download a bootstrap descriptor

Use the canonical Project ID from the product. The read-only endpoint is:

```text
GET /projects/{project_id}/workspace-bootstrap
```

For example, save the JSON response as `workspace-bootstrap.json` using an HTTP
client. Generate the Package first when the descriptor should authorize that
exact Package for adoption. A descriptor downloaded before Package generation
can still bootstrap identity; download a fresh descriptor and pass it to
`adopt --descriptor` when adopting later.

## Bootstrap a Workspace

From the ReAgent repository:

```bash
python reagent_local.py bootstrap "$WORKSPACE_DIR" \
  --descriptor workspace-bootstrap.json
```

The command is non-interactive. It validates the descriptor, creates all files
in a same-filesystem staging directory, verifies them, and atomically publishes
the Workspace. Repeating the command with the same Project/Workspace identity
returns `ALREADY_BOOTSTRAPPED`. A different identity or damaged descriptor
fails without overwrite.

The B3 layout is deliberately minimal:

```text
<workspace>/
├── AGENT.md
├── project.json
├── reagent_local.py
├── .reagent/
│   ├── bootstrap.json
│   ├── desired-manifest.json
│   └── capsule-registry.json
└── capsules/
```

`project.json` is checksum-bound identity metadata. Do not edit it. Bootstrap
does not claim installation. The first successful B4 sync creates the distinct
`.reagent/installed-lock.json`; acknowledgement metadata is stored separately.

Inspect identity without changing the Workspace:

```bash
python reagent_local.py workspace status "$WORKSPACE_DIR"
```

Add `--json` to any command for one stable machine-readable result on stdout.

## Explicitly synchronize desired Capsules

With the loopback ReAgent API running, execute:

```bash
python reagent_local.py sync "$WORKSPACE_DIR"
```

Preview without writing local installation state:

```bash
python reagent_local.py sync "$WORKSPACE_DIR" --dry-run --json
```

The command reads current cloud desired state, compares exact Workflow
Instance/version/checksum pins with `.reagent/installed-lock.json`, downloads
only missing available Capsules, verifies the ZIP and immutable Package
contract, stages on the destination filesystem, and atomically publishes each
Capsule. It then atomically writes the lock and reports the active installation
set to the cloud. No downloaded script is executed during installation.

The lock is the sole installed-state truth source. The B3
`.reagent/capsule-registry.json` remains immutable legacy adoption evidence; on
first sync it is revalidated against the Package and cloud Manifest before an
Installed Lock is created. It is not updated afterward. Declared mutable
outputs, memory, Progress and receipts are excluded from immutable drift and
are never overwritten by no-op sync.

`workspace status` distinguishes `BOOTSTRAPPED_NO_LOCK`,
`INSTALLED_LOCK_CURRENT`, `ACK_PENDING`, and `ACKNOWLEDGED_CURRENT`. A cloud
acknowledgement means only that the client submitted a checksum-bound report
matching a cloud Manifest revision. It does not mean ReAgent has copied,
inspected, or backed up local files.

If acknowledgement fails after installation, sync returns `ACK_PENDING` and
preserves the Capsule and Lock. Run the same command again; it retries only the
stored envelope with the same idempotency key. If the Manifest advanced during
installation, the stale acknowledgement is rejected, the revision-N local
files remain, and the next plan handles the new revision. A retired instance is
marked `RETAINED_NOT_DESIRED`; its local Capsule and research files are not
deleted.

## Adopt an existing Literature Search Package

The source may be the extracted Package directory or the original ReAgent ZIP:

```bash
python reagent_local.py adopt "$LEGACY_PACKAGE" "$WORKSPACE_DIR"
```

When using a newer descriptor than the Workspace bootstrap cache:

```bash
python reagent_local.py adopt "$LEGACY_PACKAGE" "$WORKSPACE_DIR" \
  --descriptor workspace-bootstrap.json
```

Adoption:

- verifies Package schema, Project/Package/Workflow identity, the frozen legacy
  Workflow Instance, exact Capsule pin, manifest checksums, immutable files,
  required launcher/helpers, and declared mutable policy;
- rejects traversal, absolute paths, portable-name collisions, symlinks,
  hardlinks, special files, unsafe ZIP members, excessive size/compression,
  credentials, and target conflicts;
- copies through staging into
  `capsules/<workflow_definition_id>/<workflow_instance_id>/<capsule_version>/`;
- preserves outputs, memory, Progress reports/receipts, and other declared
  mutable state;
- leaves the source byte-for-byte unchanged and never executes source code;
- returns `ALREADY_ADOPTED` when the same source state is already present.

If the source changes after adoption, the command does not merge or overwrite.
It reports `CAPSULE_ADOPTION_CONFLICT`; incremental updates belong to a future
sync phase.

## Run Literature Search

Standalone mode remains supported:

```bash
cd "$LEGACY_PACKAGE"
python reagent_local.py run .
```

For Workspace-adopted mode, enter the Capsule path printed by `adopt` and use
the same accepted command:

```bash
cd "$WORKSPACE_DIR/capsules/<workflow_definition_id>/<workflow_instance_id>/<capsule_version>"
python reagent_local.py run .
```

The original interactive checkpoints, fresh upload-only session, upload retry,
Progress identity, and OpenAlex boundary are unchanged. The Package launcher
continues to validate its own manifest and never infers identity from a folder
name or current working directory.

## Run an exact Workspace Workflow

For a synchronized Workspace, preflight or run an installed instance without
inferring identity from its directory:

```bash
python reagent_local.py run "$WORKSPACE_DIR" \
  --workflow-instance <workflow-instance-id> --preflight-only
python reagent_local.py run "$WORKSPACE_DIR" \
  --workflow-instance <workflow-instance-id>
```

Idea Discovery preflight additionally requires a specific Cloud Artifact
binding, a current local Artifact Index, a materialization receipt, and exact
input bytes. It never materializes automatically. See
[Idea Discovery and Artifact handoff](IDEA_DISCOVERY.md).

## Recovery and exit codes

Bootstrap never writes a success descriptor into a partial target. Adoption
cleans failed staging copies. If a verified Capsule was atomically published
but the registry write failed, rerun the same adoption; it revalidates the
existing Capsule and repairs only the registry. Never download a new Package
to recover an existing Progress upload.

Stable exit classes are:

- `0`: created, adopted, already complete, or valid status;
- `2`: command usage;
- `10`: identity/schema/descriptor conflict;
- `20`: bootstrap descriptor unavailable;
- `30`: installation complete with cloud acknowledgement pending;
- `40`: Workspace busy or cloud revision/idempotency conflict;
- `50`: Package validation, identity, or checksum failure;
- `60`: filesystem conflict, unsafe path, or recoverable partial state;
- `70`: unexpected internal failure.

Errors print a safe stage and application code. They do not print credentials,
database URLs, tokens, or complete sensitive request URLs.

Sync additionally uses `.reagent/sync/current.json` as a checksummed recovery
journal and an OS advisory lock at `.reagent/runtime/sync.lock`. Staging is not
installed state. If a process stops after Capsule publication but before Lock
write, rerunning sync revalidates and adopts the exact published directory
without overwrite. Damaged Lock/receipt files and immutable drift fail closed.

## Not implemented

Writing, Review and Experiment Workflows, Skills/Resources products, Workspace
snapshots, automatic/background sync, cross-device recovery, in-place Capsule
upgrade/deletion and browser-local execution remain unimplemented. Retired
Capsules and their outputs are never automatically removed.
