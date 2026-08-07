"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { useCreateProject } from "@/api/hooks";

import { PageHeader } from "./page-header";

export function ProjectCreateForm() {
  const router = useRouter();
  const createProject = useCreateProject();
  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");
  const [message, setMessage] = useState<string | null>(null);
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
        <label>
          Workflow
          <select name="selected_workflow" value="LITERATURE_SEARCH" disabled>
            <option value="LITERATURE_SEARCH">Literature Search</option>
          </select>
          <small>Every new Project starts with Literature Search. You can explicitly add Idea Discovery later from the Workflow Board.</small>
        </label>
        {message ? <p id="project-create-error" className="form-error" role="alert" tabIndex={-1} ref={errorRef}>{message}</p> : null}
        <div className="form-actions">
          <button className="button button-primary" disabled={createProject.isPending}>
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
