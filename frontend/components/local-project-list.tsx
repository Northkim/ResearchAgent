"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { useProjects } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";
import type { LocalProject } from "@/types/api";

import { PageHeader } from "./page-header";
import { EmptyState, ErrorState, LoadingState } from "./query-state";
import { presentWorkflowAction } from "./workflow-detail";

const NEEDS_ATTENTION = new Set(["OWNER_ACTION_REQUIRED", "ATTENTION_REQUIRED", "BLOCKED"]);

function ProjectRow({ project }: { project: LocalProject }) {
  const attention = project.attention;
  const action = attention.action;
  const presentation = presentWorkflowAction(action, attention.recommended_workflow_label, attention.recent_change.summary);
  const actionHref = action.next_action.code === "SETUP"
    ? `/projects/${project.project_id}/help`
    : action.next_action.code === "REVIEW_RESULT"
    ? `/projects/${project.project_id}/outputs`
    : attention.recommended_workflow_instance_id
      ? `/projects/${project.project_id}/workflows/${attention.recommended_workflow_instance_id}`
      : `/projects/${project.project_id}`;
  return (
    <article className="project-work-row" data-attention-state={action.attention_state}>
      <div className="project-work-identity">
        <Link href={`/projects/${project.project_id}`}>
          <div className="project-work-heading"><h3>{project.name}</h3></div>
          <p>{project.research_topic}</p>
        </Link>
      </div>
      <div className="project-work-state">
        <span>Current step</span>
        <strong>{presentation.task}</strong>
        <small>{attention.recommended_workflow_label ?? "Project"} · {presentation.stage}</small>
      </div>
      <div className="project-work-context">
        <span>Status</span>
        <strong className="project-status-line"><i aria-hidden="true" />{presentation.attention}</strong>
        <small>{presentation.reason}</small>
      </div>
      <div className="project-work-updated">
        <span>Updated</span>
        <strong>{attention.recent_change.changed_at ? formatDateTime(attention.recent_change.changed_at) : "No activity yet"}</strong>
      </div>
      <Link href={actionHref} className="project-row-action">{presentation.actionLabel} <span>→</span></Link>
    </article>
  );
}

export function LocalProjectList() {
  const projects = useProjects();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "attention" | "other">("all");
  const filtered = useMemo(() => {
    const term = query.trim().toLocaleLowerCase();
    return (projects.data ?? []).filter((project) => (
      !term || `${project.name} ${project.research_topic} ${project.attention.recommended_workflow_label ?? ""}`
        .toLocaleLowerCase().includes(term)
    )).filter((project) => filter === "all" || (filter === "attention") === NEEDS_ATTENTION.has(project.attention.action.attention_state));
  }, [filter, projects.data, query]);
  const attention = filtered.filter((project) => NEEDS_ATTENTION.has(project.attention.action.attention_state));
  const other = filtered.filter((project) => !NEEDS_ATTENTION.has(project.attention.action.attention_state));

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Research portfolio"
        title="Projects"
        description="Continue the study that needs your attention."
        action={
          <Link href="/projects/new" className="button button-primary">
            New Project
          </Link>
        }
      />

      <div className="project-toolbar">
        <label className="project-search"><span className="sr-only">Search Projects</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search Projects" type="search" /></label>
        <label className="project-filter"><span className="sr-only">Filter Projects</span><select value={filter} onChange={(event) => setFilter(event.target.value as typeof filter)}><option value="all">All projects</option><option value="attention">Needs attention</option><option value="other">No attention needed</option></select></label>
      </div>

      {projects.isLoading ? <LoadingState label="Loading local projects" /> : null}
      {projects.isError ? <ErrorState /> : null}
      {projects.data?.length === 0 ? (
        <EmptyState
          title="No local projects yet"
          message="Create a Project to start Literature Search and set up a Local Workspace."
        />
      ) : null}
      {projects.data && projects.data.length > 0 ? (
        <div className="project-work-lists">
          {filtered.length === 0 ? <EmptyState title="No matching Projects" message="Clear the search to see the full research portfolio." /> : null}
          {attention.length ? (
            <section aria-labelledby="projects-attention-title">
              <div className="section-heading"><div><p className="eyebrow">Act now</p><h2 id="projects-attention-title">Needs your attention</h2></div><span>{attention.length} {attention.length === 1 ? "project" : "projects"}</span></div>
              <div className="project-work-list">{attention.map((project) => <ProjectRow key={project.project_id} project={project} />)}</div>
            </section>
          ) : null}
          {other.length ? (
            <section aria-labelledby="other-projects-title">
              <div className="section-heading"><div><p className="eyebrow">Portfolio</p><h2 id="other-projects-title">Other projects</h2></div><span>{other.length} {other.length === 1 ? "project" : "projects"}</span></div>
              <div className="project-work-list">{other.map((project) => <ProjectRow key={project.project_id} project={project} />)}</div>
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
