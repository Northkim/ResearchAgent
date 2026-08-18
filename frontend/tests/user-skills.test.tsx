import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, test, vi } from "vitest";

import { apiClient, type UserSkill } from "@/api/client";
import SkillsPage from "@/app/skills/page";

const skill: UserSkill = {
  skill_id: `skill-${"1".repeat(32)}`,
  name: "Academic Literature Review",
  slug: "academic-literature-review",
  description: "Review papers and extract grounded evidence.",
  source_locator: "https://github.com/example/sample-research-skill",
  source_revision: "a".repeat(40),
  source_checksum: `sha256:${"b".repeat(64)}`,
  usage_count: 2,
  local_status: null,
};

afterEach(() => {
  window.history.replaceState({}, "", "/");
  vi.restoreAllMocks();
});

test("keeps the global Skill library and Add form small", async () => {
  vi.spyOn(apiClient, "listUserSkills").mockResolvedValue({ items: [], total: 0 });
  const create = vi.spyOn(apiClient, "createUserSkill").mockResolvedValue(skill);
  render(<SkillsPage />);

  expect(await screen.findByText("No skills yet.")).toBeVisible();
  await userEvent.click(screen.getAllByRole("button", { name: "Add skill" })[0]);
  expect(screen.getByLabelText("Name")).toBeVisible();
  expect(screen.getByLabelText("What does it help with?")).toBeVisible();
  expect(screen.getByLabelText("GitHub URL")).toBeVisible();
  expect(screen.queryByText(/checksum|manifest|capsule/i)).not.toBeInTheDocument();

  await userEvent.type(screen.getByLabelText("Name"), skill.name);
  await userEvent.type(screen.getByLabelText("What does it help with?"), skill.description);
  await userEvent.type(screen.getByLabelText("GitHub URL"), skill.source_locator);
  vi.mocked(apiClient.listUserSkills).mockResolvedValue({ items: [skill], total: 1 });
  await userEvent.click(screen.getByRole("button", { name: "Add skill" }));
  await waitFor(() => expect(create).toHaveBeenCalledWith({
    name: skill.name,
    description: skill.description,
    source_locator: skill.source_locator,
  }));
  expect(await screen.findByText(skill.name)).toBeVisible();
  expect(screen.getByText("Used in 2 projects")).toBeVisible();
});

test("attaches exact Owner-selected Skills and shows sync state", async () => {
  window.history.replaceState({}, "", "/skills?project=project-1");
  vi.spyOn(apiClient, "listUserSkills").mockResolvedValue({ items: [skill], total: 1 });
  vi.spyOn(apiClient, "listProjectUserSkills")
    .mockResolvedValueOnce({ items: [], total: 0 })
    .mockResolvedValueOnce({ items: [], total: 0 })
    .mockResolvedValue({ items: [{ ...skill, local_status: "Needs sync" }], total: 1 });
  const attach = vi.spyOn(apiClient, "attachProjectUserSkill")
    .mockResolvedValue({ ...skill, local_status: "Needs sync" });
  render(<SkillsPage />);

  const choice = await screen.findByRole("checkbox", { name: /Academic Literature Review/ });
  expect(choice).not.toBeChecked();
  await userEvent.click(choice);
  await userEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(attach).toHaveBeenCalledWith("project-1", skill.skill_id));
  expect(await screen.findByText("Needs sync")).toBeVisible();
});

test("global navigation exposes one Skills destination", async () => {
  const { AppShell } = await import("@/components/app-shell");
  render(<AppShell><div>content</div></AppShell>);
  const navigation = screen.getByRole("navigation", { name: "Primary navigation" });
  expect(navigation).toContainElement(screen.getByRole("link", { name: /Skills/ }));
  expect(screen.getByRole("link", { name: /Skills/ })).toHaveAttribute("href", "/skills");
});
