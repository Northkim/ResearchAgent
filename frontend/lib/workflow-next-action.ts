import type {
  ArtifactDependencyEdge,
  ProjectWorkflowInstance,
  WorkflowInstanceProgress,
} from "@/types/api";

export type WorkflowNextActionCode =
  | "SETUP"
  | "SYNC"
  | "WAIT_FOR_UPSTREAM"
  | "SELECT_INPUT"
  | "MATERIALIZE"
  | "RUN"
  | "CONTINUE"
  | "REVIEW_RESULT"
  | "REVISE_MANUSCRIPT";

export interface WorkflowNextAction {
  code: WorkflowNextActionCode;
  title: string;
  description: string;
  priority: number;
}

export function deriveWorkflowNextAction({
  instance,
  progress,
  requiresInput,
  dependencies,
}: {
  instance: Pick<ProjectWorkflowInstance, "desired_state">;
  progress: WorkflowInstanceProgress | undefined;
  requiresInput: boolean;
  dependencies: ArtifactDependencyEdge[];
}): WorkflowNextAction {
  if (progress?.next_action) {
    const content: Record<string, [string, string, number]> = {
      SETUP: ["Set up your Local Workspace", "Open the supported Project setup instructions before creating and syncing the Local Workspace.", 5],
      SYNC: ["Set up or sync your Local Workspace", "Cloud has not confirmed the current local installation.", 10],
      WAIT_FOR_UPSTREAM: ["Complete an upstream workflow", `Required results are not available yet: ${(progress.missing_required_inputs ?? []).join(", ")}.`, 20],
      SELECT_INPUT: ["Select exact inputs", "Choose specific compatible results. ReAgent never selects the latest result implicitly.", 30],
      MATERIALIZE: ["Prepare selected inputs locally", "Materialize verified copies in the Local Workspace. The browser cannot verify local bytes.", 40],
      RUN: ["Run this Workflow locally", "Open the Local Workspace to start this independent Workflow.", 50],
      CONTINUE: ["Continue this Workflow", progress.latest_summary ?? "Continue from its saved local memory.", 60],
      REVIEW_RESULT: ["Review the latest result", "Inspect the immutable result and choose the next workflow explicitly.", 80],
      REVISE_MANUSCRIPT: ["Create a new Writing round", "Use this review and its source manuscript as explicit inputs to a new Writing instance.", 70],
    };
    const [title, description, priority] = content[progress.next_action];
    return { code: progress.next_action, title, description, priority };
  }
  if (instance.desired_state === "RETIRED") {
    return {
      code: "REVIEW_RESULT",
      title: "Review retained results",
      description: "This Workflow is retired, but its Progress and local research files remain available.",
      priority: 60,
    };
  }
  if (!progress || progress.installation_state === "UNKNOWN") {
    return {
      code: "SETUP",
      title: "Set up your Local Workspace",
      description: "Open the supported Project setup instructions before creating and syncing the Local Workspace.",
      priority: 5,
    };
  }
  if (progress.installation_state !== "ACKNOWLEDGED_CURRENT") {
    return {
      code: "SYNC",
      title: "Set up or sync your Local Workspace",
      description: "Download the setup file if this is your first visit; otherwise run local sync. Cloud has not confirmed the current local installation.",
      priority: 10,
    };
  }
  if (requiresInput && !dependencies.some((item) => item.state === "ACTIVE")) {
    return {
      code: "SELECT_INPUT",
      title: "Select a literature input",
      description: "Choose one specific completed Literature Search result before preparing Idea Discovery locally.",
      priority: 20,
    };
  }
  if (progress?.research_status === "COMPLETED") {
    return {
      code: "REVIEW_RESULT",
      title: "Review the latest result",
      description: "Research completion is separate from local installation and can be continued with a new explicit round.",
      priority: 60,
    };
  }
  if (progress && progress.report_count > 0) {
    return {
      code: "CONTINUE",
      title: "Continue this Workflow",
      description: progress.latest_summary ?? "Open the Local Workspace and continue from its saved memory.",
      priority: 40,
    };
  }
  if (requiresInput) {
    return {
      code: "MATERIALIZE",
      title: "Prepare the selected input locally",
      description: "Materialize the bound input explicitly, then run the Workflow. The browser cannot verify local files.",
      priority: 30,
    };
  }
  return {
    code: "RUN",
    title: "Run this Workflow locally",
    description: "Open the Local Workspace with Codex or Claude Code to start the next research round.",
    priority: 50,
  };
}
