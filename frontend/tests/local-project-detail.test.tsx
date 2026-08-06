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
  expect(await screen.findByRole("heading", { name: "Eight guided steps" })).toBeVisible();
  expect(screen.getByText("Generate and download Package")).toBeVisible();
  expect(screen.getByText("Review the search plan with Codex")).toBeVisible();
  expect(screen.getByText("Inspect candidate-paper screening")).toBeVisible();
  expect(screen.getByText("Type finish when ready")).toBeVisible();
  expect(screen.getByText(/Ctrl\+C preserves valid local work/)).toBeVisible();
  expect(screen.getByText("Cloud progress summary")).toBeVisible();
  expect(screen.getByRole("link", { name: "Read full guide →" })).toHaveAttribute(
    "href",
    expect.stringContaining("/guide"),
  );
  expect(screen.queryByText(/start research run|resume hosted workflow/i)).not.toBeInTheDocument();
});
