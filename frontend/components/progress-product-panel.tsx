"use client";

import Link from "next/link";

import { useProgressReports, useProject, useProjectProgress } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";

import { PageHeader } from "./page-header";
import { EmptyState, ErrorState, LoadingState } from "./query-state";

export function ProgressProductPanel({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  const history = useProgressReports(projectId);
  const hasAccepted = history.data?.some((report) => report.accepted_for_projection) ?? false;
  const progress = useProjectProgress(projectId, hasAccepted);

  if (project.isLoading || history.isLoading) return <LoadingState label="Loading uploaded local progress" />;
  if (project.isError || !project.data) return <ErrorState title="Project unavailable" />;
  if (history.isError) return <ErrorState title="Progress history unavailable" />;

  const latestAccepted = [...(history.data ?? [])]
    .filter((report) => report.accepted_for_projection && report.normalized_record)
    .sort((left, right) => right.received_at.localeCompare(left.received_at))[0];

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Uploaded local Progress Reports"
        title={`${project.data.name} progress`}
        description="This is a deterministic cloud projection of reports explicitly produced and uploaded from the local Package. It is not a Hosted execution timeline."
        action={<Link href={`/projects/${projectId}`} className="button button-ghost">Project overview</Link>}
      />
      {!hasAccepted ? (
        <EmptyState
          title="No accepted Progress Report yet"
          message="Complete one local Codex round, finalize and validate its report, then upload it explicitly with the committed client."
        />
      ) : null}
      {progress.isLoading ? <LoadingState label="Building progress projection" /> : null}
      {progress.isError ? <ErrorState title="Progress projection unavailable" /> : null}
      {progress.data ? (
        <>
          <section className="progress-hero" aria-label="Current project progress">
            <div><span>Round</span><strong>{progress.data.latest_execution_round}</strong></div>
            <div><span>Status</span><strong>{progress.data.latest_status}</strong></div>
            <div><span>Chain</span><strong>{progress.data.chain_state}</strong></div>
            <div><span>Updated</span><strong>{formatDateTime(progress.data.latest_upload_timestamp)}</strong></div>
          </section>
          <section className="progress-sections">
            <article>
              <p className="eyebrow">Completed work</p>
              <ul>{progress.data.completed_work_summary.map((item) => <li key={item}>{item}</li>)}</ul>
            </article>
            <article>
              <p className="eyebrow">Current state</p>
              <p>{progress.data.current_state_summary}</p>
            </article>
            <article>
              <p className="eyebrow">Next recommended action</p>
              <p>{progress.data.next_recommended_action}</p>
            </article>
            <article>
              <p className="eyebrow">Outputs</p>
              {progress.data.output_artifacts.length ? (
                <ul>{progress.data.output_artifacts.map((output) => <li key={output.relative_path}><code>{output.relative_path}</code> · {output.artifact_kind}</li>)}</ul>
              ) : <p>No output references reported.</p>}
            </article>
          </section>
          <section className="issue-grid" aria-label="Warnings and errors">
            <article>
              <h2>Warnings ({progress.data.warning_count})</h2>
              {latestAccepted?.normalized_record?.warnings.length ? <ul>{latestAccepted.normalized_record.warnings.map((item) => <li key={item}>{item}</li>)}</ul> : <p>No warnings reported.</p>}
            </article>
            <article>
              <h2>Errors ({progress.data.error_count})</h2>
              {latestAccepted?.normalized_record?.errors.length ? <ul>{latestAccepted.normalized_record.errors.map((item) => <li key={item}>{item}</li>)}</ul> : <p>No errors reported.</p>}
            </article>
          </section>
        </>
      ) : null}
      {(history.data?.length ?? 0) > 0 ? (
        <section className="report-history">
          <div className="section-heading"><div><p className="eyebrow">Immutable history</p><h2>Progress Report receipts</h2></div><span className="section-caption">{history.data?.length} retained</span></div>
          <ol>
            {[...(history.data ?? [])].reverse().map((report) => (
              <li key={report.receipt_id}>
                <div><strong>Round {report.normalized_record?.execution_round ?? "—"}</strong><span>{report.validation_status} · {report.chain_state}</span></div>
                <code>{report.report_id}</code>
                <time>{formatDateTime(report.received_at)}</time>
                {report.validation_warnings.length ? <p>{report.validation_warnings.join(" · ")}</p> : null}
                {report.validation_errors.length ? <p className="form-error">{report.validation_errors.join(" · ")}</p> : null}
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </div>
  );
}
