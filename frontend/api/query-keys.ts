export const queryKeys = {
  workflows: ["workflows"] as const,
  runs: ["runs"] as const,
  run: (runId: string) => ["runs", runId] as const,
  events: (runId: string) => ["runs", runId, "events"] as const,
  artifacts: (runId: string) => ["runs", runId, "artifacts"] as const,
  artifactContent: (artifactId: string) => ["artifacts", artifactId, "content"] as const,
  providerUsage: (runId: string) => ["runs", runId, "provider-usage"] as const,
  approvals: ["approvals"] as const,
};
