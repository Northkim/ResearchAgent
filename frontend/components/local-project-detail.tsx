"use client";

import Link from "next/link";

import { useProject, useProjectProgress } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";

import { PageHeader } from "./page-header";
import { ProjectNavigation } from "./project-navigation";
import { ErrorState, LoadingState } from "./query-state";
import { WorkflowStatusBadge } from "./workflow-status-badge";

export function LocalProjectDetail({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  const progress = useProjectProgress(projectId);

  if (project.isLoading || progress.isLoading) return <LoadingState label="Loading project overview" />;
  if (project.isError || !project.data || progress.isError || !progress.data) {
    return <ErrorState title="Project overview unavailable" />;
  }

  const data = project.data;
  const projection = progress.data;
  const recent = projection.instances
    .filter((item) => item.latest_activity_at)
    .sort((left, right) => (right.latest_activity_at ?? "").localeCompare(left.latest_activity_at ?? ""))
    .slice(0, 3);
  const firstRunnable = projection.instances.find((item) => item.lifecycle === "ACTIVE");

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Project workspace"
        title={data.name}
        description={data.research_topic}
        action={<Link href="/projects" className="button button-ghost">All projects</Link>}
      />
      <ProjectNavigation projectId={projectId} active="Overview" />

      <section className="overview-hero" aria-labelledby="project-state-title">
        <div>
          <p className="eyebrow">Overview</p>
          <h2 id="project-state-title">Your research workflows at a glance</h2>
          <p>Research progress is reported by each Workflow Instance. Local installation is shown separately and never counts as research completion.</p>
        </div>
        <dl className="overview-counts">
          <div><dt>Active</dt><dd>{projection.active_workflow_count}</dd></div>
          <div><dt>Not started</dt><dd>{projection.status_counts.NOT_STARTED ?? 0}</dd></div>
          <div><dt>In progress</dt><dd>{projection.status_counts.IN_PROGRESS ?? 0}</dd></div>
          <div><dt>Completed</dt><dd>{projection.status_counts.COMPLETED ?? 0}</dd></div>
          <div><dt>Retired</dt><dd>{projection.retired_workflow_count}</dd></div>
        </dl>
      </section>

      <section className="overview-grid">
        <article>
          <p className="eyebrow">Recommended next action</p>
          <h2>{firstRunnable?.next_recommended_action ?? (data.current_package ? "Run or review Literature Search" : "Prepare Literature Search locally")}</h2>
          <p>{firstRunnable?.latest_summary ?? "No Workflow Progress has been uploaded yet. Cloud cannot inspect the local Workspace."}</p>
          <div className="button-row">
            <Link href={`/projects/${projectId}/workflows`} className="button button-primary">Open workflows</Link>
            <Link href={`/projects/${projectId}/help`} className="button button-ghost">Local workflow help</Link>
          </div>
        </article>
        <article>
          <p className="eyebrow">Cloud desired state</p>
          <h2>Manifest revision {projection.manifest_revision}</h2>
          <p>The browser records desired Workflow configuration. Run <code>python reagent_local.py sync .</code> in the Workspace to reconcile local Capsules.</p>
        </article>
        <article>
          <p className="eyebrow">Latest project activity</p>
          <h2>{projection.latest_project_activity_at ? formatDateTime(projection.latest_project_activity_at) : "No Progress yet"}</h2>
          <p>{projection.total_progress_report_count} immutable Progress Report{projection.total_progress_report_count === 1 ? "" : "s"} retained.</p>
          <Link href={`/projects/${projectId}/progress`} className="text-link">Review project progress →</Link>
        </article>
      </section>

      <section className="recent-workflows" aria-labelledby="recent-workflows-title">
        <div className="section-heading">
          <div><p className="eyebrow">Recent workflow progress</p><h2 id="recent-workflows-title">Independent instance state</h2></div>
          <Link href={`/projects/${projectId}/workflows`} className="text-link">View all workflows →</Link>
        </div>
        {recent.length ? (
          <div className="workflow-card-grid">
            {recent.map((item) => (
              <article className="workflow-card" key={item.workflow_instance_id}>
                <div className="workflow-card-heading">
                  <div><h3>{item.instance_display_name}</h3><code>{item.workflow_instance_id.slice(-8)}</code></div>
                  <WorkflowStatusBadge value={item.research_status} dimension="research" />
                </div>
                <p>{item.latest_summary ?? "No summary reported."}</p>
                <time>{item.latest_activity_at ? formatDateTime(item.latest_activity_at) : "No activity"}</time>
              </article>
            ))}
          </div>
        ) : <div className="empty-panel"><h3>No Workflow Progress yet</h3><p>Run Literature Search locally, then upload its bounded Progress Report.</p></div>}
      </section>

      <details className="technical-details">
        <summary>Technical details</summary>
        <dl>
          <div><dt>Project ID</dt><dd><code>{data.project_id}</code></dd></div>
          <div><dt>Manifest revision</dt><dd>{projection.manifest_revision}</dd></div>
          <div><dt>Created</dt><dd>{formatDateTime(data.created_at)}</dd></div>
          {data.current_package ? <div><dt>Legacy Package checksum</dt><dd><code>{data.current_package.package_checksum}</code></dd></div> : null}
        </dl>
      </details>
    </div>
  );
}
