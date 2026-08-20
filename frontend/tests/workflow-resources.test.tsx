import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { WorkflowResourceSetup } from "@/components/workflow-resource-setup";
import { Providers } from "@/lib/providers";

import { localProjectFixture, workflowInstancesFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("shows exact external metadata without claiming local download or network resolution", async () => {
  const instance = {
    ...workflowInstancesFixture.items[0],
    workflow_definition_id: "reproduction-experiment-local-experimental",
    workflow_version: "0.3.0",
    capsule_version: "0.3.0",
  };
  const requirement = {
    requirement_key: "dataset",
    resource_kind: "DATASET" as const,
    required: false,
    cardinality_min: 0,
    cardinality_max: 1,
    allowed_providers: ["HUGGING_FACE" as const, "LOCAL_TEST" as const],
    usage_description: "Optional dataset reference.",
  };
  const resource = {
    resource_id: `resource-${"a".repeat(32)}`,
    project_id: localProjectFixture.project_id,
    resource_kind: "DATASET" as const,
    provider: "HUGGING_FACE" as const,
    locator: "owner/dataset",
    exact_revision: "b".repeat(40),
    expected_content_checksum: `sha256:${"c".repeat(64)}`,
    display_name: "Exact synthetic dataset",
    metadata: {},
    lifecycle: "ACTIVE" as const,
    created_at: "2026-08-09T00:00:00Z",
  };
  vi.spyOn(apiClient, "listProjectResources").mockResolvedValue({
    items: [resource], total: 1, offset: 0, limit: 100,
  });
  vi.spyOn(apiClient, "listWorkflowResourceBindings").mockResolvedValue({
    items: [{
      binding_id: `resource-binding-${"d".repeat(32)}`,
      project_id: localProjectFixture.project_id,
      workflow_instance_id: instance.workflow_instance_id,
      workflow_definition_id: instance.workflow_definition_id,
      workflow_version: "0.3.0",
      requirement_key: "dataset",
      resource_id: resource.resource_id,
      expected_content_checksum: resource.expected_content_checksum,
      state: "ACTIVE",
      resource,
    }],
    total: 1,
  });

  render(
    <Providers>
      <WorkflowResourceSetup
        projectId={localProjectFixture.project_id}
        instance={instance}
        requirements={[requirement]}
      />
    </Providers>,
  );

  expect((await screen.findAllByText(/Exact synthetic dataset/)).length).toBeGreaterThan(0);
  expect(screen.getByText(/local staging and verification remain pending/i)).toBeInTheDocument();
  expect(screen.getByText(/does not resolve GitHub or Hugging Face content over the network/i)).toBeInTheDocument();
  expect(screen.queryByText(/scaffold version/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/downloaded locally/i)).not.toBeInTheDocument();
});

test("renders the Real Experiment source repository as an exact required owner-staged package", async () => {
  const user = userEvent.setup();
  const instance = {
    ...workflowInstancesFixture.items[0],
    workflow_definition_id: "reproduction-experiment-local-experimental",
    workflow_version: "0.4.0",
    capsule_version: "0.7.0",
  };
  const requirement = {
    requirement_key: "source_repository",
    resource_kind: "SOURCE_REPOSITORY" as const,
    required: true,
    cardinality_min: 1,
    cardinality_max: 1,
    allowed_providers: ["GITHUB" as const],
    usage_description: "One exact owner-staged local Experiment Package; Cloud metadata alone is not execution readiness.",
  };
  vi.spyOn(apiClient, "listProjectResources").mockResolvedValue({
    items: [], total: 0, offset: 0, limit: 100,
  });
  vi.spyOn(apiClient, "listWorkflowResourceBindings").mockResolvedValue({
    items: [], total: 0,
  });
  const createResource = vi.spyOn(apiClient, "createProjectResource").mockResolvedValue({
    resource_id: `resource-${"f".repeat(32)}`,
    project_id: localProjectFixture.project_id,
    resource_kind: "SOURCE_REPOSITORY",
    provider: "GITHUB",
    locator: "owner/knn-experiment",
    exact_revision: "a".repeat(40),
    expected_content_checksum: `sha256:${"b".repeat(64)}`,
    display_name: "KNN Wine package",
    metadata: {},
    lifecycle: "ACTIVE",
    created_at: "2026-08-17T00:00:00Z",
  });

  render(
    <Providers>
      <WorkflowResourceSetup
        projectId={localProjectFixture.project_id}
        instance={instance}
        requirements={[requirement]}
      />
    </Providers>,
  );

  expect(await screen.findByRole("heading", { name: "Experiment Package" })).toBeVisible();
  expect(screen.getByText("Required", { selector: ".section-heading span" })).toBeVisible();
  expect(screen.getByText(/package stays in your Local Workspace/i)).toBeVisible();
  expect(screen.getByText(/cannot run yet because its required Experiment Package source has not been selected/i)).toBeVisible();
  expect(screen.getByRole("heading", { name: "Prepare your Experiment Package" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Register or choose a source" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Stage and verify locally" })).toBeVisible();
  expect(screen.getByRole("list", { name: "Experiment Package setup progression" })).toHaveTextContent(
    "Prepare packageRegister or choose sourceUse this sourceStage and verify locallyRun experiment",
  );
  expect(screen.getByText(/\.reagent-experiment\.json/)).toBeVisible();
  expect(screen.getByText(
    `python reagent_local.py resource stage . <package-path> --workflow-instance ${instance.workflow_instance_id}`,
  )).toBeVisible();
  expect(screen.queryByRole("button", { name: "Copy Experiment Package staging command" })).not.toBeInTheDocument();
  expect(screen.getByText("Local command template")).toBeVisible();
  expect(screen.getByRole("button", { name: "Use this source" })).toBeDisabled();
  expect(screen.queryByText("Add reference metadata")).not.toBeInTheDocument();
  expect(screen.queryByText("Bind exact Resource")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Provider")).not.toBeInTheDocument();
  expect(screen.queryByText(/all Resource requirements are optional/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/scaffold version/i)).not.toBeInTheDocument();

  await user.click(screen.getByText("Register an Experiment Package source"));
  expect(screen.getByText("GitHub", { selector: ".fixed-source-type strong" })).toBeVisible();
  expect(screen.getByText(/current Experiment contract accepts GitHub sources only/i)).toBeVisible();
  await user.type(screen.getByRole("textbox", { name: /Package name/ }), "KNN Wine package");
  await user.type(screen.getByRole("textbox", { name: /GitHub repository/ }), "owner/knn-experiment");
  await user.type(screen.getByRole("textbox", { name: /Commit SHA/ }), "a".repeat(40));
  await user.type(screen.getByRole("textbox", { name: /Package SHA-256/ }), `sha256:${"b".repeat(64)}`);
  await user.click(screen.getByRole("button", { name: "Register source" }));

  expect(createResource).toHaveBeenCalledWith(localProjectFixture.project_id, {
    resource_kind: "SOURCE_REPOSITORY",
    provider: "GITHUB",
    locator: "owner/knn-experiment",
    exact_revision: "a".repeat(40),
    expected_content_checksum: `sha256:${"b".repeat(64)}`,
    display_name: "KNN Wine package",
    metadata: {},
  });
  expect(await screen.findByText(/Experiment Package source registered/i)).toBeVisible();

  await user.click(screen.getByText("Technical details"));
  expect(screen.getByText(/source_repository/)).toBeVisible();
  expect(screen.getByText(/SOURCE_REPOSITORY/)).toBeVisible();
  expect(screen.getByText(/required=/)).toHaveTextContent("required=true");
  expect(screen.getByText(/cardinality Exactly 1/)).toBeVisible();
  expect(screen.getByText(/provider=GITHUB/)).toBeVisible();
});

test("uses an existing registered Experiment Package source through the unchanged binding operation", async () => {
  const user = userEvent.setup();
  const instance = {
    ...workflowInstancesFixture.items[0],
    workflow_definition_id: "reproduction-experiment-local-experimental",
    workflow_version: "0.4.0",
    capsule_version: "0.7.0",
  };
  const requirement = {
    requirement_key: "source_repository",
    resource_kind: "SOURCE_REPOSITORY" as const,
    required: true,
    cardinality_min: 1,
    cardinality_max: 1,
    allowed_providers: ["GITHUB" as const],
    usage_description: "One exact owner-staged local Experiment Package.",
  };
  const resource = {
    resource_id: `resource-${"a".repeat(32)}`,
    project_id: localProjectFixture.project_id,
    resource_kind: "SOURCE_REPOSITORY" as const,
    provider: "GITHUB" as const,
    locator: "owner/knn-experiment",
    exact_revision: "b".repeat(40),
    expected_content_checksum: `sha256:${"c".repeat(64)}`,
    display_name: "Registered KNN package",
    metadata: {},
    lifecycle: "ACTIVE" as const,
    created_at: "2026-08-17T00:00:00Z",
  };
  vi.spyOn(apiClient, "listProjectResources").mockResolvedValue({ items: [resource], total: 1, offset: 0, limit: 100 });
  vi.spyOn(apiClient, "listWorkflowResourceBindings").mockResolvedValue({ items: [], total: 0 });
  const bindResource = vi.spyOn(apiClient, "bindWorkflowResource").mockResolvedValue({
    binding_id: `resource-binding-${"d".repeat(32)}`,
    project_id: localProjectFixture.project_id,
    workflow_instance_id: instance.workflow_instance_id,
    workflow_definition_id: instance.workflow_definition_id,
    workflow_version: instance.workflow_version,
    requirement_key: requirement.requirement_key,
    resource_id: resource.resource_id,
    expected_content_checksum: resource.expected_content_checksum,
    state: "ACTIVE",
    resource,
  });

  render(
    <Providers>
      <WorkflowResourceSetup projectId={localProjectFixture.project_id} instance={instance} requirements={[requirement]} />
    </Providers>,
  );

  await screen.findByRole("option", { name: /Registered KNN package/ });
  const sourcePicker = screen.getByRole("combobox", { name: "Choose a registered source" });
  await user.selectOptions(sourcePicker, resource.resource_id);
  await user.click(screen.getByRole("button", { name: "Use this source" }));

  expect(bindResource).toHaveBeenCalledWith(
    localProjectFixture.project_id,
    instance.workflow_instance_id,
    expect.objectContaining({ requirement_key: "source_repository", resource_id: resource.resource_id }),
  );
  expect(await screen.findByText(/Source selected for this experiment/i)).toBeVisible();
});
