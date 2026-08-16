import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import { CopyCommand } from "@/components/copy-command";

test("copies a visible command with an accessible control", async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });
  render(<CopyCommand command="python reagent_local.py sync ." label="local sync command" />);
  const copy = screen.getByRole("button", { name: "Copy local sync command" });
  expect(copy).toHaveClass("button-ghost");
  expect(copy).toBeEnabled();
  await userEvent.click(copy);
  expect(writeText).toHaveBeenCalledWith("python reagent_local.py sync .");
  expect(screen.getByRole("button", { name: "Copy local sync command" })).toHaveTextContent("Copied");
  expect(screen.getByRole("status")).toHaveTextContent("local sync command copied");
});
