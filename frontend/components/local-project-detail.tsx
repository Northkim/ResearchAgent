"use client";

import Link from "next/link";

import { useProject } from "@/api/hooks";
import { formatDateTime, truncateId } from "@/lib/format";

import { PageHeader } from "./page-header";
import { ErrorState, LoadingState } from "./query-state";

export function LocalProjectDetail({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  if (project.isLoading) return <LoadingState label="Loading project" />;
  if (project.isError || !project.data) return <ErrorState title="Project unavailable" />;
  const data = project.data;

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Local Literature Search"
        title={data.name}
        description={data.research_topic}
        action={<Link href="/projects" className="button button-ghost">All projects</Link>}
      />
      <section className="detail-metadata" aria-label="Project identity">
        <div><span>Project ID</span><code title={data.project_id}>{truncateId(data.project_id)}</code></div>
        <div><span>Workflow</span><strong>Literature Search</strong></div>
        <div><span>Created</span><strong>{formatDateTime(data.created_at)}</strong></div>
      </section>
      <section className="product-action-grid">
        <article>
          <p className="eyebrow">01 · Package</p>
          <h2>{data.current_package ? "Workflow Package ready" : "Prepare the local folder"}</h2>
          <p>Generate a deterministic, credential-free ZIP with Codex instructions and explicit local state boundaries.</p>
          {data.current_package ? <code>{truncateId(data.current_package.package_checksum)}</code> : null}
          <Link href={`/projects/${projectId}/package`} className="button button-secondary">
            {data.current_package ? "View Package" : "Generate Package"}
          </Link>
        </article>
        <article>
          <p className="eyebrow">02 · Local work</p>
          <h2>Open the folder with Codex</h2>
          <p>Validate the extracted Package, read <code>AGENT.md</code>, then let Codex work only in declared local files.</p>
          <Link href="/local-guide" className="text-link">Read local instructions →</Link>
        </article>
        <article>
          <p className="eyebrow">03 · Progress</p>
          <h2>{data.progress ? `Round ${data.progress.latest_execution_round} · ${data.progress.latest_status}` : "No uploaded progress yet"}</h2>
          <p>Progress Reports are uploaded explicitly. ReAgent displays the accepted projection and immutable report history without resuming work.</p>
          <Link href={`/projects/${projectId}/progress`} className="button button-secondary">View progress</Link>
        </article>
      </section>
    </div>
  );
}
