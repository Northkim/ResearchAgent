import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { LocalProjectDetail } from "@/components/local-project-detail";
import { LocalProjectList } from "@/components/local-project-list";
import { WorkflowDetail } from "@/components/workflow-detail";
import { Providers } from "@/lib/providers";
import type { LocalProject, ProjectProgress, WorkflowActionProjection } from "@/types/api";

import {
  localProjectFixture,
  projectProgressFixture,
  workflowCatalogFixture,
  workflowInstanceId,
  workflowInstancesFixture,
} from "./fixtures";

const push = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

afterEach(() => vi.restoreAllMocks());

const setupAction: WorkflowActionProjection = {
  stage: { code: "LOCAL_SETUP", label: "Local Workspace setup required" },
  actor: "OWNER",
  attention_state: "ATTENTION_REQUIRED",
  blocker: {
    code: "LOCAL_SETUP_REQUIRED",
    message: "No Local Workspace installation has been acknowledged for this Project.",
  },
  next_action: {
    surface: "BROWSER",
    code: "SETUP",
    label: "Set up Local Workspace",
    description: "Open the supported Project setup instructions before creating and syncing the Local Workspace.",
    command: null,
  },
  expected_output: projectProgressFixture.instances[0].action.expected_output,
  latest_output: null,
};

const setupProject: LocalProject = {
  ...localProjectFixture,
  attention: {
    recommended_workflow_instance_id: workflowInstanceId,
    recommended_workflow_label: "Literature Search",
    action: setupAction,
    recent_change: { summary: setupAction.stage.label, changed_at: null },
    latest_output: null,
  },
};

const setupProgress: ProjectProgress = {
  ...projectProgressFixture,
  total_progress_report_count: 0,
  history: [],
  history_total: 0,
  attention: setupProject.attention,
  instances: [{
    ...projectProgressFixture.instances[0],
    research_status: "NOT_STARTED",
    latest_report_id: null,
    latest_report_checksum: null,
    latest_execution_round: null,
    latest_summary: null,
    report_count: 0,
    installation_state: "UNKNOWN",
    installation_manifest_revision: null,
    readiness: "NOT_INSTALLED",
    next_action: "SETUP" as const,
    action: setupAction,
  }],
};

const fullSetupProgress: ProjectProgress = {
  ...setupProgress,
  active_workflow_count: 5,
  instances: ([
    ["review-local-experimental", "Review", "5"],
    ["writing-local-experimental", "Writing", "4"],
    ["reproduction-experiment-local-experimental", "Reproduction & Experiment", "3"],
    ["idea-discovery-local-experimental", "Idea Discovery", "2"],
  ].map(([workflow_definition_id, workflow_display_name, identity]) => ({
    ...setupProgress.instances[0],
    workflow_instance_id: `wfi-${identity.repeat(32)}`,
    workflow_definition_id,
    workflow_display_name,
    instance_display_name: workflow_display_name,
    friendly_instance_label: workflow_display_name,
  })) as ProjectProgress["instances"]).concat(setupProgress.instances),
};

const runAction: WorkflowActionProjection = {
  ...setupAction,
  stage: { code: "READY", label: "Ready to start" },
  attention_state: "NORMAL",
  blocker: null,
  next_action: {
    surface: "LOCAL",
    code: "RUN",
    label: "Start in Local Workspace",
    description: "Run this Workflow through the public local Workspace command.",
    command: "python reagent_local.py run . --workflow literature-search-local-experimental",
  },
};

const runProject: LocalProject = {
  ...setupProject,
  attention: {
    ...setupProject.attention,
    action: runAction,
    recent_change: { summary: runAction.stage.label, changed_at: null },
  },
};

const runProgress: ProjectProgress = {
  ...setupProgress,
  attention: runProject.attention,
  instances: [{
    ...setupProgress.instances[0],
    installation_state: "ACKNOWLEDGED_CURRENT",
    installation_manifest_revision: 1,
    readiness: "READY_TO_RUN",
    next_action: "RUN",
    action: runAction,
  }],
};

function arrangeWorkflowDetail(
  progress: ProjectProgress = setupProgress,
  project: LocalProject = setupProject,
) {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(project);
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue(progress);
  vi.spyOn(apiClient, "listProjectWorkflowInstances").mockResolvedValue(workflowInstancesFixture);
  vi.spyOn(apiClient, "getWorkflowDefinition").mockResolvedValue({
    ...workflowCatalogFixture.items[0],
    versions: [workflowCatalogFixture.items[0].recommended_version!],
    capsules: [workflowCatalogFixture.items[0].recommended_capsule!],
  });
}

test("leads the Project Overview with the current research action", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue(projectProgressFixture);
  render(<Providers><LocalProjectDetail projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Review the selected papers" })).toBeVisible();
  expect(screen.queryByText("Owner acts now")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View selected papers" })).toHaveAttribute("href", expect.stringContaining("/outputs"));
  expect(screen.getAllByText("Literature Search").length).toBeGreaterThan(0);
  expect(screen.getByRole("heading", { name: "Workflow progress" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Latest output" })).toBeVisible();
  expect(screen.getByText("Selected paper library")).toBeVisible();
  expect(screen.queryByText(/% complete/i)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("link", { name: "Workflows" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Outputs" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Activity" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Help" })).toBeVisible();
  expect(screen.queryByRole("link", { name: "Download setup file" })).not.toBeInTheDocument();
  expect(screen.getByText("Technical Details")).toBeVisible();
});

test("deletes only after the explicit Cloud-only Project confirmation", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue(projectProgressFixture);
  const remove = vi.spyOn(apiClient, "deleteProject").mockResolvedValue();
  render(<Providers><LocalProjectDetail projectId={localProjectFixture.project_id} /></Providers>);

  await screen.findByRole("heading", { name: "Review the selected papers" });
  await userEvent.click(screen.getByText("Project settings"));
  await userEvent.click(screen.getByRole("button", { name: "Delete project" }));
  expect(screen.getByText(/Your Local Workspace and research files will not be deleted/)).toBeVisible();
  expect(remove).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "Delete from ReAgent" }));
  expect(remove).toHaveBeenCalledWith(localProjectFixture.project_id);
  expect(push).toHaveBeenCalledWith("/projects");
});

test("routes fresh Projects and Project Overview to the canonical setup surface", async () => {
  vi.spyOn(apiClient, "listProjects").mockResolvedValue([setupProject]);
  const list = render(<Providers><LocalProjectList /></Providers>);

  expect(await screen.findByText("Local workspace not set up")).toBeVisible();
  expect(screen.getByRole("link", { name: "Set up local workspace →" })).toHaveAttribute(
    "href",
    `/projects/${localProjectFixture.project_id}/help`,
  );
  expect(screen.queryByText("Local workspace needs syncing")).not.toBeInTheDocument();
  list.unmount();

  vi.spyOn(apiClient, "getProject").mockResolvedValue(setupProject);
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue(fullSetupProgress);
  render(<Providers><LocalProjectDetail projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Set up local workspace" })).toBeVisible();
  expect(screen.getAllByText("Local workspace not set up")).toHaveLength(1);
  expect(screen.getByRole("link", { name: "Set up local workspace" })).toHaveAttribute(
    "href",
    `/projects/${localProjectFixture.project_id}/help`,
  );
  expect(screen.queryByRole("link", { name: "Sync workspace" })).not.toBeInTheDocument();
  const workflowProgress = screen.getByRole("region", { name: "Workflow progress" });
  expect([...workflowProgress.querySelectorAll("strong")].map((element) => element.textContent)).toEqual([
    "Literature Search",
    "Idea Discovery",
    "Reproduction & Experiment",
    "Writing",
    "Review",
  ]);
  expect(screen.getByText("Waiting for workspace")).toBeVisible();
  expect(screen.getAllByText("Not started")).toHaveLength(8);
});

test("Project Overview describes ready local execution as navigation to instructions", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(runProject);
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue(runProgress);
  render(<Providers><LocalProjectDetail projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Literature Search is ready" })).toBeVisible();
  expect(screen.getByText(/Run Literature Search in your Local Workspace/)).toBeVisible();
  expect(screen.getByRole("link", { name: "View run instructions" })).toHaveAttribute(
    "href",
    `/projects/${localProjectFixture.project_id}/workflows/${workflowInstanceId}`,
  );
  expect(screen.queryByRole("link", { name: "Run locally" })).not.toBeInTheDocument();
});

test("Workflow Detail visibly opens human-labeled exact run instructions", async () => {
  const user = userEvent.setup();
  arrangeWorkflowDetail(runProgress, runProject);
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={workflowInstanceId} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Run Literature Search in your Local Workspace" })).toBeVisible();
  const reveal = screen.getByRole("button", { name: "Show run instructions" });
  const instructions = screen.getByText("Run Literature Search", { selector: "summary span" }).closest("details");
  expect(reveal).toHaveAttribute("aria-controls", "run-locally");
  expect(reveal).toHaveAttribute("aria-expanded", "false");
  expect(instructions).not.toHaveAttribute("open");

  await user.click(reveal);

  expect(reveal).toHaveAttribute("aria-expanded", "true");
  expect(instructions).toHaveAttribute("open");
  expect(screen.getByText("Exact command")).toBeVisible();
  expect(screen.getByText("python reagent_local.py run . --workflow literature-search-local-experimental")).toBeVisible();
  expect(screen.getByText(/runs the exact Literature Search Workflow/)).toBeVisible();
  expect(screen.getByRole("button", { name: "Copy Literature Search exact command" })).toBeEnabled();
  expect(screen.getByRole("heading", { name: "Run Literature Search in your Local Workspace" })).not.toHaveTextContent("wfi-");
});

test("Workflow Detail resolves Artifact inputs from the exact pinned Workflow version", async () => {
  const experimentInstanceId = `wfi-${"e".repeat(32)}`;
  const experimentInstance = {
    ...workflowInstancesFixture.items[0],
    workflow_instance_id: experimentInstanceId,
    workflow_definition_id: "reproduction-experiment-local-experimental",
    workflow_version: "0.4.0",
    capsule_id: `capsule-${"a".repeat(32)}`,
    capsule_version: "0.7.0",
    display_name: "Reproduction & Experiment",
    resource_requirements: [{
      requirement_key: "source_repository",
      resource_kind: "SOURCE_REPOSITORY" as const,
      required: true,
      cardinality_min: 1,
      cardinality_max: 1,
      allowed_providers: ["GITHUB" as const],
      usage_description: "One exact owner-staged local Experiment Package; Cloud metadata alone is not execution readiness.",
    }],
  };
  const resourceAction: WorkflowActionProjection = {
    ...runAction,
    stage: { code: "RESOURCE_BINDING", label: "Required Resource not bound" },
    attention_state: "OWNER_ACTION_REQUIRED",
    blocker: {
      code: "REQUIRED_RESOURCE_NOT_BOUND",
      message: "Bind the exact required Resource before local staging: source repository.",
    },
    next_action: {
      surface: "BROWSER",
      code: "SELECT_RESOURCE",
      label: "Bind exact Resource",
      description: "Select or register the exact required Resource metadata for this Workflow.",
      command: null,
    },
  };
  const experimentProgress: ProjectProgress = {
    ...runProgress,
    attention: {
      ...runProgress.attention,
      recommended_workflow_instance_id: experimentInstanceId,
      recommended_workflow_label: "Reproduction & Experiment",
      action: resourceAction,
    },
    instances: [{
      ...runProgress.instances[0],
      workflow_instance_id: experimentInstanceId,
      workflow_definition_id: experimentInstance.workflow_definition_id,
      workflow_definition_version: "0.4.0",
      workflow_display_name: "Reproduction & Experiment",
      instance_display_name: "Reproduction & Experiment",
      capsule_id: experimentInstance.capsule_id,
      capsule_version: "0.7.0",
      readiness: "WAITING_FOR_RESOURCE",
      next_action: "SELECT_RESOURCE",
      action: resourceAction,
    }],
  };
  vi.spyOn(apiClient, "getProject").mockResolvedValue(runProject);
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue(experimentProgress);
  vi.spyOn(apiClient, "listProjectWorkflowInstances").mockResolvedValue({
    ...workflowInstancesFixture,
    items: [experimentInstance],
  });
  vi.spyOn(apiClient, "getWorkflowDefinition").mockResolvedValue({
    workflow_definition_id: experimentInstance.workflow_definition_id,
    stable_workflow_key: experimentInstance.workflow_definition_id,
    display_name: "Reproduction & Experiment",
    description: "Run a bounded local experiment.",
    lifecycle: "AVAILABLE",
    creatable: true,
    allows_multiple_instances: true,
    recommended_version: {
      version: "0.3.0",
      contract_checksum: `sha256:${"3".repeat(64)}`,
      input_schema_id: "experiment-input/v0.3",
      output_schema_id: "experiment-record/v1",
      review_status: "REVIEWED",
      core_capability_maturity: "SCAFFOLD_CORE",
      published_at: "2026-08-09T00:00:00Z",
      artifact_requirements: [
        { requirement_key: "research_idea", artifact_type: "selected-research-idea/v1", schema_constraint: "selected-research-idea/v1", required: true, target_relative_path: "inputs/selected-research-idea.json" },
        { requirement_key: "literature_library", artifact_type: "selected-paper-library/v1", schema_constraint: "selected-paper-library/v1", required: false, target_relative_path: "inputs/selected-papers.json" },
      ],
    },
    recommended_capsule: null,
    versions: [{
      version: "0.4.0",
      contract_checksum: `sha256:${"4".repeat(64)}`,
      input_schema_id: "real-experiment-input/v0.1",
      output_schema_id: "experiment-record/v2",
      review_status: "REVIEWED",
      core_capability_maturity: "REVIEWED_CORE",
      published_at: "2026-08-14T00:00:00Z",
      artifact_requirements: [
        { requirement_key: "research_idea", artifact_type: "selected-research-idea/v1", schema_constraint: "selected-research-idea/v1", required: true, target_relative_path: "inputs/selected-research-idea.json" },
      ],
      resource_requirements: experimentInstance.resource_requirements,
    }],
    capsules: [],
  });
  vi.spyOn(apiClient, "listProjectResources").mockResolvedValue({ items: [], total: 0, offset: 0, limit: 100 });
  vi.spyOn(apiClient, "listWorkflowResourceBindings").mockResolvedValue({ items: [], total: 0 });

  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={experimentInstanceId} /></Providers>);

  expect(await screen.findByText("Selected research idea")).toBeVisible();
  expect(screen.queryByText("Selected literature")).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Choose the Experiment Package source" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Choose package source" })).toHaveAttribute("href", "#resources");
  expect(screen.getByRole("heading", { name: "Experiment Package" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Register or choose a source" })).toBeVisible();
  expect(screen.getByText(/one exact Experiment Package/i)).toBeVisible();
  expect(screen.queryByText(/scaffold version/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/runs the exact Reproduction & Experiment Workflow/i)).not.toBeInTheDocument();
});

test("Workflow Detail sends SETUP to Project help without presenting a sync command", async () => {
  arrangeWorkflowDetail();
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={workflowInstanceId} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Set up local workspace" })).toBeVisible();
  expect(screen.getByText("Local workspace setup", { exact: true })).toBeVisible();
  expect(screen.getByRole("link", { name: "Set up local workspace" })).toHaveAttribute(
    "href",
    `/projects/${localProjectFixture.project_id}/help`,
  );
  expect(screen.queryByText("python reagent_local.py sync .")).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "Sync workspace" })).not.toBeInTheDocument();
});

test("Workflow Detail preserves stale installation sync semantics", async () => {
  const staleAction: WorkflowActionProjection = {
    ...setupAction,
    stage: { code: "LOCAL_SYNC", label: "Local Workspace out of date" },
    blocker: {
      code: "LOCAL_SYNC_REQUIRED",
      message: "The Local Workspace acknowledges an older Project revision.",
    },
    next_action: {
      surface: "LOCAL",
      code: "SYNC",
      label: "Sync Local Workspace",
      description: "Bring this Workflow's installed Capsule up to the current Project revision.",
      command: "python reagent_local.py sync .",
    },
  };
  arrangeWorkflowDetail({
    ...setupProgress,
    attention: { ...setupProgress.attention, action: staleAction },
    instances: [{
      ...setupProgress.instances[0],
      installation_state: "ACKNOWLEDGED_STALE",
      installation_manifest_revision: 1,
      next_action: "SYNC",
      action: staleAction,
    }],
  });
  render(<Providers><WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={workflowInstanceId} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Sync the local workspace" })).toBeVisible();
  expect(screen.getByText("Local workspace needs syncing")).toBeVisible();
  expect(screen.getByRole("link", { name: "Sync workspace" })).toHaveAttribute("href", "#run-locally");
  expect(screen.getByText("python reagent_local.py sync .")).toBeInTheDocument();
});
