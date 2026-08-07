import { describe, expect, test } from "vitest";

import { deriveWorkflowNextAction } from "@/lib/workflow-next-action";
import type { ArtifactDependencyEdge } from "@/types/api";

import { projectProgressFixture, workflowInstancesFixture } from "./fixtures";

const instance = workflowInstancesFixture.items[0];
const progress = projectProgressFixture.instances[0];
const dependency: ArtifactDependencyEdge = {
  binding_id: `artifact-binding-${"1".repeat(32)}`,
  consumer_workflow_instance_id: instance.workflow_instance_id,
  requirement_key: "paper_library",
  artifact_id: `artifact-${"2".repeat(32)}`,
  expected_checksum: `sha256:${"3".repeat(64)}`,
  state: "ACTIVE",
  producer_workflow_instance_id: `wfi-${"4".repeat(32)}`,
  artifact_type: "selected-paper-library/v1",
  artifact_schema_version: "selected-paper-library/v1",
  produced_at: "2026-08-07T00:00:00Z",
};

describe("derived Workflow next actions", () => {
  test("prioritizes local sync before research actions", () => {
    expect(deriveWorkflowNextAction({
      instance,
      progress: { ...progress, installation_state: "STALE", research_status: "NOT_STARTED", report_count: 0 },
      requiresInput: false,
      dependencies: [],
    }).code).toBe("SYNC");
  });

  test("requires explicit input selection and then local preparation", () => {
    const base = { ...progress, installation_state: "ACKNOWLEDGED_CURRENT", research_status: "NOT_STARTED", report_count: 0 };
    expect(deriveWorkflowNextAction({
      instance, progress: base, requiresInput: true, dependencies: [],
    }).code).toBe("SELECT_INPUT");
    expect(deriveWorkflowNextAction({
      instance, progress: base, requiresInput: true, dependencies: [dependency],
    }).code).toBe("MATERIALIZE");
  });

  test("separates first run, continuation, and result review", () => {
    const installed = { ...progress, installation_state: "ACKNOWLEDGED_CURRENT" };
    expect(deriveWorkflowNextAction({
      instance,
      progress: { ...installed, research_status: "NOT_STARTED", report_count: 0 },
      requiresInput: false,
      dependencies: [],
    }).code).toBe("RUN");
    expect(deriveWorkflowNextAction({
      instance,
      progress: { ...installed, research_status: "IN_PROGRESS", report_count: 1 },
      requiresInput: false,
      dependencies: [],
    }).code).toBe("CONTINUE");
    expect(deriveWorkflowNextAction({
      instance,
      progress: { ...installed, research_status: "COMPLETED", report_count: 1 },
      requiresInput: false,
      dependencies: [],
    }).code).toBe("REVIEW_RESULT");
  });
});
