"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import type {
  CanonicalArtifactReference,
  LocalProject,
  ProjectProgress,
  ProjectWorkflowInstance,
  WorkflowActionProjection,
  WorkflowArtifactRequirement,
  WorkflowInstanceProgress,
  WorkflowResourceRequirement,
} from "@/types/api";

import {
  useControlledLocalRunApproval,
  useControlledLocalRunApprovalDecision,
  useProject,
  useProjectProgress,
  useProjectArtifactReferences,
  useProjectWorkflowInstances,
  useWorkflowDefinition,
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
      ? code === "SETUP" ? "Local workspace not set up" : code === "SYNC" ? "Local workspace needs syncing" : "Needs attention"
      : action.attention_state === "BLOCKED"
        ? "Blocked"
        : action.actor === "AGENT"
          ? "Agent working"
          : action.attention_state === "COMPLETED" ? "Completed" : "Ready";

  if (code === "SETUP") return {
    attention,
    stage: "Local workspace setup",
    task: "Set up local workspace",
    reason: "Create the local workspace before starting research.",
    actionLabel: "Set up local workspace",
  };
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
  if (code === "SELECT_RESOURCE") return {
    attention: "Experiment Package source needed",
    stage: "Package source setup",
    task: "Choose the Experiment Package source",
    reason: "Register or choose the exact GitHub source for the local Experiment Package before staging it.",
    actionLabel: "Choose package source",
  };
  if (code === "STAGE_RESOURCE") return {
    attention: "Local resource preparation required",
    stage: "Resource staging",
    task: "Stage and verify the Experiment Package",
    reason: "Cloud knows the exact binding; the Local Workspace must verify the package bytes before execution.",
    actionLabel: "View staging instructions",
  };
  if (code === "RUN") return {
    attention: "Ready to continue locally",
    stage: "Ready to run",
    task: `${kind} is ready`,
    reason: `Run ${kind} in your Local Workspace to produce ${action.expected_output?.label?.toLocaleLowerCase() ?? "the next output"}.`,
    actionLabel: "View run instructions",
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
  revealLocalInstructions,
  instructionsExpanded,
}: {
  action: WorkflowActionProjection;
  workflowLabel: string | null;
  href?: string;
  context?: string;
  revealLocalInstructions?: () => void;
  instructionsExpanded?: boolean;
}) {
  const basePresentation = presentWorkflowAction(action, workflowLabel, context);
  const presentation = action.next_action.code === "RUN" && revealLocalInstructions
    ? {
        ...basePresentation,
        task: `Run ${workflowLabel ?? "this Workflow"} in your Local Workspace`,
        reason: "This step runs from the Local Workspace on your machine.",
        actionLabel: "Show run instructions",
      }
    : basePresentation;
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
        {revealLocalInstructions ? (
          <button
            type="button"
            className="button button-primary"
            aria-controls="run-locally"
            aria-expanded={instructionsExpanded}
            onClick={revealLocalInstructions}
          >
            {presentation.actionLabel}
          </button>
        ) : href && action.next_action.surface !== "NONE" ? <Link href={href} className="button button-primary">{presentation.actionLabel}</Link> : null}
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

type ExperimentPresentationBlock = {
  kind: "PROSE" | "SCALAR" | "TABLE" | "SERIES" | "FIGURE_REFERENCE" | "OUTPUT_REFERENCE";
  label: string;
  value: unknown;
};

type ExperimentPresentation = {
  schema_identity: string;
  artifact_id: string;
  artifact_checksum: string;
  presentation_checksum: string;
  payload: {
    schema: string;
    artifact_id: string;
    artifact_checksum: string;
    blocks: ExperimentPresentationBlock[];
    presentation_checksum: string;
  };
  reported_at: string;
};

type PresentedArtifact = CanonicalArtifactReference & {
  presentation?: ExperimentPresentation | null;
};

function experimentPresentation(artifact: CanonicalArtifactReference | undefined): ExperimentPresentation | null {
  const value = (artifact as PresentedArtifact | undefined)?.presentation;
  if (
    !value
    || value.schema_identity !== "reagent.artifact-presentation.experiment-record/v0.2"
    || value.artifact_id !== artifact?.artifact_id
    || value.artifact_checksum !== artifact.content_checksum
    || value.payload?.presentation_checksum !== value.presentation_checksum
    || !Array.isArray(value.payload?.blocks)
  ) return null;
  return value;
}

function blockValue(blocks: ExperimentPresentationBlock[], label: string): string | null {
  const block = blocks.find((item) => item.label.toLocaleLowerCase() === label.toLocaleLowerCase());
  if (!block || !["string", "number", "boolean"].includes(typeof block.value)) return null;
  return String(block.value);
}

function statusText(value: string | null, fallback: string): string {
  return value?.replaceAll("_", " ") ?? fallback;
}

function PresentationBlockView({ block }: { block: ExperimentPresentationBlock }) {
  if (block.kind === "PROSE") return <section className="plain-section"><h3>{block.label}</h3><p>{String(block.value)}</p></section>;
  if (block.kind === "SCALAR") return <dl className="input-readiness-list"><div><div><strong>{block.label}</strong></div><span>{String(block.value ?? "Not reported")}</span></div></dl>;
  if (block.kind === "TABLE" && block.value && typeof block.value === "object") {
    const table = block.value as { columns?: unknown[]; rows?: unknown[][] };
    const columns = Array.isArray(table.columns) ? table.columns : [];
    const rows = Array.isArray(table.rows) ? table.rows : [];
    return <section className="plain-section"><h3>{block.label}</h3><div style={{ overflowX: "auto" }} tabIndex={0}><table><thead><tr>{columns.map((column, index) => <th key={index} scope="col">{String(column)}</th>)}</tr></thead><tbody>{rows.map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, cellIndex) => <td key={cellIndex}>{String(cell ?? "—")}</td>)}</tr>)}</tbody></table></div></section>;
  }
  if (block.kind === "SERIES" && Array.isArray(block.value)) {
    const points = block.value as { x: unknown; y: unknown }[];
    const numeric = points.every((point) => typeof point.y === "number" && Number.isFinite(point.y));
    const values = numeric ? points.map((point) => Number(point.y)) : [];
    const minimum = values.length ? Math.min(...values) : 0;
    const maximum = values.length ? Math.max(...values) : 1;
    const span = maximum - minimum || 1;
    const polyline = values.map((value, index) => `${10 + (index * 280) / Math.max(1, values.length - 1)},${90 - ((value - minimum) * 70) / span}`).join(" ");
    return <figure className="plain-section"><figcaption><h3>{block.label}</h3></figcaption>{numeric ? <svg viewBox="0 0 300 100" role="img" aria-label={`${block.label} series chart`} style={{ maxWidth: 520, width: "100%" }}><polyline points={polyline} fill="none" stroke="currentColor" strokeWidth="3" /></svg> : null}<details><summary>View chart data</summary><div style={{ overflowX: "auto" }}><table><thead><tr><th scope="col">Point</th><th scope="col">Value</th></tr></thead><tbody>{points.map((point, index) => <tr key={index}><td>{String(point.x)}</td><td>{String(point.y)}</td></tr>)}</tbody></table></div></details></figure>;
  }
  return <section className="plain-section"><h3>{block.label}</h3><p>Validated {block.kind === "FIGURE_REFERENCE" ? "figure" : "output"} reference available. Local research bytes remain in the Workspace.</p></section>;
}

export function ExperimentPresentationView({ artifact }: { artifact: CanonicalArtifactReference }) {
  const presentation = experimentPresentation(artifact);
  if (!presentation) return <section className="plain-section"><h3>Experiment result</h3><p>Local result presentation has not yet been reported.</p></section>;
  return <div className="page-stack" aria-label="Experiment result presentation">{presentation.payload.blocks.map((block, index) => <PresentationBlockView key={`${block.label}-${index}`} block={block} />)}</div>;
}

const EXPERIMENT_CHECKPOINTS = {
  METHODOLOGY_DECISION_REQUIRED: {
    title: "ReAgent needs your decision",
    explanation: "A scientific choice must be resolved before the experiment design can continue.",
    action: "Review methodology",
    section: "design",
  },
  CAPABILITY_SELECTION_REQUIRED: {
    title: "Choose how ReAgent should prepare the experiment",
    explanation: "More than one scientifically meaningful preparation method is available.",
    action: "Review preparation methods",
    section: "preparation",
  },
  DESIGN_APPROVAL_REQUIRED: {
    title: "Experiment design ready for review",
    explanation: "Review and approve the scientific design before ReAgent prepares the implementation.",
    action: "Approve experiment design",
    section: "design",
  },
  RESOURCE_READINESS_REQUIRED: {
    title: "A research resource is needed",
    explanation: "One or more research resources must be resolved before ReAgent can prepare the experiment.",
    action: "Resolve research resources",
    section: "resources",
  },
  PREPARATION_REQUIREMENT_UNMET: {
    title: "A preparation prerequisite is missing",
    explanation: "This computer is missing something ReAgent needs to prepare the experiment.",
    action: "Review preparation requirements",
    section: "preparation",
  },
  PREPARATION_COMPLETE: {
    title: "Experiment implementation prepared",
    explanation: "The durable local preparation checkpoint has been reported.",
    action: "Review preparation",
    section: "preparation",
  },
  RUNTIME_INCOMPATIBLE: {
    title: "No compatible execution environment is ready",
    explanation: "A compatible local execution environment is needed before this experiment can run.",
    action: "Review execution environment",
    section: "runtime",
  },
  RUN_APPROVAL_REQUIRED: {
    title: "Experiment ready for approval",
    explanation: "Review the exact prepared run before authorizing one local execution attempt.",
    action: "Approve this run",
    section: "run",
  },
  RESULT_REVIEW_REQUIRED: {
    title: "Experiment result ready for review",
    explanation: "Review the scientific result and its limitations before finalizing.",
    action: "Review result",
    section: "results",
  },
} as const;

type ExperimentCheckpoint = keyof typeof EXPERIMENT_CHECKPOINTS;

function experimentCheckpoint(state: WorkflowInstanceProgress): ExperimentCheckpoint | null {
  const source = `${state.latest_summary ?? ""} ${state.next_recommended_action ?? ""}`;
  return (Object.keys(EXPERIMENT_CHECKPOINTS) as ExperimentCheckpoint[])
    .find((code) => source.includes(code)) ?? null;
}

function ownerSafeDetail(value: string | null | undefined): string | null {
  if (!value) return null;
  let result = value;
  for (const code of Object.keys(EXPERIMENT_CHECKPOINTS)) {
    result = result.replaceAll(code, "");
  }
  result = result
    .replaceAll("AUTOMATIC_PREPARATION_UNSUPPORTED", "")
    .replaceAll("APPROVAL_INVALIDATED", "")
    .replace(/sha256:[0-9a-f]{64}/gi, "")
    .replace(/^\s*[:—-]\s*/, "")
    .trim();
  return result || null;
}

function approvalOwnerError(error: unknown): string {
  const code = (error as { code?: string } | null)?.code;
  if (code === "APPROVAL_SUPERSEDED" || code === "APPROVAL_IDENTITY_MISMATCH" || code === "APPROVAL_INVALIDATED") {
    return "The prepared experiment changed after approval. Review the updated experiment before continuing.";
  }
  if (code === "APPROVAL_REJECTED") return "Changes have already been requested for this run.";
  if (code === "APPROVAL_NOT_REQUESTED") return "This approval request is no longer waiting for a decision.";
  return "ReAgent could not record this decision. Refresh the page and review the current run before trying again.";
}

function SummaryList({ label, values }: { label: string; values: string[] }) {
  if (!values.length) return null;
  return <div><div><strong>{label}</strong><small>{values.join(" · ")}</small></div><span>Reported</span></div>;
}

function GenericExperimentDetail({
  project,
  instance,
  state,
  progress,
  requirements,
  resourceRequirements,
}: {
  project: LocalProject;
  instance: ProjectWorkflowInstance;
  state: WorkflowInstanceProgress;
  progress: ProjectProgress;
  requirements: WorkflowArtifactRequirement[];
  resourceRequirements: WorkflowResourceRequirement[];
}) {
  const [pathASelected, setPathASelected] = useState(state.report_count > 0);
  const approvalProjection = useControlledLocalRunApproval(project.project_id, instance.workflow_instance_id);
  const approvalDecision = useControlledLocalRunApprovalDecision(project.project_id, instance.workflow_instance_id);
  const artifacts = useProjectArtifactReferences(project.project_id, "experiment-record/v4");
  const artifact = artifacts.data?.artifacts.find((item) => item.producer_workflow_instance_id === instance.workflow_instance_id);
  const presentation = experimentPresentation(artifact);
  const blocks = presentation?.payload.blocks ?? [];
  const checkpoint = experimentCheckpoint(state);
  const checkpointPresentation = checkpoint ? EXPERIMENT_CHECKPOINTS[checkpoint] : null;
  const checkpointDetail = ownerSafeDetail(state.latest_summary);
  const approvalRequest = approvalProjection.data?.request ?? null;
  const approvalStatus = approvalRequest?.status ?? null;
  const runSummary = approvalRequest?.summary;
  const ideaBinding = progress.dependency_edges.find((edge) => edge.consumer_workflow_instance_id === instance.workflow_instance_id && edge.artifact_type === "selected-research-idea/v1");
  const ideaProducer = progress.instances.find((item) => item.workflow_instance_id === ideaBinding?.producer_workflow_instance_id);
  const objective = blockValue(blocks, "Research objective") ?? ideaProducer?.latest_summary ?? project.research_topic;
  const unsupported = /AUTOMATIC_PREPARATION_UNSUPPORTED|cannot prepare this experiment automatically/i.test(state.latest_summary ?? "");
  const methodologyDecision = checkpoint === "METHODOLOGY_DECISION_REQUIRED";
  const designCheckpoint = checkpoint === "DESIGN_APPROVAL_REQUIRED";
  const capabilityCheckpoint = checkpoint === "CAPABILITY_SELECTION_REQUIRED";
  const resourceCheckpoint = checkpoint === "RESOURCE_READINESS_REQUIRED";
  const preparationRequirementCheckpoint = checkpoint === "PREPARATION_REQUIREMENT_UNMET";
  const runtimeCheckpoint = checkpoint === "RUNTIME_INCOMPATIBLE";
  const runCheckpoint = checkpoint === "RUN_APPROVAL_REQUIRED" || approvalRequest !== null;
  const resultReviewCheckpoint = checkpoint === "RESULT_REVIEW_REQUIRED" || state.action.next_action.code === "REVIEW_RESULT";
  const lifecyclePastPreparation = checkpoint === "PREPARATION_COMPLETE"
    || runtimeCheckpoint || runCheckpoint || resultReviewCheckpoint || Boolean(artifact);
  const lifecyclePastResources = preparationRequirementCheckpoint || lifecyclePastPreparation;
  const capability = runSummary?.preparation_method
    ?? blockValue(blocks, "Preparation method")
    ?? "Reviewed preparation method selected from the compatible installed set";
  const executionOutcome = blockValue(blocks, "Process outcome") ?? (artifact ? "Completed" : "Not run");
  const evaluationValidity = blockValue(blocks, "Evaluation validity") ?? (artifact ? "Not reported" : "Pending execution");
  const evidenceStatus = blockValue(blocks, "Scientific evidence status") ?? (artifact ? "Not reported" : "Pending evaluation");
  const command = `python reagent_local.py run . --workflow-instance ${instance.workflow_instance_id}`;
  const decisionPending = approvalDecision.isPending;
  const approvalError = approvalDecision.isError ? approvalOwnerError(approvalDecision.error) : null;
  const localReason = approvalStatus === "APPROVED"
    ? "The exact run is approved and ready to continue locally."
    : approvalStatus === "CONSUMED"
      ? "The one-use approval has been consumed for this local execution."
      : approvalStatus === "SUPERSEDED"
        ? "The prepared experiment changed. Review the updated run before continuing."
        : approvalStatus === "REJECTED"
          ? "Changes were requested. Continue locally after the experiment has been revised."
          : runCheckpoint
            ? "Review and approve the exact run first."
            : "Local action is required because concrete research files and execution stay in the Local Workspace.";

  return <div className="page-stack workflow-detail-page">
    <p className="breadcrumb"><Link href={`/projects/${project.project_id}`}>{project.name}</Link><span>/</span><Link href={`/projects/${project.project_id}/workflows`}>Workflows</Link><span>/</span><strong>Reproduction &amp; Experiment</strong></p>
    <header className="workflow-detail-header"><div><p className="eyebrow">Reproduction &amp; Experiment</p><h1>Prepare and run an experiment</h1><p>Turn an exact research objective into a reproducible local computational experiment.</p></div><Link href={`/projects/${project.project_id}/workflows`} className="button button-ghost">All Workflows</Link></header>
    <ProjectNavigation projectId={project.project_id} active="Workflows" />

    <section className="plain-section" aria-labelledby="research-objective-title"><p className="eyebrow">Research objective</p><h2 id="research-objective-title">{objective}</h2><p>{objective}</p><p className="muted-copy">Source · Selected research idea · exact version recorded</p>{ideaProducer ? <Link className="text-link" href={`/projects/${project.project_id}/workflows/${ideaProducer.workflow_instance_id}`}>View research idea →</Link> : null}</section>

    <section className="plain-section" aria-labelledby="experiment-start-title"><p className="eyebrow">Start</p><h2 id="experiment-start-title">How would you like to start?</h2><div className="workflow-support-grid">
      <article className="output-highlight"><p className="attention-copy">Recommended</p><h3>Prepare a new experiment with ReAgent</h3><p>ReAgent will help turn the research objective into a reproducible local experiment. No existing code or Git repository is required.</p><button type="button" className="button button-primary" aria-pressed={pathASelected} onClick={() => setPathASelected(true)}>{pathASelected ? "Selected" : "Choose this path"}</button></article>
      <article className="output-highlight"><p className="attention-copy">Coming next</p><h3>Use an existing local project</h3><p>Start from research code or files already on this computer. Git is optional.</p><button type="button" className="button button-ghost" disabled>Not available in this build</button></article>
    </div></section>

    {pathASelected ? <>
      <section className="plain-section" aria-labelledby="experiment-design-title"><p className="eyebrow">Experiment design</p><h2 id="experiment-design-title">What ReAgent understands</h2><p>{checkpointPresentation?.section === "design" ? checkpointPresentation.explanation : checkpointDetail ?? "Continue locally so ReAgent can recover the scientific design without assuming a particular research domain."}</p><div className="input-readiness-list">{["Questions or hypotheses", "Inputs or materials", "Protocol", "Observations or expected outputs", "Evaluation criteria", "Reproducibility controls", "Resource constraints", "Compute constraints", "Network policy", "Assumptions", "Claim boundaries"].map((label) => <div key={label}><div><strong>{label}</strong><small>{blockValue(blocks, label) ?? "Recorded when the methodology checkpoint is reported."}</small></div><span>{blockValue(blocks, label) ? "Recorded" : "Pending"}</span></div>)}</div>{designCheckpoint ? <div><p><strong>Approve experiment design</strong></p><p>This approves the scientific design so ReAgent can prepare the implementation. It does not run the experiment.</p><a className="button button-primary" href="#local-workflow">Approve experiment design</a></div> : null}</section>

      {methodologyDecision || capabilityCheckpoint || designCheckpoint ? <section className="current-action-panel" data-attention-state="OWNER_ACTION_REQUIRED"><div className="current-action-main"><p className="attention-copy">Needs your attention</p><h2>{checkpointPresentation?.title}</h2><p>{checkpointPresentation?.explanation}</p>{checkpointDetail && checkpointDetail !== checkpointPresentation?.explanation ? <p>{checkpointDetail}</p> : null}</div><aside className="current-action-next"><span>Next action</span><a className="button button-primary" href="#local-workflow">{checkpointPresentation?.action}</a></aside></section> : null}

      {unsupported ? <section className="plain-section"><h2>ReAgent cannot prepare this experiment automatically yet.</h2><p>The research design is preserved. You can revise the experiment design, keep the current work and return later, or use an existing local project when that capability becomes available.</p></section> : null}

      <section className="plain-section" aria-labelledby="preparation-title"><p className="eyebrow">Preparation</p><h2 id="preparation-title">How ReAgent will prepare this experiment</h2>{checkpointPresentation && ["resources", "preparation", "runtime"].includes(checkpointPresentation.section) ? <div className="output-highlight"><p className="attention-copy">{checkpoint === "PREPARATION_COMPLETE" ? "Ready" : "Needs attention"}</p><h3>{checkpointPresentation.title}</h3><p>{checkpointPresentation.explanation}</p></div> : null}<div className="input-readiness-list">
        <div><div><strong>Preparation method</strong><small>{capability}</small></div><span>{unsupported ? "Unsupported" : capabilityCheckpoint ? "Needs your decision" : "Reviewed"}</span></div>
        {resourceCheckpoint ? <div><div><strong>Research resources</strong><small>{checkpointDetail ?? EXPERIMENT_CHECKPOINTS.RESOURCE_READINESS_REQUIRED.explanation}</small></div><span>Needs attention</span></div> : resourceRequirements.length ? resourceRequirements.map((requirement) => <div key={requirement.requirement_key}><div><strong>Research resources</strong><small>{requirement.usage_description}</small></div><span>{lifecyclePastResources ? "Ready" : requirement.required ? "Needs a source" : "Optional"}</span></div>) : null}
        {preparationRequirementCheckpoint ? <div><div><strong>What ReAgent needs to prepare</strong><small>{checkpointDetail ?? EXPERIMENT_CHECKPOINTS.PREPARATION_REQUIREMENT_UNMET.explanation}</small></div><span>Needs attention</span></div> : null}
        <div><div><strong>Implementation preparation</strong><small>{checkpoint === "PREPARATION_COMPLETE" ? checkpointDetail ?? "The experiment implementation is prepared." : "ReAgent owns the managed Workflow-local preparation area."}</small></div><span>{lifecyclePastPreparation ? "Implementation prepared" : "Not yet prepared"}</span></div>
        {approvalRequest ? <div><div><strong>Package validation</strong><small>The exact validated package was reported with this approval request.</small></div><span>Package validated</span></div> : null}
        <div><div><strong>Execution environment</strong><small>{runtimeCheckpoint ? checkpointDetail ?? "No compatible execution environment is ready." : runSummary?.execution_environment ?? "Runtime details remain local and are checked only when relevant."}</small></div><span>{runtimeCheckpoint ? "Needs attention" : runSummary ? "Compatible environment reported" : lifecyclePastPreparation ? "Ready for local check" : "Checked after preparation"}</span></div>
      </div></section>

      {runCheckpoint ? <section className="plain-section" aria-labelledby="exact-run-title"><p className="eyebrow">Ready to run</p><h2 id="exact-run-title">Exact run summary</h2>{runSummary ? <div className="input-readiness-list">
        <div><div><strong>What will run</strong><small>{runSummary.what_will_run}</small></div><span>Exact prepared run</span></div>
        <div><div><strong>Research objective</strong><small>{runSummary.research_objective}</small></div><span>Exact input</span></div>
        <div><div><strong>Preparation method</strong><small>{runSummary.preparation_method}</small></div><span>Reviewed</span></div>
        <SummaryList label="Research resources" values={runSummary.research_resources} />
        <div><div><strong>Execution environment</strong><small>{runSummary.execution_environment}</small></div><span>Reported locally</span></div>
        <div><div><strong>Network policy</strong><small>{runSummary.network_policy === "DISABLED" ? "Network disabled" : "Bounded declared network access"}</small></div><span>Bounded</span></div>
        <SummaryList label="Compute and runtime limits" values={runSummary.compute_limits} />
        <SummaryList label="Expected outputs" values={runSummary.expected_outputs} />
        <div><div><strong>Evaluation approach</strong><small>{runSummary.evaluation_approach}</small></div><span>Declared</span></div>
        <SummaryList label="Important assumptions" values={runSummary.important_assumptions} />
        <SummaryList label="Important limitations" values={runSummary.important_limitations} />
      </div> : <p>The exact run summary has not yet been reported from Local Workspace.</p>}
      {approvalStatus === "REQUESTED" ? <div className="current-action-panel" data-attention-state="OWNER_ACTION_REQUIRED"><div className="current-action-main"><p className="attention-copy">Experiment ready for approval</p><h3>Approve this exact prepared experiment</h3><p>This approves this exact prepared experiment for one local execution attempt. The browser records authorization; it does not start the local process.</p>{approvalError ? <p role="alert" className="attention-copy">{approvalError}</p> : null}</div><aside className="current-action-next"><span>Next action</span><button type="button" className="button button-primary" disabled={decisionPending} onClick={() => approvalRequest && approvalDecision.mutate({ request: approvalRequest, decision: "approve" })}>{decisionPending ? "Recording approval…" : "Approve this run"}</button><button type="button" className="button button-ghost" disabled={decisionPending} onClick={() => approvalRequest && approvalDecision.mutate({ request: approvalRequest, decision: "reject" })}>Request changes</button></aside></div> : null}
      {approvalStatus === "APPROVED" ? <div className="current-action-panel" data-attention-state="NORMAL"><div className="current-action-main"><p className="attention-copy">Run approved</p><h3>This exact experiment is approved for one local execution.</h3><p>The Local Workflow will verify that the experiment has not changed, consume this one-use approval, and execute through the controlled local runner.</p></div><aside className="current-action-next"><span>Next action</span><a className="button button-primary" href="#local-workflow">Continue in Local Workspace</a></aside></div> : null}
      {approvalStatus === "REJECTED" ? <div className="current-action-panel" data-attention-state="OWNER_ACTION_REQUIRED"><div className="current-action-main"><p className="attention-copy">Changes requested</p><h3>This run is not approved.</h3><p>Revise the prepared experiment locally before requesting approval again.</p></div></div> : null}
      {approvalStatus === "SUPERSEDED" ? <div className="current-action-panel" data-attention-state="OWNER_ACTION_REQUIRED"><div className="current-action-main"><p className="attention-copy">The experiment changed</p><h3>Review the updated run.</h3><p>The prepared experiment changed after this approval request. Review the updated experiment before continuing.</p></div></div> : null}
      {approvalStatus === "CONSUMED" ? <div className="current-action-panel" data-attention-state="NORMAL"><div className="current-action-main"><p className="attention-copy">Approval used for this execution</p><h3>The one-use authorization was consumed locally.</h3><p>Execution status will be reported separately from scientific evidence.</p></div></div> : null}
      </section> : null}

      <section id="local-workflow" className="run-local-details" aria-labelledby="local-workflow-title"><div><p className="eyebrow">Local Workflow</p><h2 id="local-workflow-title">Continue safely on this computer</h2><p>{localReason}</p><p className="exact-command-label">One recommended command</p><CopyCommand command={command} label="Experiment local workflow command" /><p>Expected next state: ReAgent resumes from the exact saved checkpoint. Use this same command after an Owner checkpoint.</p></div></section>

      <section className="plain-section" aria-labelledby="experiment-results-title"><p className="eyebrow">Results</p><h2 id="experiment-results-title">Experiment result</h2><div className="input-readiness-list"><div><div><strong>Process outcome</strong><small>Whether the bounded process completed.</small></div><span>{statusText(executionOutcome, "Not run")}</span></div><div><div><strong>Evaluation validity</strong><small>Whether the Capability accepted the result evidence.</small></div><span>{statusText(evaluationValidity, "Pending")}</span></div><div><div><strong>Scientific evidence</strong><small>Evidence sufficiency remains separate from process completion.</small></div><span>{statusText(evidenceStatus, "Pending")}</span></div></div>{artifact ? <ExperimentPresentationView artifact={artifact} /> : <p>Local result presentation has not yet been reported.</p>}</section>

      {artifact || resultReviewCheckpoint ? <section className="current-action-panel" data-attention-state="OWNER_ACTION_REQUIRED"><div className="current-action-main"><p className="attention-copy">Experiment result ready for review</p><h2>Does this accurately represent the experiment and its limitations?</h2><p>Review the findings, evaluation validity, scientific evidence, limitations, output references, and execution warnings before finalizing.</p></div><aside className="current-action-next"><span>Next action</span><a className="button button-primary" href="#local-workflow">Review result</a></aside></section> : null}
    </> : null}

    <details className="technical-details"><summary>Technical details</summary><dl>
      <div><dt>Workflow Definition</dt><dd><code>{instance.workflow_definition_id}@{instance.workflow_version}</code></dd></div>
      <div><dt>Capsule</dt><dd><code>{instance.capsule_id}@{instance.capsule_version}</code></dd></div>
      <div><dt>Workflow Instance</dt><dd><code>{instance.workflow_instance_id}</code></dd></div>
      <div><dt>Current checkpoint</dt><dd><code>{checkpoint ?? "Not currently reported"}</code></dd></div>
      <div><dt>Research Objective</dt><dd><code>{ideaBinding?.artifact_id ?? "Not yet reported from Local Workspace"}</code></dd></div>
      {requirements.map((requirement) => <div key={requirement.requirement_key}><dt>Input requirement</dt><dd><code>{requirement.requirement_key}</code></dd></div>)}
      <div><dt>Capability</dt><dd><code>{approvalRequest?.capability_checksum ?? "Not yet reported from Local Workspace"}</code></dd></div>
      <div><dt>Validated package</dt><dd><code>{approvalRequest?.validated_package_checksum ?? "Not yet reported from Local Workspace"}</code></dd></div>
      <div><dt>Runtime compatibility</dt><dd><code>{approvalRequest?.runtime_compatibility_checksum ?? "Not yet reported from Local Workspace"}</code></dd></div>
      <div><dt>Design Approval</dt><dd><code>Not yet reported from Local Workspace</code></dd></div>
      <div><dt>Run Approval request</dt><dd><code>{approvalRequest?.request_id ?? "Not yet reported from Local Workspace"}</code></dd></div>
      <div><dt>Run Approval status</dt><dd><code>{approvalStatus ?? "Not yet reported from Local Workspace"}</code></dd></div>
      <div><dt>Execution Plan</dt><dd><code>{approvalRequest?.execution_plan_checksum ?? "Not yet reported from Local Workspace"}</code></dd></div>
      {artifact ? <><div><dt>Artifact schema</dt><dd><code>{artifact.artifact_schema_version}</code></dd></div><div><dt>Artifact checksum</dt><dd><code>{artifact.content_checksum}</code></dd></div></> : <div><dt>Artifact</dt><dd><code>Not yet reported from Local Workspace</code></dd></div>}
      {presentation ? <div><dt>Presentation checksum</dt><dd><code>{presentation.presentation_checksum}</code></dd></div> : <div><dt>Presentation</dt><dd><code>Not yet reported from Local Workspace</code></dd></div>}
    </dl></details>
  </div>;
}

export function WorkflowDetail({ projectId, workflowInstanceId }: { projectId: string; workflowInstanceId: string }) {
  const [runInstructionsOpen, setRunInstructionsOpen] = useState(false);
  const runInstructionsRef = useRef<HTMLDetailsElement>(null);
  const project = useProject(projectId);
  const instances = useProjectWorkflowInstances(projectId);
  const progress = useProjectProgress(projectId, { workflowInstanceId });
  const instance = instances.data?.items.find((item) => item.workflow_instance_id === workflowInstanceId);
  const definition = useWorkflowDefinition(instance?.workflow_definition_id ?? "");

  if (project.isLoading || instances.isLoading || progress.isLoading || definition.isLoading) {
    return <LoadingState label="Loading Workflow Detail" />;
  }
  if (project.isError || !project.data || instances.isError || !instances.data || progress.isError || !progress.data || definition.isError || !definition.data) {
    return <ErrorState title="Workflow Detail unavailable" />;
  }

  const state = progress.data.instances.find((item) => item.workflow_instance_id === workflowInstanceId);
  if (!instance || !state) return <ErrorState title="Workflow not found" />;
  const pinnedVersion = definition.data.versions.find((item) => item.version === instance.workflow_version);
  if (!pinnedVersion) return <ErrorState title="Pinned Workflow contract unavailable" />;
  const requirements = pinnedVersion.artifact_requirements ?? [];
  const resourceRequirements = pinnedVersion.resource_requirements ?? instance.resource_requirements ?? [];
  if (
    instance.workflow_definition_id === "reproduction-experiment-local-experimental"
    && instance.workflow_version === "0.6.0"
  ) {
    return <GenericExperimentDetail
      project={project.data}
      instance={instance}
      state={state}
      progress={progress.data}
      requirements={requirements}
      resourceRequirements={resourceRequirements}
    />;
  }
  const dependencies = progress.data.dependency_edges.filter((edge) => edge.consumer_workflow_instance_id === workflowInstanceId);
  const visibleRequirements = requirements.filter((requirement) => (
    requirement.required
    || requirement.artifact_type.toLocaleLowerCase().includes("experiment")
    || dependencies.some((edge) => edge.requirement_key === requirement.requirement_key && edge.state === "ACTIVE")
  ));
  const activity = progress.data.history.filter((report) => report.workflow_instance_id === workflowInstanceId).slice(0, 5);
  const command = localCommand(state.action.next_action.code, workflowInstanceId);
  const actionHref = state.action.next_action.code === "SETUP"
    ? `/projects/${projectId}/help`
    : state.action.next_action.surface === "BROWSER" && state.action.next_action.code === "SELECT_INPUT"
    ? "#inputs"
      : state.action.next_action.code === "REVIEW_RESULT"
        ? `/projects/${projectId}/outputs`
      : state.action.next_action.code === "SELECT_RESOURCE" || state.action.next_action.code === "STAGE_RESOURCE"
        ? "#resources"
      : state.action.next_action.surface === "LOCAL" ? "#run-locally" : undefined;
  const presentation = presentWorkflowAction(state.action, state.workflow_display_name, state.latest_summary ?? "");
  const revealRunInstructions = state.action.next_action.code === "RUN"
    ? () => {
        setRunInstructionsOpen(true);
        window.requestAnimationFrame(() => {
          runInstructionsRef.current?.scrollIntoView?.({ behavior: "smooth", block: "center" });
          runInstructionsRef.current?.focus();
        });
      }
    : undefined;

  return (
    <div className="page-stack workflow-detail-page">
      <p className="breadcrumb"><Link href={`/projects/${projectId}`}>{project.data.name}</Link><span>/</span><Link href={`/projects/${projectId}/workflows`}>Workflows</Link><span>/</span><strong>{state.friendly_instance_label ?? state.instance_display_name}</strong></p>
      <header className="workflow-detail-header">
        <div><p className="eyebrow">{state.workflow_display_name} workflow</p><h1>{state.friendly_instance_label ?? state.instance_display_name}</h1><p>{workflowDescription(state.workflow_display_name, definition.data.description)}</p></div>
        <Link href={`/projects/${projectId}/workflows`} className="button button-ghost">All Workflows</Link>
      </header>
      <ProjectNavigation projectId={projectId} active="Workflows" />

      <WorkflowActionPanel
        action={state.action}
        workflowLabel={state.workflow_display_name}
        href={actionHref}
        context={state.latest_summary ?? ""}
        revealLocalInstructions={revealRunInstructions}
        instructionsExpanded={runInstructionsOpen}
      />

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

      {resourceRequirements.length ? (
        <WorkflowResourceSetup
          projectId={projectId}
          instance={instance}
          requirements={resourceRequirements}
        />
      ) : null}

      {command ? (
        <details
          id="run-locally"
          className="run-local-details"
          open={runInstructionsOpen}
          onToggle={(event) => setRunInstructionsOpen(event.currentTarget.open)}
          ref={runInstructionsRef}
          tabIndex={-1}
        >
          <summary><span>{state.action.next_action.code === "RUN" ? `Run ${state.workflow_display_name}` : presentation.task}</span><span>{runInstructionsOpen ? "Hide instructions" : "Show instructions"}</span></summary>
          <div>
            <p>Use this command in your Local Workspace. The browser does not run it or write research files.</p>
            <p>This command runs the exact {state.workflow_display_name} Workflow selected for this Project.</p>
            <p className="exact-command-label">Exact command</p>
            <CopyCommand command={command} label={`${state.workflow_display_name} exact command`} />
          </div>
        </details>
      ) : null}

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
          {resourceRequirements.map((requirement) => <div key={requirement.requirement_key}><dt>Resource requirement</dt><dd><code>{requirement.requirement_key}</code> · {requirement.required ? "required" : "optional"}</dd></div>)}
          {dependencies.map((dependency) => <div key={dependency.requirement_key}><dt>Bound Artifact</dt><dd><code>{dependency.artifact_id}</code></dd></div>)}
          {state.action.latest_output ? <div><dt>Output checksum</dt><dd><code>{state.action.latest_output.checksum}</code></dd></div> : null}
        </dl>
      </details>
    </div>
  );
}
