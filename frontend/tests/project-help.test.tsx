import { render, screen } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { ProjectHelp } from "@/components/project-help";
import { Providers } from "@/lib/providers";

import { localProjectFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("keeps Project Help contextual and sends generic reference to Local guide", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  render(<Providers><ProjectHelp projectId={localProjectFixture.project_id} /></Providers>);

  expect(await screen.findByRole("heading", { name: `Use ${localProjectFixture.name} locally` })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Set up this Project" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Download setup file" })).toHaveAttribute(
    "href", `/backend/projects/${localProjectFixture.project_id}/workspace-bootstrap`,
  );
  expect(screen.getByRole("link", { name: "Download local tool" })).toHaveAttribute(
    "href", "/backend/local-client/reagent_local.py",
  );
  expect(screen.getByText((_, element) => (
    element?.tagName === "CODE"
    && element.textContent === "cd ./reagent-workspace\npython reagent_local.py sync ."
  ))).toBeVisible();
  expect(screen.getByRole("button", { name: "Copy Workspace sync command" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Open Workflow Board" })).toBeVisible();
  expect(screen.getByRole("link", { name: /Open Local guide/ })).toHaveAttribute("href", "/local-guide");
  expect(screen.getByRole("link", { name: "Activity" })).toBeVisible();
  expect(screen.getByRole("link", { name: "Help" })).toHaveAttribute("aria-current", "page");
  expect(screen.queryByText(/Literature Search 0.3.0/)).not.toBeInTheDocument();
});
