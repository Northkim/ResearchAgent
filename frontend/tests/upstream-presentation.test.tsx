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

function artifact(type: string, suffix: string, payload?: Record<string, unknown>): CanonicalArtifactReference {
  const artifactId = `artifact-${suffix.repeat(32)}`;
  const checksum = `sha256:${suffix.repeat(64)}`;
  const schema = {
    "selected-paper-library/v1": "reagent.artifact-presentation.selected-paper-library/v0.1",
    "selected-research-idea/v1": "reagent.artifact-presentation.selected-research-idea/v0.1",
    "manuscript-draft/v4": "reagent.artifact-presentation.manuscript-draft/v0.1",
    "manuscript-draft/v5": "reagent.artifact-presentation.manuscript-draft/v0.1",
    "review-report/v3": "reagent.artifact-presentation.review-report/v0.1",
  }[type] ?? "reagent.artifact-presentation.experiment-record/v0.2";
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
  vi.spyOn(apiClient, "getWorkflowInputSetup").mockResolvedValue({
    schema_version: "reagent.workflow-input-setup-state/v0.1",
    project_id: projectId,
    consumer_workflow_instance_id: workflowInstancesFixture.items[0].workflow_instance_id,
    binding_set_checksum: `sha256:${"0".repeat(64)}`,
    missing_required_requirement_keys: ["literature_library"],
    omitted_optional_requirement_keys: [],
    decision_required: false,
    current_decision: null,
  });
  const instance = workflowInstancesFixture.items[0];
  const view = render(<Providers><WorkflowInputSetup
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
  expect(new Set(radios.map((radio) => radio.closest("label")?.getAttribute("data-artifact-id"))).size).toBe(2);
  radios.forEach((radio) => expect(radio).not.toBeChecked());
  expect(screen.getByText("Bounded archival study")).toBeVisible();
  expect(screen.getByText("Preview not yet reported from Local Workspace.")).toBeVisible();
  expect(screen.getByRole("button", { name: "Confirm exact input" })).toBeDisabled();
  expect(screen.queryByText(/sha256:/)).not.toBeInTheDocument();

  view.rerender(<Providers><WorkflowInputSetup
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
    dependencies={[{
      binding_id: `artifact-binding-${"7".repeat(32)}`,
      consumer_workflow_instance_id: instance.workflow_instance_id,
      requirement_key: "literature_library",
      artifact_id: choices[1].artifact_id,
      expected_checksum: choices[1].content_checksum,
      state: "ACTIVE",
      producer_workflow_instance_id: choices[1].producer_workflow_instance_id,
      artifact_type: choices[1].artifact_type,
      artifact_schema_version: choices[1].artifact_schema_version,
      produced_at: choices[1].produced_at,
    }]}
  /></Providers>);
  const accepted = await screen.findAllByRole("radio");
  expect(accepted[0]).not.toBeChecked();
  expect(accepted[1]).toBeChecked();
  expect(screen.getByRole("button", { name: "Confirm changed input" })).toBeDisabled();
});

test("manuscript and Review previews prioritize bounded content over identities", () => {
  const manuscript = {
    mode: "INITIAL", title: "A bounded manuscript", summary: "Reports one exact categorical observation.",
    sections: ["Introduction", "Results", "Limitations"],
    evidence_coverage: { claim_count: 2, supported_claim_count: 1, planned_claim_count: 0, unavailable_claim_count: 1 },
    result_availability: "AVAILABLE", limitations: ["The result is narrowly bounded."],
    owner_review_status: "APPROVED", changed_sections: [], change_summary: null,
    issue_dispositions: [], unresolved_issue_count: 0,
  };
  const { rerender } = render(<ArtifactPresentationPreview artifact={artifact("manuscript-draft/v4", "c", manuscript)} />);
  expect(screen.getByRole("heading", { name: manuscript.title })).toBeVisible();
  expect(screen.getByText(/1 supported/)).toBeVisible();
  expect(screen.getByText(/complete manuscript remains in the Local Workspace/)).toBeVisible();
  expect(screen.queryByText(/sha256:/)).not.toBeInTheDocument();

  const review = {
    reviewed_manuscript: { artifact_id: `artifact-${"c".repeat(32)}`, artifact_type: "manuscript-draft/v4", artifact_checksum: `sha256:${"c".repeat(64)}` },
    scope: "Claims and exact supporting evidence.", status: "REVISION_REQUIRED",
    summary: "One bounded revision is required.",
    issues: [{ issue_id: "issue-1", severity: "MINOR", blocking: true, anchor: "Results", rationale: "State the limitation.", requested_revision: "Add the retained limitation." }],
    requested_revisions: ["Add the retained limitation."], unresolved_evidence_gaps: [],
    reproducibility_findings: [], limitations: ["Exact supplied evidence only."], owner_review_status: "APPROVED",
  };
  rerender(<ArtifactPresentationPreview artifact={artifact("review-report/v3", "d", review)} />);
  expect(screen.getByText("One bounded revision is required.")).toBeVisible();
  expect(screen.getByText(/minor issue/)).toBeVisible();
  expect(screen.getAllByText("Add the retained limitation.").length).toBeGreaterThan(0);
});
