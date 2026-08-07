"use client";

import Link from "next/link";

import { useProject } from "@/api/hooks";

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
        title={`Work locally on ${project.data.name}`}
        description="ReAgent Cloud manages desired configuration and bounded continuity. Your Local Project Workspace remains the authoritative home for complete research files."
        action={<Link href={`/projects/${projectId}/workflows`} className="button button-ghost">Workflow Board</Link>}
      />
      <ProjectNavigation projectId={projectId} active="Help" />

      <section className="help-boundary-grid">
        <article><p className="eyebrow">ReAgent Cloud</p><h2>Configuration and continuity</h2><ul><li>Project and Workflow Instance configuration</li><li>Desired Manifest and version pins</li><li>Bounded Progress Reports and artifact metadata</li><li>Client-reported installation acknowledgement</li></ul></article>
        <article><p className="eyebrow">Local Workspace</p><h2>Complete research state</h2><ul><li>Workflow Capsules and code</li><li>Inputs, outputs, datasets, and memory</li><li>Installed Workspace Lock</li><li>Local receipts and complete result files</li></ul></article>
      </section>

      <section><p className="eyebrow">Explicit local synchronization</p><h2>Pull desired Workflow Capsules</h2><pre><code>python reagent_local.py sync .</code></pre><p>The browser cannot write to your computer. Run this command inside the Workspace after adding or retiring a Workflow in Cloud. Retired Capsules and their research results are retained locally.</p></section>
      <section><p className="eyebrow">Current executable scope</p><h2>Literature Search</h2><p>Literature Search is the only currently executable production Workflow. Standalone Packages remain supported, and Workspace-adopted or sync-installed Capsules use the same launcher contract.</p><pre><code>python reagent_local.py run .</code></pre><p>For complete Literature Search checkpoints, Provider behavior, recovery, and output locations, use the accepted compatibility guide.</p><Link href={`/projects/${projectId}/guide`} className="button button-secondary">Open Literature Search guide</Link></section>
      <section><h2>Continuity is not backup</h2><p>Progress Reports provide bounded cognitive and project continuity. Installation acknowledgement records what a local client reported; it does not upload, verify, or back up the complete Workspace. Moving to another device still requires the real Workspace or external storage.</p></section>
      <section><h2>What is not available yet</h2><ul><li>Idea Discovery, Writing, Review, and Experiment execution</li><li>Cross-Workflow Artifact handoff or materialization</li><li>Automatic background sync</li><li>Cloud-hosted full Workspace backup</li><li>Complete cross-device file restoration</li></ul></section>
      <section><h2>Recovery cues</h2><dl className="guide-definitions"><div><dt>Cloud Desired differs from local</dt><dd>Run <code>python reagent_local.py sync .</code>; do not manually rewrite the Installed Lock.</dd></div><div><dt>Progress upload outcome unknown</dt><dd>Run the same Package command again. Upload-only recovery reuses the immutable report identity.</dd></div><div><dt>Local drift detected</dt><dd>Preserve outputs and inspect the reported immutable-file conflict. Sync never force-overwrites mutable research state.</dd></div></dl></section>
    </div>
  );
}
