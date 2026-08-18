"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/api/client";
import { useProject, useProjectProgress } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";

import { PageHeader } from "./page-header";
import { ProjectNavigation } from "./project-navigation";
import { ErrorState, LoadingState } from "./query-state";
import { presentWorkflowAction, WorkflowActionPanel } from "./workflow-detail";

const WORKFLOW_PRESENTATION_ORDER: Record<string, number> = {
  "literature-search-local-experimental": 10,
  "idea-discovery-local-experimental": 20,
  "reproduction-experiment-local-experimental": 30,
  "writing-local-experimental": 40,
  "review-local-experimental": 50,
};

export function LocalProjectDetail({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  const progress = useProjectProgress(projectId);
  const skills = useQuery({
    queryKey: ["projects", projectId, "user-skills"],
    queryFn: () => apiClient.listProjectUserSkills(projectId),
  });

  if (project.isLoading || progress.isLoading) return <LoadingState label="Loading Project Overview" />;
  if (project.isError || !project.data || progress.isError || !progress.data) {
    return <ErrorState title="Project Overview unavailable" />;
  }

  const data = project.data;
  const projection = progress.data;
  const attention = projection.attention;
  const workflowHref = attention.action.next_action.code === "SETUP"
    ? `/projects/${projectId}/help`
    : attention.action.next_action.code === "REVIEW_RESULT"
    ? `/projects/${projectId}/outputs`
    : attention.recommended_workflow_instance_id
      ? `/projects/${projectId}/workflows/${attention.recommended_workflow_instance_id}`
      : `/projects/${projectId}/workflows`;
  const recent = projection.history.slice(0, 3);
  const output = attention.latest_output;
  const syncRequired = attention.action.next_action.code === "SYNC";
  const setupRequired = attention.action.next_action.code === "SETUP";
  const currentPresentation = presentWorkflowAction(attention.action, attention.recommended_workflow_label, attention.recent_change.summary);
  const visibleWorkflows = projection.instances
    .filter((item) => item.lifecycle === "ACTIVE")
    .sort((left, right) => (
      (WORKFLOW_PRESENTATION_ORDER[left.workflow_definition_id] ?? 90)
      - (WORKFLOW_PRESENTATION_ORDER[right.workflow_definition_id] ?? 90)
    ))
    .slice(0, 5);

  return (
    <div className="page-stack project-overview-page">
      <Link href="/projects" className="back-link">← Projects</Link>
      <PageHeader
        eyebrow="Project Overview"
        title={data.name}
        description={data.research_topic}
      />
      <ProjectNavigation projectId={projectId} active="Overview" />

      <WorkflowActionPanel
        action={attention.action}
        workflowLabel={attention.recommended_workflow_label}
        href={workflowHref}
        context={attention.recent_change.summary}
      />

      <div className="overview-support-grid">
        <section className="plain-section" aria-labelledby="overview-workflows-title">
          <div className="section-heading"><h2 id="overview-workflows-title">Workflow progress</h2><Link href={`/projects/${projectId}/workflows`} className="text-link">View all workflows →</Link></div>
          <div className="overview-workflow-list">
            {visibleWorkflows.map((item) => {
              const presentation = presentWorkflowAction(item.action, item.friendly_instance_label ?? item.workflow_display_name, item.latest_summary ?? "");
              const projectSetupPresentation = setupRequired
                ? item.workflow_instance_id === attention.recommended_workflow_instance_id
                  ? { task: "Waiting for workspace", attention: "Waiting" }
                  : { task: "Not started", attention: "Not started" }
                : presentation;
              return <div key={item.workflow_instance_id}><div><strong>{item.friendly_instance_label ?? item.workflow_display_name}</strong><p>{projectSetupPresentation.task}</p></div><span>{projectSetupPresentation.attention}</span></div>;
            })}
          </div>
        </section>

        <div className="overview-side-column">
          <section className="plain-section" aria-labelledby="overview-skills-title">
            <div className="section-heading"><h2 id="overview-skills-title">Skills</h2><Link href={`/skills?project=${projectId}`} className="text-link">Manage skills →</Link></div>
            {skills.data?.items.length ? (
              <div className="overview-workflow-list">
                {skills.data.items.map((skill) => <div key={skill.skill_id}><strong>{skill.name}</strong><span>{skill.local_status}</span></div>)}
              </div>
            ) : <p className="muted-copy">No skills added yet.</p>}
          </section>

          <section id="outputs" className="plain-section" aria-labelledby="overview-output-title">
            <div className="section-heading"><h2 id="overview-output-title">Latest output</h2><Link href={`/projects/${projectId}/outputs`} className="text-link">All outputs →</Link></div>
            {output ? <div className="output-summary-row"><div><strong>{output.label}</strong><p>{currentPresentation.stage} · {output.produced_at ? formatDateTime(output.produced_at) : "Available now"}</p></div></div> : <p className="muted-copy">Expected next: {attention.action.expected_output?.label ?? "No output is expected yet."}</p>}
          </section>

          <section id="activity" className="plain-section" aria-labelledby="overview-activity-title">
            <div className="section-heading"><h2 id="overview-activity-title">Recent activity</h2><Link href={`/projects/${projectId}/progress`} className="text-link">All activity →</Link></div>
            {recent.length ? <ol className="activity-list">{recent.slice(0, 2).map((report) => {
              const workflow = projection.instances.find((item) => item.workflow_instance_id === report.workflow_instance_id);
              const presentation = workflow ? presentWorkflowAction(workflow.action, workflow.friendly_instance_label ?? workflow.workflow_display_name, workflow.latest_summary ?? "") : null;
              return <li key={report.receipt_id}><div><strong>{workflow?.friendly_instance_label ?? "Workflow"}</strong><p>{presentation?.task ?? "Activity recorded."}</p></div><time>{formatDateTime(report.received_at)}</time></li>;
            })}</ol> : <p className="muted-copy">No workflow activity has been reported yet.</p>}
          </section>
        </div>
      </div>

      {syncRequired ? (
        <section className="local-boundary-strip" aria-labelledby="local-setup-title">
          <div><p className="eyebrow">Local Workspace</p><h2 id="local-setup-title">Set up or sync locally</h2><p>The browser downloads metadata and tools only. It never writes research files.</p></div>
          <div className="button-row">
            <a href={apiClient.localClientDownloadUrl()} download="reagent_local.py" className="button button-secondary">Download local tool</a>
            <a href={apiClient.workspaceBootstrapDownloadUrl(projectId)} download="workspace-bootstrap.json" className="button button-secondary">Download setup file</a>
          </div>
        </section>
      ) : null}

      <details className="technical-details">
        <summary>Technical Details</summary>
        <dl>
          <div><dt>Project ID</dt><dd><code>{data.project_id}</code></dd></div>
          <div><dt>Manifest revision</dt><dd>{projection.manifest_revision}</dd></div>
          <div><dt>Active Workflows</dt><dd>{projection.active_workflow_count}</dd></div>
          <div><dt>Progress reports</dt><dd>{projection.total_progress_report_count}</dd></div>
          <div><dt>Created</dt><dd>{formatDateTime(data.created_at)}</dd></div>
          {output ? <div><dt>Latest Artifact checksum</dt><dd><code>{output.checksum}</code></dd></div> : null}
        </dl>
      </details>
    </div>
  );
}
