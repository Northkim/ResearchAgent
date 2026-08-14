import { readFileSync, writeFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

import { requireIsolatedQualification } from "./qualification-safety";

type FixtureManifest = {
  project_id: string;
  instances: Record<string, string>;
};

function fixtures(): FixtureManifest {
  const path = process.env.REAGENT_B0_FIXTURE_MANIFEST;
  if (!path) throw new Error("REAGENT_B0_FIXTURE_MANIFEST is required");
  return JSON.parse(readFileSync(path, "utf8")) as FixtureManifest;
}

test.beforeAll(() => requireIsolatedQualification());

test("qualifies durable controlled states and screenshot capture", async ({ page, request }, testInfo) => {
  const fixture = fixtures();
  const backend = process.env.REAGENT_E2E_BACKEND_URL!;
  const response = await request.get(`${backend}/projects/${fixture.project_id}/progress`);
  expect(response.ok()).toBe(true);
  const progress = await response.json();
  const byId = new Map(progress.instances.map((item: { workflow_instance_id: string }) => [item.workflow_instance_id, item]));
  const state = (workflow: string) => byId.get(fixture.instances[workflow]) as Record<string, unknown>;

  expect(state("literature-search-local-experimental")).toMatchObject({ research_status: "COMPLETED" });
  expect(state("writing-local-experimental")).toMatchObject({
    research_status: "BLOCKED",
  });
  expect(state("writing-local-experimental").bound_required_inputs).toEqual(
    expect.arrayContaining(["literature_library", "research_idea"]),
  );
  expect(state("reproduction-experiment-local-experimental")).toMatchObject({
    research_status: "BLOCKED",
    bound_required_inputs: [],
    missing_required_inputs: ["research_idea"],
  });
  expect(state("review-local-experimental")).toMatchObject({
    installation_state: "ACKNOWLEDGED_STALE",
  });

  await page.goto(`/projects/${fixture.project_id}/workflows`);
  const current = page.locator("section").filter({
    has: page.getByRole("heading", { name: "Your Project workflows" }),
  });
  const card = (workflow: string) => current.locator("article.workflow-card").filter({
    hasText: fixture.instances[workflow],
  });
  await expect(card("literature-search-local-experimental").getByText("Completed", { exact: true })).toBeVisible();
  await expect(card("writing-local-experimental").getByText("Needs attention", { exact: true })).toBeVisible();
  await expect(card("writing-local-experimental").getByText(/Awaiting owner confirmation/)).toBeVisible();
  await expect(card("reproduction-experiment-local-experimental").getByText(/no experiment ran/)).toBeVisible();
  await expect(card("review-local-experimental").getByText("Installed · sync needed", { exact: true })).toBeVisible();

  const desktop = await page.screenshot({ fullPage: true });
  expect(desktop.byteLength).toBeGreaterThan(1_000);
  await testInfo.attach("b0-desktop-workflow-board", { body: desktop, contentType: "image/png" });
  await page.setViewportSize({ width: 390, height: 844 });
  const mobile = await page.screenshot({ fullPage: true });
  expect(mobile.byteLength).toBeGreaterThan(1_000);
  await testInfo.attach("b0-mobile-workflow-board", { body: mobile, contentType: "image/png" });
  writeFileSync(process.env.REAGENT_B0_SCREENSHOT_MARKER!, "PASS\n", { mode: 0o600 });
});

test("qualifies loading, empty, API-error, and not-found surfaces", async ({ page }) => {
  await page.route("**/backend/projects", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 2_000));
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.goto("/projects");
  await expect(page.getByText("Loading local projects…", { exact: true })).toBeVisible();
  await expect(page.getByText("No local projects yet", { exact: true })).toBeVisible();

  await page.unroute("**/backend/projects");
  await page.route("**/backend/projects", (route) => route.fulfill({ status: 503, body: "{}" }));
  await page.reload();
  await expect(page.getByRole("alert").getByText("Could not reach the ReAgent API")).toBeVisible();

  await page.goto("/b0-controlled-route-that-does-not-exist");
  await expect(page.getByText(/page could not be found/i)).toBeVisible();
});
