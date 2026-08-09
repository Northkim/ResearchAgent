"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useCreateProject, useWorkflowDefinitions } from "@/api/hooks";

import { PageHeader } from "./page-header";

export function ProjectCreateForm() {
  const router = useRouter();
  const createProject = useCreateProject();
  const catalog = useWorkflowDefinitions();
  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [setup, setSetup] = useState<"literature-only" | "literature-and-idea" | "full-research" | "custom">("literature-only");
  const [customIds, setCustomIds] = useState<string[]>([]);
  const errorRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => {
    if (message) errorRef.current?.focus();
  }, [message]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    try {
      const project = await createProject.mutateAsync({
        name,
        research_topic: topic,
        selected_workflow: "LITERATURE_SEARCH",
        workflow_setup: setup,
        custom_workflow_definition_ids: setup === "custom" ? customIds : [],
      });
      router.push(`/projects/${project.project_id}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Project creation failed");
    }
  }

  return (
    <div className="page-stack page-narrow">
      <PageHeader
        eyebrow="New research project"
        title="Choose the topic to investigate."
        description="Creating a Project records metadata and prepares Literature Search. It does not search OpenAlex, write local files, or start a cloud model."
      />
      <form className="product-form" onSubmit={submit} aria-busy={createProject.isPending}>
        <label>
          Project name
          <small>A short name shown in your local project list.</small>
          <input
            name="name"
            value={name}
            maxLength={160}
            onChange={(event) => setName(event.target.value)}
            aria-describedby={message ? "project-create-error" : undefined}
            aria-invalid={Boolean(message)}
            required
          />
        </label>
        <label>
          Fictional or public research topic
          <small>This topic is packaged for local Codex execution. Do not enter private or sensitive material.</small>
          <textarea
            name="research_topic"
            value={topic}
            maxLength={500}
            rows={5}
            onChange={(event) => setTopic(event.target.value)}
            aria-describedby={message ? "project-create-error" : undefined}
            aria-invalid={Boolean(message)}
            required
          />
        </label>
        <fieldset>
          <legend>Project setup</legend>
          {([
            ["literature-only", "Literature Search only", "Find and select research literature."],
            ["literature-and-idea", "Literature + Idea Discovery", "Search literature and develop a research direction."],
            ["full-research", "Full Research Project", "Create all five workflows for end-to-end product testing."],
            ["custom", "Custom", "Choose independently from the production Workflow Registry."],
          ] as const).map(([value, title, description]) => (
            <label key={value} className="artifact-choice">
              <input type="radio" name="workflow_setup" value={value} checked={setup === value} onChange={() => setSetup(value)} />
              <span><strong>{title}</strong><small>{description}</small></span>
            </label>
          ))}
        </fieldset>
        {setup === "full-research" ? (
          <div className="boundary-callout" role="note">
            <strong>Includes prototype cores</strong>
            <p>Writing, Review, and Reproduction &amp; Experiment have functional product flows but produce scaffold outputs only. No substantive manuscript, peer review, or experiment is performed.</p>
          </div>
        ) : null}
        {setup === "custom" ? (
          <fieldset>
            <legend>Choose workflows</legend>
            <p className="section-caption">A workflow may be added before its upstream result exists; it will wait safely for an exact input.</p>
            {catalog.data?.items.filter((item) => item.creatable && item.lifecycle === "AVAILABLE").map((item) => (
              <label key={item.workflow_definition_id} className="artifact-choice">
                <input
                  type="checkbox"
                  checked={customIds.includes(item.workflow_definition_id)}
                  onChange={(event) => setCustomIds((current) => event.target.checked ? [...current, item.workflow_definition_id] : current.filter((id) => id !== item.workflow_definition_id))}
                />
                <span>{item.display_name}<small>{item.recommended_version?.core_capability_maturity === "SCAFFOLD_CORE" ? "Prototype core" : "Reviewed core"}{item.recommended_version?.artifact_requirements?.some((requirement) => requirement.required) ? ` · waits for ${item.recommended_version.artifact_requirements.filter((requirement) => requirement.required).map((requirement) => requirement.requirement_key.replaceAll("_", " ")).join(" + ")}` : ""}</small></span>
              </label>
            ))}
          </fieldset>
        ) : null}
        {message ? <p id="project-create-error" className="form-error" role="alert" tabIndex={-1} ref={errorRef}>{message}</p> : null}
        <div className="form-actions">
          <button className="button button-primary" disabled={createProject.isPending || (setup === "custom" && customIds.length === 0)}>
            {createProject.isPending ? "Creating…" : "Create project"}
          </button>
          <button className="button button-ghost" type="button" onClick={() => router.push("/projects")}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
