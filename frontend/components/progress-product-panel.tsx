"use client";

import Link from "next/link";

import { useProgressReports, useProject, useProjectProgress } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";

import { PageHeader } from "./page-header";
import { ErrorState, LoadingState } from "./query-state";

const roundStates = [
  "Package not generated",
  "Ready for local execution",
  "Local round pending",
  "Upload pending",
  "Round completed",
  "Round failed",
];

function countLine(items: string[], prefix: string): string {
  return items.find((item) => item.startsWith(`${prefix}:`))?.split(":", 2)[1]?.trim() ?? "—";
}

export function ProgressProductPanel({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  const history = useProgressReports(projectId);
  const hasAccepted = history.data?.some((report) => report.accepted_for_projection) ?? false;
  const progress = useProjectProgress(projectId, hasAccepted);

  if (project.isLoading || history.isLoading) return <LoadingState label="Loading Literature Search progress" />;
  if (project.isError || !project.data) return <ErrorState title="Project unavailable" />;
  if (history.isError) return <ErrorState title="Progress history unavailable" />;

  const latestAccepted = [...(history.data ?? [])]
    .filter((report) => report.accepted_for_projection && report.normalized_record)
    .sort((left, right) => right.received_at.localeCompare(left.received_at))[0];
  const hasRejected = history.data?.some((report) => report.validation_status === "REJECTED") ?? false;
  const currentState = !project.data.current_package
    ? "Package not generated"
    : progress.data?.latest_status === "COMPLETED"
      ? "Round completed"
      : hasRejected
        ? "Round failed"
        : hasAccepted
          ? "Local round pending"
          : "Ready for local execution";
  const completedWork = progress.data?.completed_work_summary ?? [];
  const evidenceLimitation = latestAccepted?.normalized_record?.warnings.find((warning) => /metadata|abstract|full text/i.test(warning));

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Literature Search result"
        title={`${project.data.name} progress`}
        description="This page displays the bounded summary uploaded by the local Package. ReAgent did not generate or store the complete literature report."
        action={<Link href={`/projects/${projectId}`} className="button button-ghost">Project overview</Link>}
      />

      <section className="round-state-machine" aria-label="Literature Search round state">
        {roundStates.map((state) => <div key={state} className={state === currentState ? "active" : ""}><span aria-hidden="true" />{state}</div>)}
      </section>

      {!hasAccepted ? (
        <section className="progress-empty">
          <p className="eyebrow">Current state · {currentState}</p>
          <h2>{project.data.current_package ? "Run the extracted Package locally" : "Generate the Workflow Package first"}</h2>
          <p>The one-command workflow automatically uploads and verifies its Progress Report. If an upload is interrupted, rerunning the command performs upload-only recovery.</p>
          <Link href={`/projects/${projectId}/${project.data.current_package ? "guide" : "package"}`} className="button button-primary">{project.data.current_package ? "Read run guide" : "Generate Package"}</Link>
        </section>
      ) : null}
      {progress.isLoading ? <LoadingState label="Building progress projection" /> : null}
      {progress.isError ? <ErrorState title="Progress projection unavailable" /> : null}
      {progress.data ? (
        <>
          <section className="result-summary-card">
            <div><p className="eyebrow">Round {progress.data.latest_execution_round} · {progress.data.latest_status}</p><h2>{progress.data.current_state_summary}</h2><p>Updated {formatDateTime(progress.data.latest_upload_timestamp)}</p></div>
            <div className="result-counts">
              <div><span>Queries</span><strong>{countLine(completedWork, "Queries performed")}</strong></div>
              <div><span>Candidates</span><strong>{countLine(completedWork, "Candidates retained")}</strong></div>
              <div><span>Selected</span><strong>{countLine(completedWork, "Papers selected")}</strong></div>
            </div>
          </section>
          <section className="progress-sections">
            <article><p className="eyebrow">Evidence limitation</p><p>{evidenceLimitation ?? "No evidence limitation was supplied."}</p></article>
            <article><p className="eyebrow">Next recommended action</p><p>{progress.data.next_recommended_action}</p></article>
            <article className="wide"><p className="eyebrow">Local output references</p>{progress.data.output_artifacts.length ? <ul>{progress.data.output_artifacts.map((output) => <li key={output.relative_path}><code>{output.relative_path}</code><span>{output.artifact_kind}</span><code>{output.checksum}</code></li>)}</ul> : <p>No output references reported.</p>}<p className="boundary-caption">Names and checksums are retained here; complete artifact contents remain in the local Package.</p></article>
          </section>
          <section className="issue-grid" aria-label="Warnings and errors">
            <article><h2>Warnings ({progress.data.warning_count})</h2>{latestAccepted?.normalized_record?.warnings.length ? <ul>{latestAccepted.normalized_record.warnings.map((item) => <li key={item}>{item}</li>)}</ul> : <p>No warnings reported.</p>}</article>
            <article><h2>Errors ({progress.data.error_count})</h2>{latestAccepted?.normalized_record?.errors.length ? <ul>{latestAccepted.normalized_record.errors.map((item) => <li key={item}>{item}</li>)}</ul> : <p>No errors reported.</p>}</article>
          </section>
        </>
      ) : null}
      {(history.data?.length ?? 0) > 0 ? (
        <section className="report-history">
          <div className="section-heading"><div><p className="eyebrow">Immutable history</p><h2>Progress Report receipts</h2></div><span className="section-caption">{history.data?.length} retained</span></div>
          <ol>{[...(history.data ?? [])].reverse().map((report) => <li key={report.receipt_id}><div><strong>Round {report.normalized_record?.execution_round ?? "—"}</strong><span>{report.validation_status} · {report.chain_state}</span></div><div><span>Report</span><code>{report.report_id}</code></div><div><span>Upload receipt</span><code>{report.receipt_id}</code></div><time>{formatDateTime(report.received_at)}</time>{report.validation_warnings.length ? <p>{report.validation_warnings.join(" · ")}</p> : null}{report.validation_errors.length ? <p className="form-error">{report.validation_errors.join(" · ")}</p> : null}</li>)}</ol>
        </section>
      ) : null}
    </div>
  );
}
