# Local typed Artifact handoff

NIGHT-B6 adds a metadata-and-local-files boundary for reproducible handoff
between Workflow Instances. It does not add a new production Workflow.

## Boundary

The cloud stores typed Artifact identity, producer Progress provenance,
relative logical path, byte size and checksum. It does not store the Artifact
bytes and does not back up the Workspace. A cloud Artifact Reference can remain
historically valid even when the corresponding local bytes are unavailable;
local use always re-verifies the bytes.

The local Workspace uses three distinct state files:

- `.reagent/installed-lock.json` records verified Capsule installation only;
- `.reagent/artifact-index.json` records verified producer output bytes;
- `.reagent/receipts/materializations/<binding-id>.json` records one verified
  copy into a consumer input.

These files are not interchangeable. Artifact state never makes a Capsule
installed, and Capsule installation never proves that a research output exists.

## Cloud flow

An exact Capsule contract must declare a reviewed Artifact output before a
Progress upload may promote its metadata to a canonical Artifact Reference.
The declaration must match the Progress output path, media type, byte size and
SHA-256 checksum exactly. Existing Literature Search metadata is preserved but
is not guessed into a production Artifact type.

Consumer requirements are declared by Workflow Definition Version. A binding
selects one exact `artifact_id` and checksum for one consumer Workflow Instance
and input slot. There is no automatic “latest Artifact” policy and no
cross-Project binding.

The bounded APIs are:

- `GET /projects/{project_id}/artifacts`;
- `GET /projects/{project_id}/workflow-instances/{instance_id}/artifacts`;
- `POST /projects/{project_id}/workflow-instances/{instance_id}/artifact-dependencies`;
- `GET /projects/{project_id}/workflow-instances/{instance_id}/artifact-dependencies`;
- `GET /projects/{project_id}/workflow-instances/{instance_id}/artifact-materialization-plan`.

Artifact and dependency histories use deterministic ordering and bounded
offset/limit pagination. The materialization plan contains identities,
Workspace-relative source/target paths and checksums, never local absolute
paths or bytes.

## Local commands

Run commands from the generated Workspace CLI or the repository entry point:

```text
python reagent_local.py artifact status <workspace> [--json]
python reagent_local.py artifact refresh <workspace> [--api-url URL] [--json]
python reagent_local.py artifact materialize <workspace> \
  --workflow-instance <consumer-instance-id> [--dry-run] [--api-url URL] [--json]
```

`artifact refresh` obtains canonical cloud metadata, locates the exact
producer Capsule from Installed Lock, rejects unsafe paths and links, reads the
producer file, verifies size/checksum, then atomically writes the checksummed
Index.

`artifact materialize` is always explicit. It obtains a checksum-bound plan,
requires installed producer and consumer Capsules, re-reads the source through
a no-follow file descriptor, compares Cloud/Index/source identities, copies to
same-filesystem staging, flushes and fsyncs, verifies the copied checksum, and
publishes without overwrite. The producer is never moved, modified or deleted.

An existing exact target plus valid receipt is idempotent. Different target
bytes, source drift, corrupt Index/receipt, path escape, symlink, hardlink or
special file fail closed. A publish-before-receipt crash can be retried: the
client verifies the exact target and writes the missing receipt without
overwriting it. The B4 Workspace writer lock means sync, Index refresh and
materialization cannot mutate the same Workspace concurrently.

## Current limitations

There is no production Artifact type seed in NIGHT-B6 because the current
Literature Search Capsule does not contain a ratified typed output contract.
Idea Discovery and every test consumer remain non-production. There is no
Artifact byte upload/download, cross-Project sharing, automatic latest binding,
background watcher, automatic materialization during sync, top-level Artifact
UI, Workspace backup or recovery of lost producer bytes from cloud metadata.
