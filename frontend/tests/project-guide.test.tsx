import { render, screen } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { ProjectGuide } from "@/components/project-guide";
import { Providers } from "@/lib/providers";

import { localProjectFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("explains the exact command, modes, retry, and privacy boundary", async () => {
  vi.spyOn(apiClient, "getProject").mockResolvedValue(localProjectFixture);
  render(<Providers><ProjectGuide projectId={localProjectFixture.project_id} /></Providers>);
  expect(await screen.findByText("python reagent_local.py run .")).toBeVisible();
  expect(screen.getByText("python reagent_local.py run . --mode demo")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Cloud and privacy boundary" })).toBeVisible();
  expect(screen.getByText(/upload-only retry/i)).toBeVisible();
  expect(screen.getByText(/There is no fake fallback/)).toBeVisible();
});
