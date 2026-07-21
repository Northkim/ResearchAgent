import type { StepRun } from "@/types/api";

import { StatusBadge } from "./status-badge";

export function StepProgress({ steps }: { steps: StepRun[] }) {
  return (
    <section className="detail-card" aria-labelledby="step-progress-title">
      <div className="card-heading">
        <div>
          <p className="eyebrow">Workflow graph</p>
          <h2 id="step-progress-title">Step progress</h2>
        </div>
        <span>{steps.length} total</span>
      </div>
      <ol className="step-progress-list">
        {steps.map((step, index) => (
          <li key={step.id}>
            <span className="step-number">{String(index + 1).padStart(2, "0")}</span>
            <div className="step-copy">
              <strong>{step.step_id.replaceAll("_", " ")}</strong>
              <small>Attempt {step.attempt}</small>
            </div>
            <StatusBadge status={step.status} />
          </li>
        ))}
      </ol>
    </section>
  );
}
