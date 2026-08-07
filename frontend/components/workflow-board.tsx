"use client";

import { useState } from "react";
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
import { WorkflowStatusBadge } from "./workflow-status-badge";

function shortIdentity(value: string): string {
  return value.slice(-8);
}

export function WorkflowBoard({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  const instances = useProjectWorkflowInstances(projectId);
  const catalog = useWorkflowDefinitions();
  const progress = useProjectProgress(projectId);
  const create = useCreateProjectWorkflowInstance(projectId);
  const retire = useRetireProjectWorkflowInstance(projectId);
  const [notice, setNotice] = useState<string | null>(null);

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
  const activeDefinitions = new Set(
    instances.data.items
      .filter((item) => item.desired_state === "ACTIVE")
      .map((item) => item.workflow_definition_id),
  );

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
      setNotice("Workflow added to the Cloud Desired Manifest. Run local sync to install its Capsule.");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        await instances.refetch();
        setNotice("The Project Manifest changed elsewhere. Current state was refreshed; review it before retrying.");
      }
    }
  }

  async function retireWorkflow(instance: ProjectWorkflowInstance) {
    if (!window.confirm("Retire this Workflow Instance? Its local Capsule and Progress history will be retained.")) return;
    setNotice(null);
    try {
      await retire.mutateAsync({ instance, baseRevision: instances.data!.manifest_revision });
      setNotice("Workflow retired from Cloud Desired State. Local research files were not deleted; run local sync to refresh status.");
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        await instances.refetch();
        setNotice("The Project Manifest changed elsewhere. Current state was refreshed; review it before retrying.");
      }
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Workflow Board"
        title={`${project.data.name} workflows`}
        description="Each card is one independent Workflow Instance. Research progress, Cloud desired state, and local installation knowledge are separate dimensions."
        action={<Link href={`/projects/${projectId}/help`} className="button button-ghost">Workflow help</Link>}
      />
      <ProjectNavigation projectId={projectId} active="Workflows" />
      {notice ? <div className="boundary-callout" role="status"><strong>Project state updated</strong><p>{notice}</p></div> : null}
      {(create.error || retire.error) && !notice ? (
        <div className="form-error" role="alert">{(create.error ?? retire.error)?.message}</div>
      ) : null}

      <section aria-labelledby="current-workflows-title">
        <div className="section-heading">
          <div><p className="eyebrow">Current Workflow Instances</p><h2 id="current-workflows-title">Cloud-managed research configuration</h2></div>
          <span className="section-caption">Manifest revision {instances.data.manifest_revision}</span>
        </div>
        {instances.data.items.length ? (
          <div className="workflow-card-grid">
            {instances.data.items.map((instance) => {
              const state = projections.get(instance.workflow_instance_id);
              const definition = catalog.data!.items.find(
                (item) => item.workflow_definition_id === instance.workflow_definition_id,
              );
              return (
                <article className="workflow-card" key={instance.workflow_instance_id}>
                  <div className="workflow-card-heading">
                    <div>
                      <p className="eyebrow">{definition?.display_name ?? instance.workflow_definition_id}</p>
                      <h3>{instance.display_name}</h3>
                      <code title={instance.workflow_instance_id}>Instance {shortIdentity(instance.workflow_instance_id)}</code>
                    </div>
                    <WorkflowStatusBadge value={instance.desired_state} dimension="lifecycle" />
                  </div>
                  <div className="workflow-badge-row">
                    <WorkflowStatusBadge value={state?.research_status ?? "NOT_STARTED"} dimension="research" />
                    <WorkflowStatusBadge value={state?.desired_state ?? (instance.in_current_manifest ? "DESIRED" : "NOT_DESIRED")} dimension="desired" />
                    <WorkflowStatusBadge value={state?.installation_state ?? "UNKNOWN"} dimension="installation" />
                  </div>
                  <p>{state?.latest_summary ?? "No Progress Report has been uploaded for this instance."}</p>
                  <dl className="workflow-card-details">
                    <div><dt>Workflow version</dt><dd>{instance.workflow_version}</dd></div>
                    <div><dt>Capsule version</dt><dd>{instance.capsule_version ?? "Not pinned"}</dd></div>
                    <div><dt>Reports</dt><dd>{state?.report_count ?? 0}</dd></div>
                    <div><dt>Latest activity</dt><dd>{state?.latest_activity_at ? formatDateTime(state.latest_activity_at) : "None"}</dd></div>
                  </dl>
                  <div className="button-row">
                    <Link href={`/projects/${projectId}/progress?workflow_instance_id=${encodeURIComponent(instance.workflow_instance_id)}`} className="button button-secondary">View progress</Link>
                    {instance.desired_state === "ACTIVE" ? (
                      <button className="button button-ghost" disabled={retire.isPending} onClick={() => retireWorkflow(instance)}>Retire</button>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        ) : <div className="empty-panel"><h3>No Workflow Instances</h3><p>Add a published Workflow from the catalog below.</p></div>}
      </section>

      <section className="workflow-catalog-section" aria-labelledby="catalog-title">
        <div className="section-heading">
          <div><p className="eyebrow">Available Workflow Catalog</p><h2 id="catalog-title">Reviewed Cloud definitions</h2></div>
          <span className="section-caption">{catalog.data.total} registered</span>
        </div>
        {catalog.data.items.length ? (
          <div className="workflow-catalog-grid">
            {catalog.data.items.map((item) => {
              const activeAlready = activeDefinitions.has(item.workflow_definition_id);
              const canAdd = item.creatable && item.lifecycle === "AVAILABLE" && !activeAlready && item.recommended_version && item.recommended_capsule;
              return (
                <article key={item.workflow_definition_id}>
                  <div className="workflow-card-heading"><h3>{item.display_name}</h3><WorkflowStatusBadge value={item.lifecycle} dimension="catalog" /></div>
                  <p>{item.description}</p>
                  <p className="section-caption">{item.recommended_version ? `Version ${item.recommended_version.version}` : "No published executable version"}</p>
                  <button className="button button-secondary" disabled={!canAdd || create.isPending} onClick={() => addWorkflow(item)}>
                    {item.lifecycle === "PLANNED" ? "Planned" : activeAlready ? "Already active" : "Add workflow"}
                  </button>
                </article>
              );
            })}
          </div>
        ) : <div className="empty-panel"><h3>Catalog is empty</h3><p>No production Workflow Definitions are currently published.</p></div>}
      </section>
    </div>
  );
}
