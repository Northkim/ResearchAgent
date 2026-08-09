import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { ProjectCreateForm } from "@/components/project-create-form";
import { Providers } from "@/lib/providers";

import { localProjectFixture, workflowCatalogFixture } from "./fixtures";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

afterEach(() => {
  vi.restoreAllMocks();
  push.mockReset();
});

test("creates metadata-only Literature Search project from the form", async () => {
  const user = userEvent.setup();
  const create = vi.spyOn(apiClient, "createProject").mockResolvedValue({
    ...localProjectFixture,
    current_package: null,
    progress: null,
  });
  vi.spyOn(apiClient, "listWorkflowDefinitions").mockResolvedValue(workflowCatalogFixture);
  render(<Providers><ProjectCreateForm /></Providers>);
  await user.type(screen.getByRole("textbox", { name: /^Project name/ }), localProjectFixture.name);
  await user.type(
    screen.getByRole("textbox", { name: /^Fictional or public research topic/ }),
    localProjectFixture.research_topic,
  );
  expect(screen.getByRole("radio", { name: /Literature Search only/ })).toBeChecked();
  await user.click(screen.getByRole("button", { name: "Create project" }));
  expect(create).toHaveBeenCalledWith({
    name: localProjectFixture.name,
    research_topic: localProjectFixture.research_topic,
    selected_workflow: "LITERATURE_SEARCH",
    workflow_setup: "literature-only",
    custom_workflow_definition_ids: [],
  });
  expect(push).toHaveBeenCalledWith(`/projects/${localProjectFixture.project_id}`);
});

test("discloses scaffold cores before creating the full research preset", async () => {
  const user = userEvent.setup();
  vi.spyOn(apiClient, "listWorkflowDefinitions").mockResolvedValue(workflowCatalogFixture);
  const create = vi.spyOn(apiClient, "createProject").mockResolvedValue(localProjectFixture);
  render(<Providers><ProjectCreateForm /></Providers>);
  await user.type(screen.getByRole("textbox", { name: /^Project name/ }), "Full product test");
  await user.type(screen.getByRole("textbox", { name: /^Fictional or public research topic/ }), "Public synthetic topic");
  await user.click(screen.getByRole("radio", { name: /Full Research Project/ }));
  expect(screen.getByText("Includes prototype cores")).toBeVisible();
  expect(screen.getByText(/No substantive manuscript/)).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Create project" }));
  expect(create).toHaveBeenCalledWith(expect.objectContaining({ workflow_setup: "full-research" }));
});
