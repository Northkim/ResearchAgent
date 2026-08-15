"use client";

import Link from "next/link";
import type { WorkflowActionProjection } from "@/types/api";

import {
  useProject,
  useProjectProgress,
  useProjectWorkflowInstances,
  useWorkflowDefinitions,
} from "@/api/hooks";
import { formatDateTime } from "@/lib/format";

import { CopyCommand } from "./copy-command";
import { ErrorState, LoadingState } from "./query-state";
import { ProjectNavigation } from "./project-navigation";
import { WorkflowInputSetup } from "./workflow-input-setup";
import { WorkflowResourceSetup } from "./workflow-resource-setup";

type ActionPresentation = {
  attention: string;
  stage: string;
  task: string;
  reason: string;
  actionLabel: string;
};

function workflowKind(label: string | null): string {
  return (label ?? "workflow").toLocaleLowerCase();
}

function outputAction(action: WorkflowActionProjection): Pick<ActionPresentation, "stage" | "task" | "actionLabel"> {
  const output = (action.latest_output?.label ?? action.expected_output?.label ?? "output").toLocaleLowerCase();
  if (output.includes("paper library")) return { stage: "Literature review completed", task: "Review the selected papers", actionLabel: "View selected papers" };
  if (output.includes("research idea")) return { stage: "Idea discovery completed", task: "Review the selected research idea", actionLabel: "View selected idea" };
  if (output.includes("experiment")) return { stage: "Experiment completed", task: "Review the experiment result", actionLabel: "View experiment result" };
  if (output.includes("structured review")) return { stage: "Evidence audit completed", task: "Review the structured issues", actionLabel: "Review issues" };
  if (output.includes("revised manuscript")) return { stage: "Revision completed", task: "Review the revised manuscript", actionLabel: "View revised manuscript" };
  if (output.includes("manuscript")) return { stage: "Writing completed", task: "Review the manuscript draft", actionLabel: "View manuscript" };
  return { stage: action.stage.label, task: `Review ${output}`, actionLabel: "View output" };
}

function checkpointAction(workflowLabel: string | null, context: string): Pick<ActionPresentation, "stage" | "task" | "reason" | "actionLabel"> {
  const kind = workflowKind(workflowLabel);
  const normalized = context.toLocaleLowerCase();
  if (kind.includes("writing") && normalized.includes("revision")) {
    return { stage: "Revision review", task: "Review the revision plan", reason: "The revision plan is ready for your approval.", actionLabel: "Review revision plan" };
  }
  if (kind.includes("writing")) {
    return { stage: "Outline approval", task: "Review the writing outline", reason: "The evidence map and outline are ready.", actionLabel: "Review outline" };
  }
  if (kind.includes("experiment")) {
    return { stage: "Experiment plan approval", task: "Approve the experiment plan", reason: "The bounded experiment plan is ready for your approval.", actionLabel: "Approve plan" };
  }
  if (kind.includes("review")) {
    return { stage: "Evidence audit", task: "Review the structured issues", reason: "The evidence audit is ready for your review.", actionLabel: "Review issues" };
  }
  if (kind.includes("idea")) {
    return { stage: "Idea review", task: "Review the research idea", reason: "The selected research direction is ready for your review.", actionLabel: "Review idea" };
  }
  if (kind.includes("literature")) {
    return { stage: "Literature review", task: "Review the selected papers", reason: "The selected literature is ready for your review.", actionLabel: "Review papers" };
  }
  return { stage: "Review checkpoint", task: `Review the ${workflowLabel ?? "workflow"} checkpoint`, reason: "The current work is ready for your review.", actionLabel: "Review checkpoint" };
}

export function presentWorkflowAction(
  action: WorkflowActionProjection,
  workflowLabel: string | null,
  context = "",
): ActionPresentation {
  const kind = workflowLabel ?? "Workflow";
  const code = action.next_action.code;
  const attention = action.attention_state === "OWNER_ACTION_REQUIRED"
    ? "Needs your review"
    : action.attention_state === "ATTENTION_REQUIRED"
      ? code === "SYNC" ? "Local workspace needs syncing" : "Needs attention"
      : action.attention_state === "BLOCKED"
        ? "Blocked"
        : action.actor === "AGENT"
          ? "Agent working"
          : action.attention_state === "COMPLETED" ? "Completed" : "Ready";

  if (code === "SYNC") return {
    attention,
    stage: "Workspace sync",
    task: "Sync the local workspace",
    reason: "The local workspace is not up to date with this project.",
    actionLabel: "Sync workspace",
  };
  if (code === "WAIT_FOR_UPSTREAM") return {
    attention: "Missing required input",
    stage: "Waiting for input",
    task: "Provide the required research input",
    reason: "An upstream result is required before this workflow can continue.",
    actionLabel: "View workflow",
  };
  if (code === "SELECT_INPUT") return {
    attention: "Missing required input",
    stage: "Input selection",
    task: "Choose the required input",
    reason: "A compatible output is available and still needs to be selected.",
    actionLabel: "Choose input",
  };
  if (code === "MATERIALIZE") return {
    attention,
    stage: "Input preparation",
    task: "Prepare the workflow inputs",
    reason: "The selected inputs need to be copied into the local workspace.",
    actionLabel: "Prepare inputs",
  };
  if (code === "RUN") return {
    attention: "Ready to continue locally",
    stage: "Ready to run",
    task: `Run ${kind} locally`,
    reason: `${action.expected_output?.label ?? "The next output"} can now be produced in the local workspace.`,
    actionLabel: "Run locally",
  };
  if (code === "CONTINUE" && action.stage.code === "OWNER_APPROVAL") {
    return { attention, ...checkpointAction(workflowLabel, `${context} ${action.blocker?.message ?? ""}`) };
  }
  if (code === "CONTINUE") return {
    attention,
    stage: action.stage.label,
    task: `Continue ${kind} locally`,
    reason: action.attention_state === "BLOCKED"
      ? "Review the preserved local state before continuing this workflow."
      : "Continue from the work already saved in the local workspace.",
    actionLabel: `Continue ${kind}`,
  };
  if (code === "REVIEW_RESULT") {
    const output = outputAction(action);
    return { attention, ...output, reason: `${action.latest_output?.label ?? "The output"} is ready to view.` };
  }
  if (code === "REVISE_MANUSCRIPT") return {
    attention: "Needs your review",
    stage: "Revision planning",
    task: "Review the structured issues",
    reason: "The review is ready to guide the next manuscript revision.",
    actionLabel: "Review issues",
  };
  return {
    attention,
    stage: action.stage.label,
    task: action.stage.label,
    reason: action.blocker ? "This workflow needs attention before it can continue." : "No action is needed right now.",
    actionLabel: "View workflow",
  };
}

function workflowDescription(label: string, fallback?: string): string {
  const kind = label.toLocaleLowerCase();
  if (kind.includes("writing")) return "Draft a manuscript using the selected idea, literature, and any validated experiment results.";
  if (kind.includes("review")) return "Audit the manuscript's claims, evidence, citations, and limitations.";
  if (kind.includes("experiment")) return "Plan and run a bounded experiment from the selected research idea.";
  if (kind.includes("idea")) return "Develop a research direction from the selected literature.";
  if (kind.includes("literature")) return "Find and review relevant research literature.";
  return fallback ?? label;
}

function requirementLabel(value: string): string {
  const key = value.toLocaleLowerCase();
  if (key.includes("paper") || key.includes("literature")) return "Selected literature";
  if (key.includes("idea")) return "Selected research idea";
  if (key.includes("experiment")) return "Experiment result";
  if (key.includes("review")) return "Structured review";
  if (key.includes("manuscript")) return "Manuscript draft";
  return value.replaceAll("-", " ");
}

export function WorkflowActionPanel({
  action,
  workflowLabel,
  href,
  context,
}: {
  action: WorkflowActionProjection;
  workflowLabel: string | null;
  href?: string;
  context?: string;
}) {
  const presentation = presentWorkflowAction(action, workflowLabel, context);
  const panelReason = action.next_action.code === "CONTINUE"
    && action.stage.code === "OWNER_APPROVAL"
    && workflowKind(workflowLabel).includes("writing")
    ? "The evidence map and six-section outline are ready."
    : presentation.reason;
  return (
    <section className="current-action-panel" data-attention-state={action.attention_state} aria-labelledby="current-action-title">
      <div className="current-action-main">
        <p className="attention-copy">{presentation.attention}</p>
        <h2 id="current-action-title">{presentation.task}</h2>
        <p className="current-action-reason">{panelReason}</p>
        <p className="current-action-meta"><span>{workflowLabel ?? "Project"}</span><span>{presentation.stage}</span></p>
      </div>
      <aside className="current-action-next">
        <span>Next action</span>
        {href && action.next_action.surface !== "NONE" ? <Link href={href} className="button button-primary">{presentation.actionLabel}</Link> : null}
      </aside>
    </section>
  );
}

function localCommand(code: string, workflowInstanceId: string): string | null {
  if (code === "SYNC") return "python reagent_local.py sync .";
  if (code === "MATERIALIZE") return `python reagent_local.py artifact materialize . --workflow-instance ${workflowInstanceId}`;
  if (code === "RUN" || code === "CONTINUE") return `python reagent_local.py run . --workflow-instance ${workflowInstanceId}`;
  return null;
}

export function WorkflowDetail({ projectId, workflowInstanceId }: { projectId: string; workflowInstanceId: string }) {
  const project = useProject(projectId);
  const instances = useProjectWorkflowInstances(projectId);
  const progress = useProjectProgress(projectId, { workflowInstanceId });
  const catalog = useWorkflowDefinitions();

  if (project.isLoading || instances.isLoading || progress.isLoading || catalog.isLoading) {
    return <LoadingState label="Loading Workflow Detail" />;
  }
  if (project.isError || !project.data || instances.isError || !instances.data || progress.isError || !progress.data || catalog.isError || !catalog.data) {
    return <ErrorState title="Workflow Detail unavailable" />;
  }

  const instance = instances.data.items.find((item) => item.workflow_instance_id === workflowInstanceId);
  const state = progress.data.instances.find((item) => item.workflow_instance_id === workflowInstanceId);
  if (!instance || !state) return <ErrorState title="Workflow not found" />;
  const definition = catalog.data.items.find((item) => item.workflow_definition_id === instance.workflow_definition_id);
  const requirements = definition?.recommended_version?.artifact_requirements ?? [];
  const dependencies = progress.data.dependency_edges.filter((edge) => edge.consumer_workflow_instance_id === workflowInstanceId);
  const visibleRequirements = requirements.filter((requirement) => (
    requirement.required
    || requirement.artifact_type.toLocaleLowerCase().includes("experiment")
    || dependencies.some((edge) => edge.requirement_key === requirement.requirement_key && edge.state === "ACTIVE")
  ));
  const activity = progress.data.history.filter((report) => report.workflow_instance_id === workflowInstanceId).slice(0, 5);
  const command = localCommand(state.action.next_action.code, workflowInstanceId);
  const actionHref = state.action.next_action.surface === "BROWSER" && state.action.next_action.code === "SELECT_INPUT"
    ? "#inputs"
      : state.action.next_action.code === "REVIEW_RESULT"
        ? `/projects/${projectId}/outputs`
      : state.action.next_action.surface === "LOCAL" ? "#run-locally" : undefined;
  const presentation = presentWorkflowAction(state.action, state.workflow_display_name, state.latest_summary ?? "");

  return (
    <div className="page-stack workflow-detail-page">
      <p className="breadcrumb"><Link href={`/projects/${projectId}`}>{project.data.name}</Link><span>/</span><Link href={`/projects/${projectId}/workflows`}>Workflows</Link><span>/</span><strong>{state.friendly_instance_label ?? state.instance_display_name}</strong></p>
      <header className="workflow-detail-header">
        <div><p className="eyebrow">{state.workflow_display_name} workflow</p><h1>{state.friendly_instance_label ?? state.instance_display_name}</h1><p>{workflowDescription(state.workflow_display_name, definition?.description)}</p></div>
        <Link href={`/projects/${projectId}/workflows`} className="button button-ghost">All Workflows</Link>
      </header>
      <ProjectNavigation projectId={projectId} active="Workflows" />

      <WorkflowActionPanel action={state.action} workflowLabel={state.workflow_display_name} href={actionHref} context={state.latest_summary ?? ""} />

      <div className="workflow-support-grid">
        <section id="inputs" className="plain-section" aria-labelledby="workflow-inputs-title">
          <div className="section-heading"><h2 id="workflow-inputs-title">Inputs</h2></div>
          {visibleRequirements.length ? (
            <div className="input-readiness-list">
              {visibleRequirements.map((requirement) => {
                const bound = dependencies.find((edge) => edge.requirement_key === requirement.requirement_key && edge.state === "ACTIVE");
                return <div key={requirement.requirement_key}><div><strong>{requirementLabel(requirement.artifact_type)}</strong><small>{bound ? "Selected for this workflow" : requirement.required ? "Required before work can continue" : "Optional supporting input"}</small></div><span>{bound ? "Ready" : requirement.required ? "Missing" : "Optional · Not provided"}</span></div>;
              })}
            </div>
          ) : <p className="muted-copy">No upstream research input is required.</p>}
          {requirements.length && state.action.next_action.code === "SELECT_INPUT" ? (
            <WorkflowInputSetup projectId={projectId} instance={instance} instances={instances.data.items} projections={progress.data.instances} requirements={requirements} dependencies={dependencies} />
          ) : dependencies.length ? (
            <details className="secondary-control"><summary>Manage input bindings</summary><WorkflowInputSetup projectId={projectId} instance={instance} instances={instances.data.items} projections={progress.data.instances} requirements={requirements} dependencies={dependencies} /></details>
          ) : null}
        </section>

        <div className="workflow-support-column">
          <section className="workflow-output-section plain-section" aria-labelledby="workflow-output-title">
            <div className="section-heading"><h2 id="workflow-output-title">{state.action.latest_output ? "Latest output" : "Expected output"}</h2></div>
            <div className="output-highlight"><strong>{state.action.latest_output?.label ?? state.action.expected_output?.label ?? "No output declared"}</strong><p>{state.action.latest_output ? `Produced in round ${state.action.latest_output.progress_round}.` : "Produced after this workflow task is completed."}</p></div>
            <Link href={`/projects/${projectId}/outputs`} className="text-link">All outputs →</Link>
          </section>

          <section className="plain-section" aria-labelledby="workflow-activity-title">
            <div className="section-heading"><h2 id="workflow-activity-title">Recent activity</h2><Link href={`/projects/${projectId}/progress?workflow_instance_id=${encodeURIComponent(workflowInstanceId)}`} className="text-link">All activity →</Link></div>
            {activity.length ? <ol className="activity-list">{activity.slice(0, 2).map((report) => <li key={report.receipt_id}><div><strong>{presentation.stage}</strong><p>{presentation.reason}</p></div><time>{formatDateTime(report.received_at)}</time></li>)}</ol> : <p className="muted-copy">No activity has been reported yet.</p>}
          </section>
        </div>
      </div>

      {command ? (
        <details id="run-locally" className="run-local-details">
          <summary><span>Run locally</span><span>Show command</span></summary>
          <div><p>Copy this command into the local workspace. The browser does not run it or write research files.</p><CopyCommand command={command} label={`${presentation.actionLabel} command`} /></div>
        </details>
      ) : null}

      {(instance.resource_requirements ?? []).length ? <details className="secondary-control"><summary>Resources</summary><WorkflowResourceSetup projectId={projectId} instance={instance} requirements={instance.resource_requirements ?? []} /></details> : null}

      <details className="technical-details">
        <summary>Technical Details</summary>
        <dl>
          <div><dt>Workflow Instance</dt><dd><code>{workflowInstanceId}</code></dd></div>
          <div><dt>Definition</dt><dd><code>{instance.workflow_definition_id}@{instance.workflow_version}</code></dd></div>
          <div><dt>Capsule</dt><dd><code>{instance.capsule_id ?? "Not pinned"}@{instance.capsule_version ?? "—"}</code></dd></div>
          <div><dt>Core maturity</dt><dd>{state.core_capability_maturity.replaceAll("_", " ")}</dd></div>
          <div><dt>Desired / installed</dt><dd>{state.desired_state.replaceAll("_", " ")} / {state.installation_state.replaceAll("_", " ")}</dd></div>
          <div><dt>Readiness</dt><dd>{state.readiness?.replaceAll("_", " ") ?? "Unknown"}</dd></div>
          {requirements.map((requirement) => <div key={requirement.requirement_key}><dt>Input requirement</dt><dd><code>{requirement.requirement_key}</code></dd></div>)}
          {dependencies.map((dependency) => <div key={dependency.requirement_key}><dt>Bound Artifact</dt><dd><code>{dependency.artifact_id}</code></dd></div>)}
          {state.action.latest_output ? <div><dt>Output checksum</dt><dd><code>{state.action.latest_output.checksum}</code></dd></div> : null}
        </dl>
      </details>
    </div>
  );
}
