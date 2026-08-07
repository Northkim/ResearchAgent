export const queryKeys = {
  projects: ["projects"] as const,
  project: (projectId: string) => ["projects", projectId] as const,
  projectPackage: (projectId: string) => ["projects", projectId, "package"] as const,
  projectProgress: (projectId: string, workflowInstanceId?: string, offset = 0) =>
    ["projects", projectId, "progress", workflowInstanceId ?? "ALL", offset] as const,
  projectProgressReports: (projectId: string) => ["projects", projectId, "progress-reports"] as const,
  workflowDefinitions: ["workflow-definitions"] as const,
  projectWorkflowInstances: (projectId: string) =>
    ["projects", projectId, "workflow-instances"] as const,
  projectArtifactReferences: (projectId: string, artifactType: string) =>
    ["projects", projectId, "artifact-references", artifactType] as const,
  artifactDependencies: (projectId: string, workflowInstanceId: string) =>
    ["projects", projectId, "workflow-instances", workflowInstanceId, "artifact-dependencies"] as const,
  workflows: ["workflows"] as const,
  runs: ["runs"] as const,
  run: (runId: string) => ["runs", runId] as const,
  events: (runId: string) => ["runs", runId, "events"] as const,
  artifacts: (runId: string) => ["runs", runId, "artifacts"] as const,
  artifactContent: (artifactId: string) => ["artifacts", artifactId, "content"] as const,
  providerUsage: (runId: string) => ["runs", runId, "provider-usage"] as const,
  approvals: ["approvals"] as const,
};
