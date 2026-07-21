import Link from "next/link";

import { formatDateTime, truncateId } from "@/lib/format";
import type { WorkflowRunSummary } from "@/types/api";

import { EmptyState } from "./query-state";
import { StatusBadge } from "./status-badge";

export function RunList({ runs }: { runs: WorkflowRunSummary[] }) {
  if (!runs.length) {
    return (
      <EmptyState
        title="No runs yet"
        message="Choose a workflow to create your first research run."
      />
    );
  }

  return (
    <div className="run-table-wrap">
      <table className="run-table">
        <thead>
          <tr>
            <th>Run</th>
            <th>Workflow</th>
            <th>Status</th>
            <th>Created</th>
            <th aria-label="Open run" />
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td className="mono">{truncateId(run.id)}</td>
              <td>
                <strong>{run.workflow_name}</strong>
                <span>v{run.workflow_version}</span>
              </td>
              <td><StatusBadge status={run.status} /></td>
              <td>{formatDateTime(run.created_at)}</td>
              <td>
                <Link className="row-link" href={`/runs/${run.id}`} aria-label={`Open ${run.workflow_name}`}>
                  →
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
