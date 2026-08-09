"use client";

import { useState } from "react";

import {
  useBindWorkflowResource,
  useCreateProjectResource,
  useProjectResources,
  useWorkflowResourceBindings,
} from "@/api/hooks";
import type { ProjectWorkflowInstance, WorkflowResourceRequirement } from "@/types/api";

const EXTERNAL_PROVIDERS = ["GITHUB", "HUGGING_FACE"] as const;

export function WorkflowResourceSetup({
  projectId,
  instance,
  requirements,
}: {
  projectId: string;
  instance: ProjectWorkflowInstance;
  requirements: WorkflowResourceRequirement[];
}) {
  const resources = useProjectResources(projectId);
  const bindings = useWorkflowResourceBindings(projectId, instance.workflow_instance_id);
  const create = useCreateProjectResource(projectId);
  const bind = useBindWorkflowResource(projectId, instance.workflow_instance_id);
  const [requirementKey, setRequirementKey] = useState(requirements[0]?.requirement_key ?? "");
  const selectedRequirement = requirements.find((item) => item.requirement_key === requirementKey);
  const [provider, setProvider] = useState<(typeof EXTERNAL_PROVIDERS)[number]>("GITHUB");
  const [locator, setLocator] = useState("");
  const [revision, setRevision] = useState("");
  const [checksum, setChecksum] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [selectedResource, setSelectedResource] = useState("");
  const [notice, setNotice] = useState("");

  if (!requirements.length) return null;
  const allowedExternalProviders = EXTERNAL_PROVIDERS.filter((item) =>
    selectedRequirement?.allowed_providers.includes(item),
  );
  const effectiveProvider = allowedExternalProviders.includes(provider)
    ? provider
    : (allowedExternalProviders[0] ?? "GITHUB");
  const activeBindings = bindings.data?.items.filter((item) => item.state === "ACTIVE") ?? [];
  const compatible = resources.data?.items.filter((item) => (
    item.resource_kind === selectedRequirement?.resource_kind &&
    selectedRequirement.allowed_providers.includes(item.provider)
  )) ?? [];

  async function addReference() {
    if (!selectedRequirement) return;
    const created = await create.mutateAsync({
      resource_kind: selectedRequirement.resource_kind,
      provider: effectiveProvider,
      locator,
      exact_revision: revision,
      expected_content_checksum: checksum,
      display_name: displayName,
      metadata: {},
    });
    setSelectedResource(created.resource_id);
    setNotice("Reference metadata saved in Cloud. No external bytes were downloaded.");
  }

  async function bindReference() {
    if (!selectedResource || !selectedRequirement) return;
    await bind.mutateAsync({
      requirement_key: selectedRequirement.requirement_key,
      resource_id: selectedResource,
      idempotency_key: crypto.randomUUID(),
    });
    setNotice("Exact Resource reference bound. Resolve and verify it in the Local Workspace before use.");
  }

  return (
    <details className="technical-details" aria-label="External Resource setup">
      <summary>External Resources · optional</summary>
      <div className="boundary-callout">
        <strong>Resource references are not research results or Skills</strong>
        <p>ReAgent Cloud stores only provider, locator, exact immutable revision, and expected checksum. It never stores repository, dataset, model, checkpoint, or credential bytes.</p>
        <p><strong>Resolver boundary:</strong> GitHub and Hugging Face network resolution is not implemented in this scaffold version.</p>
      </div>
      {activeBindings.length ? (
        <ul>
          {activeBindings.map((item) => (
            <li key={item.binding_id}>
              {item.requirement_key.replaceAll("_", " ")} · {item.resource.display_name} · {item.resource.provider.replaceAll("_", " ")} · revision <code>{item.resource.exact_revision}</code>
              <br /><small>Bound in Cloud; local resolution is not claimed.</small>
            </li>
          ))}
        </ul>
      ) : <p>No Resource is configured. Experiment remains runnable because all Resource requirements are optional.</p>}
      <label>
        Requirement
        <select value={requirementKey} onChange={(event) => setRequirementKey(event.target.value)}>
          {requirements.map((item) => <option key={item.requirement_key} value={item.requirement_key}>{item.requirement_key.replaceAll("_", " ")} · optional</option>)}
        </select>
      </label>
      <label>
        Existing compatible reference
        <select value={selectedResource} onChange={(event) => setSelectedResource(event.target.value)}>
          <option value="">Choose an exact Resource</option>
          {compatible.map((item) => <option key={item.resource_id} value={item.resource_id}>{item.display_name} · {item.provider} · {item.exact_revision}</option>)}
        </select>
      </label>
      <button className="button button-secondary" disabled={!selectedResource || bind.isPending} onClick={bindReference}>Bind exact Resource</button>
      <details>
        <summary>Add reference metadata</summary>
        <label>Provider<select value={effectiveProvider} onChange={(event) => setProvider(event.target.value as typeof provider)}>{allowedExternalProviders.map((item) => <option key={item}>{item.replaceAll("_", " ")}</option>)}</select></label>
        <label>Display name<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
        <label>Provider locator<input placeholder="owner/repository" value={locator} onChange={(event) => setLocator(event.target.value)} /></label>
        <label>Exact immutable revision<input value={revision} onChange={(event) => setRevision(event.target.value)} /></label>
        <label>Expected SHA-256 checksum<input placeholder="sha256:…" value={checksum} onChange={(event) => setChecksum(event.target.value)} /></label>
        <button className="button button-secondary" disabled={create.isPending || !displayName || !locator || !revision || !checksum} onClick={addReference}>Save metadata reference</button>
      </details>
      {notice ? <p role="status">{notice}</p> : null}
      {(resources.isError || bindings.isError || create.isError || bind.isError) ? <p role="alert">Resource metadata could not be updated. No local bytes changed.</p> : null}
    </details>
  );
}
