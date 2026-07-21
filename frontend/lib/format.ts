import type {
  ApprovalStatus,
  EventType,
  StepRunStatus,
  WorkflowRunStatus,
} from "@/types/api";

const DATE_TIME_FORMAT = new Intl.DateTimeFormat("en", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "UTC",
});

export function formatDateTime(value: string): string {
  return DATE_TIME_FORMAT.format(new Date(value)) + " UTC";
}

export function formatIdentifier(value: string): string {
  return value.replaceAll("_", " ").toLowerCase();
}

export function formatStatus(
  value: WorkflowRunStatus | StepRunStatus | ApprovalStatus,
): string {
  return value.replaceAll("_", " ").toLowerCase();
}

export function formatEventType(value: EventType): string {
  return value.replaceAll("_", " ").toLowerCase();
}

export function truncateId(value: string): string {
  return value.length > 16 ? `${value.slice(0, 8)}…${value.slice(-5)}` : value;
}

export function isActiveRun(status: WorkflowRunStatus): boolean {
  return !["COMPLETED", "FAILED", "CANCELLED"].includes(status);
}
