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

function cardinality(requirement: WorkflowResourceRequirement): string {
  if (requirement.cardinality_min === requirement.cardinality_max) {
    return `Exactly ${requirement.cardinality_min}`;
  }
  return `${requirement.cardinality_min}..${requirement.cardinality_max}`;
}

function human(value: string): string {
  return value.replaceAll("_", " ").toLocaleLowerCase();
}

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
    item.resource_kind === selectedRequirement?.resource_kind
    && selectedRequirement.allowed_providers.includes(item.provider)
  )) ?? [];
  const requiredMissing = requirements.filter((requirement) => (
    requirement.required
    && !activeBindings.some((binding) => binding.requirement_key === requirement.requirement_key)
  ));
  const experimentPackageRequirement = requirements.find((requirement) => (
    requirement.resource_kind === "SOURCE_REPOSITORY"
    && requirement.required
    && requirement.cardinality_min === 1
    && requirement.cardinality_max === 1
    && requirement.allowed_providers.length === 1
    && requirement.allowed_providers[0] === "GITHUB"
  ));
  const ownerStagedPackage = Boolean(experimentPackageRequirement);
  const stageCommand = `python reagent_local.py resource stage . <package-path> --workflow-instance ${instance.workflow_instance_id}`;

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
    setNotice(ownerStagedPackage
      ? "Experiment Package source registered. Choose Use this source to bind it to this experiment."
      : "Source registered in Cloud. No external bytes were downloaded.");
  }

  async function bindReference() {
    if (!selectedResource || !selectedRequirement) return;
    await bind.mutateAsync({
      requirement_key: selectedRequirement.requirement_key,
      resource_id: selectedResource,
      idempotency_key: crypto.randomUUID(),
    });
    setNotice(ownerStagedPackage
      ? "Source selected for this experiment. Stage and verify the local package before running."
      : "Source selected. Resolve and verify it in the Local Workspace before use.");
  }

  return (
    <section id="resources" className="plain-section workflow-resource-section" aria-labelledby="workflow-resources-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Local prerequisite</p>
          <h2 id="workflow-resources-title">{ownerStagedPackage ? "Experiment Package" : "External Resources"}</h2>
        </div>
        <span>{requirements.some((item) => item.required) ? "Required" : "Optional"}</span>
      </div>

      {ownerStagedPackage ? (
        <>
          <p className="experiment-package-intro">This experiment requires one exact Experiment Package so the Local Runner can verify exactly what will run. The package stays in your Local Workspace. ReAgent does not download or clone repositories from this page.</p>

          <ol className="experiment-package-progress" aria-label="Experiment Package setup progression">
            <li>Prepare package</li>
            <li>Register or choose source</li>
            <li>Use this source</li>
            <li>Stage and verify locally</li>
            <li>Run experiment</li>
          </ol>

          <p className="experiment-package-state" role="status">
            {requiredMissing.length
              ? "This experiment cannot run yet because its required Experiment Package source has not been selected and the local package has not been staged."
              : "The source is selected. Stage and verify the local Experiment Package before running; Cloud cannot observe local staging."}
          </p>

          <div className="experiment-package-steps">
            <section aria-labelledby="experiment-package-step-1">
              <p className="step-label">Step 1</p>
              <h3 id="experiment-package-step-1">Prepare your Experiment Package</h3>
              <p>Prepare the package in your Local Workspace. The browser does not upload or execute it.</p>
              <ul>
                <li><code>.reagent-experiment.json</code></li>
                <li>one relative Python entrypoint</li>
                <li>a supported Python runtime</li>
                <li>an environment or lock file</li>
                <li>bounded embedded data or configuration required by the experiment</li>
              </ul>
            </section>

            <section aria-labelledby="experiment-package-step-2">
              <p className="step-label">Step 2</p>
              <h3 id="experiment-package-step-2">Register or choose a source</h3>
              <p>This records which exact GitHub revision your local Experiment Package comes from. ReAgent does not clone or download the repository.</p>

              {activeBindings.length ? (
                <div className="selected-package-source">
                  <strong>Selected source</strong>
                  {activeBindings.map((item) => (
                    <div key={item.binding_id}>
                      <span>{item.resource.display_name}</span>
                      <small>GitHub repository {item.resource.locator} · commit <code>{item.resource.exact_revision}</code></small>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="registered-source-picker">
                  <label>
                    Registered sources
                    <select aria-label="Choose a registered source" value={selectedResource} onChange={(event) => setSelectedResource(event.target.value)}>
                      <option value="">Choose a registered source</option>
                      {compatible.map((item) => <option key={item.resource_id} value={item.resource_id}>{item.display_name} · {item.locator} · {item.exact_revision}</option>)}
                    </select>
                    <small>{compatible.length ? "Choose the exact source for this experiment." : "No compatible source is registered yet. Register one below."}</small>
                  </label>
                  <button className="button button-secondary" disabled={!selectedResource || bind.isPending} onClick={bindReference}>Use this source</button>
                </div>
              )}

              <details className="register-package-source">
                <summary>Register an Experiment Package source</summary>
                <div>
                  <p>This records source identity and provenance only. Your package bytes remain local.</p>
                  <div className="fixed-source-type"><span>Source type</span><strong>GitHub</strong><small>The current Experiment contract accepts GitHub sources only.</small></div>
                  <label>
                    Package name
                    <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
                    <small>A short name you will recognize when selecting this package source.</small>
                  </label>
                  <label>
                    GitHub repository
                    <input placeholder="owner/repository" value={locator} onChange={(event) => setLocator(event.target.value)} />
                    <small>Enter the repository identity as owner/repository. ReAgent will not clone it.</small>
                  </label>
                  <label>
                    Commit SHA
                    <input value={revision} onChange={(event) => setRevision(event.target.value)} />
                    <small>Use the exact immutable Git commit that corresponds to your local package.</small>
                  </label>
                  <label>
                    Package SHA-256
                    <input placeholder="sha256:…" value={checksum} onChange={(event) => setChecksum(event.target.value)} />
                    <small>Enter the expected SHA-256 for the complete local Experiment Package.</small>
                  </label>
                  <button className="button button-secondary" disabled={create.isPending || !displayName || !locator || !revision || !checksum} onClick={addReference}>Register source</button>
                </div>
              </details>
            </section>

            <section aria-labelledby="experiment-package-step-3">
              <p className="step-label">Step 3</p>
              <h3 id="experiment-package-step-3">Stage and verify locally</h3>
              <p>After selecting the source, stage the local Experiment Package from your Local Workspace. Replace <code>&lt;package-path&gt;</code> with its local directory.</p>
              <p className="exact-command-label">Local command template</p>
              <code>{stageCommand}</code>
              <p>The Local Runner verifies the package manifest and checksum. It blocks execution when the source is unresolved or the staged package has drifted. Run the experiment only after this command succeeds.</p>
            </section>
          </div>
        </>
      ) : (
        <>
          <div className="boundary-callout">
            <strong>Cloud stores source identity and provenance metadata only</strong>
            <p>Repository, dataset, model, checkpoint, credential, staging, verification, and drift-check bytes remain in the Local Workspace. ReAgent does not resolve GitHub or Hugging Face content over the network.</p>
          </div>
          {activeBindings.length ? (
            <div className="selected-package-source">
              <strong>Selected sources</strong>
              {activeBindings.map((item) => (
                <div key={item.binding_id}>
                  <span>{item.resource.display_name}</span>
                  <small>{human(item.requirement_key)} · {human(item.resource.provider)} · revision <code>{item.resource.exact_revision}</code> · local staging and verification remain pending</small>
                </div>
              ))}
            </div>
          ) : null}
          <div className="resource-binding-controls">
            <label>
              Requirement
              <select value={requirementKey} onChange={(event) => setRequirementKey(event.target.value)}>
                {requirements.map((item) => <option key={item.requirement_key} value={item.requirement_key}>{human(item.requirement_key)} · {item.required ? "required" : "optional"}</option>)}
              </select>
            </label>
            <label>
              Registered sources
              <select value={selectedResource} onChange={(event) => setSelectedResource(event.target.value)}>
                <option value="">Choose a registered source</option>
                {compatible.map((item) => <option key={item.resource_id} value={item.resource_id}>{item.display_name} · {item.provider} · {item.exact_revision}</option>)}
              </select>
            </label>
            <button className="button button-secondary" disabled={!selectedResource || bind.isPending} onClick={bindReference}>Use this source</button>
            {allowedExternalProviders.length ? (
              <details>
                <summary>Register a source</summary>
                <label>Provider<select value={effectiveProvider} onChange={(event) => setProvider(event.target.value as typeof provider)}>{allowedExternalProviders.map((item) => <option key={item}>{item.replaceAll("_", " ")}</option>)}</select></label>
                <label>Source name<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
                <label>Source locator<input value={locator} onChange={(event) => setLocator(event.target.value)} /></label>
                <label>Exact revision<input value={revision} onChange={(event) => setRevision(event.target.value)} /></label>
                <label>Expected SHA-256<input value={checksum} onChange={(event) => setChecksum(event.target.value)} /></label>
                <button className="button button-secondary" disabled={create.isPending || !displayName || !locator || !revision || !checksum} onClick={addReference}>Register source</button>
              </details>
            ) : null}
          </div>
        </>
      )}

      <details className="technical-details resource-technical-details">
        <summary>Technical details</summary>
        <dl>
          {requirements.map((requirement) => (
            <div key={requirement.requirement_key}>
              <dt>Requirement</dt>
              <dd><code>{requirement.requirement_key}</code> · <code>{requirement.resource_kind}</code> · required=<code>{String(requirement.required)}</code> · cardinality {cardinality(requirement)} · provider={requirement.allowed_providers.join(",")}</dd>
            </div>
          ))}
          {compatible.map((item) => <div key={item.resource_id}><dt>Resource</dt><dd><code>{item.resource_id}</code> · revision <code>{item.exact_revision}</code> · checksum <code>{item.expected_content_checksum}</code></dd></div>)}
          {activeBindings.map((item) => <div key={item.binding_id}><dt>Binding</dt><dd><code>{item.binding_id}</code> → <code>{item.resource_id}</code></dd></div>)}
        </dl>
      </details>
      {notice ? <p role="status">{notice}</p> : null}
      {(resources.isError || bindings.isError || create.isError || bind.isError) ? <p role="alert">Package source information could not be updated. No local bytes changed.</p> : null}
    </section>
  );
}
