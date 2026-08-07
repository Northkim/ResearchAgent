import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, test, vi } from "vitest";

import { ApiError, apiClient } from "@/api/client";
import { WorkflowBoard } from "@/components/workflow-board";
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
  vi.spyOn(apiClient, "listProjectWorkflowInstances").mockResolvedValue(workflowInstancesFixture);
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue(projectProgressFixture);
}

test("renders Registry-driven Workflow cards and keeps planned definitions disabled", async () => {
  arrange();
  render(<Providers><WorkflowBoard projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Your Project workflows" })).toBeVisible();
  expect(screen.getByText("Next: Review the latest result")).toBeVisible();
  expect(screen.getByText("Completed")).toBeVisible();
  expect(screen.getByText("Cloud desired")).toBeVisible();
  expect(screen.getByText("Installed · current")).toBeVisible();
  expect(screen.getByRole("button", { name: "Planned" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Already active" })).toBeDisabled();
  expect(screen.getByRole("link", { name: "Workflows" })).toHaveAttribute("aria-current", "page");
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
  expect(screen.getAllByText("Technical details")).toHaveLength(2);
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

  await userEvent.click(await screen.findByRole("button", { name: "Add workflow" }));
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
