import { formatDateTime, truncateId } from "@/lib/format";
import type { WorkflowRun } from "@/types/api";

import { StatusBadge } from "./status-badge";

export function RunStatusPanel({ run }: { run: WorkflowRun }) {
  const outputs = Object.entries(run.outputs);

  return (
    <div className="run-result-stack">
      <section className="run-status-panel" aria-labelledby="run-status-title">
        <div className="run-status-primary">
          <div>
            <p className="eyebrow">Current state</p>
            <h2 id="run-status-title">{run.workflow_id.replaceAll("-", " ")}</h2>
            <p className="mono">Run {truncateId(run.id)} · workflow v{run.workflow_version}</p>
          </div>
          <StatusBadge status={run.status} />
        </div>
        <dl className="run-facts">
          <div><dt>Completed steps</dt><dd>{run.completed_steps.length}/{run.steps.length}</dd></div>
          <div><dt>Checkpoints</dt><dd>{run.checkpoint_count}</dd></div>
          <div><dt>Updated</dt><dd>{formatDateTime(run.updated_at)}</dd></div>
          <div><dt>Project</dt><dd>{run.project_id}</dd></div>
        </dl>
        {run.wait_reason ? <p className="run-notice">Waiting reason: {run.wait_reason}</p> : null}
        {run.error_code ? <p className="run-notice run-notice-error">Error: {run.error_code}</p> : null}
      </section>

      {outputs.length > 0 ? (
        <section className="run-output-panel" aria-labelledby="run-output-title">
          <div>
            <p className="eyebrow">Durable result</p>
            <h2 id="run-output-title">Research output</h2>
          </div>
          <dl>
            {outputs.map(([name, value]) => (
              <div key={name}>
                <dt>{name.replaceAll("_", " ")}</dt>
                <dd>{typeof value === "string" ? value : JSON.stringify(value, null, 2)}</dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}
    </div>
  );
}
