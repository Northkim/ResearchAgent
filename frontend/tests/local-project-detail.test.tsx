import { render, screen } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { LocalProjectDetail } from "@/components/local-project-detail";
import { Providers } from "@/lib/providers";

import { localProjectFixture, projectProgressFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("leads the Project Overview with the current research action", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue(projectProgressFixture);
  render(<Providers><LocalProjectDetail projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Review the selected papers" })).toBeVisible();
  expect(screen.queryByText("Owner acts now")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View selected papers" })).toHaveAttribute("href", expect.stringContaining("/outputs"));
  expect(screen.getAllByText("Literature Search").length).toBeGreaterThan(0);
  expect(screen.getByRole("heading", { name: "Workflow progress" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Latest output" })).toBeVisible();
  expect(screen.getByText("Selected paper library")).toBeVisible();
  expect(screen.queryByText(/% complete/i)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("link", { name: "Workflows" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Outputs" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Activity" })).toBeVisible();
  expect(screen.queryByRole("link", { name: "Download setup file" })).not.toBeInTheDocument();
  expect(screen.getByText("Technical Details")).toBeVisible();
});
