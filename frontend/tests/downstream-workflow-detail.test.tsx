import { render, screen } from "@testing-library/react";
import { beforeEach, test, vi } from "vitest";

import { WorkflowDetail } from "@/components/workflow-detail";

import { localProjectFixture, projectProgressFixture, workflowInstancesFixture } from "./fixtures";

const hooks = vi.hoisted(() => ({
  useProject: vi.fn(), useProjectWorkflowInstances: vi.fn(), useProjectProgress: vi.fn(),
  useProjectArtifactReferences: vi.fn(), useCompatibleArtifactReferences: vi.fn(),
  useWorkflowDefinition: vi.fn(),
  useControlledLocalRunApproval: vi.fn(), useControlledLocalRunApprovalDecision: vi.fn(),
  useWorkflowInputSetup: vi.fn(), useConfirmWorkflowInputSetup: vi.fn(),
  useBindArtifactDependency: vi.fn(),
}));

vi.mock("@/api/hooks", () => hooks);

const artifactId = `artifact-${"d".repeat(32)}`;
const manuscriptId = `artifact-${"c".repeat(32)}`;

function state(instance: Record<string, unknown>, role: "INITIAL" | "REVIEW" | "REVISION") {
  const type = role === "REVIEW" ? "review-report/v3" : role === "REVISION" ? "manuscript-draft/v5" : "manuscript-draft/v4";
  return {
    ...projectProgressFixture.instances[0],
    workflow_instance_id: instance.workflow_instance_id,
    workflow_display_name: role === "REVIEW" ? "Review" : "Writing",
    friendly_instance_label: role === "REVISION" ? "Writing Revision" : role === "INITIAL" ? "Initial Writing" : "Review",
    instance_display_name: role,
    action: {
      ...projectProgressFixture.instances[0].action,
      stage: { code: "COMPLETED", label: "Completed" },
      attention_state: "COMPLETED",
      next_action: { surface: "NONE", code: "REVIEW_RESULT", label: "Review", description: "Review completed output" },
      latest_output: { label: role === "REVIEW" ? "Review report" : "Manuscript", artifact_id: artifactId, artifact_type: type, artifact_schema: type, checksum: `sha256:${"d".repeat(64)}`, produced_at: "2026-08-18T08:00:00Z", progress_round: 1, state: "PRODUCED" },
    },
  };
}

function artifact(role: "INITIAL" | "REVIEW" | "REVISION") {
  const type = role === "REVIEW" ? "review-report/v3" : role === "REVISION" ? "manuscript-draft/v5" : "manuscript-draft/v4";
  const schema = role === "REVIEW" ? "reagent.artifact-presentation.review-report/v0.1" : "reagent.artifact-presentation.manuscript-draft/v0.1";
  const payload = role === "REVIEW" ? {
    reviewed_manuscript: { artifact_id: manuscriptId, artifact_type: "manuscript-draft/v4", artifact_checksum: `sha256:${"c".repeat(64)}` },
    scope: "Claims and exact evidence.", status: "REVISION_REQUIRED", summary: "One bounded revision is required.",
    issues: [{ issue_id: "issue-1", severity: "MINOR", blocking: true, anchor: "Results", rationale: "State the limitation.", requested_revision: "Add the limitation." }],
    requested_revisions: ["Add the limitation."], unresolved_evidence_gaps: [], reproducibility_findings: [], limitations: ["Exact supplied evidence only."], owner_review_status: "APPROVED",
  } : {
    mode: role, title: role === "REVISION" ? "Revised bounded manuscript" : "Bounded manuscript", summary: "Reports exact bounded evidence.",
    sections: ["Results", "Limitations"], evidence_coverage: { claim_count: 1, supported_claim_count: 1, planned_claim_count: 0, unavailable_claim_count: 0 },
    result_availability: "AVAILABLE", limitations: ["The claim remains bounded."], owner_review_status: "APPROVED",
    changed_sections: role === "REVISION" ? ["Results"] : [], change_summary: role === "REVISION" ? "One issue addressed." : null,
    issue_dispositions: role === "REVISION" ? [{ issue_id: "issue-1", disposition: "ADDRESSED" }] : [], unresolved_issue_count: 0,
  };
  return {
    schema_version: "reagent.artifact-reference/v0.1", artifact_id: artifactId, project_id: localProjectFixture.project_id,
    producer_workflow_instance_id: "", producer_progress_receipt_id: "receipt", producer_progress_report_id: "report",
    producer_execution_round: 1, producer_capsule_id: `capsule-${"2".repeat(32)}`, producer_capsule_version: "0.7.0",
    producer_core_capability_maturity: "REVIEWED_CORE", artifact_type: type, artifact_schema_version: type, media_type: "application/json",
    state: "LOCAL_AVAILABLE", relative_path: "outputs/final.json", content_checksum: `sha256:${"d".repeat(64)}`, size_bytes: 100,
    cloud_metadata_available: true, produced_at: "2026-08-18T08:00:00Z", retired_at: null, created_at: "2026-08-18T08:00:00Z", updated_at: "2026-08-18T08:00:00Z",
    presentation: { schema_identity: schema, artifact_id: artifactId, artifact_checksum: `sha256:${"d".repeat(64)}`, presentation_checksum: `sha256:${"e".repeat(64)}`, payload: { schema, artifact_id: artifactId, artifact_checksum: `sha256:${"d".repeat(64)}`, ...payload, presentation_checksum: `sha256:${"e".repeat(64)}` }, reported_at: "2026-08-18T08:01:00Z" },
  };
}

function setup(role: "INITIAL" | "REVIEW" | "REVISION") {
  const instance = {
    ...workflowInstancesFixture.items[0],
    workflow_definition_id: role === "REVIEW" ? "review-local-experimental" : "writing-local-experimental",
    workflow_version: role === "REVIEW" ? "0.4.0" : role === "REVISION" ? "0.6.0" : "0.5.0",
    capsule_version: role === "REVIEW" ? "0.6.0" : role === "REVISION" ? "0.8.0" : "0.7.0",
    display_name: role === "REVISION" ? "Writing Revision" : role === "INITIAL" ? "Initial Writing" : "Review",
  };
  const exactArtifact = { ...artifact(role), producer_workflow_instance_id: instance.workflow_instance_id };
  const progress = {
    ...projectProgressFixture,
    instances: [state(instance, role)],
    dependency_edges: role === "REVIEW" ? [{ consumer_workflow_instance_id: instance.workflow_instance_id, requirement_key: "manuscript", artifact_id: manuscriptId, state: "ACTIVE" }] : [],
  };
  hooks.useProject.mockReturnValue({ data: localProjectFixture, isLoading: false, isError: false });
  hooks.useProjectWorkflowInstances.mockReturnValue({ data: { items: [instance], total: 1, manifest_revision: 1 }, isLoading: false, isError: false });
  hooks.useProjectProgress.mockReturnValue({ data: progress, isLoading: false, isError: false });
  hooks.useProjectArtifactReferences.mockReturnValue({ data: { artifacts: [exactArtifact] }, isLoading: false, isError: false });
  hooks.useWorkflowDefinition.mockReturnValue({ data: { description: "", versions: [{ version: instance.workflow_version, artifact_requirements: role === "REVIEW" ? [{ requirement_key: "manuscript", artifact_type: "manuscript-draft/v4", schema_constraint: "manuscript-draft/v4", required: true, target_relative_path: "inputs/manuscript.json" }] : [], resource_requirements: [] }] }, isLoading: false, isError: false });
  return instance;
}

beforeEach(() => vi.clearAllMocks());

beforeEach(() => {
  hooks.useCompatibleArtifactReferences.mockReturnValue({
    data: { artifacts: [] }, isLoading: false, isError: false,
  });
  hooks.useWorkflowInputSetup.mockReturnValue({
    data: null, isLoading: false, isError: false,
  });
  hooks.useConfirmWorkflowInputSetup.mockReturnValue({
    mutate: vi.fn(), isPending: false,
  });
  hooks.useBindArtifactDependency.mockReturnValue({
    mutate: vi.fn(), isPending: false,
  });
});

test("completed manuscript is primary and has no misleading Local command", () => {
  const instance = setup("INITIAL");
  render(<WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={instance.workflow_instance_id} />);
  expect(screen.getByRole("heading", { name: "Manuscript completed" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Bounded manuscript" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Continue in the Local Workspace" })).not.toBeInTheDocument();
});

test("Review evidence precedes the exact Start revision action", () => {
  const instance = setup("REVIEW");
  render(<WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={instance.workflow_instance_id} />);
  const issue = screen.getByText("State the limitation.");
  const action = screen.getByRole("button", { name: "Start manuscript revision" });
  expect(issue.compareDocumentPosition(action) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  const checksum = screen.getByText(/sha256:/);
  expect(checksum.closest("details")).toHaveClass("technical-details");
});

test("completed Revision preserves issue disposition without a Local command", () => {
  const instance = setup("REVISION");
  render(<WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={instance.workflow_instance_id} />);
  expect(screen.getByRole("heading", { name: "Revision completed" })).toBeVisible();
  expect(screen.getByText(/issue-1: addressed/)).toBeVisible();
  expect(screen.queryByText("One recommended command")).not.toBeInTheDocument();
});

test("Review keeps unresolved optional evidence visible until explicit continuation", () => {
  const instance = setup("REVIEW");
  const requiredBinding = {
    binding_id: `artifact-binding-${"1".repeat(32)}`,
    consumer_workflow_instance_id: instance.workflow_instance_id,
    requirement_key: "manuscript",
    artifact_id: manuscriptId,
    expected_checksum: `sha256:${"c".repeat(64)}`,
    state: "ACTIVE",
    producer_workflow_instance_id: `wfi-${"8".repeat(32)}`,
    artifact_type: "manuscript-draft/v4",
    artifact_schema_version: "manuscript-draft/v4",
    produced_at: "2026-08-18T08:00:00Z",
  };
  const completedState = state(instance, "REVIEW");
  const selecting = {
    ...completedState,
    action: {
    ...completedState.action,
    stage: { code: "INPUT_REVIEW", label: "Inputs need attention" },
    attention_state: "OWNER_ACTION_REQUIRED",
    next_action: { surface: "BROWSER", code: "SELECT_INPUT", label: "Choose input", description: "Resolve optional evidence." },
    latest_output: null,
    },
  };
  hooks.useProjectProgress.mockReturnValue({
    data: { ...projectProgressFixture, instances: [selecting], dependency_edges: [requiredBinding] },
    isLoading: false, isError: false,
  });
  hooks.useProjectArtifactReferences.mockReturnValue({
    data: { artifacts: [] }, isLoading: false, isError: false,
  });
  hooks.useWorkflowDefinition.mockReturnValue({
    data: { description: "", versions: [{
      version: instance.workflow_version,
      artifact_requirements: [
        { requirement_key: "manuscript", artifact_type: "manuscript-draft/v4", schema_constraint: "manuscript-draft/v4", required: true, target_relative_path: "inputs/manuscript.json" },
        { requirement_key: "research_idea", artifact_type: "selected-research-idea/v1", schema_constraint: "selected-research-idea/v1", required: false, target_relative_path: "inputs/idea.json" },
      ],
      resource_requirements: [],
    }] },
    isLoading: false, isError: false,
  });
  hooks.useWorkflowInputSetup.mockReturnValue({
    data: {
      schema_version: "reagent.workflow-input-setup-state/v0.1",
      project_id: localProjectFixture.project_id,
      consumer_workflow_instance_id: instance.workflow_instance_id,
      binding_set_checksum: `sha256:${"9".repeat(64)}`,
      missing_required_requirement_keys: [],
      omitted_optional_requirement_keys: ["research_idea"],
      decision_required: true,
      current_decision: null,
    },
    isLoading: false, isError: false,
  });

  render(<WorkflowDetail projectId={localProjectFixture.project_id} workflowInstanceId={instance.workflow_instance_id} />);

  expect(screen.getByText("Optional · Not selected")).toBeVisible();
  expect(screen.getByRole("button", { name: "Continue without optional evidence" })).toBeVisible();
  expect(screen.queryByText("Prepare verified local copies of the selected research inputs:")).not.toBeInTheDocument();
});
