"use client";

import Link from "next/link";

import { useResumeRun, useRun, useRunEvents } from "@/api/hooks";

import { EventTimeline } from "./event-timeline";
import { PageHeader } from "./page-header";
import { ErrorState, LoadingState } from "./query-state";
import { RunStatusPanel } from "./run-status-panel";
import { ResearchResults } from "./research-results";
import { StepProgress } from "./step-progress";

export function RunDetailClient({ runId }: { runId: string }) {
  const run = useRun(runId);
  const events = useRunEvents(runId);
  const resume = useResumeRun(runId);

  if (run.isLoading) return <LoadingState label="Loading run state" />;
  if (run.isError || !run.data) {
    return <ErrorState title="Run could not be loaded" message={run.error?.message} />;
  }

  const canResume = ["CREATED", "RETRY_SCHEDULED"].includes(run.data.status);
  const waitingApproval = run.data.status === "WAITING_FOR_APPROVAL";

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Run ledger"
        title="Execution, without the black box."
        description="The aggregate status, step attempts, and append-only event stream are read from independent backend query contracts."
        action={
          waitingApproval ? (
            <Link className="button button-primary" href="/approvals">Review approval</Link>
          ) : canResume ? (
            <button
              className="button button-primary"
              onClick={() => resume.mutate()}
              disabled={resume.isPending}
            >
              {resume.isPending ? "Submitting…" : "Continue run"}
            </button>
          ) : (
            <span className="live-caption"><span className="live-dot" /> Auto-refreshing</span>
          )
        }
      />

      {resume.isError ? <ErrorState title="Run could not continue" message={resume.error.message} /> : null}
      <RunStatusPanel run={run.data} />
      <ResearchResults
        runId={runId}
        isResearchV2={
          run.data.workflow_id === "guided-literature-review" &&
          run.data.workflow_version === "2.0.0"
        }
      />

      <div className="detail-grid">
        <StepProgress steps={run.data.steps} />
        <section className="detail-card timeline-card" aria-labelledby="timeline-title">
          <div className="card-heading">
            <div>
              <p className="eyebrow">Audit stream</p>
              <h2 id="timeline-title">Execution timeline</h2>
            </div>
            <span>{events.data?.length ?? 0} events</span>
          </div>
          {events.isLoading ? <LoadingState label="Loading event timeline" /> : null}
          {events.isError ? <ErrorState title="Timeline unavailable" message={events.error.message} /> : null}
          {events.data ? <EventTimeline events={events.data} /> : null}
        </section>
      </div>
    </div>
  );
}
