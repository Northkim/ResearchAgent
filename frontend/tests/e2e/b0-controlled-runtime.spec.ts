import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
type FixtureManifest = { run_id: string; project_id: string; project_name: string; instances: Record<string, string> };
const viewports = [{ width: 1440, height: 900 }, { width: 1280, height: 800 }, { width: 390, height: 844 }] as const;
function fixtures(): FixtureManifest {
  const path = process.env.REAGENT_B0_FIXTURE_MANIFEST;
  if (!path) throw new Error("REAGENT_B0_FIXTURE_MANIFEST is required"); return JSON.parse(readFileSync(path, "utf8")) as FixtureManifest;
}
test("qualifies the controlled browser surface at all B0 viewports", async ({ page, request }) => {
  const fixture = fixtures();
  const backend = process.env.REAGENT_E2E_BACKEND_URL!, frontend = process.env.REAGENT_E2E_BASE_URL!;
  const screenshotRoot = process.env.REAGENT_B0_SCREENSHOT_DIR!, launchMarker = process.env.REAGENT_B0_BROWSER_LAUNCH_MARKER!;
  const pageErrors: string[] = [], externalRequests: string[] = [];
  const allowedPorts = new Set([new URL(frontend).port, new URL(backend).port]);
  const loopbackHosts = new Set(["127.0.0.1", "localhost", "[::1]"]);
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (requestEvent) => {
    const url = new URL(requestEvent.url());
    if (["data:", "blob:", "about:"].includes(url.protocol)) return;
    if (!(["http:", "https:", "ws:", "wss:"].includes(url.protocol) && loopbackHosts.has(url.hostname) && allowedPorts.has(url.port))) externalRequests.push(requestEvent.url());
  });
  const assertBrowserSafe = async () => {
    await expect(page.locator('[role="alert"]:not(#__next-route-announcer__)')).toHaveCount(0);
    expect(pageErrors, "unexpected pageerror").toEqual([]); expect(externalRequests, "unexpected non-loopback browser request").toEqual([]);
  };
  writeFileSync(launchMarker, `run_id=${fixture.run_id}\n`, { mode: 0o600 });
  const response = await request.get(`${backend}/projects/${fixture.project_id}/progress`); expect(response.ok()).toBe(true);
  const progress = await response.json();
  expect(progress.project_name).toBe(fixture.project_name);
  const byId = new Map(progress.instances.map((item: { workflow_instance_id: string }) => [item.workflow_instance_id, item]));
  const state = (workflow: string) => byId.get(fixture.instances[workflow]) as Record<string, unknown>;
  expect(state("literature-search-local-experimental")).toMatchObject({ research_status: "COMPLETED", result_count: 1 }); expect(state("idea-discovery-local-experimental")).toMatchObject({ research_status: "BLOCKED" });
  expect(state("writing-local-experimental")).toMatchObject({ research_status: "BLOCKED" }); expect(state("review-local-experimental")).toMatchObject({ installation_state: "ACKNOWLEDGED_STALE" });
  for (const viewport of viewports) {
    await page.setViewportSize(viewport); await page.goto(`/projects/${fixture.project_id}/workflows`);
    await expect(page.getByRole("heading", { name: `${fixture.project_name} workflows` })).toBeVisible();
    const board = page.getByRole("region", { name: "Workflow progression" });
    const row = (name: string) => board.locator("article.workflow-work-row").filter({ hasText: name });
    await expect(row("Literature Search").getByText("Literature Search completed", { exact: true })).toBeVisible(); await expect(row("Idea Discovery").getByText(/Blocked until an exact controlled input/)).toBeVisible();
    await expect(row("Initial Writing").getByText(/Awaiting owner action/)).toBeVisible(); await expect(board.getByText("1 retired Workflow · history", { exact: true })).toBeVisible(); await assertBrowserSafe();
    await page.screenshot({ path: join(screenshotRoot, `projects-workflows__${viewport.width}x${viewport.height}__controlled-states__fold.png`), fullPage: false });
    await assertBrowserSafe();
  }
  await assertBrowserSafe();
});
