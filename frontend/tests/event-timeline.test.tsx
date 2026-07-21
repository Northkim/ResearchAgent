import { render, screen } from "@testing-library/react";

import { EventTimeline } from "@/components/event-timeline";

import { eventsFixture } from "./fixtures";

test("renders execution events in their supplied sequence", () => {
  render(<EventTimeline events={eventsFixture} />);

  const timeline = screen.getByRole("list", { name: "Execution timeline" });
  expect(timeline).toHaveTextContent("workflow started");
  expect(timeline).toHaveTextContent("step started");
  expect(screen.getByText("#01")).toBeVisible();
  expect(screen.getByText("#02")).toBeVisible();
});
