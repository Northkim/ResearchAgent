import { render, screen } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { ArtifactPresentationPreview } from "@/components/artifact-presentation";
import { WorkflowInputSetup } from "@/components/workflow-input-setup";
import { Providers } from "@/lib/providers";
import type { CanonicalArtifactReference } from "@/types/api";

import { projectProgressFixture, workflowInstancesFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

const projectId = `project-${"1".repeat(32)}`;

function artifact(type: "selected-paper-library/v1" | "selected-research-idea/v1", suffix: string, payload?: Record<string, unknown>): CanonicalArtifactReference {
  const artifactId = `artifact-${suffix.repeat(32)}`;
  const checksum = `sha256:${suffix.repeat(64)}`;
  const schema = type === "selected-paper-library/v1"
    ? "reagent.artifact-presentation.selected-paper-library/v0.1"
    : "reagent.artifact-presentation.selected-research-idea/v0.1";
  return {
    schema_version: "reagent.artifact-reference/v0.1",
    artifact_id: artifactId,
    project_id: projectId,
    producer_workflow_instance_id: workflowInstancesFixture.items[0].workflow_instance_id,
    producer_progress_receipt_id: "receipt-preview",
    producer_progress_report_id: `prv2-${"e".repeat(64)}`,
    producer_execution_round: 1,
    producer_capsule_id: `capsule-${"2".repeat(32)}`,
    producer_capsule_version: "0.6.0",
    producer_core_capability_maturity: "REVIEWED_CORE",
    artifact_type: type,
    artifact_schema_version: type,
    media_type: "application/json",
    state: "LOCAL_AVAILABLE",
    relative_path: "outputs/final.json",
    content_checksum: checksum,
    size_bytes: 100,
    cloud_metadata_available: true,
    produced_at: "2026-08-18T08:00:00Z",
    retired_at: null,
    created_at: "2026-08-18T08:00:00Z",
    updated_at: "2026-08-18T08:00:00Z",
    presentation: payload ? {
      schema_identity: schema,
      artifact_id: artifactId,
      artifact_checksum: checksum,
      presentation_checksum: "sha256:" + "f".repeat(64),
      payload: {
        schema, artifact_id: artifactId, artifact_checksum: checksum,
        ...payload, presentation_checksum: "sha256:" + "f".repeat(64),
      },
      reported_at: "2026-08-18T08:01:00Z",
    } : null,
  };
}

const paperPayload = {
  selected_count: 1,
  selection_status: "SELECTED",
  evidence_basis: ["METADATA_AND_ABSTRACT"],
  limitations: ["Full text is not represented."],
  papers_truncated: false,
  papers: [{
    title: "Bounded archival study",
    authors: ["Fictional Author"],
    year: 2024,
    identifier_kind: "DOI",
    identifier: "10.1000/fictional.1",
    why_selected: "Directly addresses the bounded research question.",
    evidence_availability: "METADATA_AND_ABSTRACT",
    limitation: "Abstract only; full text is not represented.",
  }],
};

const ideaPayload = {
  title: "Compare archival classification practices",
  summary: "Investigate how two practices shape categorical outcomes.",
  research_question: "Where do their categories diverge?",
  observed_gap: "The selected literature has no direct comparison.",
  proposed_direction: "Apply a bounded comparative protocol.",
  assumptions: ["The metadata is internally consistent."],
  risks: ["Full text is unavailable."],
  validation_needed: ["Confirm archival access."],
  literature_basis_count: 1,
};

test("paper and idea previews show bounded research content and limitations", () => {
  const { rerender } = render(<ArtifactPresentationPreview artifact={artifact("selected-paper-library/v1", "a", paperPayload)} />);
  expect(screen.getByRole("heading", { name: "Selected paper library" })).toBeVisible();
  expect(screen.getByText("Bounded archival study")).toBeVisible();
  expect(screen.getByText("10.1000/fictional.1")).toBeVisible();
  expect(screen.getByText(/Full text is not represented/)).toBeVisible();

  rerender(<ArtifactPresentationPreview artifact={artifact("selected-research-idea/v1", "b", ideaPayload)} />);
  expect(screen.getByRole("heading", { name: ideaPayload.title })).toBeVisible();
  expect(screen.getByText(ideaPayload.research_question)).toBeVisible();
  expect(screen.getByText("Risks and limitations")).toBeVisible();
});

test("presentation absence is truthful and does not block exact multi-candidate selection", async () => {
  const choices = [
    artifact("selected-paper-library/v1", "a", paperPayload),
    artifact("selected-paper-library/v1", "b"),
  ];
  vi.spyOn(apiClient, "listProjectArtifactReferences").mockResolvedValue({
    schema_version: "reagent.artifact-reference-page/v0.1",
    project_id: projectId,
    artifacts: choices,
    offset: 0, limit: 100, total: 2, has_more: false,
  });
  vi.spyOn(apiClient, "bindArtifactDependency").mockResolvedValue({} as never);
  const instance = workflowInstancesFixture.items[0];
  render(<Providers><WorkflowInputSetup
    projectId={projectId}
    instance={instance}
    instances={workflowInstancesFixture.items}
    projections={projectProgressFixture.instances}
    requirements={[{
      requirement_key: "literature_library",
      artifact_type: "selected-paper-library/v1",
      schema_constraint: "selected-paper-library/v1",
      required: true,
      target_relative_path: "inputs/selected-paper-library.json",
    }]}
    dependencies={[]}
  /></Providers>);

  const radios = await screen.findAllByRole("radio");
  expect(radios).toHaveLength(2);
  radios.forEach((radio) => expect(radio).not.toBeChecked());
  expect(screen.getByText("Bounded archival study")).toBeVisible();
  expect(screen.getByText("Preview not yet reported from Local Workspace.")).toBeVisible();
  expect(screen.getByRole("button", { name: "Confirm exact input" })).toBeDisabled();
  expect(screen.queryByText(/sha256:/)).not.toBeInTheDocument();
});
