import { expect, test } from "@playwright/test";

import { requireIsolatedQualification } from "./qualification-safety";

test.beforeAll(() => requireIsolatedQualification());

test("exposes the complete product skeleton without hiding scaffold boundaries", async ({ page }) => {
  await page.goto("/projects/new");
  await expect(page.getByRole("radio", { name: /Literature Search only/ })).toBeVisible();
  await expect(page.getByRole("radio", { name: /Literature \+ Idea Discovery/ })).toBeVisible();
  await expect(page.getByRole("radio", { name: /Full Research Project/ })).toBeVisible();
  await expect(page.getByRole("radio", { name: /Custom/ })).toBeVisible();

  await page.getByRole("textbox", { name: /^Project name/ }).fill("F1F browser product width");
  await page.getByRole("textbox", { name: /^Fictional or public research topic/ }).fill(
    "Synthetic immutable cross-workflow continuity",
  );
  await page.getByRole("radio", { name: /Full Research Project/ }).check();
  await expect(page.getByText("Includes prototype cores")).toBeVisible();
  await expect(page.getByText(/No substantive manuscript, peer review, or experiment/)).toBeVisible();
  await page.getByRole("button", { name: "Create project" }).click();

  await expect(page).toHaveURL(/\/projects\/project-[0-9a-f]{32}$/);
  const projectId = page.url().split("/").at(-1)!;
  await expect(page.getByRole("heading", { name: "Your research workflows at a glance" })).toBeVisible();
  await expect(page.getByText("Local installation is shown separately")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Set up or sync your Local Workspace" })).toBeVisible();

  await page.goto(`/projects/${projectId}/workflows`);
  const current = page.locator("section").filter({
    has: page.getByRole("heading", { name: "Your Project workflows" }),
  });
  await expect(current.locator("article.workflow-card")).toHaveCount(5);
  for (const name of [
    "Literature Search", "Idea Discovery", "Writing", "Review",
    "Reproduction & Experiment",
  ]) {
    await expect(current.getByRole("heading", { name, exact: true })).toBeVisible();
  }
  await expect(current.getByText("Core · Scaffold")).toHaveCount(3);
  await expect(current.getByText(/Product flow is functional\. Research capability is placeholder\./)).toHaveCount(3);
  await expect(current.getByText(/Research Artifact Provenance 0\.1\.0/)).toHaveCount(3);
  await expect(current.getByText(/Scaffold Core Safety 0\.1\.0/)).toHaveCount(3);

  const experiment = current.locator("article.workflow-card").filter({
    has: page.getByRole("heading", { name: "Reproduction & Experiment", exact: true }),
  });
  await expect(experiment.getByText("External Resources · optional")).toBeVisible();
  await experiment.getByText("External Resources · optional").click();
  await expect(experiment.getByText(/Cloud stores only provider, locator, exact immutable revision/)).toBeVisible();
  await expect(experiment.getByText(/GitHub and Hugging Face network resolution is not implemented/)).toBeVisible();
  await expect(experiment.getByText(/Experiment remains runnable/)).toBeVisible();

  await page.goto(`/projects/${projectId}/progress`);
  await expect(page.getByLabel("Workflow Instance")).toBeVisible();
  await expect(page.getByLabel("Workflow Instance")).toHaveValue("");
  await expect(page.getByText("No Progress Report received")).toBeVisible();

  await page.goto(`/projects/${projectId}/help`);
  await expect(page.getByRole("heading", { name: "Writing, Review, and Experiment validate the flow—not the science" })).toBeVisible();
  await expect(page.getByText(/you never install Skills separately/)).toBeVisible();
  await expect(page.getByText(/Adding a reference never means it was downloaded/)).toBeVisible();
});
