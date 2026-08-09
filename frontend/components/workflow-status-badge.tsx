const labels: Record<string, string> = {
  NOT_STARTED: "Not started",
  IN_PROGRESS: "In progress",
  COMPLETED: "Completed",
  BLOCKED: "Needs attention",
  FAILED: "Failed",
  CANCELLED: "Cancelled",
  ACTIVE: "Active",
  RETIRED: "Retired",
  DESIRED: "Cloud desired",
  NOT_DESIRED: "Not desired",
  ACKNOWLEDGED_CURRENT: "Installed · current",
  ACKNOWLEDGED_STALE: "Installed · sync needed",
  UNKNOWN: "Local state unknown",
  REVIEWED_CORE: "Core · Reviewed",
  SCAFFOLD_CORE: "Core · Scaffold",
};

export function WorkflowStatusBadge({ value, dimension }: {
  value: string;
  dimension: "lifecycle" | "research" | "desired" | "installation" | "catalog" | "maturity";
}) {
  return <span className={`workflow-badge workflow-badge-${dimension}`}>{labels[value] ?? value}</span>;
}
