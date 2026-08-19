"use client";

import { useState } from "react";

import {
  useBindArtifactDependency,
  useCompatibleArtifactReferences,
} from "@/api/hooks";
import { formatDateTime } from "@/lib/format";
import type { ArtifactDependencyEdge, ProjectWorkflowInstance } from "@/types/api";

import { CopyCommand } from "./copy-command";

const ARTIFACT_TYPE = "selected-paper-library/v1";

function short(value: string): string {
  return value.slice(-8);
}

function idempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  const suffix = Math.floor(Math.random() * 0xffffffffffff)
    .toString(16)
    .padStart(12, "0");
  return `00000000-0000-4000-8000-${suffix}`;
}

export function IdeaDiscoverySetup({
  projectId,
  instance,
  instances,
  installationState,
  dependencies,
}: {
  projectId: string;
  instance: ProjectWorkflowInstance;
  instances: ProjectWorkflowInstance[];
  installationState: string;
  dependencies: ArtifactDependencyEdge[];
}) {
  const artifacts = useCompatibleArtifactReferences(
    projectId,
    instance.workflow_instance_id,
    "paper_library",
  );
  const bind = useBindArtifactDependency(projectId, instance.workflow_instance_id);
  const [selection, setSelection] = useState<string>("");
  const [notice, setNotice] = useState<string | null>(null);

  if (artifacts.isLoading) {
    return <p className="section-caption">Loading required literature Artifacts…</p>;
  }
  if (artifacts.isError || !artifacts.data) {
    return <p className="form-error" role="alert">Input setup is temporarily unavailable.</p>;
  }

  const activeBinding = dependencies.find((item) => item.state === "ACTIVE");
  const boundArtifact = artifacts.data.artifacts.find(
    (item) => item.artifact_id === activeBinding?.artifact_id,
  );
  const effectiveSelection = selection || (
    artifacts.data.artifacts.length === 1 ? artifacts.data.artifacts[0].artifact_id : ""
  );
  const sameDefinitionActive = instances.filter(
    (item) => item.workflow_definition_id === instance.workflow_definition_id && item.desired_state === "ACTIVE",
  );
  const workflowSelector = sameDefinitionActive.length === 1
    ? `--workflow ${instance.workflow_definition_id}`
    : `--workflow-instance ${instance.workflow_instance_id}`;
  const installationLabel = ({
    ACKNOWLEDGED_CURRENT: "Installed and confirmed",
    ACK_PENDING: "Installed; Cloud confirmation pending",
    STALE: "Sync required",
    UNKNOWN: "Not confirmed locally",
  } as Record<string, string>)[installationState] ?? installationState;

  async function selectArtifact() {
    if (!effectiveSelection) return;
    setNotice(null);
    try {
      await bind.mutateAsync({
        artifactId: effectiveSelection,
        replaceBindingId: activeBinding?.binding_id,
        idempotencyKey: idempotencyKey(),
      });
      setNotice("Input selected. Next, prepare the verified copy in your Local Workspace.");
    } catch {
      setNotice("The input selection changed elsewhere or could not be saved. Refresh this page, review the current selection, then retry.");
    }
  }

  return (
    <div className="boundary-callout" aria-label="Idea Discovery input setup">
      <strong>Required input · Selected paper library</strong>
      <dl className="workflow-card-details">
        <div><dt>Cloud desired</dt><dd>{instance.in_current_manifest ? "Yes" : "No"}</dd></div>
        <div><dt>Local installation</dt><dd>{installationLabel}</dd></div>
        <div><dt>Input selection</dt><dd>{activeBinding ? "Selected" : "Required"}</dd></div>
        <div><dt>Local input</dt><dd>Verified only by the Local Workspace</dd></div>
      </dl>
      {boundArtifact ? (
        <div>
          <p>Selected result from Literature Search · {formatDateTime(boundArtifact.produced_at)}.</p>
          <details className="technical-details compact-technical-details">
            <summary>Input identity</summary>
            <dl>
              <div><dt>Producer instance</dt><dd><code>{boundArtifact.producer_workflow_instance_id}</code></dd></div>
              <div><dt>Checksum</dt><dd><code>{boundArtifact.content_checksum}</code></dd></div>
            </dl>
          </details>
        </div>
      ) : null}
      {artifacts.data.artifacts.length ? (
        <fieldset>
          <legend>Choose a specific Literature Search result</legend>
          {artifacts.data.artifacts.length === 1 ? <p className="section-caption">Recommended: this is the only compatible result. Confirm it explicitly below.</p> : null}
          {artifacts.data.artifacts.map((artifact) => {
            const producer = instances.find(
              (item) => item.workflow_instance_id === artifact.producer_workflow_instance_id,
            );
            return (
              <label key={artifact.artifact_id} className="artifact-choice">
                <input
                  type="radio"
                  name={`artifact-${instance.workflow_instance_id}`}
                  value={artifact.artifact_id}
                  checked={effectiveSelection === artifact.artifact_id}
                  onChange={() => setSelection(artifact.artifact_id)}
                />
                <span>
                  {producer?.display_name ?? "Literature Search"} · {formatDateTime(artifact.produced_at)}
                  <small>Result …{short(artifact.artifact_id)}</small>
                </span>
              </label>
            );
          })}
          <button
            className="button button-secondary"
            disabled={!effectiveSelection || bind.isPending || effectiveSelection === activeBinding?.artifact_id}
            onClick={selectArtifact}
          >
            {activeBinding ? "Confirm changed input" : "Confirm selected input"}
          </button>
        </fieldset>
      ) : (
        <div>
          <p>Idea Discovery needs a completed paper library containing at least one selected paper.</p>
          <p>If this Project only has legacy Literature Search 0.3.0, keep its history, add a new Literature Search Workflow, finish it, then return here.</p>
        </div>
      )}
      {notice ? <p role="status">{notice}</p> : null}
      {activeBinding ? (
        <div>
          <p>Input selected, but the browser cannot verify or copy local files. Run these commands inside the Local Workspace:</p>
          <CopyCommand command="python reagent_local.py artifact refresh ." label="Artifact refresh command" />
          <CopyCommand command={`python reagent_local.py artifact materialize . ${workflowSelector}`} label="input materialization command" />
          <CopyCommand command={`python reagent_local.py run . ${workflowSelector}`} label="Workflow run command" />
        </div>
      ) : null}
      <details className="technical-details compact-technical-details">
        <summary>Input contract details</summary>
        <dl>
          <div><dt>Artifact type</dt><dd><code>{ARTIFACT_TYPE}</code></dd></div>
          <div><dt>Selection</dt><dd>One exact result and checksum</dd></div>
        </dl>
        {activeBinding ? (
          <div>
            <p>Existing Workspace CLI compatibility:</p>
            <code>python reagent_local.py artifact materialize . --workflow-instance {instance.workflow_instance_id}</code>
            <br />
            <code>python reagent_local.py run . --workflow-instance {instance.workflow_instance_id}</code>
          </div>
        ) : null}
      </details>
    </div>
  );
}
