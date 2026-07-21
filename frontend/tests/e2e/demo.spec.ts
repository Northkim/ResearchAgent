import { expect, test } from "@playwright/test";

const WORKFLOW_NAME = "Guided literature review";
const QUERY = "persistent research agents";
const EXPECTED_SUMMARY =
  "Mock summary: Mock Foundations of persistent research agents; Mock Advances in persistent research agents";

test("completes and reloads the supervised literature demo", async ({ page }, testInfo) => {
  await page.goto("/workflows");
  await expect(page.getByRole("heading", { name: WORKFLOW_NAME })).toBeVisible();

  const workflow = page.getByRole("group", {
    name: `${WORKFLOW_NAME} version 1.0.0`,
  });
  await workflow.getByRole("button", { name: "Select workflow" }).click();

  const queryInput = page.getByRole("textbox", { name: /query/i });
  await expect(queryInput).toHaveValue(QUERY);
  await queryInput.fill(QUERY);

  await testInfo.attach("workflow-catalog-ready", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });

  const createButton = page.getByRole("button", {
    name: "Create & execute run",
  });
  await createButton.click();
  await expect(page).toHaveURL(/\/runs\/[^/]+$/);

  const runUrl = page.url();
  const runStatus = page.getByRole("region", { name: "guided literature review" });
  await expect(runStatus.getByText("waiting for approval", { exact: true })).toBeVisible();
  await expect(page.getByText("search", { exact: true })).toBeVisible();
  await expect(page.getByText("approve sources", { exact: true })).toBeVisible();

  await testInfo.attach("run-waiting-for-approval", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });

  await page.getByRole("link", { name: "Review approval" }).click();
  await expect(page).toHaveURL(/\/approvals$/);
  await expect(
    page.getByRole("heading", {
      name: "Approval required for workflow step approve_sources",
    }),
  ).toBeVisible();
  await page.getByRole("textbox", { name: /decision note/i }).fill(
    "Deterministic sources reviewed for the demo.",
  );
  await testInfo.attach("approval-center-pending", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
  await page.getByRole("button", { name: "Approve & continue" }).click();
  await expect(page.getByRole("status")).toContainText("completed");

  await page.goto(runUrl);
  await expect(runStatus.getByText("completed", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Research output" })).toBeVisible();
  await expect(page.getByText(EXPECTED_SUMMARY, { exact: true })).toBeVisible();

  const timeline = page.getByRole("list", { name: "Execution timeline" });
  const entries = (await timeline.getByRole("listitem").allTextContents()).map((value) =>
    value.replace(/\s+/g, " ").trim(),
  );
  const sequences = entries.map((entry) => Number(entry.match(/#(\d+)/)?.[1]));
  expect(sequences).toEqual(entries.map((_, index) => index + 1));

  const requiredEvents = [
    /workflow started/i,
    /step started.*step search/i,
    /skill executed.*step search/i,
    /approval requested.*step approve sources/i,
    /step started.*step summarize/i,
    /skill executed.*step summarize/i,
    /workflow completed/i,
  ];
  let previousIndex = -1;
  for (const eventPattern of requiredEvents) {
    const currentIndex = entries.findIndex(
      (entry, index) => index > previousIndex && eventPattern.test(entry),
    );
    expect(currentIndex).toBeGreaterThan(previousIndex);
    previousIndex = currentIndex;
  }

  await page.reload();
  await expect(runStatus.getByText("completed", { exact: true })).toBeVisible();
  await expect(page.getByText(EXPECTED_SUMMARY, { exact: true })).toBeVisible();

  const completedScreenshot = await page.screenshot({ fullPage: true });
  await testInfo.attach("completed-persisted-run", {
    body: completedScreenshot,
    contentType: "image/png",
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Keep every research run legible." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);
  await testInfo.attach("mobile-dashboard", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
});
