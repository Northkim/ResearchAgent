import { formatDateTime, formatEventType } from "@/lib/format";
import type { ExecutionEvent } from "@/types/api";

import { EmptyState } from "./query-state";

function eventSummary(event: ExecutionEvent): string {
  const payload = event.payload;
  if (typeof payload.step_id === "string") {
    return `Step ${payload.step_id.replaceAll("_", " ")}`;
  }
  if (typeof payload.boundary === "string") {
    return `Checkpoint boundary ${payload.boundary.replaceAll("_", " ").toLowerCase()}`;
  }
  if (typeof payload.error_code === "string" && payload.error_code) {
    return `Execution error ${payload.error_code}`;
  }
  if (typeof payload.status === "string") {
    return `Workflow is ${payload.status.replaceAll("_", " ").toLowerCase()}`;
  }
  return "Durable execution boundary recorded";
}

export function EventTimeline({ events }: { events: ExecutionEvent[] }) {
  if (!events.length) {
    return (
      <EmptyState
        title="No execution events yet"
        message="Events appear after the run is submitted for execution."
      />
    );
  }

  return (
    <ol className="event-timeline" aria-label="Execution timeline">
      {events.map((event) => (
        <li key={event.id} className={`event-${event.severity.toLowerCase()}`}>
          <span className="event-node" aria-hidden="true" />
          <div className="event-content">
            <div className="event-title-row">
              <strong>{formatEventType(event.type)}</strong>
              <time dateTime={event.timestamp}>{formatDateTime(event.timestamp)}</time>
            </div>
            <p>{eventSummary(event)}</p>
            <span className="event-sequence">#{String(event.sequence).padStart(2, "0")}</span>
          </div>
        </li>
      ))}
    </ol>
  );
}
