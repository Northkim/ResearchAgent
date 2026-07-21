import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApprovalCard } from "@/components/approval-card";

import { approvalFixture } from "./fixtures";

test("submits approval and rejection interactions with the review note", async () => {
  const user = userEvent.setup();
  const onApprove = vi.fn();
  const onReject = vi.fn();

  render(
    <ApprovalCard
      approval={approvalFixture}
      onApprove={onApprove}
      onReject={onReject}
    />,
  );

  await user.type(screen.getByLabelText(/Decision note/i), "Sources are in scope");
  await user.click(screen.getByRole("button", { name: "Approve & continue" }));
  expect(onApprove).toHaveBeenCalledWith(approvalFixture, "Sources are in scope");

  await user.click(screen.getByRole("button", { name: "Reject & cancel" }));
  expect(onReject).toHaveBeenCalledWith(approvalFixture, "Sources are in scope");
});
