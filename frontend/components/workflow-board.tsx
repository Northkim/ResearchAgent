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
import { deriveWorkflowNextAction } from "@/lib/workflow-next-action";
import type { ProjectWorkflowInstance, WorkflowCatalogItem } from "@/types/api";

import { PageHeader } from "./page-header";
import { ProjectNavigation } from "./project-navigation";
import { ErrorState, LoadingState } from "./query-state";
import { WorkflowStatusBadge } from "./workflow-status-badge";
import { IdeaDiscoverySetup } from "./idea-discovery-setup";
import { WorkflowInputSetup } from "./workflow-input-setup";
import { CopyCommand } from "./copy-command";
import { WorkflowResourceSetup } from "./workflow-resource-setup";

const IDEA_DISCOVERY_WORKFLOW_ID = "idea-discovery-local-experimental";
const INPUT_WORKFLOW_IDS = new Set([
  IDEA_DISCOVERY_WORKFLOW_ID,
  "writing-local-experimental",
  "review-local-experimental",
  "reproduction-experiment-local-experimental",
]);

function WorkflowSkills({ skills }: { skills: NonNullable<ProjectWorkflowInstance["skills"]> }) {
  if (!skills.length) return null;
  return (
    <div className="boundary-callout workflow-skills" aria-label="Bundled skills">
      <strong>Skills bundled with this Workflow</strong>
      <ul>
        {skills.map((skill) => (
          <li key={`${skill.skill_id}@${skill.version}`}>
            {skill.display_name} {skill.version} · Built-in reviewed
          </li>
        ))}
      </ul>
      <p>These exact versions arrive inside the verified Capsule when you sync. Skills do not change the Workflow&apos;s core maturity.</p>
    </div>
  );
}

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
        eyebrow="Workflow Board"
        title={`${project.data.name} workflows`}
        description="Each card is one independent Workflow. Research progress, Cloud selection, and local installation knowledge remain separate."
        action={<Link href={`/projects/${projectId}/help`} className="button button-ghost">Workflow help</Link>}
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

      <section className="boundary-callout" aria-labelledby="research-relationships-title">
        <strong id="research-relationships-title">Research relationships · guidance, not a pipeline</strong>
        <p>Each Workflow remains independent. These links come from the current immutable Artifact requirement contracts.</p>
        <ul>
          {relationships.map((item) => (
            <li key={item.key}>{item.producer} → {item.consumer}{item.required ? " · required" : " · optional"}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="current-workflows-title">
        <div className="section-heading">
          <div><p className="eyebrow">Current Workflows</p><h2 id="current-workflows-title">Your Project workflows</h2></div>
          <span className="section-caption">Cloud configuration</span>
        </div>
        {instances.data.items.length ? (
          <div className="workflow-card-grid">
            {instances.data.items.map((instance) => {
              const state = projections.get(instance.workflow_instance_id);
              const definition = catalog.data!.items.find(
                (item) => item.workflow_definition_id === instance.workflow_definition_id,
              );
              const dependencyEdges = progress.data.dependency_edges.filter(
                (item) => item.consumer_workflow_instance_id === instance.workflow_instance_id,
              );
              const nextAction = deriveWorkflowNextAction({
                instance,
                progress: state,
                requiresInput: INPUT_WORKFLOW_IDS.has(definition?.stable_workflow_key ?? ""),
                dependencies: dependencyEdges,
              });
              return (
                <article className="workflow-card" key={instance.workflow_instance_id}>
                  <div className="workflow-card-heading">
                    <div>
                      <p className="eyebrow">{definition?.display_name ?? instance.workflow_definition_id}</p>
                      <h3>{state?.friendly_instance_label ?? instance.display_name}</h3>
                    </div>
                    <WorkflowStatusBadge value={instance.desired_state} dimension="lifecycle" />
                  </div>
                  <div className="workflow-badge-row">
                    {definition?.recommended_version ? (
                      <WorkflowStatusBadge value={definition.recommended_version.core_capability_maturity} dimension="maturity" />
                    ) : null}
                    <WorkflowStatusBadge value={state?.research_status ?? "NOT_STARTED"} dimension="research" />
                    <WorkflowStatusBadge value={state?.desired_state ?? (instance.in_current_manifest ? "DESIRED" : "NOT_DESIRED")} dimension="desired" />
                    <WorkflowStatusBadge value={state?.installation_state ?? "UNKNOWN"} dimension="installation" />
                    {state?.readiness ? <WorkflowStatusBadge value={state.readiness} dimension="readiness" /> : null}
                  </div>
                  {definition?.recommended_version?.core_capability_maturity === "SCAFFOLD_CORE" ? (
                    <div className="boundary-callout">
                      <strong>Scaffold core</strong>
                      <p>Product flow is functional. Research capability is placeholder.</p>
                    </div>
                  ) : null}
                  <WorkflowSkills skills={instance.skills ?? []} />
                  {(instance.resource_requirements ?? []).length ? (
                    <WorkflowResourceSetup
                      projectId={projectId}
                      instance={instance}
                      requirements={instance.resource_requirements ?? []}
                    />
                  ) : null}
                  <p>{state?.latest_summary ?? "No Progress Report has been uploaded for this instance."}</p>
                  <div className="workflow-next-action" data-action={nextAction.code}>
                    <strong>Next: {nextAction.title}</strong>
                    <p>{nextAction.description}</p>
                  </div>
                  <dl className="workflow-card-details">
                    <div><dt>Progress reports</dt><dd>{state?.report_count ?? 0}</dd></div>
                    <div><dt>Latest activity</dt><dd>{state?.latest_activity_at ? formatDateTime(state.latest_activity_at) : "None"}</dd></div>
                  </dl>
                  {instance.workflow_definition_id === IDEA_DISCOVERY_WORKFLOW_ID ? (
                    <IdeaDiscoverySetup
                      projectId={projectId}
                      instance={instance}
                      instances={instances.data.items}
                      installationState={state?.installation_state ?? "UNKNOWN"}
                      dependencies={dependencyEdges}
                    />
                  ) : null}
                  {instance.workflow_definition_id !== IDEA_DISCOVERY_WORKFLOW_ID ? (
                    <WorkflowInputSetup
                      projectId={projectId}
                      instance={instance}
                      instances={instances.data.items}
                      projections={progress.data.instances}
                      requirements={definition?.recommended_version?.artifact_requirements ?? []}
                      dependencies={dependencyEdges}
                    />
                  ) : null}
                  <details className="technical-details compact-technical-details">
                    <summary>Technical details</summary>
                    <dl>
                      <div><dt>Instance ID</dt><dd><code>{instance.workflow_instance_id}</code></dd></div>
                      <div><dt>Workflow version</dt><dd>{instance.workflow_version}</dd></div>
                      <div><dt>Capsule version</dt><dd>{instance.capsule_version ?? "Not pinned"}</dd></div>
                    </dl>
                  </details>
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

      <details className="technical-details">
        <summary>Cloud configuration details</summary>
        <dl><div><dt>Revision</dt><dd>{instances.data.manifest_revision}</dd></div></dl>
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
              return (
                <article key={item.workflow_definition_id}>
                  <div className="workflow-card-heading"><h3>{item.display_name}</h3><WorkflowStatusBadge value={item.lifecycle} dimension="catalog" /></div>
                  {item.recommended_version ? (
                    <div className="workflow-badge-row"><WorkflowStatusBadge value={item.recommended_version.core_capability_maturity} dimension="maturity" /></div>
                  ) : null}
                  <p>{item.description}</p>
                  {item.recommended_version?.core_capability_maturity === "SCAFFOLD_CORE" ? (
                    <p><strong>Prototype core:</strong> Product flow is functional. Research capability is placeholder.</p>
                  ) : null}
                  <WorkflowSkills skills={item.recommended_version?.skills ?? []} />
                  {(item.recommended_version?.resource_requirements ?? []).length ? (
                    <p><strong>Optional external Resources:</strong> exact references are selected per Project. GitHub/Hugging Face resolution is not implemented yet.</p>
                  ) : null}
                  <p className="section-caption">{item.recommended_version ? `Version ${item.recommended_version.version}` : "No published executable version"}</p>
                  <button className="button button-secondary" disabled={!canAdd || create.isPending} onClick={() => addWorkflow(item)}>
                    {item.lifecycle === "PLANNED" ? "Planned" : "Add workflow"}
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
