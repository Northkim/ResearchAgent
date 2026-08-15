# E1 Real Experiment closure

- Date: 2026-08-15
- Baseline: `main` at `689812051f97cd633b7df776ac002c47c63a4549`
- Status: `PASS_E1_COMPLETE`
- Migration sole head: `20260815_0023`
- Product identity: Real Experiment Definition 0.4.0 / Capsule 0.7.0

## Closure defect and correction

The public Workspace path had already produced valid local
`experiment-record/v2` and terminal Progress, but upload-only session creation
returned HTTP 503. The exact cause was qualification app composition:
`enable_local_workflow_sessions=True` included the router while no
`proxy_container` was supplied. `backend.api.routers.local_sessions._proxy()`
therefore raised `ApplicationUnavailableError("Local Workflow session
capabilities are unavailable")` before the report-scoped session could open.

Classification: `QUALIFICATION_APP_CONFIGURATION_DEFECT`.

The qualifier now composes the existing production `CloudAPIProxyService` via
`ProxyApplicationContainer`, backed by the deterministic fake adapter and
in-memory Proxy unit of work used by controlled tests. This restores the normal
report-scoped zero-operation token path; it adds no bypass and changes no
production session, authorization, Progress, Artifact, or Experiment contract.
A focused regression creates a legitimate Project and proves an upload-only
session returns 201 with zero Provider calls.

## Verification

- New regression plus existing report-bound session contract: `2 passed`.
- Affected Real Experiment Workspace and local-session service suites:
  `9 passed`.
- Compile and `git diff --check`: pass.
- Public qualification command:
  `conda run --no-capture-output -n reagent-dev python -m backend.project_workspaces.tests.e1_q1_public_workspace_qualification`.
- Public qualification attempts after correction: `1`.
- Result markers: `PUBLIC_WORKSPACE_QUALIFICATION=PASS`,
  `PLAN_APPROVAL_ONE_ATTEMPT=PASS`, `LOCAL_EXECUTION=PASS`,
  `NO_EGRESS_ENFORCEMENT=PASS`, `EVALUATION_VALID=PASS`,
  `EXPERIMENT_RECORD_V2=PASS`, `PROGRESS_EXACTLY_ONCE=PASS`,
  `CLOUD_PROJECTION=PASS`, and `TEMPORARY_STATE_REMOVED=PASS`.

The clean run observed local-session creation 201, terminal Progress upload
201, session close 204, one accepted round, one promoted v2 Artifact, completed
Workflow/Project projection, and one checksummed local Cloud acknowledgement.

## Boundaries and next action

Capsule 0.6.0 and `experiment-record/v1` remain unchanged. No frontend,
migration, hosted runtime, Provider call, owner state, or secret was added or
used. Evidence is a controlled synthetic E5 public Workspace journey; it does
not prove arbitrary scientific correctness, hostile-code containment, Real
Codex completion, or long-lived Workspace compatibility.

`E1_STATUS = COMPLETE`. The next product phase is W1 Real Writing; do not begin
it automatically.
