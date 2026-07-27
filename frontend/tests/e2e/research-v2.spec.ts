import { expect, test } from "@playwright/test";

const WORKFLOW_NAME = "Guided Literature Review v2 (deterministic synthetic)";
const TOPIC = "persistent research agent auditability";

test("completes and reloads the full fake-provider research v2 path", async ({
  page,
}, testInfo) => {
  await page.goto("/workflows");
  const workflow = page.getByRole("group", {
    name: `${WORKFLOW_NAME} version 2.0.0`,
  });
  await expect(workflow).toBeVisible();
  await workflow.getByRole("button", { name: "Select workflow" }).click();

  await page.getByRole("textbox", { name: /topic/i }).fill(TOPIC);
  await expect(page.getByRole("spinbutton", { name: /year from/i })).toHaveValue("2020");
  await expect(page.getByRole("spinbutton", { name: /year to/i })).toHaveValue("2026");
  await expect(page.getByRole("spinbutton", { name: /max papers/i })).toHaveValue("3");
  await testInfo.attach("v2-workflow-input", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });

  await page.getByRole("button", { name: "Create & execute run" }).click();
  await expect(page).toHaveURL(/\/runs\/[^/]+$/);
  const runUrl = page.url();
  const runStatus = page.getByRole("region", {
    name: "guided literature review",
  });
  await expect(
    runStatus.getByText("waiting for approval", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Abstract-only synthetic demonstration")).toBeVisible();
  await expect(page.getByText("papers.json", { exact: true })).toBeVisible();
  await expect(page.getByText("selected_papers.json", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Review approval" }).click();
  const approvalCard = page.locator("article.approval-card").filter({
    has: page.locator(`a[href="${new URL(runUrl).pathname}"]`),
  });
  await expect(
    approvalCard.getByRole("heading", {
      name: "Review 3 selected synthetic papers",
    }),
  ).toBeVisible();
  await expect(
    approvalCard.getByText("abstract-only", { exact: true }).first(),
  ).toBeVisible();
  await expect(approvalCard.getByText("[P1]", { exact: true })).toBeVisible();
  await expect(approvalCard.getByText("[P2]", { exact: true })).toBeVisible();
  await expect(approvalCard.getByText("[P3]", { exact: true })).toBeVisible();
  await expect(
    approvalCard.getByText("Synthetic Research Fixtures").first(),
  ).toBeVisible();
  await testInfo.attach("v2-candidate-approval", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });

  await approvalCard.getByRole("textbox", { name: /decision note/i }).fill(
    "Exact synthetic candidate IDs and selected_papers.json checksum reviewed.",
  );
  await approvalCard.getByRole("button", { name: "Approve & continue" }).click();
  await expect(page.getByRole("status")).toContainText("completed");

  await page.goto(runUrl);
  await expect(runStatus.getByText("completed", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Grounded Markdown report" }),
  ).toBeVisible();
  const report = page.getByLabel("Generated Markdown report");
  await expect(report).toContainText(TOPIC);
  await expect(report).toContainText("[P1]");
  await expect(report).toContainText("[P2]");
  await expect(report).toContainText("[P3]");
  await expect(
    page.getByRole("heading", { name: "Citation references" }),
  ).toBeVisible();
  const citationLinks = page.getByRole("link", {
    name: "Open synthetic citation link",
  });
  await expect(citationLinks).toHaveCount(3);
  await expect(citationLinks.first()).toHaveAttribute(
    "href",
    /^https:\/\/example\.invalid\/papers\//,
  );
  await testInfo.attach("v2-completed-report", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });

  const artifacts = page.getByRole("list", { name: "Research artifacts" });
  await expect(artifacts.getByRole("listitem")).toHaveCount(8);
  await expect(artifacts.getByText("report.md", { exact: true })).toBeVisible();
  await expect(artifacts.getByText("provenance.json", { exact: true })).toBeVisible();
  await expect(artifacts.getByText("usage.json", { exact: true })).toBeVisible();
  await expect(page.getByText("0 USD minor units · all settled")).toBeVisible();
  await testInfo.attach("v2-artifact-provenance-ledger", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });

  const timeline = page.getByRole("list", { name: "Execution timeline" });
  await expect(timeline.getByText(/workflow completed/i)).toBeVisible();
  await expect(timeline.getByText(/approval requested/i)).toBeVisible();

  await page.reload();
  await expect(runStatus.getByText("completed", { exact: true })).toBeVisible();
  await expect(report).toContainText(TOPIC);
  await expect(artifacts.getByRole("listitem")).toHaveCount(8);
  await expect(page.getByText("0 USD minor units · all settled")).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(report).toContainText("[P3]");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    ),
  ).toBe(true);
});
