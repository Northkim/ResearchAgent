"use client";

import { useState } from "react";
import Link from "next/link";

import { useProject, useProjectProgress } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";

import { PageHeader } from "./page-header";
import { ProjectNavigation } from "./project-navigation";
import { ErrorState, LoadingState } from "./query-state";
import { WorkflowStatusBadge } from "./workflow-status-badge";

const PAGE_SIZE = 20;

export function ProgressProductPanel({ projectId, initialWorkflowInstanceId }: {
  projectId: string;
  initialWorkflowInstanceId?: string;
}) {
  const [workflowInstanceId, setWorkflowInstanceId] = useState(initialWorkflowInstanceId ?? "");
  const [offset, setOffset] = useState(0);
  const project = useProject(projectId);
  const progress = useProjectProgress(projectId, {
    workflowInstanceId: workflowInstanceId || undefined,
    offset,
    limit: PAGE_SIZE,
  });

  if (project.isLoading || progress.isLoading) return <LoadingState label="Loading Project Progress" />;
  if (project.isError || !project.data || progress.isError || !progress.data) {
    return <ErrorState title="Project Progress unavailable" />;
  }

  const data = progress.data;
  const selected = workflowInstanceId
    ? data.instances.find((item) => item.workflow_instance_id === workflowInstanceId)
    : undefined;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Project Progress"
        title={`${project.data.name} history`}
        description="Progress Reports are bounded Cloud continuity records grouped by Workflow Instance. Complete research files remain in the Local Workspace."
        action={<Link href={`/projects/${projectId}/workflows`} className="button button-ghost">Workflow Board</Link>}
      />
      <ProjectNavigation projectId={projectId} active="Progress" />

      <section className="progress-summary-strip" aria-label="Project Progress summary">
        <div><span>Total reports</span><strong>{data.total_progress_report_count}</strong></div>
        <div><span>Active workflows</span><strong>{data.active_workflow_count}</strong></div>
        <div><span>Retired workflows</span><strong>{data.retired_workflow_count}</strong></div>
        <div><span>Latest activity</span><strong>{data.latest_project_activity_at ? formatDateTime(data.latest_project_activity_at) : "None"}</strong></div>
      </section>

      <section className="progress-toolbar" aria-label="Progress filters">
        <label htmlFor="workflow-progress-filter">Workflow Instance</label>
        <select
          id="workflow-progress-filter"
          value={workflowInstanceId}
          onChange={(event) => { setWorkflowInstanceId(event.target.value); setOffset(0); }}
        >
          <option value="">All workflows</option>
          {data.instances.map((instance) => (
            <option key={instance.workflow_instance_id} value={instance.workflow_instance_id}>
              {instance.friendly_instance_label ?? instance.instance_display_name} · {instance.workflow_instance_id.slice(-8)}
            </option>
          ))}
        </select>
        <span>{data.history_total} matching report{data.history_total === 1 ? "" : "s"}</span>
      </section>

      {selected ? (
        <section className="selected-progress-card">
          <div>
            <p className="eyebrow">Selected Workflow Instance</p>
            <h2>{selected.friendly_instance_label ?? selected.instance_display_name}</h2>
            <code>{selected.workflow_instance_id}</code>
          </div>
          <div className="workflow-badge-row">
            <WorkflowStatusBadge value={selected.lifecycle} dimension="lifecycle" />
            <WorkflowStatusBadge value={selected.core_capability_maturity} dimension="maturity" />
            <WorkflowStatusBadge value={selected.research_status} dimension="research" />
            <WorkflowStatusBadge value={selected.desired_state} dimension="desired" />
            <WorkflowStatusBadge value={selected.installation_state} dimension="installation" />
          </div>
          {selected.core_capability_maturity === "SCAFFOLD_CORE" ? (
            <p className="scaffold-warning">Product flow is functional. Research capability is placeholder.</p>
          ) : null}
          <p>{selected.latest_summary ?? "No Progress Report has been uploaded for this instance."}</p>
          {selected.next_recommended_action ? <p><strong>Next:</strong> {selected.next_recommended_action}</p> : null}
        </section>
      ) : null}

      {data.history.length ? (
        <section className="project-progress-history" aria-labelledby="progress-history-title">
          <div className="section-heading">
            <div><p className="eyebrow">Immutable history</p><h2 id="progress-history-title">Progress Report activity</h2></div>
            <span className="section-caption">Newest first · stable ordering</span>
          </div>
          <ol>
            {data.history.map((report) => {
              const instance = data.instances.find((item) => item.workflow_instance_id === report.workflow_instance_id);
              return (
                <li key={report.receipt_id}>
                  <div className="progress-history-heading">
                    <div>
                      <p className="eyebrow">{instance?.workflow_display_name ?? "Workflow"}</p>
                      <h3>{instance?.friendly_instance_label ?? instance?.instance_display_name ?? report.workflow_instance_id}</h3>
                      <code>Instance {report.workflow_instance_id.slice(-8)}</code>
                    </div>
                    <WorkflowStatusBadge value={report.normalized_record?.status ?? report.validation_status} dimension="research" />
                  </div>
                  <p>{report.normalized_record?.current_state ?? "No normalized summary is available."}</p>
                  {report.normalized_record?.next_recommended_action ? <p><strong>Next:</strong> {report.normalized_record.next_recommended_action}</p> : null}
                  {report.normalized_record?.output_artifacts.length ? (
                    <div className="artifact-metadata-list">
                      <strong>Local artifact metadata</strong>
                      <ul>{report.normalized_record.output_artifacts.map((artifact) => (
                        <li key={`${report.report_id}-${artifact.relative_path}`}><code>{artifact.relative_path}</code><span>{artifact.artifact_kind}</span><code>{artifact.checksum}</code></li>
                      ))}</ul>
                      <p className="boundary-caption">Cloud retains names and checksums only; these files remain local.</p>
                    </div>
                  ) : null}
                  <dl>
                    <div><dt>Round</dt><dd>{report.normalized_record?.execution_round ?? "—"}</dd></div>
                    <div><dt>Report</dt><dd><code>{report.report_id}</code></dd></div>
                    <div><dt>Receipt</dt><dd><code>{report.receipt_id}</code></dd></div>
                    <div><dt>Received</dt><dd>{formatDateTime(report.received_at)}</dd></div>
                  </dl>
                </li>
              );
            })}
          </ol>
          <div className="pagination-controls" aria-label="Progress pagination">
            <button className="button button-ghost" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>Previous</button>
            <span>{data.history_total ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, data.history_total)} of ${data.history_total}` : "0 reports"}</span>
            <button className="button button-ghost" disabled={!data.has_more_history} onClick={() => setOffset(offset + PAGE_SIZE)}>Next</button>
          </div>
        </section>
      ) : (
        <section className="progress-empty">
          <p className="eyebrow">Research Progress · Not started</p>
          <h2>No Progress Report received</h2>
          <p>The Workflow may not have been run, or its local upload may still be pending. ReAgent cannot inspect the Local Workspace.</p>
          <p><strong>Use the same Package for upload recovery.</strong> A retry keeps the original report identity and does not repeat Provider search.</p>
          <div className="button-row"><Link href={`/projects/${projectId}/help`} className="button button-primary">Read local workflow help</Link><Link href={`/projects/${projectId}/package`} className="button button-ghost">Legacy Package</Link></div>
        </section>
      )}
    </div>
  );
}
