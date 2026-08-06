import { render, screen } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { ProgressProductPanel } from "@/components/progress-product-panel";
import { Providers } from "@/lib/providers";

import { localProjectFixture, progressReportFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("renders projection, outputs, warnings, errors, and report history", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  vi.spyOn(apiClient, "listProgressReports").mockResolvedValue([progressReportFixture]);
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue(localProjectFixture.progress!);
  render(<Providers><ProgressProductPanel projectId={localProjectFixture.project_id} /></Providers>);
  expect(await screen.findByText("Selection rationale is ready for review.")).toBeVisible();
  expect(screen.getByText("Review the local report.")).toBeVisible();
  expect(screen.getByText("outputs/search_plan.md")).toBeVisible();
  expect(screen.getByText("Fictional warning for owner review.")).toBeVisible();
  expect(screen.getByText("Fictional recoverable report error.")).toBeVisible();
  expect(screen.getByText(progressReportFixture.report_id)).toBeVisible();
  expect(screen.getByText(progressReportFixture.receipt_id)).toBeVisible();
  expect(screen.getByText("Round completed")).toHaveClass("active");
  expect(screen.getByText("8")).toBeVisible();
  expect(screen.getByText(/complete artifact contents remain/)).toBeVisible();
  expect(screen.getByRole("heading", { name: "Progress Report receipts" })).toBeVisible();
});
