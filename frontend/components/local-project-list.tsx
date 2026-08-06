"use client";

import Link from "next/link";

import { useProjects } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";

import { PageHeader } from "./page-header";
import { EmptyState, ErrorState, LoadingState } from "./query-state";

export function LocalProjectList() {
  const projects = useProjects();

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="ReAgent V0.1 · local workspace"
        title="Research stays in your folder."
        description="Create a Literature Search project, download its credential-free Workflow Package, and run one complete local Codex round with automatic Progress upload."
        action={
          <Link href="/projects/new" className="button button-primary">
            Create project
          </Link>
        }
      />

      <div className="boundary-callout" role="note">
        <strong>Local-first boundary</strong>
        <p>ReAgent manages project metadata, Packages, progress, and bounded API capabilities. It does not run or resume the research task in the cloud.</p>
      </div>

      {projects.isLoading ? <LoadingState label="Loading local projects" /> : null}
      {projects.isError ? <ErrorState /> : null}
      {projects.data?.length === 0 ? (
        <EmptyState
          title="No local projects yet"
          message="Create a Literature Search project to generate your first portable Workflow Package."
        />
      ) : null}
      {projects.data && projects.data.length > 0 ? (
        <section className="project-grid" aria-label="Local research projects">
          {projects.data.map((project) => (
            <article className="project-card" key={project.project_id}>
              <div className="project-card-topline">
                <span>Literature Search</span>
                <span className={`local-status ${project.progress ? "local-status-active" : ""}`}>
                  {project.progress?.latest_status ?? (project.current_package ? "PACKAGE READY" : "NOT STARTED")}
                </span>
              </div>
              <h2>{project.name}</h2>
              <p>{project.research_topic}</p>
              <dl className="compact-metadata">
                <div>
                  <dt>Round</dt>
                  <dd>{project.progress?.latest_execution_round ?? "—"}</dd>
                </div>
                <div>
                  <dt>Updated</dt>
                  <dd>{formatDateTime(project.progress?.latest_upload_timestamp ?? project.updated_at)}</dd>
                </div>
              </dl>
              <Link href={`/projects/${project.project_id}`} className="text-link">
                Open project →
              </Link>
            </article>
          ))}
        </section>
      ) : null}
    </div>
  );
}
