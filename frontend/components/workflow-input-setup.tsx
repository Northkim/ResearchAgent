"use client";

import { useState } from "react";

import {
  useBindArtifactDependency,
  useConfirmWorkflowInputSetup,
  useProjectArtifactReferences,
  useWorkflowInputSetup,
} from "@/api/hooks";
import { formatDateTime } from "@/lib/format";
import type { ArtifactDependencyEdge, ProjectWorkflowInstance, WorkflowArtifactRequirement, WorkflowInstanceProgress } from "@/types/api";

import { CopyCommand } from "./copy-command";
import { ArtifactPresentationPreview } from "./artifact-presentation";

function key(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `00000000-0000-4000-8000-${Math.floor(Math.random() * 0xffffffffffff).toString(16).padStart(12, "0")}`;
}

function RequirementChoice({ projectId, instance, instances, projections, requirement, dependencies }: {
  projectId: string;
  instance: ProjectWorkflowInstance;
  instances: ProjectWorkflowInstance[];
  projections: WorkflowInstanceProgress[];
  requirement: WorkflowArtifactRequirement;
  dependencies: ArtifactDependencyEdge[];
}) {
  const artifacts = useProjectArtifactReferences(projectId, requirement.artifact_type);
  const bind = useBindArtifactDependency(projectId, instance.workflow_instance_id);
  const [selected, setSelected] = useState("");
  const active = dependencies.find((edge) => edge.state === "ACTIVE" && edge.requirement_key === requirement.requirement_key);
  const choices = artifacts.data?.artifacts ?? [];
  const effective = selected || active?.artifact_id || (choices.length === 1 ? choices[0].artifact_id : "");

  return (
    <fieldset>
      <legend>{requirement.requirement_key.replaceAll("_", " ")} {requirement.required ? "· required" : "· optional"}</legend>
      {artifacts.isLoading ? <p>Loading compatible results…</p> : null}
      {!artifacts.isLoading && choices.length === 0 ? <p>{requirement.required ? "Complete an upstream workflow to produce this required result." : "No optional result is available yet; this does not block the run."}</p> : null}
      {choices.map((artifact) => {
        const producer = instances.find((item) => item.workflow_instance_id === artifact.producer_workflow_instance_id);
        const projection = projections.find((item) => item.workflow_instance_id === artifact.producer_workflow_instance_id);
        return (
          <label className="artifact-choice" key={artifact.artifact_id} data-artifact-id={artifact.artifact_id}>
            <input type="radio" name={`${instance.workflow_instance_id}-${requirement.requirement_key}`} checked={effective === artifact.artifact_id} onChange={() => setSelected(artifact.artifact_id)} />
            <span>
              {projection?.friendly_instance_label ?? producer?.display_name ?? "Upstream workflow"} · {formatDateTime(artifact.produced_at)}
              <small>{projection?.core_capability_maturity === "SCAFFOLD_CORE" ? "Scaffold Core" : "Reviewed Core"} · result …{artifact.artifact_id.slice(-8)}</small>
            </span>
            {["selected-paper-library/v1", "selected-research-idea/v1", "experiment-record/v5", "manuscript-draft/v4", "review-report/v3", "manuscript-draft/v5"].includes(artifact.artifact_type) ? <ArtifactPresentationPreview artifact={artifact} compact selection /> : null}
          </label>
        );
      })}
      {choices.length ? (
        <button className="button button-secondary" disabled={!effective || bind.isPending || effective === active?.artifact_id} onClick={async () => {
          await bind.mutateAsync({ artifactId: effective, requirementKey: requirement.requirement_key, replaceBindingId: active?.binding_id, idempotencyKey: key() });
          setSelected("");
        }}>
          {active ? "Confirm changed input" : "Confirm exact input"}
        </button>
      ) : null}
    </fieldset>
  );
}

export function WorkflowInputSetup({ projectId, instance, instances, projections, requirements, dependencies }: {
  projectId: string;
  instance: ProjectWorkflowInstance;
  instances: ProjectWorkflowInstance[];
  projections: WorkflowInstanceProgress[];
  requirements: WorkflowArtifactRequirement[];
  dependencies: ArtifactDependencyEdge[];
}) {
  const setup = useWorkflowInputSetup(projectId, instance.workflow_instance_id);
  const confirmSetup = useConfirmWorkflowInputSetup(
    projectId,
    instance.workflow_instance_id,
  );
  if (!requirements.length) return null;
  const sameType = instances.filter((item) => item.workflow_definition_id === instance.workflow_definition_id && item.desired_state === "ACTIVE");
  const selector = sameType.length === 1 ? `--workflow ${instance.workflow_definition_id}` : `--workflow-instance ${instance.workflow_instance_id}`;
  const omitted = setup.data?.omitted_optional_requirement_keys ?? [];
  const setupReady = setup.data
    ? !setup.data.decision_required || Boolean(setup.data.current_decision)
    : false;
  return (
    <div className="boundary-callout" aria-label="Exact workflow input setup">
      <strong>Exact Artifact inputs</strong>
      <p>Select each result explicitly. ReAgent never binds “latest” automatically.</p>
      {requirements.map((requirement) => <RequirementChoice key={requirement.requirement_key} {...{ projectId, instance, instances, projections, requirement, dependencies }} />)}
      {setup.data?.decision_required && !setup.data.current_decision ? (
        <div className="input-setup-decision">
          <p>{omitted.length === 1 ? "One optional evidence source is not selected." : `${omitted.length} optional evidence sources are not selected.`}</p>
          <button
            type="button"
            className="button button-primary"
            disabled={confirmSetup.isPending}
            onClick={() => confirmSetup.mutate({
              omittedOptionalRequirementKeys: omitted,
              idempotencyKey: key(),
            })}
          >
            {confirmSetup.isPending ? "Saving decision…" : "Continue without optional evidence"}
          </button>
        </div>
      ) : setup.data?.current_decision ? (
        <p>Optional evidence was intentionally left unselected for this pass.</p>
      ) : null}
      {dependencies.some((edge) => edge.state === "ACTIVE") && setupReady ? (
        <div>
          <p>Prepare verified local copies of the selected research inputs:</p>
          <CopyCommand command={`python reagent_local.py artifact materialize . ${selector}`} label="input materialization command" />
        </div>
      ) : null}
    </div>
  );
}
