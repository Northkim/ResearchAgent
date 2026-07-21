export const queryKeys = {
  workflows: ["workflows"] as const,
  runs: ["runs"] as const,
  run: (runId: string) => ["runs", runId] as const,
  events: (runId: string) => ["runs", runId, "events"] as const,
  approvals: ["approvals"] as const,
};
