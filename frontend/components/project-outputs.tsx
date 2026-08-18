"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { apiClient } from "@/api/client";
import { useProject, useProjectProgress } from "@/api/hooks";
import { queryKeys } from "@/api/query-keys";
import { formatDateTime } from "@/lib/format";

import { ErrorState, LoadingState } from "./query-state";
import { ArtifactPresentationPreview } from "./artifact-presentation";
import { PageHeader } from "./page-header";
import { ProjectNavigation } from "./project-navigation";
import { ExperimentPresentationView } from "./workflow-detail";

const OUTPUT_LABELS: Record<string, string> = {
  paper_library: "Selected paper library",
  "selected-paper-library/v1": "Selected paper library",
  research_idea: "Selected research idea",
  "selected-research-idea/v1": "Selected research idea",
  experiment_record: "Experiment record",
  "experiment-record/v1": "Experiment record",
  "experiment-record/v2": "Experiment result",
  "experiment-record/v4": "Experiment result",
  "experiment-record/v5": "Experiment result",
  manuscript_draft: "Manuscript draft",
  "manuscript-draft/v1": "Manuscript draft",
  "manuscript-draft/v2": "Initial manuscript draft",
  "manuscript-draft/v3": "Revised manuscript draft",
  "manuscript-draft/v4": "Initial manuscript",
  "manuscript-draft/v5": "Revised manuscript",
  review_report: "Review report",
  "review-report/v1": "Review report",
  "review-report/v2": "Structured review report",
  "review-report/v3": "Review report",
};

function outputLabel(type: string, schema: string): string {
  return OUTPUT_LABELS[schema] ?? OUTPUT_LABELS[type] ?? type.replaceAll("_", " ");
}

export function ProjectOutputs({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  const artifacts = useQuery({
    queryKey: queryKeys.projectArtifactReferences(projectId, "all"),
    queryFn: () => apiClient.listProjectArtifactReferences(projectId),
    retry: false,
  });
  const progress = useProjectProgress(projectId);
  if (project.isLoading || artifacts.isLoading || progress.isLoading) return <LoadingState label="Loading Outputs" />;
  if (project.isError || !project.data || artifacts.isError || !artifacts.data || progress.isError || !progress.data) return <ErrorState title="Outputs unavailable" />;

  return (
    <div className="page-stack">
      <PageHeader eyebrow="Project Outputs" title={`${project.data.name} Outputs`} description="Exact research products, with technical provenance available separately." action={<Link href={`/projects/${projectId}`} className="button button-ghost">Project Overview</Link>} />
      <ProjectNavigation projectId={projectId} active="Outputs" />
      {artifacts.data.artifacts.length ? (
        <section className="output-work-list" aria-label="Project Outputs">
          {artifacts.data.artifacts.map((artifact) => {
            const producer = progress.data.instances.find((item) => item.workflow_instance_id === artifact.producer_workflow_instance_id);
            const report = progress.data.history.find((item) => item.workflow_instance_id === artifact.producer_workflow_instance_id);
            return (
              <article className="output-work-row" key={artifact.artifact_id}>
                <div><p className="eyebrow">Output</p><h2>{outputLabel(artifact.artifact_type, artifact.artifact_schema_version)}</h2><p>Produced by <Link href={`/projects/${projectId}/workflows/${artifact.producer_workflow_instance_id}`}>{producer?.friendly_instance_label ?? producer?.workflow_display_name ?? "Project Workflow"}</Link>.</p></div>
                <dl><div><dt>Outcome</dt><dd>{producer?.research_status.replaceAll("_", " ") ?? artifact.state.replaceAll("_", " ")}</dd></div><div><dt>Produced</dt><dd>{formatDateTime(artifact.produced_at)}</dd></div><div><dt>Round</dt><dd>{artifact.producer_execution_round}</dd></div>{report?.normalized_record?.warnings.length ? <div className="output-limitation"><dt>Limitation</dt><dd>{report.normalized_record.warnings[0]}</dd></div> : null}</dl>
                {artifact.artifact_schema_version === "experiment-record/v4" || artifact.artifact_schema_version === "experiment-record/v5" ? <ExperimentPresentationView artifact={artifact} /> : null}
                {["selected-paper-library/v1", "selected-research-idea/v1", "manuscript-draft/v4", "review-report/v3", "manuscript-draft/v5"].includes(artifact.artifact_schema_version) ? <ArtifactPresentationPreview artifact={artifact} /> : null}
                <details className="technical-details compact-technical-details"><summary>Technical Details</summary><dl><div><dt>Artifact ID</dt><dd><code>{artifact.artifact_id}</code></dd></div><div><dt>Schema</dt><dd><code>{artifact.artifact_schema_version}</code></dd></div><div><dt>Checksum</dt><dd><code>{artifact.content_checksum}</code></dd></div><div><dt>Capsule</dt><dd><code>{artifact.producer_capsule_id}@{artifact.producer_capsule_version}</code></dd></div><div><dt>Progress round</dt><dd>{artifact.producer_execution_round}</dd></div></dl></details>
              </article>
            );
          })}
        </section>
      ) : <section className="empty-panel"><h2>No Outputs yet</h2><p>Complete a Workflow to produce its first exact Output.</p><Link href={`/projects/${projectId}/workflows`} className="button button-primary">View Workflows</Link></section>}
    </div>
  );
}
