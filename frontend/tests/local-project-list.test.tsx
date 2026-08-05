import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { LocalProjectList } from "@/components/local-project-list";
import { AppShell } from "@/components/app-shell";
import { Providers } from "@/lib/providers";

import { localProjectFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("renders local projects and their uploaded progress summary", async () => {
  vi.spyOn(apiClient, "listProjects").mockResolvedValue([localProjectFixture]);
  render(<Providers><LocalProjectList /></Providers>);
  expect(await screen.findByRole("heading", { name: localProjectFixture.name })).toBeVisible();
  expect(screen.getByText("IN_PROGRESS")).toBeVisible();
  expect(screen.getByText("2")).toBeVisible();
  expect(screen.getByRole("link", { name: "Open project →" })).toHaveAttribute(
    "href",
    `/projects/${localProjectFixture.project_id}`,
  );
});

test("renders the empty project state", async () => {
  vi.spyOn(apiClient, "listProjects").mockResolvedValue([]);
  render(<Providers><LocalProjectList /></Providers>);
  expect(await screen.findByText("No local projects yet")).toBeVisible();
});

test("primary navigation contains no Hosted run or resume action", async () => {
  render(<AppShell><div>content</div></AppShell>);
  const navigation = screen.getByRole("navigation", { name: "Primary navigation" });
  expect(navigation).toHaveTextContent("Projects");
  expect(navigation).toHaveTextContent("Local guide");
  expect(navigation).not.toHaveTextContent(/run|resume|approval|hosted/i);
  await waitFor(() => expect(screen.getByText("content")).toBeVisible());
});
