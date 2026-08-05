import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, test, vi } from "vitest";

import { apiClient } from "@/api/client";
import { ProjectCreateForm } from "@/components/project-create-form";
import { Providers } from "@/lib/providers";

import { localProjectFixture } from "./fixtures";

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
  render(<Providers><ProjectCreateForm /></Providers>);
  await user.type(screen.getByRole("textbox", { name: /^Project name/ }), localProjectFixture.name);
  await user.type(
    screen.getByRole("textbox", { name: /^Fictional or public research topic/ }),
    localProjectFixture.research_topic,
  );
  expect(screen.getByRole("combobox", { name: /^Workflow/ })).toHaveValue("LITERATURE_SEARCH");
  await user.click(screen.getByRole("button", { name: "Create local project" }));
  expect(create).toHaveBeenCalledWith({
    name: localProjectFixture.name,
    research_topic: localProjectFixture.research_topic,
    selected_workflow: "LITERATURE_SEARCH",
  });
  expect(push).toHaveBeenCalledWith(`/projects/${localProjectFixture.project_id}`);
});
