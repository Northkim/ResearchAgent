import { render, screen } from "@testing-library/react";

import { RunStatusPanel } from "@/components/run-status-panel";

import { runFixture } from "./fixtures";

test("renders aggregate run status and progress facts", () => {
  render(<RunStatusPanel run={runFixture} />);

  expect(screen.getByText("waiting for approval")).toBeVisible();
  expect(screen.getByText("1/2")).toBeVisible();
  expect(screen.getByText("5")).toBeVisible();
  expect(screen.getByText("Waiting reason: approval:approve_sources")).toBeVisible();
});

test("renders durable final output when a run is complete", () => {
  render(
    <RunStatusPanel
      run={{
        ...runFixture,
        status: "COMPLETED",
        outputs: { summary: "Mock summary: persisted research result" },
        wait_reason: null,
      }}
    />,
  );

  expect(screen.getByRole("heading", { name: "Research output" })).toBeVisible();
  expect(screen.getByText("Mock summary: persisted research result")).toBeVisible();
});
