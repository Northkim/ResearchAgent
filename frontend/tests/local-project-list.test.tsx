import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { LocalProjectList } from "@/components/local-project-list";
import { AppShell } from "@/components/app-shell";
import { Providers } from "@/lib/providers";

import { localProjectFixture } from "./fixtures";

afterEach(() => vi.restoreAllMocks());

test("renders task-first Projects with backend-derived attention and next action", async () => {
  vi.spyOn(apiClient, "listProjects").mockResolvedValue([localProjectFixture]);
  render(<Providers><LocalProjectList /></Providers>);
  expect(await screen.findByRole("heading", { name: localProjectFixture.name })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Needs your attention" })).toBeVisible();
  expect(screen.getByText("Needs your review")).toBeVisible();
  expect(screen.getByText("Review the selected papers")).toBeVisible();
  expect(screen.queryByText("OWNER ACTION REQUIRED")).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: "View selected papers →" })).toHaveAttribute(
    "href",
    `/projects/${localProjectFixture.project_id}/outputs`,
  );
});

test("groups non-attention results under Other projects without a misleading All projects section", async () => {
  const otherProject = {
    ...localProjectFixture,
    project_id: `project-${"9".repeat(32)}`,
    name: "Other fictional project",
    attention: {
      ...localProjectFixture.attention,
      action: {
        ...localProjectFixture.attention.action,
        attention_state: "NORMAL" as const,
      },
    },
  };
  vi.spyOn(apiClient, "listProjects").mockResolvedValue([localProjectFixture, otherProject]);
  render(<Providers><LocalProjectList /></Providers>);

  expect(await screen.findByRole("heading", { name: "Needs your attention" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Other projects" })).toBeVisible();
  expect(screen.queryByRole("heading", { name: "All projects" })).not.toBeInTheDocument();
  expect(screen.getByRole("option", { name: "All projects" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: localProjectFixture.name })).toBeVisible();
  expect(screen.getByRole("heading", { name: otherProject.name })).toBeVisible();
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
