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
    <div className="page-stack page-narrow guide-page">
      <PageHeader
        eyebrow="Project Help"
        title={`Use ${project.data.name} locally`}
        description="Set up this Project once, then follow its current task from the Workflow Board."
        action={<Link href={`/projects/${projectId}`} className="button button-ghost">Project Overview</Link>}
      />
      <ProjectNavigation projectId={projectId} active="Help" />

      <section className="plain-section">
        <h2>Set up this Project</h2>
        <p>Download the local tool and this Project&apos;s setup file into the same folder.</p>
        <div className="button-row">
          <a href={apiClient.localClientDownloadUrl()} download="reagent_local.py" className="button button-secondary">Download local tool</a>
          <a href={apiClient.workspaceBootstrapDownloadUrl(projectId)} download="workspace-bootstrap.json" className="button button-secondary">Download setup file</a>
        </div>
        <CopyCommand command="python reagent_local.py bootstrap ./reagent-workspace --descriptor ./workspace-bootstrap.json" label="Workspace bootstrap command" />
        <CopyCommand command={"cd ./reagent-workspace\npython reagent_local.py sync ."} label="Workspace sync command" />
      </section>

      <section className="plain-section">
        <h2>Continue this Project</h2>
        <p>The Workflow Board shows the current research task and one recommended Local command.</p>
        <Link href={`/projects/${projectId}/workflows`} className="button button-primary">Open Workflow Board</Link>
      </section>

      <section className="plain-section">
        <h2>Need general Local reference?</h2>
        <p>The Local guide explains Workspace boundaries, recovery, and advanced commands without repeating this Project&apos;s setup.</p>
        <Link href="/local-guide" className="text-link">Open Local guide →</Link>
      </section>

      <details className="technical-details">
        <summary>Technical details</summary>
        <p>Cloud coordinates exact Workflow and Artifact identities. Complete research files stay in the Local Workspace.</p>
      </details>
    </div>
  );
}
