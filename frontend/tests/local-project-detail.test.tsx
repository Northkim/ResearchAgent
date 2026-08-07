import { render, screen } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { LocalProjectDetail } from "@/components/local-project-detail";
import { Providers } from "@/lib/providers";

import { localProjectFixture, projectProgressFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("renders the project overview without a fake completion percentage", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  vi.spyOn(apiClient, "getProjectProgress").mockResolvedValue(projectProgressFixture);
  render(<Providers><LocalProjectDetail projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Your research workflows at a glance" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Review the latest result" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Download setup file" })).toHaveAttribute(
    "href", `/backend/projects/${localProjectFixture.project_id}/workspace-bootstrap`,
  );
  expect(screen.getByRole("link", { name: "Download local tool" })).toHaveAttribute(
    "href", "/backend/local-client/reagent_local.py",
  );
  expect(screen.getByText(/bootstrap \.\/reagent-workspace/)).toBeVisible();
  expect(screen.getByText("Literature Search")).toBeVisible();
  expect(screen.getByText("Selection rationale is ready for review.")).toBeVisible();
  expect(screen.queryByText(/% complete/i)).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute("aria-current", "page");
  expect(screen.getByRole("link", { name: "Workflows" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Progress" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Help" })).toBeVisible();
  expect(screen.queryByText(/Artifacts|Resources|Skills|Activity|Settings/)).not.toBeInTheDocument();
});
