import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, test, vi } from "vitest";

import { ApiError, apiClient } from "@/api/client";
import { WorkflowBoard } from "@/components/workflow-board";
import { WorkflowDetail } from "@/components/workflow-detail";
import { ProjectOutputs } from "@/components/project-outputs";
import { Providers } from "@/lib/providers";

import {
  localProjectFixture,
  projectProgressFixture,
  workflowCatalogFixture,
  workflowInstanceId,
  workflowInstancesFixture,
} from "./fixtures";

afterEach(() => vi.restoreAllMocks());

function arrange() {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  vi.spyOn(apiClient, "listWorkflowDefinitions").mockResolvedValue(workflowCatalogFixture);
  vi.spyOn(apiClient, "getWorkflowDefinition").mockResolvedValue({
    ...workflowCatalogFixture.items[0],
    versions: [workflowCatalogFixture.items[0].recommended_version!],
    capsules: [workflowCatalogFixture.items[0].recommended_capsule!],
  });
  vi.spyOn(apiClient, "listProjectWorkflowInstances").mockResolvedValue(workflowInstancesFixture);
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue(projectProgressFixture);
  vi.spyOn(apiClient, "listProjectArtifactReferences").mockResolvedValue({
    schema_version: "reagent.artifact-reference-page/v0.1",
    project_id: localProjectFixture.project_id,
    artifacts: [], offset: 0, limit: 100, total: 0, has_more: false,
  });
}

const genericExperimentId = `wfi-${"6".repeat(32)}`;

function arrangeGenericExperiment(options: {
  summary?: string;
  artifact?: Record<string, unknown>;
  completed?: boolean;
  reportCount?: number;
  approval?: Record<string, unknown> | null;
} = {}) {
  arrange();
  const instance = {
    ...workflowInstancesFixture.items[0],
    workflow_instance_id: genericExperimentId,
    workflow_definition_id: "reproduction-experiment-local-experimental",
    workflow_version: "0.6.0",
    capsule_id: `capsule-${"9".repeat(32)}`,
    capsule_version: "0.9.0",
    display_name: "Reproduction & Experiment",
  };
  vi.spyOn(apiClient, "listProjectWorkflowInstances").mockResolvedValue({
    ...workflowInstancesFixture,
    total: 2,
    items: [instance, workflowInstancesFixture.items[0]],
  });
  const genericVersion = {
    ...workflowCatalogFixture.items[0].recommended_version!,
    version: "0.6.0",
    input_schema_id: "selected-research-idea/v1",
    output_schema_id: "experiment-record/v4",
    artifact_requirements: [{
      workflow_definition_id: "reproduction-experiment-local-experimental",
      workflow_version: "0.6.0",
      requirement_key: "selected-research-idea",
      artifact_type: "selected-research-idea/v1",
      compatibility_mode: "EXACT",
      schema_constraint: "selected-research-idea/v1",
      cardinality_min: 1,
      cardinality_max: 1,
      required: true,
      materialization_mode: "VERIFIED_COPY",
      target_relative_path: "inputs/selected-research-idea.json",
    }],
    resource_requirements: [],
  };
  vi.spyOn(apiClient, "getWorkflowDefinition").mockResolvedValue({
    ...workflowCatalogFixture.items[0],
    workflow_definition_id: "reproduction-experiment-local-experimental",
    stable_workflow_key: "REPRODUCTION_EXPERIMENT",
    display_name: "Reproduction & Experiment",
    recommended_version: genericVersion,
    versions: [genericVersion],
    capsules: [],
  } as never);
  const action = {
    ...projectProgressFixture.instances[0].action,
    stage: { code: options.completed ? "COMPLETED" : "OWNER_APPROVAL", label: options.completed ? "Evaluation complete" : "Methodology review" },
    next_action: {
      surface: options.completed ? "BROWSER" : "LOCAL",
      code: options.completed ? "REVIEW_RESULT" : "CONTINUE",
      label: options.completed ? "Review result" : "Review methodology",
      description: options.completed ? "Review the scientific result." : "Resolve the scientific design choice.",
    },
  };
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue({
    ...projectProgressFixture,
    active_workflow_count: 2,
    instances: [{
      ...projectProgressFixture.instances[0],
      workflow_instance_id: genericExperimentId,
      workflow_definition_id: "reproduction-experiment-local-experimental",
      workflow_definition_version: "0.6.0",
      workflow_display_name: "Reproduction & Experiment",
      instance_display_name: "Reproduction & Experiment",
      capsule_id: `capsule-${"9".repeat(32)}`,
      capsule_version: "0.9.0",
      latest_summary: options.summary ?? "METHODOLOGY_DECISION_REQUIRED: choose whether the comparison uses matched or independent observations.",
      report_count: options.reportCount ?? (options.completed ? 1 : 0),
      action,
    }, projectProgressFixture.instances[0]],
    dependency_edges: [{
      binding_id: "binding-selected-idea",
      consumer_workflow_instance_id: genericExperimentId,
      requirement_key: "selected-research-idea",
      artifact_id: `artifact-${"b".repeat(32)}`,
      expected_checksum: `sha256:${"b".repeat(64)}`,
      state: "ACTIVE",
      producer_workflow_instance_id: workflowInstanceId,
      artifact_type: "selected-research-idea/v1",
      artifact_schema_version: "selected-research-idea/v1",
      produced_at: "2026-08-17T01:00:00Z",
    }],
  } as never);
  vi.spyOn(apiClient, "listProjectArtifactReferences").mockResolvedValue({
    schema_version: "reagent.artifact-reference-page/v0.1",
    project_id: localProjectFixture.project_id,
    artifacts: options.artifact ? [options.artifact] : [],
    offset: 0,
    limit: 100,
    total: options.artifact ? 1 : 0,
    has_more: false,
  } as never);
  vi.spyOn(apiClient, "observeControlledLocalRunApproval").mockResolvedValue({
    request: options.approval ?? null,
    next_action: options.approval ? "OWNER_APPROVAL_REQUIRED" : "REPORT_EXACT_RUN_APPROVAL_REQUEST",
  } as never);
}

function controlledLocalApproval(status = "REQUESTED") {
  return {
    schema: "reagent.controlled-local-run-approval/v0.1",
    request_id: `clra-${"1".repeat(32)}`,
    project_id: localProjectFixture.project_id,
    workflow_instance_id: genericExperimentId,
    research_objective_checksum: `sha256:${"1".repeat(64)}`,
    execution_plan_checksum: `sha256:${"2".repeat(64)}`,
    validated_package_checksum: `sha256:${"3".repeat(64)}`,
    runtime_compatibility_checksum: `sha256:${"4".repeat(64)}`,
    capability_checksum: `sha256:${"5".repeat(64)}`,
    summary: {
      schema: "reagent.controlled-local-run-approval-summary/v0.1",
      what_will_run: "A bounded categorical observation protocol.",
      research_objective: "Determine whether category order is preserved.",
      preparation_method: "Reviewed categorical observation preparation",
      research_resources: ["Verified observation schedule"],
      execution_environment: "Compatible local observation runtime",
      network_policy: "DISABLED",
      compute_limits: ["Five minutes", "One process"],
      expected_outputs: ["Categorical observation record"],
      evaluation_approach: "Compare the observed category order with the declared protocol.",
      important_assumptions: ["The schedule is complete"],
      important_limitations: ["This fixture supports a narrow categorical claim"],
      summary_checksum: `sha256:${"6".repeat(64)}`,
    },
    created_at: "2026-08-17T02:00:00Z",
    request_checksum: `sha256:${"7".repeat(64)}`,
    status,
    owner_actor: status === "REQUESTED" ? null : "owner",
    decision_reason: null,
    decision_idempotency_key: status === "REQUESTED" ? null : `owner-approve-clra-${"1".repeat(32)}`,
    decided_at: status === "REQUESTED" ? null : "2026-08-17T02:01:00Z",
    approval_checksum: status === "REQUESTED" ? null : `sha256:${"8".repeat(64)}`,
    consumed_attempt_id: status === "CONSUMED" ? `attempt-${"9".repeat(32)}` : null,
    consumed_at: status === "CONSUMED" ? "2026-08-17T02:02:00Z" : null,
    consumption_checksum: status === "CONSUMED" ? `sha256:${"a".repeat(64)}` : null,
  };
}

function experimentArtifact(blocks: Array<Record<string, unknown>>) {
  const checksum = `sha256:${"4".repeat(64)}`;
  const presentationChecksum = `sha256:${"5".repeat(64)}`;
  return {
    schema_version: "reagent.artifact-reference/v0.1",
    artifact_id: `artifact-${"4".repeat(32)}`,
    project_id: localProjectFixture.project_id,
    producer_workflow_instance_id: genericExperimentId,
    producer_progress_receipt_id: "receipt-generic-v4",
    producer_progress_report_id: "report-generic-v4",
    producer_execution_round: 1,
    producer_capsule_id: `capsule-${"9".repeat(32)}`,
    producer_capsule_version: "0.9.0",
    producer_core_capability_maturity: "REVIEWED_CORE",
    artifact_type: "experiment-record/v4",
    artifact_schema_version: "experiment-record/v4",
    media_type: "application/json",
    state: "LOCAL_AVAILABLE",
    relative_path: "outputs/experiment-record-v4.json",
    content_checksum: checksum,
    size_bytes: 4096,
    cloud_metadata_available: true,
    produced_at: "2026-08-17T01:30:00Z",
    retired_at: null,
    created_at: "2026-08-17T01:30:00Z",
    updated_at: "2026-08-17T01:30:00Z",
    presentation: {
      schema_identity: "reagent.artifact-presentation.experiment-record/v0.2",
      artifact_id: `artifact-${"4".repeat(32)}`,
      artifact_checksum: checksum,
      presentation_checksum: presentationChecksum,
      payload: {
        schema: "reagent.artifact-presentation.experiment-record/v0.2",
        artifact_id: `artifact-${"4".repeat(32)}`,
        artifact_checksum: checksum,
        blocks,
        presentation_checksum: presentationChecksum,
      },
      reported_at: "2026-08-17T01:31:00Z",
    },
  };
}

test("renders projection-driven Workflow rows and keeps planned definitions disabled", async () => {
  arrange();
  render(<Providers><WorkflowBoard projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Workflow progression" })).toBeVisible();
  expect(screen.getByText("Review Output")).toBeVisible();
  expect(screen.getByText("Literature selected")).toBeVisible();
  expect(screen.getByText("Owner acts")).toBeVisible();
  expect(screen.getByText("Selected paper library")).toBeVisible();
  expect(screen.getByRole("link", { name: "Open Workflow" })).toHaveAttribute("href", expect.stringContaining(workflowInstanceId));
  expect(screen.getByRole("button", { name: "Planned" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Add workflow" })).toBeEnabled();
  expect(screen.getByRole("link", { name: "Workflows" })).toHaveAttribute("aria-current", "page");
});

test("renders production scaffold maturity and warning without a Full Flow preset", async () => {
  arrange();
  vi.spyOn(apiClient, "listWorkflowDefinitions").mockResolvedValue({
    total: 5,
    items: [...workflowCatalogFixture.items, ...[
      ["writing-local-experimental", "Writing"],
      ["review-local-experimental", "Review"],
      ["reproduction-experiment-local-experimental", "Reproduction & Experiment"],
    ].map(([workflow_definition_id, display_name], index) => ({
      ...workflowCatalogFixture.items[0],
      workflow_definition_id,
      stable_workflow_key: workflow_definition_id,
      display_name,
      description: `${display_name} production scaffold flow.`,
      recommended_version: {
        ...workflowCatalogFixture.items[0].recommended_version!,
        version: "0.2.0",
        core_capability_maturity: "SCAFFOLD_CORE" as const,
        skills: [{
          skill_id: "scaffold-core-safety-local-builtin",
          display_name: "Scaffold Core Safety",
          version: "0.1.0",
          checksum: `sha256:${"7".repeat(64)}`,
          trust: "BUILT_IN_REVIEWED" as const,
          purpose: "Prevent fabricated research claims.",
        }],
      },
      recommended_capsule: {
        ...workflowCatalogFixture.items[0].recommended_capsule!,
        capsule_id: `capsule-${String(index + 5).repeat(32)}`,
        capsule_version: "0.2.0",
        workflow_version: "0.2.0",
      },
    }))],
  });
  render(<Providers><WorkflowBoard projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Writing" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Review" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Reproduction & Experiment" })).toBeVisible();
  expect(screen.getAllByText("Core · Scaffold")).toHaveLength(3);
  expect(screen.getAllByText(/Product flow is functional/)).toHaveLength(3);
  expect(screen.getAllByText(/Scaffold Core Safety 0.1.0/)).toHaveLength(3);
  expect(screen.getAllByText(/Built-in reviewed skills are bundled|exact versions arrive/i)).toHaveLength(3);
  expect(screen.queryByText(/Full Research Project/i)).not.toBeInTheDocument();
});

test("distinguishes two Instances of the same Workflow Definition", async () => {
  arrange();
  const secondId = `wfi-${"9".repeat(32)}`;
  vi.spyOn(apiClient, "listProjectWorkflowInstances").mockResolvedValue({
    ...workflowInstancesFixture,
    total: 2,
    items: [
      ...workflowInstancesFixture.items,
      { ...workflowInstancesFixture.items[0], workflow_instance_id: secondId, display_name: "Literature Search B" },
    ],
  });
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue({
    ...projectProgressFixture,
    active_workflow_count: 2,
    instances: [
      ...projectProgressFixture.instances,
      {
        ...projectProgressFixture.instances[0],
        workflow_instance_id: secondId,
        instance_display_name: "Literature Search B",
        research_status: "IN_PROGRESS",
      },
    ],
  });
  render(<Providers><WorkflowBoard projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByText("Literature Search B")).toBeVisible();
  expect(screen.getAllByText("Manage")).toHaveLength(2);
});

test("refreshes on Manifest revision conflict and never attempts a browser-local write", async () => {
  arrange();
  const catalog = {
    ...workflowCatalogFixture,
    total: 3,
    items: [...workflowCatalogFixture.items, {
      ...workflowCatalogFixture.items[0],
      workflow_definition_id: "fixture-second-available",
      stable_workflow_key: "FIXTURE_SECOND_AVAILABLE",
      display_name: "Fixture Available Workflow",
      recommended_capsule: {
        ...workflowCatalogFixture.items[0].recommended_capsule!,
        capsule_id: `capsule-${"8".repeat(32)}`,
      },
    }],
  };
  vi.spyOn(apiClient, "listWorkflowDefinitions").mockResolvedValue(catalog);
  const create = vi.spyOn(apiClient, "createProjectWorkflowInstance").mockRejectedValue(
    new ApiError("revision conflict", 409, "MANIFEST_REVISION_CONFLICT"),
  );
  const localWrite = vi.spyOn(window, "open");
  render(<Providers><WorkflowBoard projectId={localProjectFixture.project_id} /></Providers>);

  const availableCard = (await screen.findByRole("heading", { name: "Fixture Available Workflow" })).closest("article");
  await userEvent.click(within(availableCard!).getByRole("button", { name: "Add workflow" }));
  expect(await screen.findByText(/Project changed elsewhere/)).toBeVisible();
  expect(create).toHaveBeenCalledWith(
    localProjectFixture.project_id,
    expect.objectContaining({ base_revision: 1 }),
  );
  expect(localWrite).not.toHaveBeenCalled();
});

test("retire confirms history retention and uses the current base revision", async () => {
  arrange();
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const retire = vi.spyOn(apiClient, "retireProjectWorkflowInstance").mockResolvedValue({
    ...workflowInstancesFixture.items[0],
    desired_state: "RETIRED",
    in_current_manifest: false,
    retired_manifest_revision: 2,
  });
  render(<Providers><WorkflowBoard projectId={localProjectFixture.project_id} /></Providers>);

  await userEvent.click(await screen.findByRole("button", { name: "Retire" }));
  expect(retire).toHaveBeenCalledWith(
    localProjectFixture.project_id,
    workflowInstanceId,
    1,
  );
  expect(await screen.findByText(/Local research files were not deleted/)).toBeVisible();
});

test("focused Workflow Detail presents one specific action with secondary technical state", async () => {
  arrange();
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={workflowInstanceId} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Review the selected papers" })).toBeVisible();
  expect(screen.queryByText("Owner acts now")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View selected papers" })).toHaveAttribute("href", expect.stringContaining("/outputs"));
  expect(screen.getByText("Selected paper library")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Inputs" })).toBeVisible();
  expect(screen.getByText("No upstream research input is required.")).toBeVisible();
  expect(screen.getByText("Technical Details").closest("details")).not.toHaveAttribute("open");
  expect(screen.queryByText("python reagent_local.py run .", { exact: false })).not.toBeInTheDocument();
});

test("Outputs presents exact Artifact identity as secondary provenance", async () => {
  arrange();
  vi.spyOn(apiClient, "listProjectArtifactReferences").mockResolvedValue({
    schema_version: "reagent.artifact-reference-page/v0.1",
    project_id: localProjectFixture.project_id,
    artifacts: [{
      schema_version: "reagent.artifact-reference/v0.1",
      artifact_id: `artifact-${"a".repeat(32)}`,
      project_id: localProjectFixture.project_id,
      producer_workflow_instance_id: workflowInstanceId,
      producer_progress_receipt_id: "progress-receipt-fictional",
      producer_progress_report_id: `prv2-${"e".repeat(64)}`,
      producer_execution_round: 1,
      producer_capsule_id: `capsule-${"2".repeat(32)}`,
      producer_capsule_version: "0.5.0",
      producer_core_capability_maturity: "REVIEWED_CORE",
      artifact_type: "paper_library",
      artifact_schema_version: "selected-paper-library/v1",
      media_type: "application/json",
      state: "LOCAL_AVAILABLE",
      relative_path: "outputs/selected-paper-library.json",
      content_checksum: `sha256:${"1".repeat(64)}`,
      size_bytes: 128,
      cloud_metadata_available: true,
      produced_at: "2026-08-05T08:05:01Z",
      retired_at: null,
      created_at: "2026-08-05T08:05:01Z",
      updated_at: "2026-08-05T08:05:01Z",
    }],
    offset: 0,
    limit: 100,
    total: 1,
    has_more: false,
  });
  render(<Providers><ProjectOutputs projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Selected paper library" })).toBeVisible();
  expect(screen.getByText("COMPLETED")).toBeVisible();
  expect(screen.getByText(`artifact-${"a".repeat(32)}`)).toBeInTheDocument();
  expect(screen.getByText("Technical Details").closest("details")).not.toHaveAttribute("open");
  expect(screen.getByRole("link", { name: "Outputs" })).toHaveAttribute("aria-current", "page");
});

test("generic Experiment starts from the objective and a truthful two-path decision", async () => {
  arrangeGenericExperiment();
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={genericExperimentId} /></Providers>);

  expect(await screen.findByRole("heading", { name: localProjectFixture.progress!.current_state_summary })).toBeVisible();
  expect(screen.getByRole("heading", { name: "How would you like to start?" })).toBeVisible();
  expect(screen.getByText("Selected research idea · exact version recorded", { exact: false })).toBeVisible();
  expect(screen.getByRole("button", { name: "Not available in this build" })).toBeDisabled();
  expect(screen.getByText(/Git is optional\./)).toBeVisible();
  expect(screen.queryByRole("heading", { name: "What ReAgent understands" })).not.toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "Choose this path" }));
  expect(screen.queryByRole("heading", { name: "How would you like to start?" })).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Prepared with ReAgent" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Use an existing local project" })).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "What ReAgent understands" })).toBeVisible();
  const task = screen.getByRole("heading", { name: "ReAgent needs your decision" });
  const design = screen.getByRole("heading", { name: "What ReAgent understands" });
  expect(task).toBeVisible();
  expect(task.compareDocumentPosition(design) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getAllByText(/scientific choice must be resolved/).length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText("Experiment design details have not yet been reported from the Local Workspace.")).toBeVisible();
  expect(screen.queryByText("Recorded when the methodology checkpoint is reported.")).not.toBeInTheDocument();
  expect(screen.queryByText("Pending")).not.toBeInTheDocument();
  expect(screen.getByText("One recommended command")).toBeVisible();
  expect(screen.getByText("Technical details").closest("details")).not.toHaveAttribute("open");
  expect(screen.queryByText(/ResourceReference|provider locator|package tree hash/i)).not.toBeInTheDocument();
  expect(screen.getByText("METHODOLOGY_DECISION_REQUIRED")).not.toBeVisible();
});

test.each([
  {
    checkpoint: "RESOURCE_READINESS_REQUIRED: the required observation schedule is not verified locally.",
    section: "Research resources",
    status: "Needs attention",
    detail: "the required observation schedule is not verified locally.",
  },
  {
    checkpoint: "PREPARATION_REQUIREMENT_UNMET: a reviewed local observation tool is missing.",
    section: "What ReAgent needs to prepare",
    status: "Needs attention",
    detail: "a reviewed local observation tool is missing.",
  },
  {
    checkpoint: "PREPARATION_COMPLETE: the experiment implementation is prepared.",
    section: "Implementation preparation",
    status: "Implementation prepared",
    detail: "the experiment implementation is prepared.",
  },
  {
    checkpoint: "RUNTIME_INCOMPATIBLE: no compatible categorical observation runtime is available.",
    section: "Execution environment",
    status: "Needs attention",
    detail: "no compatible categorical observation runtime is available.",
  },
])("projects $checkpoint into its truthful pre-Artifact Owner section", async ({ checkpoint, section, status, detail }) => {
  arrangeGenericExperiment({ summary: checkpoint, reportCount: 1 });
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={genericExperimentId} /></Providers>);

  const row = (await screen.findByText(section)).closest("div")?.parentElement;
  const currentTask = screen.getByText(checkpoint.split(":")[0] === "RESOURCE_READINESS_REQUIRED"
    ? "A research resource is needed"
    : checkpoint.split(":")[0] === "PREPARATION_REQUIREMENT_UNMET"
      ? "A preparation prerequisite is missing"
      : checkpoint.split(":")[0] === "PREPARATION_COMPLETE"
        ? "Experiment implementation prepared"
        : "No compatible execution environment is ready");
  expect(row).toHaveTextContent(status);
  expect(row).toHaveTextContent(detail);
  expect(currentTask.compareDocumentPosition(row as Node) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getByText(checkpoint.split(":")[0])).not.toBeVisible();
  if (checkpoint.startsWith("PREPARATION_COMPLETE")) {
    expect(row).not.toHaveTextContent("In progress");
    expect(screen.getAllByRole("link", { name: "Continue in Local Workspace" })[0]).toBeVisible();
  }
  if (checkpoint.startsWith("RUNTIME_INCOMPATIBLE")) {
    expect(row).not.toHaveTextContent("Checked after the experiment is prepared");
  }
});

test("Run Approval uses the controlled-local request and updates the Local handoff without browser execution", async () => {
  const requested = controlledLocalApproval();
  arrangeGenericExperiment({
    summary: "RUN_APPROVAL_REQUIRED: review the exact categorical observation run.",
    reportCount: 1,
    approval: requested,
  });
  const approved = { ...requested, status: "APPROVED", owner_actor: "owner", decided_at: "2026-08-17T02:01:00Z" };
  const decide = vi.spyOn(apiClient, "decideControlledLocalRunApproval").mockResolvedValue(approved as never);
  const hostedResume = vi.spyOn(apiClient, "resumeRun");
  const user = userEvent.setup();
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={genericExperimentId} /></Providers>);

  const exactRunHeading = await screen.findByRole("heading", { name: "Exact run summary" });
  const topTask = screen.getByRole("heading", { name: "Experiment ready for approval" }).closest("section") as HTMLElement;
  const reviewRun = within(topTask).getByRole("link", { name: "Review exact run" });
  expect(within(topTask).queryByRole("button", { name: "Approve this run" })).not.toBeInTheDocument();
  await user.click(reviewRun);
  await waitFor(() => expect(exactRunHeading).toHaveFocus());
  expect(decide).not.toHaveBeenCalled();
  expect(await screen.findByText("A bounded categorical observation protocol.")).toBeVisible();
  expect(screen.getByText("This fixture supports a narrow categorical claim")).toBeVisible();
  const approve = screen.getByRole("button", { name: "Approve this run" });
  const requestChanges = screen.getByRole("button", { name: "Request changes" });
  expect(exactRunHeading.compareDocumentPosition(approve) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(exactRunHeading.compareDocumentPosition(requestChanges) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  approve.focus();
  await user.keyboard("{Enter}");

  expect(decide).toHaveBeenCalledWith(
    localProjectFixture.project_id,
    genericExperimentId,
    requested.request_id,
    "approve",
    expect.objectContaining({
      execution_plan_checksum: requested.execution_plan_checksum,
      request_checksum: requested.request_checksum,
      idempotency_key: `owner-approve-${requested.request_id}`,
    }),
  );
  expect(await screen.findByText("Run approved")).toBeVisible();
  expect(screen.getByRole("link", { name: "Continue in Local Workspace" })).toBeVisible();
  expect(screen.getByText(/verify that the experiment has not changed, consume this one-use approval/i)).toBeVisible();
  expect(hostedResume).not.toHaveBeenCalled();
  const technical = screen.getByText("Technical details").closest("details");
  expect(technical).toHaveTextContent(requested.execution_plan_checksum);
  expect(screen.getByText(requested.execution_plan_checksum)).not.toBeVisible();
});

test("Run Approval offers bounded rejection and translates changed-plan failures", async () => {
  const requested = controlledLocalApproval();
  arrangeGenericExperiment({
    summary: "RUN_APPROVAL_REQUIRED: review the updated run.",
    reportCount: 1,
    approval: requested,
  });
  vi.spyOn(apiClient, "decideControlledLocalRunApproval").mockRejectedValue(
    new ApiError("Run Approval was superseded", 409, "APPROVAL_SUPERSEDED"),
  );
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={genericExperimentId} /></Providers>);

  await userEvent.click(await screen.findByRole("button", { name: "Approve this run" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("The prepared experiment changed after approval.");
  expect(screen.getByRole("heading", { name: "The prepared experiment changed after approval" })).toBeVisible();
  expect(screen.getByText("Review the updated run before continuing.")).toBeVisible();
  const decide = vi.mocked(apiClient.decideControlledLocalRunApproval);
  decide.mockClear();
  const reviewUpdated = screen.getByRole("link", { name: "Review updated run" });
  await userEvent.click(reviewUpdated);
  await waitFor(() => expect(screen.getByRole("heading", { name: "Exact run summary" })).toHaveFocus());
  expect(decide).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Approve this run" })).toBeEnabled();
  expect(screen.queryByText(/checksum mismatch/i)).not.toBeInTheDocument();
});

test("Run Approval replay uses one stable decision identity and approved state is translated", async () => {
  const approved = controlledLocalApproval("APPROVED");
  arrangeGenericExperiment({
    summary: "RUN_APPROVAL_REQUIRED: exact run authorization is already recorded.",
    reportCount: 1,
    approval: approved,
  });
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={genericExperimentId} /></Providers>);

  expect(await screen.findByText("Run approved")).toBeVisible();
  expect(screen.getByText("The exact run is approved and ready to continue locally.")).toBeVisible();
  expect(screen.queryByText("APPROVED")).not.toBeVisible();
  expect(screen.queryByRole("button", { name: "Approve this run" })).not.toBeInTheDocument();
});

test("Run Approval request-changes action uses the same bounded authority", async () => {
  const requested = controlledLocalApproval();
  arrangeGenericExperiment({
    summary: "RUN_APPROVAL_REQUIRED: review the exact run.",
    reportCount: 1,
    approval: requested,
  });
  const rejected = { ...requested, status: "REJECTED", owner_actor: "owner", decision_reason: "Owner requested changes before local execution." };
  const decide = vi.spyOn(apiClient, "decideControlledLocalRunApproval").mockResolvedValue(rejected as never);
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={genericExperimentId} /></Providers>);

  await userEvent.click(await screen.findByRole("button", { name: "Request changes" }));
  expect(decide).toHaveBeenCalledWith(
    localProjectFixture.project_id,
    genericExperimentId,
    requested.request_id,
    "reject",
    expect.objectContaining({ reason: "Owner requested changes before local execution." }),
  );
  expect(await screen.findByText("Changes requested")).toBeVisible();
  expect(screen.getByText(/Continue locally after the experiment has been revised/)).toBeVisible();
});

test("unreported local provenance remains truthful and secondary", async () => {
  arrangeGenericExperiment({ summary: "DESIGN_APPROVAL_REQUIRED: review the scientific design.", reportCount: 1 });
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={genericExperimentId} /></Providers>);

  const technical = await screen.findByText("Technical details");
  expect(technical.closest("details")).not.toHaveAttribute("open");
  expect(within(technical.closest("details") as HTMLElement).getAllByText("Not yet reported from Local Workspace").length).toBeGreaterThanOrEqual(4);
  for (const item of screen.queryAllByText(/sha256:[0-9a-f]{64}/i)) expect(item).not.toBeVisible();
});

test("generic Experiment renders categorical non-ML evidence and separates scientific status", async () => {
  const artifact = experimentArtifact([
    { kind: "PROSE", label: "Research objective", value: "Determine whether a bounded state machine preserves category order." },
    { kind: "SCALAR", label: "Process outcome", value: "COMPLETED" },
    { kind: "SCALAR", label: "Evaluation validity", value: "VALID" },
    { kind: "SCALAR", label: "Scientific evidence status", value: "INSUFFICIENT" },
    { kind: "SCALAR", label: "Resource readiness", value: "Changed since verification" },
    { kind: "SCALAR", label: "Preparation requirement", value: "Compatible observation tool available" },
    { kind: "SCALAR", label: "Preparation status", value: "Package validated" },
    { kind: "SCALAR", label: "Execution environment", value: "Environment changed since validation" },
    { kind: "PROSE", label: "Key findings", value: "The final category was stable, but the observation set was too small for a broad claim." },
    { kind: "TABLE", label: "Observed categories", value: { columns: ["Step", "Category"], rows: [["Start", "amber"], ["Finish", "green"]] } },
    { kind: "SERIES", label: "Categorical sequence", value: [{ x: "Start", y: "amber" }, { x: "Finish", y: "green" }] },
    { kind: "PROSE", label: "Limitations", value: "This bounded fixture supports only a narrow categorical claim." },
  ]);
  arrangeGenericExperiment({ artifact, completed: true, summary: "RESULT_REVIEW_REQUIRED: Owner review of the bounded evaluated result is required." });
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={genericExperimentId} /></Providers>);

  expect(await screen.findByText("The final category was stable, but the observation set was too small for a broad claim.")).toBeVisible();
  expect(screen.getAllByText("COMPLETED")).toHaveLength(1);
  expect(screen.getAllByText("VALID")).toHaveLength(1);
  expect(screen.getAllByText("INSUFFICIENT")).toHaveLength(1);
  expect(screen.getAllByRole("table").length).toBeGreaterThanOrEqual(2);
  expect(screen.getByText("View chart data")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Experiment result ready for review" })).toBeVisible();
  expect(screen.getByText(/Does this result record accurately represent the experiment and its limitations/)).toBeVisible();
  const result = screen.getByRole("heading", { name: /^Experiment result$/ });
  const reviewBelow = screen.getByRole("link", { name: "Review result below" });
  await userEvent.click(reviewBelow);
  await waitFor(() => expect(result).toHaveFocus());
  const history = screen.getByText("Experiment history");
  expect(result.compareDocumentPosition(history) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(history.closest("details")).not.toHaveAttribute("open");
  const limitation = screen.getByText("This bounded fixture supports only a narrow categorical claim.");
  const finalReview = screen.getByRole("link", { name: "Continue result review locally" });
  expect(limitation.compareDocumentPosition(finalReview) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(screen.getByRole("heading", { name: "Record the result review locally" })).toBeVisible();
  expect(screen.getByText("One recommended command")).toBeVisible();
  expect(screen.getAllByText("Changed since verification").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("Environment changed since validation").length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText("Compatible observation tool available").length).toBeGreaterThanOrEqual(1);
  expect(screen.queryByText(/Metrics|Cross-validation|Robustness|Seeds/)).not.toBeInTheDocument();
});

test("generic Experiment renders only reported methodology fields inside completed history", async () => {
  const artifact = experimentArtifact([
    { kind: "PROSE", label: "Research objective", value: "Observe a bounded categorical transition." },
    { kind: "PROSE", label: "Protocol", value: "Observe exactly two declared transitions." },
    { kind: "PROSE", label: "Assumptions", value: "The category labels are stable." },
    { kind: "SCALAR", label: "Process outcome", value: "COMPLETED" },
  ]);
  arrangeGenericExperiment({ artifact, completed: true, summary: "Finalized controlled result." });
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={genericExperimentId} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Experiment completed" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Continue safely on this computer" })).not.toBeInTheDocument();
  expect(screen.queryByText("One recommended command")).not.toBeInTheDocument();
  const history = await screen.findByText("Experiment history");
  await userEvent.click(history);
  expect(screen.getAllByText("Protocol", { exact: true }).some((item) => item.tagName === "STRONG")).toBe(true);
  expect(screen.getAllByText("Assumptions", { exact: true }).some((item) => item.tagName === "STRONG")).toBe(true);
  expect(screen.queryByText("Questions or hypotheses")).not.toBeInTheDocument();
  expect(screen.queryByText("Recorded when the methodology checkpoint is reported.")).not.toBeInTheDocument();
  expect(screen.queryByText("Pending")).not.toBeInTheDocument();
});

test("generic Experiment translates unsupported automatic preparation without plumbing", async () => {
  arrangeGenericExperiment({
    summary: "AUTOMATIC_PREPARATION_UNSUPPORTED: no reviewed preparation method supports the exact methodology.",
  });
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={genericExperimentId} /></Providers>);
  await userEvent.click(await screen.findByRole("button", { name: "Choose this path" }));

  expect(screen.getByRole("heading", { name: "ReAgent cannot prepare this experiment automatically yet." })).toBeVisible();
  expect(screen.getByText(/research design is preserved/i)).toBeVisible();
  expect(screen.queryByText(/write.*Python|provide.*manifest|enter.*checksum/i)).not.toBeInTheDocument();
});

test("Outputs uses the same bounded renderer for sklearn-shaped scalar and comparison evidence", async () => {
  const artifact = experimentArtifact([
    { kind: "PROSE", label: "Research objective", value: "Compare reviewed classification configurations on a controlled reference fixture." },
    { kind: "SCALAR", label: "Evaluation validity", value: "VALID" },
    { kind: "SCALAR", label: "Scientific evidence status", value: "SUFFICIENT" },
    { kind: "SCALAR", label: "Held-out score", value: 0.91 },
    { kind: "TABLE", label: "Configuration comparison", value: { columns: ["Configuration", "Score"], rows: [["A", 0.87], ["B", 0.91]] } },
    { kind: "SERIES", label: "Comparison series", value: [{ x: "A", y: 0.87 }, { x: "B", y: 0.91 }] },
    { kind: "PROSE", label: "Key findings", value: "Configuration B was stronger in the controlled reference fixture." },
    { kind: "PROSE", label: "Limitations", value: "No scientific dependency was executed for this presentation qualification." },
  ]);
  arrangeGenericExperiment({ artifact, completed: true });
  render(<Providers><ProjectOutputs projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Experiment result" })).toBeVisible();
  expect(screen.getAllByText("0.91").length).toBeGreaterThanOrEqual(2);
  expect(screen.getByText("Configuration B was stronger in the controlled reference fixture.")).toBeVisible();
  expect(screen.getByRole("img", { name: "Comparison series series chart" })).toBeVisible();
  expect(screen.getByText("View chart data")).toBeVisible();
});
