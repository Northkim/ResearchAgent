import { render, screen } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { ProjectHelp } from "@/components/project-help";
import { Providers } from "@/lib/providers";

import { localProjectFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("guides setup, multi-Workflow work, continuation, and Cloud/local boundaries", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  render(<Providers><ProjectHelp projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Projects and continuity" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Your complete research files" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Download Workspace setup" })).toHaveAttribute(
    "href", `/backend/projects/${localProjectFixture.project_id}/workspace-bootstrap`,
  );
  expect(screen.getByRole("link", { name: "Download local tool" })).toHaveAttribute(
    "href", "/backend/local-client/reagent_local.py",
  );
  expect(screen.getByText(/browser never runs sync/i)).toBeVisible();
  expect(screen.getByRole("heading", { name: "Cloud continuity is not backup" })).toBeVisible();
  expect(screen.getByText(/Literature Search 0.3.0/)).toBeVisible();
  expect(screen.getAllByText("python reagent_local.py workflow list .")).toHaveLength(2);
  expect(screen.getByRole("link", { name: "Activity" })).toBeVisible();
  expect(screen.queryByRole("link", { name: "Help" })).not.toBeInTheDocument();
});
