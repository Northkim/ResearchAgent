"use client";

import Link from "next/link";

import { useProject } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";

import { PageHeader } from "./page-header";
import { ErrorState, LoadingState } from "./query-state";

const expectedOutputs = [
  "Search strategy",
  "Candidate paper library",
  "Selected paper library",
  "Literature search report",
  "Cloud progress summary",
];

export function LocalProjectDetail({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  if (project.isLoading) return <LoadingState label="Loading project" />;
  if (project.isError || !project.data) return <ErrorState title="Project unavailable" />;
  const data = project.data;
  const completed = data.progress?.latest_status === "COMPLETED";
  const currentStep = !data.current_package
    ? "Generate and download the Package"
    : completed
      ? "Review the uploaded progress summary"
      : "Extract the Package and run the local workflow";

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Local Literature Search"
        title={data.name}
        description={data.research_topic}
        action={<Link href="/projects" className="button button-ghost">All projects</Link>}
      />

      <section className="start-here-card" aria-labelledby="start-here-title">
        <div>
          <p className="eyebrow">Start here · One complete round</p>
          <h2 id="start-here-title">Search locally with Codex, then return to the result summary</h2>
          <p>Codex plans, screens, and synthesizes inside the downloaded folder. ReAgent only provides bounded paper metadata and stores a compact Progress Report.</p>
        </div>
        <div className="current-action">
          <span>Current step</span>
          <strong>{currentStep}</strong>
          <Link
            href={
              !data.current_package
                ? `/projects/${projectId}/package`
                : completed
                  ? `/projects/${projectId}/progress`
                  : `/projects/${projectId}/guide`
            }
            className="button button-primary"
          >
            {!data.current_package ? "Generate Package" : completed ? "View progress" : "Start local search"}
          </Link>
        </div>
      </section>

      <section className="quick-start" aria-labelledby="quick-start-title">
        <div className="section-heading">
          <div><p className="eyebrow">Quick Start</p><h2 id="quick-start-title">Four owner actions</h2></div>
          <Link href={`/projects/${projectId}/guide`} className="text-link">Read full guide →</Link>
        </div>
        <ol>
          <li><span>1</span><div><strong>Generate and download Package</strong><p>Compile the immutable topic and pinned workflow into a credential-free ZIP.</p></div></li>
          <li><span>2</span><div><strong>Extract Package locally</strong><p>Keep the folder outside this repository; its files are authoritative research state.</p></div></li>
          <li><span>3</span><div><strong>Run the one-command Codex workflow</strong><code>python reagent_local.py run .</code></div></li>
          <li><span>4</span><div><strong>View uploaded results</strong><p>The completed round uploads and verifies its bounded progress summary automatically.</p></div></li>
        </ol>
      </section>

      <section className="product-action-grid">
        <article>
          <p className="eyebrow">Package</p>
          <h2>{data.current_package ? "Package ready" : "Prepare the local workspace"}</h2>
          <p>Generate, download, extract, and launch the exact Package.</p>
          <Link href={`/projects/${projectId}/package`} className="button button-secondary">
            {data.current_package ? "Download Package" : "Generate Package"}
          </Link>
        </article>
        <article>
          <p className="eyebrow">Expected outputs</p>
          <ul>{expectedOutputs.map((output) => <li key={output}>{output}</li>)}</ul>
        </article>
        <article>
          <p className="eyebrow">Latest progress</p>
          <h2>{data.progress ? `Round ${data.progress.latest_execution_round} · ${data.progress.latest_status}` : "Waiting for local round"}</h2>
          <p>{data.progress?.current_state_summary ?? "No Progress Report has been uploaded for this Package."}</p>
          <Link href={`/projects/${projectId}/progress`} className="button button-secondary">View progress</Link>
        </article>
      </section>

      <details className="technical-details">
        <summary>Technical details</summary>
        <dl>
          <div><dt>Project ID</dt><dd><code>{data.project_id}</code></dd></div>
          <div><dt>Workflow</dt><dd>Literature Search</dd></div>
          <div><dt>Created</dt><dd>{formatDateTime(data.created_at)}</dd></div>
          {data.current_package ? <div><dt>Package checksum</dt><dd><code>{data.current_package.package_checksum}</code></dd></div> : null}
        </dl>
      </details>
    </div>
  );
}
