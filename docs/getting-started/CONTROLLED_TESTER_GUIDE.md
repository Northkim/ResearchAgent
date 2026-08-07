# Controlled Tester Guide

Your ReAgent test environment is private and assigned only to you. The host
operator gives you an authenticated URL or tunnel command. You do not need a
database login or ReAgent Provider key, and you should never receive either.

H2 uses deterministic literature fixtures. Treat their content as test data,
not real research evidence. Live Provider testing requires separate owner
authorization.

## Before starting

Install Python 3.11 or later and the supported Codex CLI on your computer.
Authenticate Codex with your normal local account. Choose a durable private
folder for your ReAgent Workspace; it contains the actual research files and
local memory.

Open your assigned ReAgent frontend. Health endpoints, database tools, and
server logs are operator concerns.

## Create the Project and Local Workspace

1. Create a Project in the browser.
2. On Overview or Help, download **Local Workspace tool** as
   `reagent_local.py` and **Workspace setup** as
   `workspace-bootstrap.json` into one ordinary download folder.
3. Run the copyable command shown in Help, for example:

   ```bash
   python3 reagent_local.py bootstrap ./reagent-workspace \
     --descriptor ./workspace-bootstrap.json
   cd ./reagent-workspace
   python3 reagent_local.py sync .
   python3 reagent_local.py workflow list .
   ```

The browser changes Cloud configuration. Only explicit local commands write
the Workspace. Do not edit `project.json`, `.reagent` locks/indexes, receipts,
or Progress JSON.

## Literature Search and Idea Discovery

Use the exact Literature Search command printed by `workflow list`. In the
controlled fixture exercise, interact normally and use `finish` only when the
selected set is ready. Successful finalization produces the selected paper
library and uploads Progress.

Then:

1. Add **Idea Discovery** on the Workflow Board.
2. Run `python3 reagent_local.py sync .` again. It adds the separate Idea
   Discovery Capsule and leaves Literature Search files unchanged.
3. In the browser, explicitly select one compatible Literature Search result.
   No result is selected automatically.
4. Copy the materialization command from the card, or use the safe selector
   when only one active Idea Discovery exists:

   ```bash
   python3 reagent_local.py artifact refresh .
   python3 reagent_local.py artifact materialize . \
     --workflow idea-discovery-local-experimental
   python3 reagent_local.py run . \
     --workflow idea-discovery-local-experimental
   ```

The input is a checksum-verified copy. ReAgent does not use a symlink and does
not let Idea Discovery write Literature Search outputs.

## Continue later

Keep the same Workspace. In a new terminal or Codex session:

```bash
cd ./reagent-workspace
python3 reagent_local.py workflow list .
```

Read the displayed next action. Capsule `AGENT.md`, local memory, outputs, and
Progress carry the context; chat history is not required.

## Recovery

- **Cloud cannot be reached / ACK pending:** leave the Workspace unchanged and
  retry the same `sync` command later.
- **Workflow not installed:** run `sync`, then `workflow list`.
- **Input not selected:** return to the Workflow Board and explicitly choose a
  result.
- **Input not materialized:** run the copyable materialization command.
- **Artifact drift:** stop. Restore the original Literature Search output or
  create/select a new result; do not edit checksum/index JSON.
- **Materialization conflict:** preserve the existing input and send the error
  code plus Request ID to the operator. ReAgent will not overwrite it.
- **Browser/API error:** send the operator only the error code, Request ID, and
  attempted action. Do not send research files without an approved channel.

Your Local Workspace is not backed up by ReAgent Cloud. Keep it on reliable
storage and follow the test program's approved local backup policy. Cloud
metadata and Progress cannot recreate lost Artifact bytes, outputs, or memory.

