import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { IdeaDiscoverySetup } from "@/components/idea-discovery-setup";
import { Providers } from "@/lib/providers";
import type { CanonicalArtifactReference, ProjectWorkflowInstance } from "@/types/api";

import { localProjectFixture, workflowInstancesFixture } from "./fixtures";

const ideaInstance: ProjectWorkflowInstance = {
  ...workflowInstancesFixture.items[0],
  workflow_instance_id: `wfi-${"7".repeat(32)}`,
  workflow_definition_id: "idea-discovery-local-experimental",
  workflow_version: "0.1.0",
  capsule_id: `capsule-${"7".repeat(32)}`,
  capsule_version: "0.1.0",
  display_name: "Idea Discovery",
  created_manifest_revision: 2,
};

function artifact(id: string, producer: string, checksumCharacter: string): CanonicalArtifactReference {
  return {
    schema_version: "reagent.artifact-reference/v0.1",
    artifact_id: id,
    project_id: localProjectFixture.project_id,
    producer_workflow_instance_id: producer,
    producer_progress_receipt_id: "progress-receipt-fixture",
    producer_progress_report_id: `prv2-${"a".repeat(64)}`,
    producer_execution_round: 1,
    producer_capsule_id: `capsule-${"1".repeat(32)}`,
    producer_capsule_version: "0.6.0",
    producer_core_capability_maturity: "REVIEWED_CORE",
    artifact_type: "selected-paper-library/v1",
    artifact_schema_version: "selected-paper-library/v1",
    media_type: "application/json",
    state: "LOCAL_AVAILABLE",
    relative_path: `outputs/artifacts/selected-paper-library/sha256-${checksumCharacter.repeat(64)}.json`,
    content_checksum: `sha256:${checksumCharacter.repeat(64)}`,
    size_bytes: 1234,
    cloud_metadata_available: true,
    produced_at: "2026-08-07T01:00:00Z",
    retired_at: null,
    created_at: "2026-08-07T01:00:00Z",
    updated_at: "2026-08-07T01:00:00Z",
  };
}

function arrange(artifacts: CanonicalArtifactReference[]) {
  const artifactRequest = vi.spyOn(apiClient, "listProjectArtifactReferences").mockResolvedValue({
    schema_version: "reagent.artifact-reference-page/v0.1",
    project_id: localProjectFixture.project_id,
    artifacts,
    offset: 0,
    limit: 100,
    total: artifacts.length,
    has_more: false,
  });
  const dependencyRequest = vi.spyOn(apiClient, "listArtifactDependencies").mockResolvedValue({
    schema_version: "reagent.artifact-dependency-page/v0.1",
    project_id: localProjectFixture.project_id,
    consumer_workflow_instance_id: ideaInstance.workflow_instance_id,
    dependencies: [],
    offset: 0,
    limit: 25,
    total: 0,
    has_more: false,
  });
  return { artifactRequest, dependencyRequest };
}

afterEach(() => vi.restoreAllMocks());

test("explains the production prerequisite when no compatible Artifact exists", async () => {
  arrange([]);
  render(
    <Providers>
      <IdeaDiscoverySetup
        projectId={localProjectFixture.project_id}
        instance={ideaInstance}
        instances={[...workflowInstancesFixture.items, ideaInstance]}
        installationState="UNKNOWN"
        dependencies={[]}
      />
    </Providers>,
  );
  expect(await screen.findByText(/needs a completed paper library from Literature Search 0.4.0/)).toBeVisible();
  expect(screen.getByText(/legacy Literature Search 0.3.0/)).toBeVisible();
  expect(screen.queryByRole("button", { name: /Confirm selected/ })).not.toBeInTheDocument();
});

test("requires an explicit choice when two compatible Artifacts exist", async () => {
  const secondProducer = `wfi-${"9".repeat(32)}`;
  const choices = [
    artifact(`artifact-${"a".repeat(32)}`, workflowInstancesFixture.items[0].workflow_instance_id, "a"),
    artifact(`artifact-${"b".repeat(32)}`, secondProducer, "b"),
  ];
  arrange(choices);
  const bind = vi.spyOn(apiClient, "bindArtifactDependency").mockResolvedValue({
    binding_id: `artifact-binding-${"c".repeat(32)}`,
    project_id: localProjectFixture.project_id,
    consumer_workflow_instance_id: ideaInstance.workflow_instance_id,
    consumer_workflow_definition_id: ideaInstance.workflow_definition_id,
    consumer_workflow_version: ideaInstance.workflow_version,
    requirement_key: "paper_library",
    artifact_id: choices[1].artifact_id,
    expected_checksum: choices[1].content_checksum,
    state: "ACTIVE",
    idempotency_key: "00000000-0000-4000-8000-000000000007",
    created_at: "2026-08-07T01:00:00Z",
    updated_at: "2026-08-07T01:00:00Z",
    retired_at: null,
  });
  render(
    <Providers>
      <IdeaDiscoverySetup
        projectId={localProjectFixture.project_id}
        instance={ideaInstance}
        instances={[
          ...workflowInstancesFixture.items,
          { ...workflowInstancesFixture.items[0], workflow_instance_id: secondProducer, display_name: "Literature Search B" },
          ideaInstance,
        ]}
        installationState="ACKNOWLEDGED_CURRENT"
        dependencies={[]}
      />
    </Providers>,
  );

  const radios = await screen.findAllByRole("radio");
  expect(radios).toHaveLength(2);
  const button = screen.getByRole("button", { name: "Confirm selected input" });
  expect(button).toBeDisabled();
  await userEvent.click(radios[1]);
  await userEvent.click(button);
  expect(bind).toHaveBeenCalledWith(
    localProjectFixture.project_id,
    ideaInstance.workflow_instance_id,
    expect.objectContaining({
      requirement_key: "paper_library",
      artifact_id: choices[1].artifact_id,
    }),
  );
  expect(await screen.findByText(/Input selected/)).toBeVisible();
  expect(screen.getByText(/prepare the verified copy/i)).toBeVisible();
});

test("shows a bounded error instead of selecting an Artifact implicitly", async () => {
  const choice = artifact(`artifact-${"d".repeat(32)}`, workflowInstancesFixture.items[0].workflow_instance_id, "d");
  arrange([choice]);
  vi.spyOn(apiClient, "bindArtifactDependency").mockRejectedValue(new Error("conflict"));
  render(
    <Providers>
      <IdeaDiscoverySetup
        projectId={localProjectFixture.project_id}
        instance={ideaInstance}
        instances={[...workflowInstancesFixture.items, ideaInstance]}
        installationState="UNKNOWN"
        dependencies={[]}
      />
    </Providers>,
  );
  await userEvent.click(await screen.findByRole("radio"));
  await userEvent.click(screen.getByRole("button", { name: "Confirm selected input" }));
  expect(await screen.findByText(/could not be saved/)).toBeVisible();
});

test("recommends the sole compatible result but still requires confirmation", async () => {
  const choice = artifact(`artifact-${"e".repeat(32)}`, workflowInstancesFixture.items[0].workflow_instance_id, "e");
  arrange([choice]);
  const bind = vi.spyOn(apiClient, "bindArtifactDependency");
  render(
    <Providers>
      <IdeaDiscoverySetup
        projectId={localProjectFixture.project_id}
        instance={ideaInstance}
        instances={[...workflowInstancesFixture.items, ideaInstance]}
        installationState="ACKNOWLEDGED_CURRENT"
        dependencies={[]}
      />
    </Providers>,
  );
  expect(await screen.findByText(/Recommended: this is the only compatible result/)).toBeVisible();
  expect(screen.getByRole("radio")).toBeChecked();
  expect(screen.getByRole("button", { name: "Confirm selected input" })).toBeEnabled();
  expect(bind).not.toHaveBeenCalled();
});

test("shows stable-key local commands for the normal single-instance path", async () => {
  const choice = artifact(`artifact-${"f".repeat(32)}`, workflowInstancesFixture.items[0].workflow_instance_id, "f");
  arrange([choice]);
  render(
    <Providers>
      <IdeaDiscoverySetup
        projectId={localProjectFixture.project_id}
        instance={ideaInstance}
        instances={[...workflowInstancesFixture.items, ideaInstance]}
        installationState="ACKNOWLEDGED_CURRENT"
        dependencies={[{
          binding_id: `artifact-binding-${"c".repeat(32)}`,
          consumer_workflow_instance_id: ideaInstance.workflow_instance_id,
          requirement_key: "paper_library",
          artifact_id: choice.artifact_id,
          expected_checksum: choice.content_checksum,
          state: "ACTIVE",
          producer_workflow_instance_id: choice.producer_workflow_instance_id,
          artifact_type: choice.artifact_type,
          artifact_schema_version: choice.artifact_schema_version,
          produced_at: choice.produced_at,
        }]}
      />
    </Providers>,
  );
  expect(await screen.findByText(
    "python reagent_local.py artifact materialize . --workflow idea-discovery-local-experimental",
  )).toBeVisible();
  expect(screen.getByText(
    "python reagent_local.py run . --workflow idea-discovery-local-experimental",
  )).toBeVisible();
  expect(screen.getByText(
    `python reagent_local.py run . --workflow-instance ${ideaInstance.workflow_instance_id}`,
  )).not.toBeVisible();
});

test("shares one bounded Artifact query across multiple Idea cards", async () => {
  const producers = Array.from({ length: 10 }, (_, index) => ({
    ...workflowInstancesFixture.items[0],
    workflow_instance_id: `wfi-${(index + 1).toString(16).padStart(32, "0")}`,
    display_name: `Literature Search ${index + 1}`,
  }));
  const choices = producers.map((producer, index) => artifact(
    `artifact-${(index + 1).toString(16).padStart(32, "0")}`,
    producer.workflow_instance_id,
    (index + 1).toString(16),
  ));
  const requests = arrange(choices);
  const ideas = Array.from({ length: 10 }, (_, index) => ({
    ...ideaInstance,
    workflow_instance_id: `wfi-${(index + 11).toString(16).padStart(32, "0")}`,
    display_name: `Idea Discovery ${index + 1}`,
  }));
  const instances = [...producers, ...ideas];
  render(
    <Providers>
      {ideas.map((instance) => (
        <IdeaDiscoverySetup
          key={instance.workflow_instance_id}
          projectId={localProjectFixture.project_id}
          instance={instance}
          instances={instances}
          installationState="UNKNOWN"
          dependencies={[]}
        />
      ))}
    </Providers>,
  );
  expect(await screen.findAllByRole("radio")).toHaveLength(100);
  expect(requests.artifactRequest).toHaveBeenCalledTimes(1);
  expect(requests.dependencyRequest).not.toHaveBeenCalled();
});
