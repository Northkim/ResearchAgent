"use client";

import type { WorkflowDefinition } from "@/types/api";

export function WorkflowList({
  workflows,
  selectedId,
  onSelect,
}: {
  workflows: WorkflowDefinition[];
  selectedId?: string;
  onSelect?: (workflow: WorkflowDefinition) => void;
}) {
  return (
    <div className="workflow-grid" aria-label="Available workflows">
      {workflows.map((workflow, index) => {
        const selected = selectedId === `${workflow.id}@${workflow.version}`;
        return (
          <article
            className={`workflow-card ${selected ? "workflow-card-selected" : ""}`}
            key={`${workflow.id}@${workflow.version}`}
            role="group"
            aria-label={`${workflow.name} version ${workflow.version}`}
          >
            <div className="workflow-card-topline">
              <span className="workflow-index">0{index + 1}</span>
              <span className="version-chip">v{workflow.version}</span>
            </div>
            <h2>{workflow.name}</h2>
            <p>
              {workflow.steps.length} stages · {Object.keys(workflow.input_schema).length}{" "}
              input{Object.keys(workflow.input_schema).length === 1 ? "" : "s"}
            </p>
            <ol className="mini-step-list">
              {workflow.steps.slice(0, 4).map((step) => (
                <li key={step.id}>
                  <span className={step.kind === "approval" ? "step-approval" : ""} />
                  {step.id.replaceAll("_", " ")}
                </li>
              ))}
            </ol>
            {onSelect ? (
              <button
                className={selected ? "button button-secondary" : "button button-ghost"}
                onClick={() => onSelect(workflow)}
                type="button"
              >
                {selected ? "Selected" : "Select workflow"}
              </button>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
