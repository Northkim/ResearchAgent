import { render, screen } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { WorkflowResourceSetup } from "@/components/workflow-resource-setup";
import { Providers } from "@/lib/providers";

import { localProjectFixture, workflowInstancesFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("shows exact external metadata without claiming local download", async () => {
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
  expect(screen.getByText(/local resolution is not claimed/i)).toBeInTheDocument();
  expect(screen.getByText(/GitHub and Hugging Face network resolution is not implemented/i)).toBeInTheDocument();
  expect(screen.queryByText(/downloaded locally/i)).not.toBeInTheDocument();
});
