import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { ProgressProductPanel } from "@/components/progress-product-panel";
import { Providers } from "@/lib/providers";

import {
  localProjectFixture,
  projectProgressFixture,
  progressReportFixture,
  workflowInstanceId,
} from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("renders human Activity with exact Progress provenance in Technical Details", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  const progress = vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue(projectProgressFixture);
  render(<Providers><ProgressProductPanel projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: `${localProjectFixture.name} Activity` })).toBeVisible();
  expect(screen.getByText("Selection rationale is ready for review.")).toBeVisible();
  expect(screen.getByText(progressReportFixture.report_id)).toBeInTheDocument();
  expect(screen.getByText(progressReportFixture.receipt_id)).toBeInTheDocument();
  expect(screen.getAllByText("Technical Details")[0].closest("details")).not.toHaveAttribute("open");
  expect(screen.getByText("Selected paper library")).toBeVisible();
  expect(screen.getByRole("link", { name: "Activity" })).toHaveAttribute("aria-current", "page");

  fireEvent.change(screen.getByLabelText("Workflow"), { target: { value: workflowInstanceId } });
  expect(await screen.findByText(workflowInstanceId)).toBeInTheDocument();
  expect(progress).toHaveBeenLastCalledWith(localProjectFixture.project_id, expect.objectContaining({ workflowInstanceId }));
});

test("describes Cloud uncertainty when no report exists", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue({ ...localProjectFixture, progress: null });
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue({
    ...projectProgressFixture,
    total_progress_report_count: 0,
    latest_project_activity_at: null,
    status_counts: { NOT_STARTED: 1 },
    history: [],
    history_total: 0,
    instances: [{
      ...projectProgressFixture.instances[0],
      research_status: "NOT_STARTED",
      latest_report_id: null,
      latest_report_checksum: null,
      latest_execution_round: null,
      latest_summary: null,
      next_recommended_action: null,
      report_count: 0,
      first_activity_at: null,
      latest_activity_at: null,
    }],
  });
  render(<Providers><ProgressProductPanel projectId={localProjectFixture.project_id} /></Providers>);
  expect(await screen.findByRole("heading", { name: "No Progress Report received" })).toBeVisible();
  expect(screen.getByText(/cannot inspect the Local Workspace/)).toBeVisible();
  expect(screen.getByText(/same Package for upload recovery/)).toBeVisible();
});
