import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, test, vi } from "vitest";

import { apiClient, type UserSkillDetail } from "@/api/client";
import SkillDetailPage from "@/app/skills/[id]/page";

const skillId = `skill-${"1".repeat(32)}`;
const push = vi.fn();
const refresh = vi.fn();
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: skillId }),
  useRouter: () => ({ push, refresh }),
}));

const detail: UserSkillDetail = {
  skill_id: skillId,
  name: "Academic Literature Review",
  slug: "academic-literature-review",
  description: "Review papers and extract grounded evidence.",
  source_locator: "https://github.com/example/sample-research-skill",
  source_revision: "a".repeat(40),
  source_checksum: `sha256:${"b".repeat(64)}`,
  usage_count: 1,
  local_status: null,
  projects: [{ project_id: `project-${"2".repeat(32)}`, name: "KNN Study" }],
};

afterEach(() => {
  vi.restoreAllMocks();
  push.mockReset();
  refresh.mockReset();
});

test("shows bounded provenance and blocks deleting an attached Skill", async () => {
  vi.spyOn(apiClient, "getUserSkill").mockResolvedValue(detail);
  const remove = vi.spyOn(apiClient, "deleteUserSkill").mockResolvedValue();
  render(<SkillDetailPage />);

  expect(await screen.findByRole("heading", { name: detail.name })).toBeVisible();
  expect(screen.getByRole("link", { name: "KNN Study" })).toHaveAttribute(
    "href", `/projects/${detail.projects[0].project_id}`,
  );
  expect(screen.getByRole("link", { name: /Open GitHub source/ })).toBeVisible();
  await userEvent.click(screen.getByText("Skill settings"));
  await userEvent.click(screen.getByRole("button", { name: "Delete skill" }));
  expect(screen.getByText(/Remove it from those Projects first/)).toBeVisible();
  expect(screen.getAllByRole("button", { name: "Delete skill" }).at(-1)).toBeDisabled();
  expect(remove).not.toHaveBeenCalled();
});

test("deletes an unattached Skill through the existing safe API", async () => {
  vi.spyOn(apiClient, "getUserSkill").mockResolvedValue({
    ...detail, usage_count: 0, projects: [],
  });
  const remove = vi.spyOn(apiClient, "deleteUserSkill").mockResolvedValue();
  render(<SkillDetailPage />);

  await screen.findByRole("heading", { name: detail.name });
  await userEvent.click(screen.getByText("Skill settings"));
  await userEvent.click(screen.getByRole("button", { name: "Delete skill" }));
  await userEvent.click(screen.getAllByRole("button", { name: "Delete skill" }).at(-1)!);
  expect(remove).toHaveBeenCalledWith(skillId);
  expect(push).toHaveBeenCalledWith("/skills");
});
