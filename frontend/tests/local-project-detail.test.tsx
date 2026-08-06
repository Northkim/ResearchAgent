import { render, screen } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { LocalProjectDetail } from "@/components/local-project-detail";
import { Providers } from "@/lib/providers";

import { localProjectFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("shows the task-oriented Quick Start and no Hosted primary action", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  render(<Providers><LocalProjectDetail projectId={localProjectFixture.project_id} /></Providers>);
  expect(await screen.findByRole("heading", { name: "Four owner actions" })).toBeVisible();
  expect(screen.getByText("Generate and download Package")).toBeVisible();
  expect(screen.getByText("Run the one-command Codex workflow")).toBeVisible();
  expect(screen.getByText("Cloud progress summary")).toBeVisible();
  expect(screen.getByRole("link", { name: "Read full guide →" })).toHaveAttribute(
    "href",
    expect.stringContaining("/guide"),
  );
  expect(screen.queryByText(/start research run|resume hosted workflow/i)).not.toBeInTheDocument();
});
