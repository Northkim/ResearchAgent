"use client";

import Link from "next/link";

import { useApprovals, useRuns, useWorkflows } from "@/api/hooks";

import { PageHeader } from "./page-header";
import { ErrorState, LoadingState } from "./query-state";
import { RunList } from "./run-list";
import { WorkflowList } from "./workflow-list";

export function DashboardView() {
  const workflows = useWorkflows();
  const runs = useRuns({ limit: 6 });
  const approvals = useApprovals("PENDING");
  const activeRuns = runs.data?.runs.filter((run) =>
    ["RUNNING", "INITIALIZING", "WAITING_FOR_APPROVAL", "RETRY_SCHEDULED"].includes(
      run.status,
    ),
  ).length ?? 0;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Research command center"
        title="Keep every research run legible."
        description="Launch a governed workflow, follow every execution boundary, and step in exactly when human judgment is required."
        action={
          <Link href="/workflows" className="button button-primary">
            Start a research run
          </Link>
        }
      />

      <section className="metric-strip" aria-label="Workspace summary">
        <article>
          <span>Available workflows</span>
          <strong>{workflows.data?.length ?? "—"}</strong>
          <small>Version-pinned definitions</small>
        </article>
        <article>
          <span>Active runs</span>
          <strong>{runs.data ? activeRuns : "—"}</strong>
          <small>Running or awaiting action</small>
        </article>
        <article className={(approvals.data?.total ?? 0) > 0 ? "metric-attention" : ""}>
          <span>Pending approvals</span>
          <strong>{approvals.data?.total ?? "—"}</strong>
          <small>{approvals.data?.total ? "Reviewer attention needed" : "No gates waiting"}</small>
        </article>
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Workflow library</p>
            <h2>Ready to investigate</h2>
          </div>
          <Link href="/workflows" className="text-link">View catalog →</Link>
        </div>
        {workflows.isLoading ? <LoadingState label="Loading workflows" /> : null}
        {workflows.isError && !workflows.data ? <ErrorState /> : null}
        {workflows.data ? <WorkflowList workflows={workflows.data.slice(0, 3)} /> : null}
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Execution ledger</p>
            <h2>Recent runs</h2>
          </div>
          <span className="section-caption">Newest first · durable status</span>
        </div>
        {runs.isLoading ? <LoadingState label="Loading recent runs" /> : null}
        {runs.isError ? <ErrorState /> : null}
        {runs.data ? <RunList runs={runs.data.runs} /> : null}
      </section>
    </div>
  );
}
