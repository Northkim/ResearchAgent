"use client";

import { useState } from "react";

import {
  useBindArtifactDependency,
  useProjectArtifactReferences,
} from "@/api/hooks";
import { formatDateTime } from "@/lib/format";
import type { ArtifactDependencyEdge, ProjectWorkflowInstance } from "@/types/api";

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
  const artifacts = useProjectArtifactReferences(projectId, ARTIFACT_TYPE);
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

  async function selectArtifact() {
    if (!selection) return;
    setNotice(null);
    try {
      await bind.mutateAsync({
        artifactId: selection,
        replaceBindingId: activeBinding?.binding_id,
        idempotencyKey: idempotencyKey(),
      });
      setNotice("Specific Artifact and checksum bound. Materialization remains an explicit local step.");
    } catch {
      setNotice("The dependency changed or could not be bound. Refresh and review the current selection.");
    }
  }

  return (
    <div className="boundary-callout" aria-label="Idea Discovery input setup">
      <strong>Required input · Selected paper library</strong>
      <dl className="workflow-card-details">
        <div><dt>Cloud desired</dt><dd>{instance.in_current_manifest ? "Yes" : "No"}</dd></div>
        <div><dt>Local installation</dt><dd>{installationState}</dd></div>
        <div><dt>Dependency</dt><dd>{activeBinding ? "Bound to a specific Artifact" : "Not bound"}</dd></div>
        <div><dt>Materialization</dt><dd>Verified only by the local Workspace</dd></div>
      </dl>
      {boundArtifact ? (
        <p>
          Bound to Literature Search instance {short(boundArtifact.producer_workflow_instance_id)},
          checksum <code>{short(boundArtifact.content_checksum)}</code>.
        </p>
      ) : null}
      {artifacts.data.artifacts.length ? (
        <fieldset>
          <legend>Choose a specific compatible Artifact</legend>
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
                  checked={selection === artifact.artifact_id}
                  onChange={() => setSelection(artifact.artifact_id)}
                />
                <span>
                  {producer?.display_name ?? "Literature Search"} · Instance {short(artifact.producer_workflow_instance_id)}
                  {" · "}{formatDateTime(artifact.produced_at)} · <code>{short(artifact.content_checksum)}</code>
                </span>
              </label>
            );
          })}
          <button
            className="button button-secondary"
            disabled={!selection || bind.isPending || selection === activeBinding?.artifact_id}
            onClick={selectArtifact}
          >
            {activeBinding ? "Change explicit binding" : "Bind selected Artifact"}
          </button>
        </fieldset>
      ) : (
        <p>Idea Discovery requires a completed compatible Literature Search 0.4.0 Artifact.</p>
      )}
      {notice ? <p role="status">{notice}</p> : null}
      {activeBinding ? (
        <div>
          <p>Next, run these commands locally; this browser will not execute them:</p>
          <code>python reagent_local.py artifact materialize . --workflow-instance {instance.workflow_instance_id}</code>
          <br />
          <code>python reagent_local.py run . --workflow-instance {instance.workflow_instance_id}</code>
        </div>
      ) : null}
    </div>
  );
}
