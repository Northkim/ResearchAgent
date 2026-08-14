# FRONTEND_CONTROLLED_RUNTIME_B0 specification

Status: Owner-ratified isolation specification; runtime not started

## Objective

Provide a safe, repeatable browser qualification surface for frontend audits and
future contract tests without connecting to owner data or a long-lived Workspace.

## Isolation contract

B0 requires all of the following before a browser opens:

- disposable controlled/test PostgreSQL database with a guard marker that
  prevents use of an owner or production database;
- disposable local Workspace under a temporary directory;
- no owner Project, Workflow, Artifact payload, or credential;
- no dependency on, inspection of, or mutation to legacy Experiment 0.4;
- an explicit controlled/demo runtime marker visible to backend and frontend;
- deterministic fixture IDs, versions, timestamps, and checksums where possible;
- fixed, loopback-only backend and frontend ports selected by the qualification
  driver and recorded in the report;
- screenshots only under a temporary or repository-ignored audit directory;
- teardown that stops processes and removes disposable state;
- no dependency installation or browser download during a qualification run.

Required viewports are `1440x900`, `1280x800`, and `390x844`. Desktop-only
behavior still captures and reports the mobile failure state.

## Permitted browser surfaces

Use the first available approved surface:

1. an approved browser-control backend available in the execution environment;
2. repository-native Playwright using its declared Chromium configuration.

Repository-native Playwright is a valid controlled verification surface even
when an interactive browser skill is unavailable. A declared package is not
proof that a compatible browser binary is installed. Unknown external browser
services and owner runtime sessions are prohibited.

## Qualification state machine

Each state is recorded as `PASS`, `FAIL`, `BLOCKED`, or `NOT_CHECKED`, with
evidence and reason:

| State | PASS criterion |
|---|---|
| `PLAYWRIGHT_PACKAGE_PRESENT` | repository-declared package resolves without installation |
| `BROWSER_BINARY_PRESENT` | declared compatible browser executable launches locally |
| `CONTROLLED_BACKEND_REACHABLE` | marked controlled backend answers health/API checks on the selected loopback port |
| `CONTROLLED_FRONTEND_REACHABLE` | frontend serves the audited build/mode and targets only the controlled backend |
| `DATASET_VERIFIED_DISPOSABLE` | DB and Workspace markers, paths, and fixture IDs prove isolation before mutation |
| `SCREENSHOT_CAPTURE_PASS` | required routes/states/viewports produce named screenshots and browser assertions |
| `TEARDOWN_PASS` | processes stop and temporary DB/Workspace/screenshot policy is satisfied |

No overall B0 PASS is allowed unless every state passes. If the package exists
but the browser binary does not, B0 is blocked; it is not silently installed.

## Fixture requirements

The deterministic dataset must cover without real Workflow execution:

- active Project with a clear next action;
- exact bound and unbound Artifact inputs;
- owner approval required;
- blocked/failed state with reason and recovery affordance;
- completed Workflow and output metadata;
- local/Cloud disagreement and upload-pending state;
- invalid or incompatible historical state that cannot advertise Continue;
- loading, empty, API error, not-found, and narrow-viewport states.

Fixtures must use public API/persistence setup approved for controlled tests, not
direct browser writes to Workspace files. Seed/teardown operations are separate
from browser actions and visibly guarded.

## Start and teardown protocol

1. Allocate temp DB/Workspace/audit paths and loopback ports.
2. Verify destructive-test guard markers before creating fixture data.
3. Start controlled backend and verify runtime marker and DB identity.
4. Start frontend with an explicit controlled API base URL.
5. Verify the loaded fixture identity before browser actions.
6. Audit public routes and capture route/state/viewport-named evidence.
7. Stop frontend/backend even after test failure.
8. Verify no owner path, owner DB, or unexpected external endpoint was touched.
9. Remove disposable state or retain only explicitly allowed ignored screenshots.

Suggested screenshot naming:

```text
<route>__<viewport>__<state>__<full-or-fold>.png
```

## Security and stop conditions

Stop before browser actions if dataset disposability, backend identity, frontend
API target, loopback binding, or Workspace path is ambiguous. Stop during the
run if any browser action can write local Workspace bytes, any external network
request is unexpected, fixtures contain owner data, or teardown cannot be
guaranteed. Logs and screenshots must not expose secrets or research payloads.

## Required output packet

Record versions, commands, ports, runtime markers, fixture manifest checksum,
all seven qualification states, route/viewports covered, screenshots, console
and network failures, accessibility results, cleanup proof, skipped states, and
the highest evidence level (`E6` only when the real controlled API was used).
