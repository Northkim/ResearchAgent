"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

import { ApiError } from "@/api/client";
import {
  useCreateProjectWorkflowInstance,
  useProject,
  useProjectProgress,
  useProjectWorkflowInstances,
  useRetireProjectWorkflowInstance,
  useWorkflowDefinitions,
} from "@/api/hooks";
import { formatDateTime } from "@/lib/format";
import type { ProjectWorkflowInstance, WorkflowCatalogItem } from "@/types/api";

import { PageHeader } from "./page-header";
import { ProjectNavigation } from "./project-navigation";
import { ErrorState, LoadingState } from "./query-state";
import { CopyCommand } from "./copy-command";

export function WorkflowBoard({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  const instances = useProjectWorkflowInstances(projectId);
  const catalog = useWorkflowDefinitions();
  const progress = useProjectProgress(projectId);
  const create = useCreateProjectWorkflowInstance(projectId);
  const retire = useRetireProjectWorkflowInstance(projectId);
  const [notice, setNotice] = useState<{ message: string; command?: string } | null>(null);
  const noticeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (notice) noticeRef.current?.focus();
  }, [notice]);

  if (project.isLoading || instances.isLoading || catalog.isLoading || progress.isLoading) {
    return <LoadingState label="Loading Workflow Board" />;
  }
  if (
    project.isError || !project.data || instances.isError || !instances.data ||
    catalog.isError || !catalog.data || progress.isError || !progress.data
  ) {
    return <ErrorState title="Workflow Board unavailable" />;
  }

  const projections = new Map(
    progress.data.instances.map((item) => [item.workflow_instance_id, item]),
  );
  const operationError = create.error ?? retire.error;
  const relationships = catalog.data.items.flatMap((consumer) =>
    (consumer.recommended_version?.artifact_requirements ?? []).map((requirement) => {
      const producer = catalog.data!.items.find(
        (candidate) => candidate.recommended_version?.output_schema_id === requirement.artifact_type,
      );
      return {
        key: `${consumer.workflow_definition_id}-${requirement.requirement_key}`,
        producer: producer?.display_name ?? requirement.artifact_type,
        consumer: consumer.display_name,
        required: requirement.required,
      };
    }),
  );
  const activeInstances = instances.data.items.filter((item) => item.desired_state === "ACTIVE");
  const retiredInstances = instances.data.items.filter((item) => item.desired_state !== "ACTIVE");
  const workflowsNeedingSync = activeInstances.filter(
    (item) => projections.get(item.workflow_instance_id)?.installation_state === "NOT_INSTALLED",
  );

  const workflowRow = (instance: ProjectWorkflowInstance) => {
    const state = projections.get(instance.workflow_instance_id);
    const definition = catalog.data!.items.find(
      (item) => item.workflow_definition_id === instance.workflow_definition_id,
    );
    if (!state) return null;
    return (
      <article className="workflow-work-row" key={instance.workflow_instance_id} data-attention-state={state.action.attention_state}>
        <div className="workflow-work-identity"><p className="eyebrow">{definition?.display_name ?? state.workflow_display_name}</p><h3>{state.friendly_instance_label ?? instance.display_name}</h3><span>{state.action.stage.label}</span></div>
        <div className="workflow-work-status"><span>Actor</span><strong>{state.action.actor === "NONE" ? "No action required" : `${state.action.actor.charAt(0)}${state.action.actor.slice(1).toLowerCase()} acts`}</strong><small>{state.action.blocker?.message ?? state.latest_summary ?? "Ready for its next valid action."}</small></div>
        <div className="workflow-work-status"><span>Next</span><strong>{state.action.next_action.label}</strong><small>{state.action.next_action.surface === "LOCAL" ? "Local Workspace" : state.action.next_action.surface === "BROWSER" ? "Browser" : "Information"}</small></div>
        <div className="workflow-work-status"><span>{state.action.latest_output ? "Latest Output" : "Expected Output"}</span><strong>{state.action.latest_output?.label ?? state.action.expected_output?.label ?? "No Output declared"}</strong><small>{state.latest_activity_at ? formatDateTime(state.latest_activity_at) : "No Activity yet"}</small></div>
        <div className="workflow-row-actions">
          <Link href={`/projects/${projectId}/workflows/${instance.workflow_instance_id}`} className="button button-secondary">Open Workflow</Link>
          <details className="compact-row-details"><summary>Manage</summary><p>{definition?.recommended_version?.core_capability_maturity.replaceAll("_", " ") ?? "Maturity unknown"}</p>{instance.desired_state === "ACTIVE" ? <button className="button button-ghost" disabled={retire.isPending} onClick={() => retireWorkflow(instance)}>Retire</button> : null}</details>
        </div>
      </article>
    );
  };

  async function addWorkflow(item: WorkflowCatalogItem) {
    if (!item.recommended_version || !item.recommended_capsule) return;
    setNotice(null);
    try {
      await create.mutateAsync({
        workflow_definition_id: item.workflow_definition_id,
        workflow_version: item.recommended_version.version,
        capsule_id: item.recommended_capsule.capsule_id,
        capsule_version: item.recommended_capsule.capsule_version,
        base_revision: instances.data!.manifest_revision,
      });
      setNotice({
        message: `${item.display_name} was added to this Project. Next, sync your Local Workspace.`,
        command: "python reagent_local.py sync .",
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        await instances.refetch();
        setNotice({ message: "This Project changed elsewhere. The current Workflow state was refreshed; review it before retrying." });
      }
    }
  }

  async function retireWorkflow(instance: ProjectWorkflowInstance) {
    if (!window.confirm("Retire this Workflow Instance? Its local Capsule and Progress history will be retained.")) return;
    setNotice(null);
    try {
      await retire.mutateAsync({ instance, baseRevision: instances.data!.manifest_revision });
      setNotice({
        message: "Workflow retired in Cloud. Local research files were not deleted; sync the Local Workspace to refresh its status.",
        command: "python reagent_local.py sync .",
      });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        await instances.refetch();
        setNotice({ message: "This Project changed elsewhere. The current Workflow state was refreshed; review it before retrying." });
      }
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Project Workflows"
        title={`${project.data.name} Workflows`}
        description="Open an exact Workflow to see its current stage, next valid action, inputs, Outputs and Activity."
        action={<Link href={`/projects/${projectId}`} className="button button-ghost">Project Overview</Link>}
      />
      <ProjectNavigation projectId={projectId} active="Workflows" />
      {notice ? (
        <div className="boundary-callout" role="status" tabIndex={-1} ref={noticeRef}>
          <strong>Project state updated</strong>
          <p>{notice.message}</p>
          {notice.command ? <CopyCommand command={notice.command} label="local sync command" /> : null}
        </div>
      ) : null}
      {operationError && !notice ? (
        <div className="form-error" role="alert">
          Could not update this Project. No local files changed. Refresh the page, review the current state, and retry.
          {operationError instanceof ApiError
            ? ` Code: ${operationError.code}.`
            : ""}
        </div>
      ) : null}
      {workflowsNeedingSync.length ? <div className="boundary-callout project-sync-notice" role="status"><strong>Project changed — sync to add {workflowsNeedingSync.map((item) => projections.get(item.workflow_instance_id)?.friendly_instance_label ?? item.display_name).join(", ")}</strong><p>Your already installed Workflows remain valid.</p><CopyCommand command="python reagent_local.py sync ." label="local sync command" /></div> : null}

      <section aria-labelledby="current-workflows-title">
        <div className="section-heading">
          <div><p className="eyebrow">Current Work</p><h2 id="current-workflows-title">Workflow progression</h2></div>
          <span className="section-caption">{activeInstances.length} active Workflow{activeInstances.length === 1 ? "" : "s"}</span>
        </div>
        {activeInstances.length ? (
          <div className="workflow-work-list">
            {activeInstances.map(workflowRow)}
          </div>
        ) : <div className="empty-panel"><h3>No Workflow Instances</h3><p>Add a published Workflow from the catalog below.</p></div>}
        {retiredInstances.length ? <details className="retired-workflow-history"><summary>{retiredInstances.length} retired Workflow{retiredInstances.length === 1 ? "" : "s"} · history</summary><div className="workflow-work-list">{retiredInstances.map(workflowRow)}</div></details> : null}
      </section>

      <details className="technical-details">
        <summary>Cloud configuration details</summary>
        <dl>
          <div><dt>Revision</dt><dd>{instances.data.manifest_revision}</dd></div>
          <div><dt>Artifact relationships</dt><dd>{relationships.length ? relationships.map((item) => `${item.producer} → ${item.consumer}${item.required ? " (required)" : " (optional)"}`).join("; ") : "None declared"}</dd></div>
          <div><dt>Bundled Workflow Skills</dt><dd>{catalog.data.items.map((item) => `${item.display_name}: ${(item.recommended_version?.skills ?? []).map((skill) => `${skill.display_name} ${skill.version}`).join(", ") || "none"}`).join(" · ")}</dd></div>
        </dl>
      </details>

      <section className="workflow-catalog-section" aria-labelledby="catalog-title">
        <div className="section-heading">
          <div><p className="eyebrow">Available Workflows</p><h2 id="catalog-title">Add another research workflow</h2></div>
          <span className="section-caption">{catalog.data.total} registered</span>
        </div>
        {catalog.data.items.length ? (
          <div className="workflow-catalog-grid">
            {catalog.data.items.map((item) => {
              const canAdd = item.creatable && item.lifecycle === "AVAILABLE" && item.recommended_version && item.recommended_capsule;
              const existingCount = activeInstances.filter(
                (instance) => instance.workflow_definition_id === item.workflow_definition_id,
              ).length;
              return (
                <article key={item.workflow_definition_id}>
                  <div className="workflow-card-heading"><h3>{item.display_name}</h3></div>
                  <p>{item.description}</p>
                  <div className="workflow-card-actions">
                    <span className="section-caption">{existingCount ? `${existingCount} already in project` : ""}</span>
                    <button className="button button-secondary" disabled={!canAdd || create.isPending} onClick={() => addWorkflow(item)}>
                      {item.lifecycle === "PLANNED" ? "Planned" : existingCount ? "Add another" : "Add workflow"}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : <div className="empty-panel"><h3>Catalog is empty</h3><p>No production Workflow Definitions are currently published.</p></div>}
      </section>
    </div>
  );
}
