"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { useCreateProject } from "@/api/hooks";

import { PageHeader } from "./page-header";

export function ProjectCreateForm() {
  const router = useRouter();
  const createProject = useCreateProject();
  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");
  const [message, setMessage] = useState<string | null>(null);

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
        eyebrow="New local project"
        title="Define the research handoff."
        description="Use a fictional or public topic. Creating a project records metadata only—it does not call OpenAlex, start a Workflow, or invoke a cloud model."
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
            required
          />
        </label>
        <label>
          Workflow
          <select name="selected_workflow" value="LITERATURE_SEARCH" disabled>
            <option value="LITERATURE_SEARCH">Literature Search</option>
          </select>
          <small>Literature Search is the only V0.1 Workflow.</small>
        </label>
        {message ? <p className="form-error" role="alert">{message}</p> : null}
        <div className="form-actions">
          <button className="button button-primary" disabled={createProject.isPending}>
            {createProject.isPending ? "Creating…" : "Create local project"}
          </button>
          <button className="button button-ghost" type="button" onClick={() => router.push("/projects")}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
