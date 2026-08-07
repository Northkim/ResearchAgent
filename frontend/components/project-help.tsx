"use client";

import Link from "next/link";

import { apiClient } from "@/api/client";
import { useProject } from "@/api/hooks";

import { CopyCommand } from "./copy-command";
import { PageHeader } from "./page-header";
import { ProjectNavigation } from "./project-navigation";
import { ErrorState, LoadingState } from "./query-state";

export function ProjectHelp({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  if (project.isLoading) return <LoadingState label="Loading project help" />;
  if (project.isError || !project.data) return <ErrorState title="Project help unavailable" />;

  return (
    <div className="page-stack guide-page">
      <PageHeader
        eyebrow="Help"
        title={`Start and continue ${project.data.name}`}
        description="Use the browser to choose Workflows and review Progress. Use the Local Workspace for complete research files and interactive Codex or Claude Code sessions."
        action={<Link href={`/projects/${projectId}/workflows`} className="button button-ghost">Workflow Board</Link>}
      />
      <ProjectNavigation projectId={projectId} active="Help" />

      <section className="help-boundary-grid">
        <article><p className="eyebrow">ReAgent Cloud</p><h2>Projects and continuity</h2><ul><li>Choose and retire Workflows</li><li>Review bounded Progress summaries</li><li>Select a specific result as another Workflow&apos;s input</li><li>Remember what a Local Workspace reported as installed</li></ul></article>
        <article><p className="eyebrow">Local Workspace</p><h2>Your complete research files</h2><ul><li>Interactive Workflow instructions</li><li>Inputs, outputs, data, and memory</li><li>Verified local copies between Workflows</li><li>The files needed to continue in a new session</li></ul></article>
      </section>

      <section>
        <p className="eyebrow">1 · First local setup</p>
        <h2>Create the Local Workspace once</h2>
        <p>Download this Project&apos;s setup file, place it beside <code>reagent_local.py</code>, then run:</p>
        <div className="button-row">
          <a href={apiClient.workspaceBootstrapDownloadUrl(projectId)} download="workspace-bootstrap.json" className="button button-secondary">Download Workspace setup</a>
        </div>
        <CopyCommand command="python reagent_local.py bootstrap ./reagent-workspace --descriptor ./workspace-bootstrap.json" label="Workspace bootstrap command" />
        <p>Then enter the new folder and install the reviewed Workflows selected in Cloud:</p>
        <CopyCommand command="python reagent_local.py sync ." label="local sync command" />
      </section>

      <section>
        <p className="eyebrow">2 · Literature Search</p>
        <h2>Run, review, and explicitly finish</h2>
        <CopyCommand command="python reagent_local.py workflow list ." label="Workflow list command" />
        <p>Use the displayed Literature Search run command. Review the search plan and selected papers with the Agent, then type <code>finish</code> only when the selection is ready. Successful finalization writes the reusable selected paper library and uploads bounded Progress metadata.</p>
        <Link href={`/projects/${projectId}/guide`} className="button button-secondary">Open the detailed Literature Search guide</Link>
      </section>

      <section>
        <p className="eyebrow">3 · Idea Discovery</p>
        <h2>Add, select, prepare, and run</h2>
        <ol>
          <li>Add Idea Discovery on the Workflow Board.</li>
          <li>Run local sync. Existing Literature Search files are not replaced.</li>
          <li>Return to the Workflow Board and explicitly confirm one Literature Search result.</li>
          <li>Run the three copyable local commands shown on the Idea Discovery card: refresh results, prepare the selected input, then run.</li>
          <li>Discuss evidence, possible gaps, and candidate directions with the Agent. A candidate direction is not proof of global novelty.</li>
        </ol>
        <p>The browser never runs sync, copies local files, or starts Codex. Those remain explicit local actions.</p>
      </section>

      <section>
        <p className="eyebrow">4 · Continue later</p>
        <h2>Start from the Workspace, not chat history</h2>
        <p>Open a new terminal in the same Local Workspace and run:</p>
        <CopyCommand command="python reagent_local.py workflow list ." label="Workflow continuation command" />
        <p>The list shows whether each Workflow needs sync, input preparation, a first run, continuation, or result review. The Capsule&apos;s memory and Progress files—not prior chat history—carry the work forward.</p>
      </section>

      <section>
        <h2>Common recovery steps</h2>
        <dl className="guide-definitions">
          <div><dt>Cloud confirmation pending</dt><dd>Keep the Workspace unchanged and run the same sync command again.</dd></div>
          <div><dt>Project changed elsewhere</dt><dd>Refresh the Workflow Board, review the current state, then repeat your explicit action.</dd></div>
          <div><dt>Input selection missing</dt><dd>Choose a specific Literature Search result on the Workflow Board.</dd></div>
          <div><dt>Input not prepared</dt><dd>Run the refresh and materialization commands shown on the Idea Discovery card.</dd></div>
          <div><dt>Local result changed</dt><dd>Restore the original Literature Search output or select a new result. Re-index and materialize; do not edit receipt JSON.</dd></div>
          <div><dt>Session interrupted</dt><dd>Run <code>workflow list</code>, then use the displayed command to continue from local memory.</dd></div>
        </dl>
      </section>

      <section>
        <h2>Legacy Literature Search remains supported</h2>
        <p>Literature Search 0.3.0 / Capsule 0.5.0 remains immutable and usable, but its old result cannot be silently converted into the production paper library required by Idea Discovery. Keep the old history, explicitly retire the old Workflow if appropriate, add Literature Search again, sync, and finish the new 0.4.0 Workflow.</p>
      </section>

      <section><h2>Cloud continuity is not backup</h2><p>Cloud stores Project configuration, bounded Progress, and result metadata—not your complete research files. Moving devices still requires the real Local Workspace or external storage.</p></section>
      <details className="technical-details">
        <summary>Technical model and current limits</summary>
        <p>Cloud Desired Manifest, Capsule pins, Installed Lock, installation acknowledgement, Artifact checksum, and materialization receipts remain available for diagnostics. Normal use does not require editing them.</p>
        <p>A Workspace bootstrapped before H1 keeps its original self-contained CLI. Its existing exact <code>--workflow-instance</code> commands remain supported and are shown under the Idea Discovery card&apos;s technical details; sync never silently overwrites the Workspace tool.</p>
        <ul><li>Writing, Review, and Experiment production Workflows are not available.</li><li>There is no automatic input selection, materialization, or background sync.</li><li>Cloud does not store Artifact bytes or provide complete Workspace backup.</li></ul>
      </details>
    </div>
  );
}
