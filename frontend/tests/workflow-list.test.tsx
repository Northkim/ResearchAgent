import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { WorkflowList } from "@/components/workflow-list";

import { workflowFixture } from "./fixtures";

test("renders workflows and lets the user select one", async () => {
  const user = userEvent.setup();
  const onSelect = vi.fn();

  render(<WorkflowList workflows={[workflowFixture]} onSelect={onSelect} />);

  expect(screen.getByRole("heading", { name: "Literature review" })).toBeVisible();
  expect(screen.getByText("2 stages · 1 input")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Select workflow" }));
  expect(onSelect).toHaveBeenCalledWith(workflowFixture);
});
