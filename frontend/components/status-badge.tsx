import { formatStatus } from "@/lib/format";
import type {
  ApprovalStatus,
  StepRunStatus,
  WorkflowRunStatus,
} from "@/types/api";

type Status = WorkflowRunStatus | StepRunStatus | ApprovalStatus;

const toneByStatus: Record<string, string> = {
  COMPLETED: "status-success",
  APPROVED: "status-success",
  RUNNING: "status-running",
  INITIALIZING: "status-running",
  READY: "status-running",
  WAITING_FOR_APPROVAL: "status-waiting",
  WAITING_APPROVAL: "status-waiting",
  WAITING_FOR_INPUT: "status-waiting",
  PENDING: "status-waiting",
  RETRY_SCHEDULED: "status-retry",
  FAILED: "status-error",
  REJECTED: "status-error",
  EXPIRED: "status-muted",
  CANCELLED: "status-muted",
  CANCELLING: "status-muted",
  CREATED: "status-neutral",
  SKIPPED: "status-muted",
};

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span className={`status-badge ${toneByStatus[status] ?? "status-neutral"}`}>
      <span aria-hidden="true" />
      {formatStatus(status)}
    </span>
  );
}
