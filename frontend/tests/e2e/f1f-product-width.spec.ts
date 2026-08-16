import { execFileSync } from "node:child_process";
import { mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { expect, test } from "@playwright/test";

import { requireIsolatedQualification } from "./qualification-safety";

type FixtureManifest = {
  project_id: string;
  project_name: string;
  instances: Record<string, string>;
};

type DesiredManifest = {
  workspace_id: string;
  manifest_revision: number;
  canonical_checksum: string;
  manifest: {
    workflow_instances: Array<Record<string, string>>;
  };
};

const checksumA = `sha256:${"a".repeat(64)}`;
const checksumB = `sha256:${"b".repeat(64)}`;

const viewports = [
  { width: 1440, height: 900 },
  { width: 1280, height: 800 },
] as const;

test.beforeAll(() => requireIsolatedQualification());

test("qualifies the FE-M task-first canonical journey", async ({ page, request }) => {
  const backend = process.env.REAGENT_E2E_BACKEND_URL!;
  const frontend = process.env.REAGENT_E2E_BASE_URL!;
  const repository = resolve(process.cwd(), "..");
  const temporary = mkdtempSync(join(tmpdir(), "reagent-fe-m-"));
  const manifestPath = join(temporary, "fixture.json");
  const screenshotRoot = resolve(repository, ".agent_read/tmp/fe-m-desktop-final-review");
  rmSync(screenshotRoot, { recursive: true, force: true });
  mkdirSync(screenshotRoot, { recursive: true });

  const supportingAttention = await request.post(`${backend}/projects`, {
    data: {
      name: "ResearchAgent architecture study",
      research_topic: "Evaluating a local-first scientific workflow system",
      selected_workflow: "LITERATURE_SEARCH",
      workflow_setup: "literature-only",
    },
  });
  expect(supportingAttention.ok()).toBe(true);
  const supportingReady = await request.post(`${backend}/projects`, {
    data: {
      name: "Maritime video monitoring",
      research_topic: "Latency-aware visual-language analysis for live streams",
      selected_workflow: "LITERATURE_SEARCH",
      workflow_setup: "literature-only",
    },
  });
  expect(supportingReady.ok()).toBe(true);
  const supportingReadyProject = await supportingReady.json() as { project_id: string };

  try {
    execFileSync("conda", [
      "run", "--no-capture-output", "-n", "reagent-dev", "python", "-m",
      "scripts.b0_controlled_fixtures",
      "--api-url", backend,
      "--run-id", crypto.randomUUID().replaceAll("-", ""),
      "--manifest", manifestPath,
      "--project-name", "Urban drainage control study",
      "--research-topic", "Stress-testing multi-agent control under unseen storms",
      "--scenario", "fe-m-desktop",
    ], { cwd: repository, env: process.env, stdio: "pipe" });
    const fixture = JSON.parse(readFileSync(manifestPath, "utf8")) as FixtureManifest;
    const response = await request.get(`${backend}/projects/${fixture.project_id}/progress`);
    expect(response.ok()).toBe(true);
    const progress = await response.json() as { instances: Array<Record<string, unknown>> };
    const state = (workflow: string) => progress.instances.find(
      (item) => item.workflow_instance_id === fixture.instances[workflow],
    )!;
    expect(state("literature-search-local-experimental")).toMatchObject({
      research_status: "COMPLETED",
      installation_state: "ACKNOWLEDGED_STALE",
      action: { attention_state: "ATTENTION_REQUIRED", latest_output: { state: "PRODUCED" } },
    });
    expect(state("idea-discovery-local-experimental")).toMatchObject({
      research_status: "COMPLETED",
      action: { attention_state: "ATTENTION_REQUIRED", latest_output: { state: "PRODUCED" } },
    });
    expect(state("writing-local-experimental")).toMatchObject({
      research_status: "BLOCKED", action: { attention_state: "ATTENTION_REQUIRED" },
    });
    expect(state("review-local-experimental")).toMatchObject({ installation_state: "ACKNOWLEDGED_STALE" });

    const acknowledgeCurrent = async (projectId: string) => {
      const desiredResponse = await request.get(`${backend}/projects/${projectId}/manifest`);
      expect(desiredResponse.ok()).toBe(true);
      const desired = await desiredResponse.json() as DesiredManifest;
      const pinKeys = [
        "workflow_instance_id", "workflow_definition_id", "workflow_definition_version",
        "capsule_id", "capsule_version", "capsule_definition_checksum",
      ];
      const acknowledgement = await request.post(
        `${backend}/projects/${projectId}/workspace/sync-ack`,
        { data: {
          schema_version: "reagent.capsule-installation-ack/v0.1",
          installation_id: `install-${crypto.randomUUID().replaceAll("-", "")}`,
          project_id: projectId,
          workspace_id: desired.workspace_id,
          manifest_revision: desired.manifest_revision,
          manifest_checksum: desired.canonical_checksum,
          plan_checksum: checksumA,
          installed_lock_schema: "reagent.workspace-installed-lock/v0.1",
          installed_lock_checksum: checksumB,
          idempotency_key: crypto.randomUUID(),
          installed_capsules: desired.manifest.workflow_instances
            .filter((item) => item.desired_state === "ACTIVE")
            .map((item) => Object.fromEntries(pinKeys.map((key) => [key, item[key]]))),
          installed_at: new Date().toISOString(),
        } },
      );
      expect(acknowledgement.ok()).toBe(true);
    };

    // The fixture deliberately creates an acknowledged-stale installation. Exercise that
    // state first, then restore the supported public sync acknowledgement so the same
    // controlled journey can also review the underlying blocked and Owner-action states.
    await acknowledgeCurrent(fixture.project_id);
    await acknowledgeCurrent(supportingReadyProject.project_id);
    const synchronizedResponse = await request.get(`${backend}/projects/${fixture.project_id}/progress`);
    expect(synchronizedResponse.ok()).toBe(true);
    const synchronized = await synchronizedResponse.json() as { instances: Array<Record<string, unknown>> };
    const synchronizedState = (workflow: string) => synchronized.instances.find(
      (item) => item.workflow_instance_id === fixture.instances[workflow],
    )!;
    expect(synchronizedState("literature-search-local-experimental")).toMatchObject({
      research_status: "COMPLETED", action: { attention_state: "COMPLETED" },
    });
    expect(synchronizedState("idea-discovery-local-experimental")).toMatchObject({
      research_status: "COMPLETED", action: { attention_state: "COMPLETED" },
    });
    expect(synchronizedState("writing-local-experimental")).toMatchObject({
      research_status: "BLOCKED", action: { attention_state: "OWNER_ACTION_REQUIRED", actor: "OWNER" },
    });

    const pageErrors: string[] = [];
    const externalRequests: string[] = [];
    const browserWorkspaceWrites: string[] = [];
    const allowedPorts = new Set([new URL(frontend).port, new URL(backend).port]);
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("request", (event) => {
      const url = new URL(event.url());
      if (!["data:", "blob:", "about:"].includes(url.protocol)) {
        const allowed = ["http:", "https:", "ws:", "wss:"].includes(url.protocol)
          && ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname)
          && allowedPorts.has(url.port);
        if (!allowed) externalRequests.push(event.url());
      }
      if (!["GET", "HEAD", "OPTIONS"].includes(event.method()) && /\/workspace(?:\/|$)/.test(url.pathname)) {
        browserWorkspaceWrites.push(`${event.method()} ${url.pathname}`);
      }
    });

    const assertSafeViewport = async () => {
      await expect(page.locator('[role="alert"]:not(#__next-route-announcer__)')).toHaveCount(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
      expect(pageErrors).toEqual([]);
      expect(externalRequests).toEqual([]);
      expect(browserWorkspaceWrites).toEqual([]);
    };

    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.goto("/projects");
      const projectRow = page.locator("article.project-work-row").filter({ hasText: fixture.project_name });
      await expect(projectRow).toBeVisible();
      await expect(page.getByRole("heading", { name: "Needs your attention" })).toBeVisible();
      await expect(projectRow.getByText("Review the writing outline", { exact: true })).toBeVisible();
      await expect(projectRow.getByText("Needs your review", { exact: true })).toBeVisible();
      await expect(projectRow.getByText("The evidence map and outline are ready.", { exact: true })).toBeVisible();
      await expect(projectRow.getByRole("link", { name: /Review outline/ })).toBeVisible();
      await expect(projectRow.getByText(/UTC/)).toHaveCount(0);
      await expect(page.getByText("Maritime video monitoring")).toBeVisible();
      await expect(page.getByText(/Owner acts now|Continue at owner checkpoint|Cloud has not received acknowledgement|B0 controlled|F1F browser/i)).toHaveCount(0);
      await assertSafeViewport();
      if (viewport.width === 1440) await page.screenshot({ path: join(screenshotRoot, "projects__1440x900.png"), fullPage: false });

      await projectRow.getByRole("link", { name: fixture.project_name }).click();
      await expect(page.getByRole("heading", { name: fixture.project_name })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Review the writing outline" })).toBeVisible();
      await expect(page.getByText("The evidence map and six-section outline are ready.", { exact: true })).toBeVisible();
      await expect(page.getByRole("link", { name: "Review outline" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Workflow progress" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Latest output" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Recent activity" })).toBeVisible();
      const workflowProgress = page.locator(".overview-workflow-list");
      await expect(workflowProgress.locator("div").filter({ hasText: "Literature Search" }).first().getByText("Completed", { exact: true })).toBeVisible();
      await expect(workflowProgress.locator("div").filter({ hasText: "Idea Discovery" }).first().getByText("Completed", { exact: true })).toBeVisible();
      await expect(workflowProgress.locator("div").filter({ hasText: "Writing" }).first().getByText("Needs your review", { exact: true })).toBeVisible();
      await expect(workflowProgress.getByText("Blocked", { exact: true })).toHaveCount(0);
      await expect(page.locator("#outputs").getByText("Selected research idea", { exact: true })).toBeVisible();
      await expect(page.getByText(/UTC/)).toHaveCount(0);
      await expect(page.locator("h1")).not.toContainText(fixture.project_id);
      await expect(page.getByText(/Owner acts now|Continue at owner checkpoint|Current research state/i)).toHaveCount(0);
      await assertSafeViewport();
      if (viewport.width === 1440) await page.screenshot({ path: join(screenshotRoot, "overview__1440x900.png"), fullPage: false });

      await page.goto(`/projects/${fixture.project_id}/workflows/${fixture.instances["writing-local-experimental"]}`);
      await expect(page.getByRole("heading", { name: "Writing", exact: true })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Review the writing outline" })).toBeVisible();
      await expect(page.getByRole("link", { name: "Review outline" })).toBeVisible();
      await expect(page.locator(".current-action-meta").getByText("Outline approval", { exact: true })).toBeVisible();
      const inputs = page.locator("#inputs");
      const inputRows = inputs.locator(".input-readiness-list > div");
      await expect(inputRows.filter({ hasText: "Selected literature" }).getByText("Ready", { exact: true })).toBeVisible();
      await expect(inputRows.filter({ hasText: "Selected research idea" }).getByText("Ready", { exact: true })).toBeVisible();
      await expect(inputRows.filter({ hasText: "Experiment result" }).getByText("Optional · Not provided", { exact: true })).toBeVisible();
      await expect(inputs.getByText("Missing", { exact: true })).toHaveCount(0);
      await expect(page.locator("details#run-locally")).not.toHaveAttribute("open");
      await expect(page.getByText("Technical Details").locator(".." )).not.toHaveAttribute("open");
      await expect(page.getByText(/Owner acts now|Continue at owner checkpoint|Run the exact public command locally|placeholder research core|Artifact flow/i)).toHaveCount(0);
      await assertSafeViewport();
      if (viewport.width === 1440) await page.screenshot({ path: join(screenshotRoot, "workflow__1440x900.png"), fullPage: false });
    }

    await page.goto(`/projects/${fixture.project_id}/workflows`);
    const workflowRows = page.locator("article.workflow-work-row");
    await expect(workflowRows).toHaveCount(4);
    await expect(workflowRows.filter({ hasText: "Idea Discovery" }).getByText("Blocked", { exact: true })).toHaveCount(0);
    await page.goto(`/projects/${fixture.project_id}/outputs`);
    await expect(page.getByRole("heading", { name: "Selected paper library" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Selected research idea" })).toBeVisible();
    await expect(page.locator("details").filter({ hasText: "Technical Details" }).first()).not.toHaveAttribute("open");
    await page.goto(`/projects/${fixture.project_id}/progress`);
    await expect(page.getByRole("heading", { name: `${fixture.project_name} Activity` })).toBeVisible();
    await assertSafeViewport();
    expect(readFileSync(join(screenshotRoot, "projects__1440x900.png"))).not.toHaveLength(0);
    expect(readFileSync(join(screenshotRoot, "overview__1440x900.png"))).not.toHaveLength(0);
    expect(readFileSync(join(screenshotRoot, "workflow__1440x900.png"))).not.toHaveLength(0);
    expect(readdirSync(screenshotRoot).sort()).toEqual([
      "overview__1440x900.png", "projects__1440x900.png", "workflow__1440x900.png",
    ]);

    // Preserve the isolated-runner cleanup markers after Owner screenshots are complete.
    for (const [name, researchTopic] of [
      ["F1F browser product width", "Controlled FE-M isolation marker"],
      ["H1 controlled product journey", "Controlled E2E isolation marker"],
    ]) {
      const marker = await request.post(`${backend}/projects`, { data: {
        name, research_topic: researchTopic, selected_workflow: "LITERATURE_SEARCH",
        workflow_setup: "literature-only",
      } });
      expect(marker.ok()).toBe(true);
    }
  } finally {
    rmSync(temporary, { recursive: true, force: true });
  }
});
