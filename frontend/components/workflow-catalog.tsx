"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useRef, useState } from "react";

import { useCreateAndRun, useWorkflows } from "@/api/hooks";
import type { CreateCatalogRunRequest, WorkflowDefinition } from "@/types/api";

import { PageHeader } from "./page-header";
import { EmptyState, ErrorState, LoadingState } from "./query-state";
import { WorkflowList } from "./workflow-list";

function idempotencyKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? `frontend:${crypto.randomUUID()}`
    : `frontend:${Date.now()}`;
}

function initialInputs(workflow: WorkflowDefinition): Record<string, string | boolean> {
  return Object.fromEntries(
    Object.entries(workflow.input_schema).filter(([, definition]) => !definition.internal).map(([name, definition]) => [
      name,
      definition.default === undefined ? (definition.type === "boolean" ? false : "") : String(definition.default),
    ]),
  );
}

function normalizeInputs(
  workflow: WorkflowDefinition,
  values: Record<string, string | boolean>,
): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(workflow.input_schema).filter(([, definition]) => !definition.internal).map(([name, definition]) => {
      const value = values[name];
      if (definition.type === "boolean") return [name, Boolean(value)];
      if (definition.type === "integer") return [name, Number.parseInt(String(value), 10)];
      if (definition.type === "number") return [name, Number.parseFloat(String(value))];
      if (definition.type === "array" || definition.type === "object") {
        return [name, JSON.parse(String(value)) as unknown];
      }
      return [name, String(value)];
    }),
  );
}

export function WorkflowCatalog() {
  const router = useRouter();
  const workflows = useWorkflows();
  const createAndRun = useCreateAndRun();
  const submitting = useRef(false);
  const [selected, setSelected] = useState<WorkflowDefinition | null>(null);
  const [projectId, setProjectId] = useState("prototype-project");
  const [actorId, setActorId] = useState("prototype-user");
  const [inputValues, setInputValues] = useState<Record<string, string | boolean>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const selectedKey = selected ? `${selected.id}@${selected.version}` : undefined;
  const inputEntries = useMemo(
    () => (selected ? Object.entries(selected.input_schema).filter(([, definition]) => !definition.internal) : []),
    [selected],
  );

  function selectWorkflow(workflow: WorkflowDefinition) {
    setSelected(workflow);
    setInputValues(initialInputs(workflow));
    setFormError(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected || submitting.current) return;
    submitting.current = true;
    setFormError(null);
    try {
      const payload: CreateCatalogRunRequest = {
        project_id: projectId,
        actor_user_id: actorId,
        idempotency_key: idempotencyKey(),
        agent_profile_ref: selected.version === "2.0.0"
          ? "deterministic-research-agent@2.0.0"
          : "deterministic-agent@1.0.0",
        workflow_id: selected.id,
        workflow_version: selected.version,
        inputs: normalizeInputs(selected, inputValues),
      };
      const run = await createAndRun.mutateAsync(payload);
      router.push(`/runs/${run.id}`);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Could not create the run");
    } finally {
      submitting.current = false;
    }
  }

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Workflow catalog"
        title="Choose how the agent should think."
        description="Each run pins an immutable workflow version. Select a reviewed sequence, provide its research inputs, and launch it through the same backend execution boundary."
      />

      {workflows.isLoading ? <LoadingState label="Loading workflow catalog" /> : null}
      {workflows.isError ? (
        <ErrorState message="The API catalog is unavailable. Confirm the backend and PostgreSQL services are healthy." />
      ) : null}
      {workflows.data?.length === 0 ? (
        <EmptyState
          title="No workflows are published"
          message="Run the documented demo Seeder, then refresh this catalog."
        />
      ) : null}
      {workflows.data && workflows.data.length > 0 ? (
        <WorkflowList
          workflows={workflows.data}
          selectedId={selectedKey}
          onSelect={selectWorkflow}
        />
      ) : null}

      <section className="launch-panel" aria-labelledby="launch-title">
        <div className="launch-copy">
          <p className="eyebrow">Run setup</p>
          <h2 id="launch-title">
            {selected ? `Launch ${selected.name}` : "Select a workflow to continue"}
          </h2>
          <p>
            The frontend creates the durable run, submits execution, then opens the live run ledger.
          </p>
        </div>

        {selected ? (
          <form className="launch-form" onSubmit={submit} aria-busy={createAndRun.isPending}>
            <div className="form-grid">
              <label>
                Project ID
                <input value={projectId} onChange={(event) => setProjectId(event.target.value)} required />
              </label>
              <label>
                Actor ID
                <input value={actorId} onChange={(event) => setActorId(event.target.value)} required />
              </label>
            </div>

            {inputEntries.map(([name, definition]) => (
              <label key={name}>
                {name.replaceAll("_", " ")}
                {definition.description ? <small>{definition.description}</small> : null}
                {definition.type === "boolean" ? (
                  <select
                    value={String(inputValues[name] ?? false)}
                    onChange={(event) =>
                      setInputValues((current) => ({
                        ...current,
                        [name]: event.target.value === "true",
                      }))
                    }
                  >
                    <option value="false">No</option>
                    <option value="true">Yes</option>
                  </select>
                ) : definition.type === "array" || definition.type === "object" ? (
                  <textarea
                    value={String(inputValues[name] ?? "")}
                    onChange={(event) =>
                      setInputValues((current) => ({ ...current, [name]: event.target.value }))
                    }
                    placeholder={definition.type === "array" ? "[]" : "{}"}
                    required={definition.required !== false}
                  />
                ) : (
                  <input
                    type={definition.type === "integer" || definition.type === "number" ? "number" : "text"}
                    value={String(inputValues[name] ?? "")}
                    onChange={(event) =>
                      setInputValues((current) => ({ ...current, [name]: event.target.value }))
                    }
                    required={definition.required !== false}
                    min={definition.minimum}
                    max={definition.maximum}
                  />
                )}
              </label>
            ))}

            {formError ? <p className="form-error" role="alert">{formError}</p> : null}
            <button className="button button-primary button-wide" disabled={createAndRun.isPending}>
              {createAndRun.isPending ? "Creating and starting…" : "Create & execute run"}
            </button>
          </form>
        ) : (
          <div className="launch-placeholder" aria-hidden="true">
            <span>01</span><i /><span>02</span><i /><span>03</span>
          </div>
        )}
      </section>
    </div>
  );
}
