import { render, screen } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { ProjectHelp } from "@/components/project-help";
import { Providers } from "@/lib/providers";

import { localProjectFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("states the Cloud/local boundary and only current executable scope", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  render(<Providers><ProjectHelp projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: "Configuration and continuity" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Complete research state" })).toBeVisible();
  expect(screen.getAllByText("python reagent_local.py sync .")).toHaveLength(2);
  expect(screen.getByText(/browser cannot write to your computer/i)).toBeVisible();
  expect(screen.getByText(/does not upload, verify, or back up the complete Workspace/)).toBeVisible();
  expect(screen.getByRole("link", { name: "Help" })).toHaveAttribute("aria-current", "page");
});
